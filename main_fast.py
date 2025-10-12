#!/usr/bin/env python3
"""
FAST Eye Tracker - Based on main.py but with extreme optimizations
Target: 25-35 FPS
"""

from picamera2 import Picamera2
import cv2
import numpy as np
import time
import threading
import argparse
from PIL import Image, ImageDraw

# Import the GC9A01 display class
from test_gc9a01 import GC9A01

# Display dimensions
WIDTH = 240
HEIGHT = 240

class FastEyeTracker:
    def __init__(self, enable_preview=False):
        self.display = None
        self.camera = None
        self.running = False
        self.enable_preview = enable_preview
        
        # Eye tracking
        self.target_eye_position = (WIDTH//2, HEIGHT//2)
        self.current_eye_position = (WIDTH//2, HEIGHT//2)
        self.eye_movement_speed = 0.2  # Faster response
        
        # Performance
        self.frame_count = 0
        self.last_fps_time = time.time()
        
        # EXTREME resolution reduction
        self.camera_width = 160  # Was 640
        self.camera_height = 120  # Was 480
        
        # Motion detection
        self.prev_frame = None
        self.motion_threshold = 30
        
        # Eye cache
        self.eye_cache = {}
        self.cache_size = 10  # Smaller cache
        self.last_rendered_pos = None
        
        # Aggressive frame skipping
        self.motion_check_counter = 0
        self.motion_check_interval = 3  # Check every 3rd frame
        
        self.display_update_counter = 0
        self.display_update_interval = 1  # Update display every frame for smoothness
    
    def init_display(self):
        try:
            self.display = GC9A01()
            print("Display initialized!")
            return True
        except Exception as e:
            print(f"Display init failed: {e}")
            return False
    
    def init_camera(self):
        try:
            self.camera = Picamera2()
            # VERY LOW resolution for maximum speed
            config = self.camera.create_video_configuration(
                main={"size": (self.camera_width, self.camera_height), "format": "RGB888"},
                raw={"size": self.camera.sensor_resolution}  # Keep full FOV
            )
            self.camera.configure(config)
            self.camera.start()
            print(f"Camera: {self.camera_width}x{self.camera_height} (Full FOV)")
            return True
        except Exception as e:
            print(f"Camera init failed: {e}")
            return False
    
    def create_eye_image(self, eye_x, eye_y):
        """Create BIGGER eye with caching"""
        cache_key = (round(eye_x / 15) * 15, round(eye_y / 15) * 15)
        
        if cache_key in self.eye_cache:
            return self.eye_cache[cache_key]
        
        # Black background
        image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # BIGGER eye (2x size)
        iris_size = 120
        pupil_size = 60
        highlight_size = 30
        
        # Clamp position
        eye_x = max(iris_size//2, min(WIDTH - iris_size//2, eye_x))
        eye_y = max(iris_size//2, min(HEIGHT - iris_size//2, eye_y))
        
        # Draw iris
        iris_x = eye_x - iris_size//2
        iris_y = eye_y - iris_size//2
        draw.ellipse([iris_x, iris_y, iris_x + iris_size, iris_y + iris_size], 
                    fill=(200, 50, 25))
        
        # Draw pupil
        pupil_x = eye_x - pupil_size//2
        pupil_y = eye_y - pupil_size//2
        draw.ellipse([pupil_x, pupil_y, pupil_x + pupil_size, pupil_y + pupil_size], 
                    fill=(0, 0, 0))
        
        # Draw highlight
        highlight_x = eye_x - highlight_size//2 + 20
        highlight_y = eye_y - highlight_size//2 - 10
        draw.ellipse([highlight_x, highlight_y, highlight_x + highlight_size, highlight_y + highlight_size], 
                    fill=(255, 255, 255))
        
        # Cache it
        if len(self.eye_cache) >= self.cache_size:
            self.eye_cache.pop(next(iter(self.eye_cache)))
        self.eye_cache[cache_key] = image
        
        return image
    
    def detect_motion_simple(self, frame):
        """SIMPLIFIED motion detection - no blur, no dilation"""
        # Already small resolution, downsample to 80x60 for speed
        tiny = cv2.resize(frame, (80, 60), interpolation=cv2.INTER_NEAREST)
        
        # Convert to grayscale
        gray = cv2.cvtColor(tiny, cv2.COLOR_RGB2GRAY)
        
        if self.prev_frame is None:
            self.prev_frame = gray
            return None
        
        # Simple difference - NO BLUR (saves 5-10ms)
        frame_delta = cv2.absdiff(self.prev_frame, gray)
        _, thresh = cv2.threshold(frame_delta, self.motion_threshold, 255, cv2.THRESH_BINARY)
        
        self.prev_frame = gray
        
        # Use moments instead of contours (MUCH faster)
        moments = cv2.moments(thresh)
        
        if moments["m00"] > 30:  # Minimum area
            # Calculate centroid
            cx = int(moments["m10"] / moments["m00"])
            cy = int(moments["m01"] / moments["m00"])
            
            # Scale from 80x60 to 160x120 (2x)
            return [(cx * 2, cy * 2, 20, 20)]  # Fake bbox
        
        return []
    
    def update_eye_position(self, motion_boxes):
        """Update eye position"""
        if motion_boxes and len(motion_boxes) > 0:
            x, y, w, h = motion_boxes[0]
            motion_center_x = x + w//2
            motion_center_y = y + h//2
            
            # Normalize
            norm_x = (motion_center_x - self.camera_width//2) / (self.camera_width//2)
            norm_y = (motion_center_y - self.camera_height//2) / (self.camera_height//2)
            
            # Map to display (full range)
            eye_x = WIDTH//2 - norm_x * (WIDTH//2 - 10)
            eye_y = HEIGHT//2 + norm_y * (HEIGHT//2 - 10)
            
            self.target_eye_position = (eye_x, eye_y)
    
    def smooth_eye_movement(self):
        current_x, current_y = self.current_eye_position
        target_x, target_y = self.target_eye_position
        
        new_x = current_x + (target_x - current_x) * self.eye_movement_speed
        new_y = current_y + (target_y - current_y) * self.eye_movement_speed
        
        self.current_eye_position = (new_x, new_y)
    
    def update_fps(self):
        self.frame_count += 1
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            fps = self.frame_count / (current_time - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = current_time
            print(f"FPS: {fps:.1f}")
    
    def camera_thread(self):
        while self.running:
            try:
                frame = self.camera.capture_array()
                
                # Aggressive frame skipping
                self.motion_check_counter += 1
                if self.motion_check_counter >= self.motion_check_interval:
                    self.motion_check_counter = 0
                    motion_boxes = self.detect_motion_simple(frame)
                    if motion_boxes:
                        self.update_eye_position(motion_boxes)
                
                self.update_fps()
                
            except Exception as e:
                print(f"Camera error: {e}")
                time.sleep(0.1)
    
    def display_thread(self):
        while self.running:
            try:
                # Smooth movement
                self.smooth_eye_movement()
                
                # Update display every frame for smoothness
                eye_x, eye_y = self.current_eye_position
                eye_image = self.create_eye_image(int(eye_x), int(eye_y))
                self.display.image(eye_image)
                
                # 25 FPS target
                time.sleep(1.0/25.0)
                
            except Exception as e:
                print(f"Display error: {e}")
                time.sleep(0.1)
    
    def start(self):
        print("Starting FAST Eye Tracker...")
        print("=" * 50)
        
        if not self.init_display():
            return
        if not self.init_camera():
            return
        
        self.running = True
        
        cam_thread = threading.Thread(target=self.camera_thread, daemon=True)
        disp_thread = threading.Thread(target=self.display_thread, daemon=True)
        
        cam_thread.start()
        disp_thread.start()
        
        print("FAST mode running! Press Ctrl+C to stop.")
        print("=" * 50)
        
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            self.stop()
    
    def stop(self):
        self.running = False
        if self.display:
            self.display.close()
        if self.camera:
            self.camera.close()
        print("Stopped")


def main():
    parser = argparse.ArgumentParser(description='Fast Eye Tracker')
    parser.add_argument('--preview', action='store_true', help='Enable preview (slower)')
    args = parser.parse_args()
    
    tracker = FastEyeTracker(enable_preview=args.preview)
    tracker.start()

if __name__ == "__main__":
    main()

