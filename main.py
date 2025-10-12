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
        self.eye_movement_speed = 0.1
        
        # Performance monitoring
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        
        # Threading
        self.frame_queue = queue.Queue(maxsize=2)
        self.display_thread = None
        
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
            config = self.camera.create_preview_configuration(
                main={"size": (640, 480), "format": "RGB888"}
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
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            if self.face_cascade.empty():
                print("Failed to load face cascade")
                return False
            print("Face detection initialized successfully!")
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
    
    def detect_faces(self, frame):
        """Detect faces in frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(30, 30)
        )
        return faces
    
    def update_eye_position(self, faces):
        """Update eye position based on face detection"""
        if len(faces) > 0:
            # Use the first detected face
            x, y, w, h = faces[0]
            face_center_x = x + w//2
            face_center_y = y + h//2
            
            # Convert face position to eye position
            # Map camera coordinates to display coordinates
            camera_width = 640
            camera_height = 480
            
            # Normalize face position (-1 to 1)
            norm_x = (face_center_x - camera_width//2) / (camera_width//2)
            norm_y = (face_center_y - camera_height//2) / (camera_height//2)
            
            # Map to display coordinates
            eye_x = WIDTH//2 + norm_x * (WIDTH//2 - 40)  # 40px margin
            eye_y = HEIGHT//2 + norm_y * (HEIGHT//2 - 40)
            
            self.target_eye_position = (eye_x, eye_y)
        else:
            # No faces detected, return to center
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
                
                # Detect faces
                faces = self.detect_faces(frame)
                
                # Update eye position
                self.update_eye_position(faces)
                
                # Update FPS
                self.update_fps()
                
                # Add frame to queue (non-blocking)
                try:
                    self.frame_queue.put_nowait((frame, faces))
                except queue.Full:
                    pass  # Skip frame if queue is full
                
                # Small delay to prevent overwhelming
                time.sleep(0.033)  # ~30 FPS
                
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
                    frame, faces = self.frame_queue.get(timeout=1.0)
                    
                    # Draw face rectangles on frame
                    for (x, y, w, h) in faces:
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    
                    # Convert RGB to BGR for OpenCV
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                    # Display frame
                    cv2.imshow('Face Detection', frame_bgr)
                    
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

