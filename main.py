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
    def __init__(self):
        self.display = None
        self.camera = None
        self.face_cascade = None
        self.running = False
        
        # Eye tracking variables
        self.target_eye_position = (WIDTH//2, HEIGHT//2)
        self.current_eye_position = (WIDTH//2, HEIGHT//2)
        self.eye_movement_speed = 0.15
        
        # Performance monitoring
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        
        # Threading
        self.frame_queue = queue.Queue(maxsize=2)
        self.display_thread = None
        
        # Motion detection variables
        self.prev_frame = None
        self.motion_threshold = 25
        self.min_motion_area = 500
        self.camera_width = 320
        self.camera_height = 240
        
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
        """Initialize the camera"""
        try:
            self.camera = Picamera2()
            # Use lower resolution for better performance
            config = self.camera.create_preview_configuration(
                main={"size": (320, 240), "format": "RGB888"},
                controls={"FrameRate": 30}
            )
            self.camera.configure(config)
            self.camera.start()
            print("Camera initialized successfully!")
            return True
        except Exception as e:
            print(f"Failed to initialize camera: {e}")
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
        """Create eye image for display"""
        # Create black background
        image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Eye parameters
        eye_size = 80
        iris_size = 60
        pupil_size = 30
        highlight_size = 15
        
        # Calculate eye position (clamp to display bounds)
        eye_x = max(eye_size//2, min(WIDTH - eye_size//2, eye_x))
        eye_y = max(eye_size//2, min(HEIGHT - eye_size//2, eye_y))
        
        # Draw eyelid (almond shape)
        eyelid_points = [
            (eye_x - eye_size//2, eye_y - eye_size//4),
            (eye_x + eye_size//2, eye_y - eye_size//4),
            (eye_x + eye_size//2, eye_y + eye_size//4),
            (eye_x - eye_size//2, eye_y + eye_size//4)
        ]
        
        # Create eyelid shape with curves
        eyelid_path = []
        eyelid_path.append((eye_x - eye_size//2, eye_y - eye_size//4))
        eyelid_path.append((eye_x, eye_y - eye_size//3))  # Top curve
        eyelid_path.append((eye_x + eye_size//2, eye_y - eye_size//4))
        eyelid_path.append((eye_x + eye_size//2, eye_y + eye_size//4))
        eyelid_path.append((eye_x, eye_y + eye_size//3))  # Bottom curve
        eyelid_path.append((eye_x - eye_size//2, eye_y + eye_size//4))
        
        # Draw eyelid
        draw.polygon(eyelid_path, fill=(20, 20, 20), outline=(40, 40, 40))
        
        # Draw iris (red/orange beast color)
        iris_x = eye_x - iris_size//2
        iris_y = eye_y - iris_size//2
        draw.ellipse([iris_x, iris_y, iris_x + iris_size, iris_y + iris_size], 
                    fill=(200, 50, 25), outline=(0, 0, 0))
        
        # Draw pupil (black)
        pupil_x = eye_x - pupil_size//2
        pupil_y = eye_y - pupil_size//2
        draw.ellipse([pupil_x, pupil_y, pupil_x + pupil_size, pupil_y + pupil_size], 
                    fill=(0, 0, 0))
        
        # Draw highlight (white)
        highlight_x = eye_x - highlight_size//2 + 10
        highlight_y = eye_y - highlight_size//2 - 5
        draw.ellipse([highlight_x, highlight_y, highlight_x + highlight_size, highlight_y + highlight_size], 
                    fill=(255, 255, 255))
        
        return image
    
    def detect_motion(self, frame):
        """Detect motion using frame differencing - much faster than face detection"""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        # Initialize previous frame
        if self.prev_frame is None:
            self.prev_frame = gray
            return None
        
        # Compute difference between current and previous frame
        frame_delta = cv2.absdiff(self.prev_frame, gray)
        thresh = cv2.threshold(frame_delta, self.motion_threshold, 255, cv2.THRESH_BINARY)[1]
        
        # Dilate to fill in holes
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Update previous frame
        self.prev_frame = gray
        
        # Find the largest contour (most likely the person)
        largest_contour = None
        max_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_motion_area and area > max_area:
                max_area = area
                largest_contour = contour
        
        if largest_contour is not None:
            # Get bounding box
            x, y, w, h = cv2.boundingRect(largest_contour)
            return [(x, y, w, h)]
        
        return []
    
    def update_eye_position(self, motion_boxes):
        """Update eye position based on motion detection"""
        if motion_boxes and len(motion_boxes) > 0:
            # Use the first detected motion
            x, y, w, h = motion_boxes[0]
            motion_center_x = x + w//2
            motion_center_y = y + h//2
            
            # Normalize motion position (-1 to 1)
            norm_x = (motion_center_x - self.camera_width//2) / (self.camera_width//2)
            norm_y = (motion_center_y - self.camera_height//2) / (self.camera_height//2)
            
            # Map to display coordinates
            eye_x = WIDTH//2 + norm_x * (WIDTH//2 - 40)  # 40px margin
            eye_y = HEIGHT//2 + norm_y * (HEIGHT//2 - 40)
            
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
        """Camera processing thread"""
        while self.running:
            try:
                # Capture frame
                frame = self.camera.capture_array()
                
                # Detect motion (much faster than face detection)
                motion_boxes = self.detect_motion(frame)
                
                # Update eye position
                if motion_boxes is not None:
                    self.update_eye_position(motion_boxes)
                
                # Update FPS
                self.update_fps()
                
                # Add frame to queue (non-blocking)
                try:
                    self.frame_queue.put_nowait((frame, motion_boxes if motion_boxes else []))
                except queue.Full:
                    pass  # Skip frame if queue is full
                
                # No delay needed - run as fast as possible
                
            except Exception as e:
                print(f"Camera thread error: {e}")
                time.sleep(0.1)
    
    def display_thread_func(self):
        """Display update thread"""
        while self.running:
            try:
                # Smooth eye movement
                self.smooth_eye_movement()
                
                # Create eye image
                eye_x, eye_y = self.current_eye_position
                eye_image = self.create_eye_image(int(eye_x), int(eye_y))
                
                # Update display
                self.display.image(eye_image)
                
                # 60 FPS display update
                time.sleep(1.0/60.0)
                
            except Exception as e:
                print(f"Display thread error: {e}")
                time.sleep(0.1)
    
    def start(self):
        """Start the eye tracker"""
        print("Starting Eye Tracker...")
        
        # Initialize components
        if not self.init_display():
            return False
        if not self.init_camera():
            return False
        if not self.init_face_detection():
            return False
        
        self.running = True
        
        # Start threads
        self.display_thread = threading.Thread(target=self.display_thread_func, daemon=True)
        self.display_thread.start()
        
        camera_thread = threading.Thread(target=self.camera_thread, daemon=True)
        camera_thread.start()
        
        print("Eye Tracker started! Press Ctrl+C to stop.")
        
        try:
            # Main loop for OpenCV display (optional)
            while self.running:
                try:
                    frame, motion_boxes = self.frame_queue.get(timeout=1.0)
                    
                    # Draw motion rectangles on frame
                    for (x, y, w, h) in motion_boxes:
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        # Draw center point
                        center_x = x + w//2
                        center_y = y + h//2
                        cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
                    
                    # Convert RGB to BGR for OpenCV
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                    # Resize for better viewing (make it wider)
                    display_frame = cv2.resize(frame_bgr, (640, 480), interpolation=cv2.INTER_LINEAR)
                    
                    # Display frame
                    cv2.imshow('Motion Detection', display_frame)
            
            # Check for 'q' key press to quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                        
                except queue.Empty:
                    continue
                
    except KeyboardInterrupt:
            print("\nStopping Eye Tracker...")
    finally:
            self.stop()
    
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
    eye_tracker = EyeTracker()
    eye_tracker.start()

if __name__ == "__main__":
    main()

