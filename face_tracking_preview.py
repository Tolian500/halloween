#!/usr/bin/env python3
"""
Face Tracking Preview - Separate code for face detection and size analysis
Shows face detection with box size information and logs last 5 face sizes
"""

from picamera2 import Picamera2
import cv2
import numpy as np
import time
import os

class FaceTracker:
    def __init__(self):
        self.camera = None
        self.face_cascade = None
        self.running = False
        
        # Face detection settings (same as main code)
        self.camera_width = 800
        self.camera_height = 600
        self.face_detection_interval = 20  # Run face detection every 20 frames
        self.face_detection_counter = 0
        
        # Face size logging
        self.face_sizes = []  # Store last 5 face sizes
        self.max_face_history = 5
        
        # Face detection parameters (same as main code)
        self.scale_factor = 1.1
        self.min_neighbors = 5
        self.min_size = (30, 30)
        
    def init_camera(self):
        """Initialize camera with same settings as main code"""
        try:
            self.camera = Picamera2()
            
            # Same Pi 5 optimized configuration as main code
            config = self.camera.create_video_configuration(
                main={"size": (self.camera_width, self.camera_height), "format": "YUV420"},
                buffer_count=4,
                queue=True
            )
            self.camera.configure(config)
            
            self.camera.start()
            print(f"Camera: {self.camera_width}x{self.camera_height} (YUV420, Pi 5 optimized)")
            print(f"Sensor resolution: {self.camera.sensor_resolution}")
            return True
        except Exception as e:
            print(f"Camera init failed: {e}")
            return False
    
    def init_face_detection(self):
        """Initialize face detection with same settings as main code"""
        try:
            # Same cascade paths as main code
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
                import urllib.request
                url = 'https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml'
                cascade_path = 'haarcascade_frontalface_default.xml'
                try:
                    urllib.request.urlretrieve(url, cascade_path)
                    print(f"Downloaded cascade file to {cascade_path}")
                except Exception as e:
                    print(f"Failed to download cascade file: {e}")
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
    
    def detect_faces(self, frame):
        """Detect faces with same settings as main code"""
        if self.face_cascade is None:
            return []
        
        # Convert frame to grayscale for face detection
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_YUV2GRAY)
        else:
            gray = frame
        
        # Detect faces with same parameters as main code
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
            minSize=self.min_size,
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        return faces
    
    def update_face_sizes(self, faces):
        """Update face size history with last 5 face sizes"""
        if len(faces) > 0:
            # Use the largest face (most prominent)
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest_face
            face_area = w * h
            
            # Add to history
            self.face_sizes.append(face_area)
            
            # Keep only last 5
            if len(self.face_sizes) > self.max_face_history:
                self.face_sizes.pop(0)
            
            # Log face size
            print(f"Face detected: {w}x{h} pixels, Area: {face_area}")
            if len(self.face_sizes) > 1:
                avg_size = sum(self.face_sizes) / len(self.face_sizes)
                print(f"Average face size (last {len(self.face_sizes)}): {avg_size:.0f}")
        else:
            # No face detected
            if len(self.face_sizes) > 0:
                print("No face detected")
    
    def draw_face_info(self, frame, faces):
        """Draw face detection info on frame"""
        if len(faces) > 0:
            # Use the largest face
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest_face
            
            # Draw face rectangle
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 165, 255), 2)  # Orange color
            
            # Draw center point
            center_x = x + w//2
            center_y = y + h//2
            cv2.circle(frame, (center_x, center_y), 5, (0, 165, 255), -1)
            
            # Add face size information
            face_area = w * h
            size_text = f"Face: {w}x{h} (Area: {face_area})"
            cv2.putText(frame, size_text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
            
            # Add face history info
            if len(self.face_sizes) > 1:
                avg_size = sum(self.face_sizes) / len(self.face_sizes)
                history_text = f"Avg Size: {avg_size:.0f} (Last {len(self.face_sizes)})"
                cv2.putText(frame, history_text, (x, y+h+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
        
        return frame
    
    def run(self):
        """Main face tracking loop"""
        print("Starting Face Tracking Preview...")
        
        # Initialize components
        if not self.init_camera():
            return False
        if not self.init_face_detection():
            return False
        
        self.running = True
        
        print("Face Tracker started! Press 'q' in preview window to quit.")
        print("Face sizes will be logged to console.")
        
        try:
            while self.running:
                # Capture frame
                frame = self.camera.capture_array()
                
                # Face detection (every 20 frames like main code)
                faces = []
                self.face_detection_counter += 1
                
                if self.face_detection_counter >= self.face_detection_interval:
                    faces = self.detect_faces(frame)
                    self.face_detection_counter = 0
                    
                    # Update face size history
                    self.update_face_sizes(faces)
                
                # Convert to BGR for OpenCV
                if len(frame.shape) == 3:
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_YUV2BGR)
                else:
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                
                # Draw face detection info
                frame_with_info = self.draw_face_info(frame_bgr, faces)
                
                # Add status information
                status_text = f"Faces: {len(faces)} | Detection: Every {self.face_detection_interval} frames"
                cv2.putText(frame_with_info, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Add face history info
                if len(self.face_sizes) > 0:
                    history_text = f"Face History: {len(self.face_sizes)}/{self.max_face_history}"
                    cv2.putText(frame_with_info, history_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # Flip image horizontally for mirror effect
                frame_mirrored = cv2.flip(frame_with_info, 1)
                
                # Show preview
                cv2.imshow('Face Tracking Preview (Mirrored)', frame_mirrored)
                
                # Check for 'q' key press to quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except KeyboardInterrupt:
            print("\nStopping Face Tracker...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the face tracker"""
        self.running = False
        
        if self.camera:
            self.camera.close()
        cv2.destroyAllWindows()
        
        # Print final face size statistics
        if len(self.face_sizes) > 0:
            print(f"\nFinal Face Size Statistics:")
            print(f"Total detections: {len(self.face_sizes)}")
            print(f"Average size: {sum(self.face_sizes) / len(self.face_sizes):.0f}")
            print(f"Min size: {min(self.face_sizes)}")
            print(f"Max size: {max(self.face_sizes)}")
            print(f"All sizes: {self.face_sizes}")
        
        print("Face Tracker stopped")

def main():
    """Main function"""
    print("=" * 60)
    print("FACE TRACKING PREVIEW")
    print("Same settings as main eye tracker")
    print("Shows face detection with size information")
    print("Logs last 5 face sizes for analysis")
    print("=" * 60)
    
    face_tracker = FaceTracker()
    face_tracker.run()

if __name__ == "__main__":
    main()
