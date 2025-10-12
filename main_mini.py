#!/usr/bin/env python3
"""
Ultra-lightweight eye tracker for maximum performance
Uses brightness centroid detection instead of OpenCV
Target: 30+ FPS on Raspberry Pi
"""

from picamera2 import Picamera2
import numpy as np
import time
import RPi.GPIO as GPIO
import spidev
from PIL import Image, ImageDraw
import threading
import cv2
import queue

# Import the GC9A01 display class
from test_gc9a01 import GC9A01

# Display configuration
WIDTH = 240
HEIGHT = 240

class MiniEyeTracker:
    def __init__(self):
        self.display = None
        self.camera = None
        self.running = False
        
        # Eye tracking
        self.target_eye_position = (WIDTH//2, HEIGHT//2)
        self.current_eye_position = (WIDTH//2, HEIGHT//2)
        self.eye_movement_speed = 0.2
        
        # Performance monitoring
        self.frame_count = 0
        self.last_fps_time = time.time()
        
        # Camera settings - VERY LOW RESOLUTION for speed
        self.camera_width = 160
        self.camera_height = 120
        
        # Brightness threshold for motion detection (lowered for better detection)
        self.brightness_threshold = 30
        
        # Pre-rendered eye cache
        self.eye_cache = {}
        self.last_rendered_pos = None
        
        # Frame queue for preview
        self.frame_queue = queue.Queue(maxsize=1)
        
        # Debug info
        self.last_centroid = None
        
    def init_display(self):
        """Initialize the GC9A01 display"""
        try:
            self.display = GC9A01()
            print("Display initialized!")
            return True
        except Exception as e:
            print(f"Display init failed: {e}")
            return False
    
    def init_camera(self):
        """Initialize camera at very low resolution"""
        try:
            self.camera = Picamera2()
            config = self.camera.create_video_configuration(
                main={"size": (self.camera_width, self.camera_height), "format": "RGB888"},
                raw={"size": self.camera.sensor_resolution}
            )
            self.camera.configure(config)
            self.camera.start()
            print(f"Camera initialized at {self.camera_width}x{self.camera_height}")
            return True
        except Exception as e:
            print(f"Camera init failed: {e}")
            return False
    
    def create_eye_image(self, eye_x, eye_y):
        """Create simplified eye image with caching"""
        # Cache key (rounded to 10px)
        cache_key = (round(eye_x / 10) * 10, round(eye_y / 10) * 10)
        
        if cache_key in self.eye_cache:
            return self.eye_cache[cache_key]
        
        # Create black background
        image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Clamp position
        eye_x = max(40, min(WIDTH - 40, eye_x))
        eye_y = max(40, min(HEIGHT - 40, eye_y))
        
        # Draw simplified eye (just 3 circles - fast!)
        # Iris
        iris_size = 60
        iris_x = eye_x - iris_size//2
        iris_y = eye_y - iris_size//2
        draw.ellipse([iris_x, iris_y, iris_x + iris_size, iris_y + iris_size], 
                    fill=(200, 50, 25))
        
        # Pupil
        pupil_size = 30
        pupil_x = eye_x - pupil_size//2
        pupil_y = eye_y - pupil_size//2
        draw.ellipse([pupil_x, pupil_y, pupil_x + pupil_size, pupil_y + pupil_size], 
                    fill=(0, 0, 0))
        
        # Highlight
        highlight_size = 12
        highlight_x = eye_x - highlight_size//2 + 8
        highlight_y = eye_y - highlight_size//2 - 5
        draw.ellipse([highlight_x, highlight_y, highlight_x + highlight_size, highlight_y + highlight_size], 
                    fill=(255, 255, 255))
        
        # Cache it (limit cache size)
        if len(self.eye_cache) >= 15:
            self.eye_cache.pop(next(iter(self.eye_cache)))
        self.eye_cache[cache_key] = image
        
        return image
    
    def detect_brightness_centroid(self, frame):
        """
        Ultra-fast brightness centroid detection
        No OpenCV morphology operations - just numpy
        """
        # Convert to grayscale using numpy (much faster than cv2)
        gray = np.dot(frame[...,:3], [0.299, 0.587, 0.114]).astype(np.uint8)
        
        # Find pixels above brightness threshold
        bright_pixels = gray > self.brightness_threshold
        
        # If no bright pixels, return None
        if not bright_pixels.any():
            return None
        
        # Calculate centroid of bright pixels (weighted average)
        y_indices, x_indices = np.where(bright_pixels)
        
        if len(x_indices) < 10:  # Too few pixels
            return None
        
        # Calculate centroid
        centroid_x = int(np.mean(x_indices))
        centroid_y = int(np.mean(y_indices))
        
        # Scale to camera resolution for consistency
        return (centroid_x, centroid_y)
    
    def update_eye_position(self, centroid):
        """Update eye position from brightness centroid"""
        self.last_centroid = centroid  # Store for debug
        
        if centroid:
            x, y = centroid
            
            # Normalize (-1 to 1)
            norm_x = (x - self.camera_width//2) / (self.camera_width//2)
            norm_y = (y - self.camera_height//2) / (self.camera_height//2)
            
            # Map to display (inverted X)
            eye_x = WIDTH//2 - norm_x * (WIDTH//2 - 40)
            eye_y = HEIGHT//2 + norm_y * (HEIGHT//2 - 40)
            
            self.target_eye_position = (eye_x, eye_y)
        # Don't return to center - keep last position
    
    def smooth_eye_movement(self):
        """Smooth interpolation"""
        current_x, current_y = self.current_eye_position
        target_x, target_y = self.target_eye_position
        
        new_x = current_x + (target_x - current_x) * self.eye_movement_speed
        new_y = current_y + (target_y - current_y) * self.eye_movement_speed
        
        self.current_eye_position = (new_x, new_y)
    
    def update_fps(self):
        """Update FPS counter"""
        self.frame_count += 1
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            fps = self.frame_count / (current_time - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = current_time
            print(f"FPS: {fps:.1f}")
    
    def camera_thread(self):
        """Camera processing thread - optimized for speed"""
        while self.running:
            try:
                # Capture frame
                frame = self.camera.capture_array()
                
                # Detect centroid every frame (it's fast enough!)
                centroid = self.detect_brightness_centroid(frame)
                self.update_eye_position(centroid)
                
                # Add to queue for preview
                try:
                    self.frame_queue.put_nowait((frame, centroid))
                except queue.Full:
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait((frame, centroid))
                    except:
                        pass
                
                # Update FPS
                self.update_fps()
                
            except Exception as e:
                print(f"Camera error: {e}")
                time.sleep(0.1)
    
    def display_thread(self):
        """Display thread - update display continuously"""
        while self.running:
            try:
                # Smooth movement
                self.smooth_eye_movement()
                
                # Always update display to see changes immediately
                eye_x, eye_y = self.current_eye_position
                eye_image = self.create_eye_image(int(eye_x), int(eye_y))
                self.display.image(eye_image)
                
                # 25 FPS target (display limit)
                time.sleep(1.0/25.0)
                
            except Exception as e:
                print(f"Display error: {e}")
                time.sleep(0.1)
    
    def preview_thread(self):
        """Preview window thread"""
        while self.running:
            try:
                frame, centroid = self.frame_queue.get(timeout=1.0)
                
                # Convert to BGR and upscale for viewing
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                frame_large = cv2.resize(frame_bgr, (640, 480))
                
                # Draw centroid if detected
                if centroid:
                    x, y = centroid
                    # Scale centroid to large frame
                    x_large = int(x * 4)
                    y_large = int(y * 4)
                    cv2.circle(frame_large, (x_large, y_large), 10, (0, 255, 0), -1)
                    cv2.putText(frame_large, f"Centroid: ({x}, {y})", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Show threshold info
                cv2.putText(frame_large, f"Threshold: {self.brightness_threshold}", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                cv2.imshow('Brightness Tracking', frame_large)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.running = False
                    break
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Preview error: {e}")
                break
    
    def start(self):
        """Start the mini tracker"""
        print("Starting Mini Eye Tracker...")
        
        if not self.init_display():
            return
        if not self.init_camera():
            return
        
        self.running = True
        
        # Start threads
        cam_thread = threading.Thread(target=self.camera_thread, daemon=True)
        disp_thread = threading.Thread(target=self.display_thread, daemon=True)
        prev_thread = threading.Thread(target=self.preview_thread, daemon=True)
        
        cam_thread.start()
        disp_thread.start()
        prev_thread.start()
        
        print("Mini Eye Tracker running!")
        print("- Green dot shows brightness centroid")
        print("- Adjust lighting if no tracking detected")
        print("- Press 'q' to quit")
        
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the tracker"""
        self.running = False
        if self.display:
            self.display.close()
        if self.camera:
            self.camera.close()
        cv2.destroyAllWindows()
        print("Stopped")

def main():
    tracker = MiniEyeTracker()
    tracker.start()

if __name__ == "__main__":
    main()

