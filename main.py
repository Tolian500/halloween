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
        self.eye_movement_speed = 0.25  # Faster response
        
        # Performance monitoring
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        
        # Performance timing
        self.timing_capture = []
        self.timing_motion = []
        self.timing_display = []
        self.timing_total = []
        self.last_perf_print = time.time()
        
        # Threading
        self.frame_queue = queue.Queue(maxsize=1) if enable_preview else None
        self.display_thread = None
        
        # Motion detection variables
        self.prev_frame = None
        self.motion_threshold = 25
        self.min_motion_area = 500
        self.camera_width = 120  # ULTRA-LOW: 120x120
        self.camera_height = 120  # Square format
        
        # Pre-rendered eye cache (optimization #1)
        self.eye_cache = {}
        self.cache_size = 50  # Cache 50 eye positions (more aggressive)
        self.last_rendered_pos = None
        
        # Frame skipping (optimization #3)
        self.display_update_counter = 0
        self.display_update_interval = 2  # Update display every 2 frames
        
        # Motion detection optimization (optimization #5)
        self.motion_check_counter = 0
        self.motion_check_interval = 1  # Check EVERY frame (motion is super fast now!)
        
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
        """Initialize camera with ULTRA-LOW 120×120 resolution (NO full FOV for speed!)"""
        try:
            self.camera = Picamera2()
            
            # ULTRA-LOW resolution: 120×120 - NO raw sensor (too slow!)
            # Use lores stream for maximum speed
            config = self.camera.create_video_configuration(
                main={"size": (self.camera_width, self.camera_height), "format": "RGB888"}
                # NO raw= parameter - it slows down capture by 3-4x!
            )
            self.camera.configure(config)
            
            self.camera.start()
            print(f"Camera: {self.camera_width}x{self.camera_height} (RGB, fast mode)")
            print(f"Sensor resolution: {self.camera.sensor_resolution}")
            print("NOTE: Using cropped FOV for maximum speed!")
            return True
        except Exception as e:
            print(f"Camera init failed: {e}")
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
        """Create BIGGER eye image with AGGRESSIVE caching - 2x size"""
        # Round to nearest 20 pixels for MORE caching (less unique images)
        cache_x = round(eye_x / 20) * 20
        cache_y = round(eye_y / 20) * 20
        cache_key = (cache_x, cache_y)
        
        # Check cache first
        if cache_key in self.eye_cache:
            return self.eye_cache[cache_key]
        
        # Create new image with NumPy (faster than PIL)
        img_array = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        
        # BIGGER Eye parameters (2x size)
        iris_radius = 60  # Was 60
        pupil_radius = 30  # Was 30
        
        # Calculate eye position (clamp to display bounds with margin)
        eye_x = int(max(iris_radius, min(WIDTH - iris_radius, eye_x)))
        eye_y = int(max(iris_radius, min(HEIGHT - iris_radius, eye_y)))
        
        # Draw iris (red circle) using NumPy
        y, x = np.ogrid[:HEIGHT, :WIDTH]
        mask_iris = (x - eye_x)**2 + (y - eye_y)**2 <= iris_radius**2
        img_array[mask_iris] = [200, 50, 25]  # Red iris
        
        # Draw pupil (black circle)
        mask_pupil = (x - eye_x)**2 + (y - eye_y)**2 <= pupil_radius**2
        img_array[mask_pupil] = [0, 0, 0]  # Black pupil
        
        # Draw highlight (white circle) - offset
        highlight_x = eye_x + 15
        highlight_y = eye_y - 10
        mask_highlight = (x - highlight_x)**2 + (y - highlight_y)**2 <= 15**2
        img_array[mask_highlight] = [255, 255, 255]  # White highlight
        
        # Convert to PIL Image
        image = Image.fromarray(img_array)
        
        # Cache management - keep only recent entries
        if len(self.eye_cache) >= self.cache_size:
            # Remove oldest entry
            self.eye_cache.pop(next(iter(self.eye_cache)))
        
        self.eye_cache[cache_key] = image
        return image
    
    def detect_motion(self, frame):
        """ULTRA-FAST motion detection at 40×40 pixels!"""
        # Extreme downsample to 40x40 (1600 pixels!)
        tiny = cv2.resize(frame, (40, 40), interpolation=cv2.INTER_NEAREST)
        
        # Convert to grayscale if needed
        if len(tiny.shape) == 3:
            # RGB/YUV - convert to grayscale
            gray = cv2.cvtColor(tiny, cv2.COLOR_RGB2GRAY)
        else:
            # Already grayscale (Y channel from YUV420)
            gray = tiny
        
        # Initialize previous frame
        if self.prev_frame is None:
            self.prev_frame = gray
            return None
        
        # NO BLUR - saves 5-10ms
        # Direct difference
        frame_delta = cv2.absdiff(self.prev_frame, gray)
        _, thresh = cv2.threshold(frame_delta, self.motion_threshold, 255, cv2.THRESH_BINARY)
        
        # Update previous frame
        self.prev_frame = gray
        
        # Use moments instead of contours (MUCH faster)
        moments = cv2.moments(thresh)
        
        if moments["m00"] > 15:  # Minimum area threshold (adjusted for 40x40)
            # Calculate centroid
            cx = int(moments["m10"] / moments["m00"])
            cy = int(moments["m01"] / moments["m00"])
            
            # Scale from 40x40 to 120x120 (3x)
            x = int(cx * 3)
            y = int(cy * 3)
            
            # Return fake bounding box
            return [(x, y, 20, 20)]
        
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
            # Don't print here - use print_performance() instead
    
    def print_performance(self):
        """Print detailed performance statistics"""
        if not self.timing_capture:
            return
        
        avg_capture = sum(self.timing_capture) / len(self.timing_capture)
        avg_motion = sum(self.timing_motion) / len(self.timing_motion) if self.timing_motion else 0
        avg_display = sum(self.timing_display) / len(self.timing_display) if self.timing_display else 0
        avg_total = sum(self.timing_total) / len(self.timing_total)
        
        print("=" * 60)
        print(f"FPS: {self.current_fps:.1f} | Frame Time: {avg_total:.1f}ms")
        print(f"  Camera Capture:   {avg_capture:.2f}ms")
        print(f"  Motion Detection: {avg_motion:.2f}ms")
        print(f"  Display Update:   {avg_display:.2f}ms (async thread)")
        print(f"  Other/Overhead:   {(avg_total - avg_capture - avg_motion):.2f}ms")
        
        # Calculate theoretical max FPS
        theoretical_fps = 1000.0 / avg_total if avg_total > 0 else 0
        print(f"Theoretical Max FPS: {theoretical_fps:.1f}")
        print("=" * 60)
        
        # Clear timing arrays
        self.timing_capture.clear()
        self.timing_motion.clear()
        self.timing_display.clear()
        self.timing_total.clear()
    
    def camera_thread(self):
        """Optimized camera thread with performance timing"""
        while self.running:
            try:
                frame_start = time.time()
                
                # Capture frame
                t0 = time.time()
                frame = self.camera.capture_array()
                capture_time = (time.time() - t0) * 1000  # ms
                
                # Frame skipping for motion detection (Optimization #3 & #5)
                self.motion_check_counter += 1
                if self.motion_check_counter >= self.motion_check_interval:
                    self.motion_check_counter = 0
                    
                    t1 = time.time()
                    motion_boxes = self.detect_motion(frame)
                    motion_time = (time.time() - t1) * 1000  # ms
                    
                    # Handle None return (first frame)
                    if motion_boxes is None:
                        motion_boxes = []
                    
                    # Update eye position only when motion detected
                    if motion_boxes:
                        self.update_eye_position(motion_boxes)
                    
                    # Store timing
                    self.timing_capture.append(capture_time)
                    self.timing_motion.append(motion_time)
                else:
                    motion_boxes = []
                
                # Update FPS
                self.update_fps()
                
                # Total frame time
                total_time = (time.time() - frame_start) * 1000
                self.timing_total.append(total_time)
                
                # Print detailed performance every 2 seconds
                if time.time() - self.last_perf_print >= 2.0:
                    self.print_performance()
                    self.last_perf_print = time.time()
                
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
        """Display thread - LIMITED to 15 FPS to not block camera"""
        while self.running:
            try:
                # Check if display is initialized
                if not self.display:
                    time.sleep(0.1)
                    continue
                
                # Smooth eye movement
                self.smooth_eye_movement()
                
                # Check if position changed enough to warrant update
                eye_x, eye_y = self.current_eye_position
                rounded_pos = (round(eye_x / 20) * 20, round(eye_y / 20) * 20)
                
                # Only update if moved more than 20 pixels (matches cache granularity)
                if rounded_pos != self.last_rendered_pos:
                    t0 = time.time()
                    eye_image = self.create_eye_image(int(eye_x), int(eye_y))
                    self.display.image(eye_image)
                    display_time = (time.time() - t0) * 1000  # ms
                    self.timing_display.append(display_time)
                    self.last_rendered_pos = rounded_pos
                
                # 15 FPS - SPI transfer is SLOW (60-80ms per frame!)
                time.sleep(1.0/15.0)
                
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

