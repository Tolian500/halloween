from picamera2 import Picamera2
import cv2
import numpy as np
import sys
import os
import time
import RPi.GPIO as GPIO
import spidev
from PIL import Image, ImageDraw, ImageFont
import threading
import queue
import argparse

# Import the GC9A01 display class from our test script
from test_gc9a01 import GC9A01

# Display configuration
CS_PIN = 8   # GPIO 8 (CE0)
DC_PIN = 25  # GPIO 25
RST_PIN = 27 # GPIO 27

# Display dimensions
WIDTH = 240
HEIGHT = 240

class EyeTracker:
    def __init__(self, enable_preview=True):
        self.display = None
        self.camera = None
        self.face_cascade = None
        self.running = False
        self.enable_preview = enable_preview  # NEW: Control preview window
        
        # Eye tracking variables
        self.target_eye_position = (WIDTH//2, HEIGHT//2)
        self.current_eye_position = (WIDTH//2, HEIGHT//2)
        self.eye_movement_speed = 0.15
        
        # Performance monitoring
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        
        # Threading
        self.frame_queue = queue.Queue(maxsize=1) if enable_preview else None
        self.display_thread = None
        
        # Motion detection variables
        self.prev_frame = None
        self.motion_threshold = 25
        self.min_motion_area = 500
        self.camera_width = 640
        self.camera_height = 480
        
        # Pre-rendered eye cache (optimization #1)
        self.eye_cache = {}
        self.cache_size = 20  # Cache 20 eye positions
        self.last_rendered_pos = None
        
        # Frame skipping (optimization #3)
        self.display_update_counter = 0
        self.display_update_interval = 2  # Update display every 2 frames
        
        # Motion detection optimization (optimization #5)
        self.motion_check_counter = 0
        self.motion_check_interval = 2  # Check motion every 2 frames
        
    def init_display(self):
        """Initialize the GC9A01 display"""
        try:
            self.display = GC9A01()
            print("GC9A01 display initialized successfully!")
            return True
        except Exception as e:
            print(f"Failed to initialize display: {e}")
            return False
    
    def init_camera(self):
        """Initialize camera with grayscale for maximum performance"""
        try:
            self.camera = Picamera2()
            
            # Use grayscale (YUV420) for better performance
            config = self.camera.create_video_configuration(
                main={"size": (640, 480), "format": "YUV420"},
                raw={"size": self.camera.sensor_resolution}
            )
            self.camera.configure(config)
            self.camera_width = 640
            self.camera_height = 480
            
            self.camera.start()
            print(f"Camera initialized at {self.camera_width}x{self.camera_height} (Grayscale) with full FOV!")
            print(f"Sensor resolution: {self.camera.sensor_resolution}")
            return True
        except Exception as e:
            print(f"Failed to initialize grayscale camera: {e}")
            print("Trying RGB fallback...")
            try:
                # Fallback to RGB
                config = self.camera.create_video_configuration(
                    main={"size": (640, 480), "format": "RGB888"},
                    raw={"size": self.camera.sensor_resolution}
                )
                self.camera.configure(config)
                self.camera_width = 640
                self.camera_height = 480
                self.camera.start()
                print(f"Camera initialized with RGB at {self.camera_width}x{self.camera_height}")
                return True
            except Exception as e2:
                print(f"Camera init failed: {e2}")
                return False
    
    def init_face_detection(self):
        """Initialize face detection"""
        try:
            # Load Haar cascade for face detection
            # Try multiple possible locations
            cascade_paths = [
                '/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
                '/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
                '/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml',
                '/home/tolian500/Coding/halloween/haarcascade_frontalface_default.xml',
                'haarcascade_frontalface_default.xml'
            ]
            
            cascade_path = None
            for path in cascade_paths:
                if os.path.exists(path):
                    cascade_path = path
                    break
            
            if cascade_path is None:
                print("Haar cascade file not found. Downloading...")
                # Download the cascade file
                import urllib.request
                url = 'https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml'
                cascade_path = 'haarcascade_frontalface_default.xml'
                try:
                    urllib.request.urlretrieve(url, cascade_path)
                    print(f"Downloaded cascade file to {cascade_path}")
                except Exception as e:
                    print(f"Failed to download cascade file: {e}")
                    print("Please install opencv-data: sudo apt install opencv-data")
                    return False
            
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            if self.face_cascade.empty():
                print("Failed to load face cascade")
                return False
            print(f"Face detection initialized successfully using: {cascade_path}")
            return True
        except Exception as e:
            print(f"Failed to initialize face detection: {e}")
            return False
    
    def create_eye_image(self, eye_x, eye_y):
        """Create BIGGER eye image with caching - 2x size"""
        # Round to nearest 10 pixels for cache key
        cache_x = round(eye_x / 10) * 10
        cache_y = round(eye_y / 10) * 10
        cache_key = (cache_x, cache_y)
        
        # Check cache first
        if cache_key in self.eye_cache:
            return self.eye_cache[cache_key]
        
        # Create new image
        image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # BIGGER Eye parameters (2x size)
        eye_size = 160  # Was 80
        iris_size = 120  # Was 60
        pupil_size = 60  # Was 30
        highlight_size = 30  # Was 15
        
        # Calculate eye position (clamp to display bounds with margin)
        eye_x = max(eye_size//2, min(WIDTH - eye_size//2, eye_x))
        eye_y = max(eye_size//2, min(HEIGHT - eye_size//2, eye_y))
        
        # Draw eyelid (simplified - less vertices)
        eyelid_path = [
            (eye_x - eye_size//2, eye_y),
            (eye_x, eye_y - eye_size//3),
            (eye_x + eye_size//2, eye_y),
            (eye_x, eye_y + eye_size//3)
        ]
        draw.polygon(eyelid_path, fill=(20, 20, 20))
        
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
        highlight_x = eye_x - highlight_size//2 + 20  # Was +10
        highlight_y = eye_y - highlight_size//2 - 10  # Was -5
        draw.ellipse([highlight_x, highlight_y, highlight_x + highlight_size, highlight_y + highlight_size], 
                    fill=(255, 255, 255))
        
        # Cache management - keep only recent entries
        if len(self.eye_cache) >= self.cache_size:
            # Remove oldest entry
            self.eye_cache.pop(next(iter(self.eye_cache)))
        
        self.eye_cache[cache_key] = image
        return image
    
    def detect_motion(self, frame):
        """Optimized motion detection with grayscale support"""
        # Downsample for faster processing (160x120)
        small_frame = cv2.resize(frame, (160, 120), interpolation=cv2.INTER_NEAREST)
        
        # Convert to grayscale (handle both YUV and RGB)
        if len(small_frame.shape) == 3:
            # RGB image
            gray = cv2.cvtColor(small_frame, cv2.COLOR_RGB2GRAY)
        else:
            # Already grayscale (Y channel from YUV420)
            gray = small_frame
        
        # Smaller blur kernel for speed
        gray = cv2.GaussianBlur(gray, (11, 11), 0)
        
        # Initialize previous frame
        if self.prev_frame is None:
            self.prev_frame = gray
            return None
        
        # Compute difference
        frame_delta = cv2.absdiff(self.prev_frame, gray)
        thresh = cv2.threshold(frame_delta, self.motion_threshold, 255, cv2.THRESH_BINARY)[1]
        
        # Single dilation (reduced from 2)
        thresh = cv2.dilate(thresh, None, iterations=1)
        
        # Find contours with simpler approximation
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Update previous frame
        self.prev_frame = gray
        
        # Find the largest contour
        largest_contour = None
        max_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 100 and area > max_area:  # Lower threshold for 160x120
                max_area = area
                largest_contour = contour
        
        if largest_contour is not None:
            # Get bounding box and scale to 640x480
            x, y, w, h = cv2.boundingRect(largest_contour)
            # Scale from 160x120 to 640x480 (4x)
            x = int(x * 4)
            y = int(y * 4)
            w = int(w * 4)
            h = int(h * 4)
            return [(x, y, w, h)]
        
        return []
    
    def update_eye_position(self, motion_boxes):
        """Update eye position with BIGGER movement range"""
        if motion_boxes and len(motion_boxes) > 0:
            # Use the first detected motion
            x, y, w, h = motion_boxes[0]
            motion_center_x = x + w//2
            motion_center_y = y + h//2
            
            # Normalize motion position (-1 to 1)
            norm_x = (motion_center_x - self.camera_width//2) / (self.camera_width//2)
            norm_y = (motion_center_y - self.camera_height//2) / (self.camera_height//2)
            
            # Map to display coordinates with MUCH larger range (margin to margin)
            # Changed from 40px margin to 10px margin for more movement
            eye_x = WIDTH//2 - norm_x * (WIDTH//2 - 10)  # Inverted X, less margin
            eye_y = HEIGHT//2 + norm_y * (HEIGHT//2 - 10)  # Less margin
            
            self.target_eye_position = (eye_x, eye_y)
        else:
            # No motion detected, return to center
            self.target_eye_position = (WIDTH//2, HEIGHT//2)
    
    def smooth_eye_movement(self):
        """Smoothly interpolate eye movement"""
        current_x, current_y = self.current_eye_position
        target_x, target_y = self.target_eye_position
        
        # Smooth interpolation
        new_x = current_x + (target_x - current_x) * self.eye_movement_speed
        new_y = current_y + (target_y - current_y) * self.eye_movement_speed
        
        self.current_eye_position = (new_x, new_y)
    
    def update_fps(self):
        """Update FPS counter"""
        self.frame_count += 1
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.current_fps = self.frame_count / (current_time - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = current_time
            print(f"FPS: {self.current_fps:.1f}")
    
    def camera_thread(self):
        """Optimized camera thread with frame skipping"""
        while self.running:
            try:
                # Capture frame
                frame = self.camera.capture_array()
                
                # Frame skipping for motion detection (Optimization #3 & #5)
                self.motion_check_counter += 1
                if self.motion_check_counter >= self.motion_check_interval:
                    self.motion_check_counter = 0
                    motion_boxes = self.detect_motion(frame)
                    
                    # Update eye position only when motion detected
                    if motion_boxes is not None:
                        self.update_eye_position(motion_boxes)
                else:
                    motion_boxes = []
                
                # Update FPS
                self.update_fps()
                
                # Add frame to queue only if preview is enabled
                if self.enable_preview and self.frame_queue:
                    try:
                        self.frame_queue.put_nowait((frame, motion_boxes))
                    except queue.Full:
                        # Drop oldest frame
                        try:
                            self.frame_queue.get_nowait()
                            self.frame_queue.put_nowait((frame, motion_boxes))
                        except:
                            pass
                
            except Exception as e:
                print(f"Camera thread error: {e}")
                time.sleep(0.1)
    
    def display_thread_func(self):
        """Optimized display thread with frame skipping - Optimization #3"""
        while self.running:
            try:
                # Smooth eye movement
                self.smooth_eye_movement()
                
                # Frame skipping - only update display every N frames
                self.display_update_counter += 1
                if self.display_update_counter >= self.display_update_interval:
                    self.display_update_counter = 0
                    
                    # Check if position changed significantly
                    eye_x, eye_y = self.current_eye_position
                    rounded_pos = (round(eye_x / 10) * 10, round(eye_y / 10) * 10)
                    
                    # Only render if position changed
                    if rounded_pos != self.last_rendered_pos:
                        eye_image = self.create_eye_image(int(eye_x), int(eye_y))
                        self.display.image(eye_image)
                        self.last_rendered_pos = rounded_pos
                
                # Reduced from 60 FPS to 30 FPS - Optimization #2
                time.sleep(1.0/30.0)
                
            except Exception as e:
                print(f"Display thread error: {e}")
                time.sleep(0.1)
    
    def start(self):
        """Start the eye tracker - uses external run function"""
        from eye_tracker_main import run_eye_tracker
        run_eye_tracker(self)
    
    def stop(self):
        """Stop the eye tracker"""
        self.running = False
        
        if self.display:
            self.display.close()
        if self.camera:
            self.camera.close()
        cv2.destroyAllWindows()
        print("Eye Tracker stopped")

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Eye Tracker with GC9A01 Display')
    parser.add_argument('--no-preview', action='store_true', 
                       help='Disable preview window for maximum performance')
    parser.add_argument('--fps-test', action='store_true',
                       help='Same as --no-preview (for FPS testing)')
    args = parser.parse_args()
    
    # Determine if preview should be enabled
    enable_preview = not (args.no_preview or args.fps_test)
    
    # Create and start tracker
    eye_tracker = EyeTracker(enable_preview=enable_preview)
    
    if not enable_preview:
        print("=" * 50)
        print("FPS TEST MODE - No preview window")
        print("Maximum performance enabled")
        print("=" * 50)
    
    eye_tracker.start()

if __name__ == "__main__":
    main()

