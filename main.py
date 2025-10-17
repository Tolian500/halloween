from picamera2 import Picamera2
import cv2
import numpy as np
import sys
import os
import time
import threading
import queue
import argparse

# Import display settings and driver
from display_settings import (
    GC9A01, DISPLAY1_CS_PIN, DISPLAY1_DC_PIN, DISPLAY1_RST_PIN,
    DISPLAY2_CS_PIN, DISPLAY2_DC_PIN, DISPLAY2_RST_PIN,
    WIDTH, HEIGHT, create_eye_image, send_to_display
)

# Import idle animations
from idle_animations import IdleAnimations

class EyeTracker:
    def __init__(self, enable_preview=True):
        self.display1 = None  # Left eye display
        self.display2 = None  # Right eye display
        self.camera = None
        self.face_cascade = None
        self.running = False
        self.enable_preview = enable_preview  # NEW: Control preview window
        
        # Eye tracking variables (both eyes)
        self.target_eye_position = (WIDTH//2, HEIGHT//2)
        self.current_eye_position = (WIDTH//2, HEIGHT//2)
        
        # Separate eye positions for dual display
        self.target_left_eye = (WIDTH//2, HEIGHT//2)
        self.target_right_eye = (WIDTH//2, HEIGHT//2)
        self.current_left_eye = (WIDTH//2, HEIGHT//2)
        self.current_right_eye = (WIDTH//2, HEIGHT//2)
        self.eye_movement_speed = 0.08  # Much slower, smoother movement to reduce shaking
        self.last_motion_time = time.time()
        self.motion_timeout = 2.0  # Return to center after 2 seconds of no motion
        
        # Motion smoothing to reduce shaking
        self.motion_history = []
        self.motion_history_size = 5  # Average last 5 positions for smoother motion
        
        # Blinking (more natural timing)
        self.is_blinking = False
        self.blink_state = 1.0  # 1.0 = open, 0.0 = closed
        self.blink_direction = -1  # -1 = closing, 1 = opening
        self.last_blink_time = time.time()
        self.next_blink_delay = np.random.uniform(3, 8)  # Random blink every 3-8 seconds (more realistic)
        
        # Separate blink states for idle animations
        self.left_blink_state = 1.0  # 1.0 = open, 0.0 = closed
        self.right_blink_state = 1.0  # 1.0 = open, 0.0 = closed
        
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
        
        # SPI timing profiling (simplified)
        self.timing_spi_total = []
        
        # Threading
        self.frame_queue = queue.Queue(maxsize=1) if enable_preview else None
        self.display_thread = None
        
        # Face detection for color changes only - Pi 5 optimized
        self.face_detection_counter = 0
        self.face_detection_interval = 20  # Run face detection every 20 frames
        self.face_detected = False
        self.face_detection_timeout = 5.0  # Keep red eyes for 5 seconds after face detection
        self.last_face_detection_time = time.time()
        
        # Face-following mode for eye positioning
        self.face_following_mode = False
        self.face_following_timeout = 7.0  # Hold face position for 5 seconds
        self.last_face_following_time = time.time()
        self.current_face_center = None
        self.last_motion_time = time.time()  # Track last motion for interruption
        
        # Idle animation system
        self.idle_animations = None
        self.idle_mode = False
        self.idle_start_time = None
        self.idle_trigger_delay = np.random.uniform(10, 30)  # 5-10 seconds for testing
        self.idle_resume_delay = np.random.uniform(20, 40)  # 5-10 seconds delay before resuming
        self.idle_animation_started = False
        
        # Dynamic eye sizing based on face size with smooth animation
        self.face_sizes = []  # Store last 5 face sizes
        self.max_face_history = 5
        self.min_face_size = 100 * 100  # 50x50 pixels (2500 area)
        self.max_face_size = 240 * 240  # 240x240 pixels (57600 area)
        self.current_eye_size_index = 15  # Current size is 15/20 (middle-large)
        self.target_eye_size_index = 15  # Target size for smooth animation
        self.total_eye_sizes = 30  # 30 different eye sizes
        self.base_eye_size = 40  # Base iris radius (current size)
        self.eye_size_transition_speed = 0.01  # How fast eye size changes (0.1 = 10% per frame)
        
        # Motion detection variables - Pi 5 optimized
        self.prev_frame = None
        self.motion_threshold = 25  # Lower threshold for higher resolution
        self.min_motion_area = 200  # Larger minimum area for higher resolution
        # Pi 5 optimized resolution - higher resolution for better detection
        self.camera_width = 800
        self.camera_height = 600 
        
        # Eye color system
        self.base_eye_color = [255, 255, 0]  # Yellow (idle/motion detection)
        self.face_eye_color = [255, 0, 0]  # Intense red (face tracking)
        self.current_eye_color = self.base_eye_color.copy()
        self.color_transition_speed = 0.05  # How fast colors change
        self.target_eye_color = self.base_eye_color.copy()
        
        # Pre-rendered eye cache (optimization #1) - separate for each eye
        self.eye_cache_left = {}
        self.eye_cache_right = {}
        self.cache_size = 100  # Cache 50 eye positions (more aggressive)
        self.last_rendered_pos_left = None
        self.last_rendered_pos_right = None
        
        # Frame skipping (optimization #3)
        self.display_update_counter = 0
        self.display_update_interval = 2  # Update display every 2 frames
        
        # Motion detection optimization (optimization #5)
        self.motion_check_counter = 0
        self.motion_check_interval = 2  # Check every 2nd frame (15-20 Hz detection)
        
        # Frame skipping for camera (optimization #3)
        self.frame_skip_counter = 0
        self.frame_skip_interval = 1  # Skip every 2nd frame capture
        
    def init_display(self):
        """Initialize both GC9A01 displays"""
        try:
            print("Initializing Display 1 (Left Eye)...")
            self.display1 = GC9A01(
                spi_bus=0, spi_device=0,
                cs_pin=DISPLAY1_CS_PIN,
                dc_pin=DISPLAY1_DC_PIN,
                rst_pin=DISPLAY1_RST_PIN
            )
            print("Display 1 initialized successfully!")
            
            print("Initializing Display 2 (Right Eye)...")
            self.display2 = GC9A01(
                spi_bus=0, spi_device=1,
                cs_pin=DISPLAY2_CS_PIN,
                dc_pin=DISPLAY2_DC_PIN,
                rst_pin=DISPLAY2_RST_PIN
            )
            print("Display 2 initialized successfully!")
            
            # Test both displays with a simple pattern
            print("Testing displays with simple pattern...")
            self._test_displays()
            
            print("Both GC9A01 displays initialized successfully!")
            
            # Initialize idle animations
            print("Initializing idle animations...")
            self.idle_animations = IdleAnimations()
            print("Idle animations initialized successfully!")
            
            return True
        except Exception as e:
            print(f"Failed to initialize displays: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _test_displays(self):
        """Test both displays with a simple pattern"""
        try:
            # Create a simple test pattern
            test_image = np.zeros((WIDTH, HEIGHT, 3), dtype=np.uint8)
            test_image[:, :] = [255, 0, 0]  # Red background
            
            # Convert to RGB565
            r = (test_image[:, :, 0] >> 3).astype(np.uint16)
            g = (test_image[:, :, 1] >> 2).astype(np.uint16)
            b = (test_image[:, :, 2] >> 3).astype(np.uint16)
            rgb565_full = (r << 11) | (g << 5) | b
            rgb565_bytes = rgb565_full.astype('>u2').tobytes()
            
            # Send to both displays
            print("Sending test pattern to Display 1...")
            self._send_to_display(self.display1, rgb565_bytes)
            time.sleep(0.5)
            
            print("Sending test pattern to Display 2...")
            self._send_to_display(self.display2, rgb565_bytes)
            time.sleep(0.5)
            
            print("Display test completed!")
            
        except Exception as e:
            print(f"Display test failed: {e}")
            import traceback
            traceback.print_exc()
    
    def init_camera(self):
        """Initialize camera with Pi 5 optimized settings"""
        try:
            self.camera = Picamera2()
            
            # Pi 5 optimized configuration - higher resolution and better performance
            config = self.camera.create_video_configuration(
                main={"size": (self.camera_width, self.camera_height), "format": "YUV420"},
                # Add buffer configuration for Pi 5
                buffer_count=4,  # More buffers for smoother operation
                queue=True       # Enable frame queue for better performance
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
    
    def create_eye_image(self, eye_x, eye_y, blink_state=1.0, eye_cache=None):
        """Create eye image with blinking support + RGB565 pre-conversion + dynamic sizing"""
        current_eye_size = self.get_current_eye_size()
        return create_eye_image(eye_x, eye_y, blink_state, eye_cache, self.cache_size, self.current_eye_color, current_eye_size)
    
    def detect_face(self, frame):
        """Detect faces in the frame"""
        if self.face_cascade is None:
            return []
        
        # Convert frame to grayscale for face detection
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_YUV2GRAY)
        else:
            gray = frame
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        return faces
    
    def update_face_detection(self, faces):
        """Update face detection for color changes and face-following mode"""
        current_time = time.time()
        
        if len(faces) > 0:
            # Face detected! Set red eyes for 5 seconds
            if not self.face_detected:
                print("Face detected! Eyes turning red for 5 seconds...")
                self.face_detected = True
                self.target_eye_color = self.face_eye_color.copy()
            
            # Reset the timer
            self.last_face_detection_time = current_time
            
            # Update face size for eye sizing
            self.update_face_size(faces)
            
            # Handle face-following mode
            self.update_face_following(faces, current_time)
            
        else:
            # No face detected - check if we should turn eyes back to yellow
            if self.face_detected:
                if current_time - self.last_face_detection_time > self.face_detection_timeout:
                    print("No face detected for 5 seconds. Eyes returning to yellow...")
                    self.face_detected = False
                    self.target_eye_color = self.base_eye_color.copy()
                    # Return to basic eye size when face not found
                    self.target_eye_size_index = 15  # Middle size (basic size)
            
            # Exit face-following mode if no face
            if self.face_following_mode:
                print("No face detected. Exiting face-following mode...")
                self.face_following_mode = False
                self.current_face_center = None
    
    def update_face_following(self, faces, current_time):
        """Update face-following mode for eye positioning"""
        if len(faces) > 0:
            # Use the largest face (most prominent)
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest_face
            
            # Calculate face center
            face_center_x = x + w//2
            face_center_y = y + h//2
            self.current_face_center = (face_center_x, face_center_y)
            
            # Check if we should enter face-following mode
            # Only enter if there's been no recent motion
            time_since_motion = current_time - self.last_motion_time
            if not self.face_following_mode and time_since_motion > 1.0:  # 1 second of no motion
                print("Entering face-following mode! Eyes will track face for 5 seconds...")
                self.face_following_mode = True
                self.last_face_following_time = current_time
            
            # Reset face-following timer if in mode
            if self.face_following_mode:
                self.last_face_following_time = current_time
    
    def get_eye_position_from_face(self, face_center):
        """Calculate eye position based on face center"""
        if face_center is None:
            return (WIDTH//2, HEIGHT//2)
        
        face_x, face_y = face_center
        
        # Normalize face position (-1 to 1)
        norm_x = (face_x - self.camera_width//2) / (self.camera_width//2)
        norm_y = (face_y - self.camera_height//2) / (self.camera_height//2)
        
        # Map to display coordinates
        eye_x = WIDTH//2 - norm_x * (WIDTH//2 - 20)  # Inverted X
        eye_y = HEIGHT//2 + norm_y * (HEIGHT//2 - 20)  # Normal Y
        
        return (eye_x, eye_y)
    
    def update_face_size(self, faces):
        """Update face size history and calculate eye size"""
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
            
            # Calculate average face size
            if len(self.face_sizes) > 0:
                avg_face_size = sum(self.face_sizes) / len(self.face_sizes)
                
                # Map face size to eye size index (0-19)
                # Face size 50x50 (2500) -> smallest eyes (index 0)
                # Face size 240x240 (57600) -> largest eyes (index 19)
                face_ratio = (avg_face_size - self.min_face_size) / (self.max_face_size - self.min_face_size)
                face_ratio = max(0, min(1, face_ratio))  # Clamp between 0 and 1
                
                # Map to eye size index (0-19)
                self.target_eye_size_index = int(face_ratio * (self.total_eye_sizes - 1))
                
                # Log face size and target eye size
                print(f"Face: {w}x{h} (Area: {face_area:.0f}), Avg: {avg_face_size:.0f}, Target Eye Size: {self.target_eye_size_index + 1}/20")
    
    def update_eye_size_smoothly(self):
        """Smoothly animate eye size towards target"""
        # Calculate difference between current and target
        size_diff = self.target_eye_size_index - self.current_eye_size_index
        
        # If there's a difference, move towards target
        if abs(size_diff) > 0.1:  # Small threshold to avoid jitter
            # Move towards target by transition speed
            move_amount = size_diff * self.eye_size_transition_speed
            self.current_eye_size_index += move_amount
            
            # Clamp to valid range
            self.current_eye_size_index = max(0, min(self.total_eye_sizes - 1, self.current_eye_size_index))
    
    def get_current_eye_size(self):
        """Get current eye size based on face size"""
        # Eye sizes range from 20 to 80 pixels radius
        min_eye_size = 20
        max_eye_size = 80
        
        # Map index (0-19) to eye size (20-80)
        size_ratio = self.current_eye_size_index / (self.total_eye_sizes - 1)
        current_size = min_eye_size + (max_eye_size - min_eye_size) * size_ratio
        
        return int(current_size)
    
    def update_eye_color(self):
        """Smoothly transition eye color"""
        # Smooth color transition
        for i in range(3):  # RGB
            diff = self.target_eye_color[i] - self.current_eye_color[i]
            self.current_eye_color[i] += diff * self.color_transition_speed
            
            # Ensure values stay within valid range
            self.current_eye_color[i] = max(0, min(255, self.current_eye_color[i]))
    
    def detect_motion(self, frame):
        """Detect motion in the frame using frame difference"""
        # Extract Y channel from YUV420 (already grayscale!)
        if len(frame.shape) == 3:
            # YUV420 - extract Y channel (grayscale)
            gray = frame[:, :, 0]  # Y channel is first
        else:
            # Already grayscale
            gray = frame
        
        # Initialize previous frame
        if self.prev_frame is None:
            self.prev_frame = gray
            return []
        
        # Calculate frame difference
        frame_delta = cv2.absdiff(self.prev_frame, gray)
        _, thresh = cv2.threshold(frame_delta, self.motion_threshold, 255, cv2.THRESH_BINARY)
        
        # Update previous frame
        self.prev_frame = gray
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by area
        motion_boxes = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_motion_area:
                x, y, w, h = cv2.boundingRect(contour)
                motion_boxes.append((x, y, w, h))
        
        return motion_boxes
    
    def update_eye_position(self, motion_boxes):
        """Update eye position based on motion detection or face-following mode"""
        current_time = time.time()
        
        # Check for motion interruption of face-following mode
        if motion_boxes and len(motion_boxes) > 0:
            self.last_motion_time = current_time
            # If in face-following mode and motion detected, exit face-following
            if self.face_following_mode:
                print("Motion detected! Exiting face-following mode...")
                self.face_following_mode = False
                self.current_face_center = None
            
            # If in idle mode and motion detected, exit idle mode
            if self.idle_mode:
                print("Motion detected! Exiting idle mode...")
                self.exit_idle_mode()
        
        # Check if face-following mode should timeout
        if self.face_following_mode:
            if current_time - self.last_face_following_time > self.face_following_timeout:
                print("Face-following timeout. Returning to motion detection...")
                self.face_following_mode = False
                self.current_face_center = None
        
        # Check for idle animation trigger
        self.check_idle_animation_trigger(current_time)
        
        # Choose positioning method based on mode
        if self.idle_mode:
            # Idle animation mode - let idle animations handle positioning
            return
        elif self.face_following_mode and self.current_face_center:
            # Face-following mode - use face position
            eye_x, eye_y = self.get_eye_position_from_face(self.current_face_center)
            
            # Add to motion history for smoothing
            self.motion_history.append((eye_x, eye_y))
            if len(self.motion_history) > self.motion_history_size:
                self.motion_history.pop(0)
            
            # Calculate smoothed position
            if len(self.motion_history) >= 2:
                avg_x = sum(pos[0] for pos in self.motion_history) / len(self.motion_history)
                avg_y = sum(pos[1] for pos in self.motion_history) / len(self.motion_history)
                self.target_eye_position = (avg_x, avg_y)
                self.target_left_eye = (avg_x, avg_y)
                self.target_right_eye = (avg_x, avg_y)
            else:
                self.target_eye_position = (eye_x, eye_y)
                self.target_left_eye = (eye_x, eye_y)
                self.target_right_eye = (eye_x, eye_y)
                
        elif motion_boxes and len(motion_boxes) > 0:
            # Motion detection mode - use motion position
            self.last_motion_time = time.time()
            
            # Use the largest motion area (most significant movement)
            largest_motion = max(motion_boxes, key=lambda m: m[2] * m[3])
            x, y, w, h = largest_motion
            
            # Calculate motion center
            motion_center_x = x + w//2
            motion_center_y = y + h//2
            
            # Normalize motion position (-1 to 1)
            norm_x = (motion_center_x - self.camera_width//2) / (self.camera_width//2)
            norm_y = (motion_center_y - self.camera_height//2) / (self.camera_height//2)
            
            # Map to display coordinates with larger range
            eye_x = WIDTH//2 - norm_x * (WIDTH//2 - 20)  # Inverted X
            eye_y = HEIGHT//2 + norm_y * (HEIGHT//2 - 20)  # Normal Y
            
            # Add to motion history for smoothing
            self.motion_history.append((eye_x, eye_y))
            if len(self.motion_history) > self.motion_history_size:
                self.motion_history.pop(0)
            
            # Calculate smoothed position
            if len(self.motion_history) >= 2:
                # Average the last few positions to reduce shaking
                avg_x = sum(pos[0] for pos in self.motion_history) / len(self.motion_history)
                avg_y = sum(pos[1] for pos in self.motion_history) / len(self.motion_history)
                self.target_eye_position = (avg_x, avg_y)
                
                # Set both eyes to the same position (synchronized movement)
                self.target_left_eye = (avg_x, avg_y)
                self.target_right_eye = (avg_x, avg_y)
            else:
                self.target_eye_position = (eye_x, eye_y)
                self.target_left_eye = (eye_x, eye_y)
                self.target_right_eye = (eye_x, eye_y)
        else:
            # No motion detected - check timeout
            if time.time() - self.last_motion_time > self.motion_timeout:
                # Return to center after timeout
                center_pos = (WIDTH//2, HEIGHT//2)
                self.target_eye_position = center_pos
                self.target_left_eye = center_pos
                self.target_right_eye = center_pos
                self.motion_history.clear()  # Clear history when returning to center
    
    def smooth_eye_movement(self):
        """Smoothly interpolate eye movement for both eyes"""
        # Smooth left eye movement
        current_left_x, current_left_y = self.current_left_eye
        target_left_x, target_left_y = self.target_left_eye
        
        new_left_x = current_left_x + (target_left_x - current_left_x) * self.eye_movement_speed
        new_left_y = current_left_y + (target_left_y - current_left_y) * self.eye_movement_speed
        
        self.current_left_eye = (new_left_x, new_left_y)
        
        # Smooth right eye movement
        current_right_x, current_right_y = self.current_right_eye
        target_right_x, target_right_y = self.target_right_eye
        
        new_right_x = current_right_x + (target_right_x - current_right_x) * self.eye_movement_speed
        new_right_y = current_right_y + (target_right_y - current_right_y) * self.eye_movement_speed
        
        self.current_right_eye = (new_right_x, new_right_y)
        
        # Keep backward compatibility
        self.current_eye_position = self.current_left_eye
    
    def check_idle_animation_trigger(self, current_time):
        """Check if idle animation should be triggered"""
        if self.idle_mode:
            return  # Already in idle mode
        
        # Check if enough time has passed without motion
        time_since_motion = current_time - self.last_motion_time
        
        if time_since_motion >= self.idle_trigger_delay:
            print(f"No motion for {time_since_motion:.1f}s. Starting idle animation...")
            self.start_idle_mode()
    
    def start_idle_mode(self):
        """Start idle animation mode"""
        if self.idle_animations is None:
            return
        
        self.idle_mode = True
        self.idle_start_time = time.time()
        self.idle_animation_started = False
        
        # Generate new random delays for next time
        self.idle_trigger_delay = np.random.uniform(5, 10)  # 5-10 seconds for testing
        self.idle_resume_delay = np.random.uniform(5, 10)  # 5-10 seconds delay before resuming
        
        print(f"Idle mode started. Will resume tracking after {self.idle_resume_delay:.1f}s")
    
    def exit_idle_mode(self):
        """Exit idle animation mode"""
        self.idle_mode = False
        self.idle_start_time = None
        self.idle_animation_started = False
        
        # Reset eye positions to center
        center_pos = (WIDTH//2, HEIGHT//2)
        self.target_eye_position = center_pos
        self.target_left_eye = center_pos
        self.target_right_eye = center_pos
        self.motion_history.clear()
        
        print("Exited idle mode. Returning to motion tracking...")
    
    def update_idle_animation(self):
        """Update idle animation if in idle mode"""
        if not self.idle_mode or self.idle_animations is None:
            return
        
        current_time = time.time()
        
        # Check if animation should end
        if current_time - self.idle_start_time >= self.idle_resume_delay:
            print("Idle animation timeout. Resuming motion tracking...")
            self.exit_idle_mode()
            return
        
        # Start animation if not started yet
        if not self.idle_animation_started:
            self.idle_animations.start_random_animation()
            self.idle_animation_started = True
        
        # Update animation
        self.idle_animations.update()
        
        # Get animation positions
        left_pos, right_pos = self.idle_animations.get_current_positions()
        
        # Debug: print positions occasionally
        if int(time.time()) != getattr(self, '_last_idle_debug', -1):
            self._last_idle_debug = int(time.time())
            print(f"Idle animation positions: Left={left_pos}, Right={right_pos}")
        
        # Update target positions
        self.target_left_eye = left_pos
        self.target_right_eye = right_pos
        
        # Handle special blink states from idle animations (animation 4)
        if hasattr(self.idle_animations, 'left_blink_state') and hasattr(self.idle_animations, 'right_blink_state'):
            # Override normal blinking with animation-specific blinking
            self.left_blink_state = self.idle_animations.left_blink_state
            self.right_blink_state = self.idle_animations.right_blink_state
    
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
        
        # Calculate data transfer (full screen update)
        full_screen_bytes = WIDTH * HEIGHT * 2  # Full screen RGB565
        
        print("=" * 60)
        print(f"FPS: {self.current_fps:.1f} | Frame Time: {avg_total:.1f}ms")
        print(f"  Camera Capture:   {avg_capture:.2f}ms ({self.camera_width}x{self.camera_height} YUV)")
        print(f"  Motion Detection: {avg_motion:.2f}ms (Frame Difference)")
        print(f"  Display Update:    {avg_display:.2f}ms (full screen)")
        print(f"  Other/Overhead:   {(avg_total - avg_capture - avg_motion):.2f}ms")
        print(f"  Data Transfer:     {full_screen_bytes:,} bytes (full screen)")
        print(f"  Camera Resolution: {self.camera_width}x{self.camera_height} (YUV420)")
        print(f"  Motion Detection: Frame Difference + Contours")
        print(f"  Display Resolution: 240x240 (full resolution)")
        print(f"  Display FPS:       60 Hz (Pi 5 optimized)")
        print(f"  SPI Speed:         150 MHz (Pi 5 optimized)")
        print(f"  Motion Tracking:   Every frame")
        
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
                
                # Capture frame for face detection
                t0 = time.time()
                frame = self.camera.capture_array()
                capture_time = (time.time() - t0) * 1000  # ms
                
                # Motion detection (every frame for better tracking)
                t1 = time.time()
                motion_boxes = self.detect_motion(frame)
                motion_time = (time.time() - t1) * 1000  # ms
                
                # Face detection (every 60 frames)
                faces = []
                face_detection_time = 0
                self.face_detection_counter += 1
                
                if self.face_detection_counter >= self.face_detection_interval:
                    t2 = time.time()
                    faces = self.detect_face(frame)
                    face_detection_time = (time.time() - t2) * 1000  # ms
                    self.face_detection_counter = 0
                    
                    # Update face detection for color changes
                    self.update_face_detection(faces)
                
                # Update eye position based on motion detection only
                self.update_eye_position(motion_boxes)
                
                # Store timing
                self.timing_capture.append(capture_time)
                self.timing_motion.append(motion_time + face_detection_time)
                
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
                        self.frame_queue.put_nowait((frame, motion_boxes, faces))
                    except queue.Full:
                        # Drop oldest frame
                        try:
                            self.frame_queue.get_nowait()
                            self.frame_queue.put_nowait((frame, motion_boxes, faces))
                        except:
                            pass
                
            except Exception as e:
                print(f"Camera thread error: {e}")
                time.sleep(0.1)
    
    def display_thread_func(self):
        """Display thread - LIMITED to 15 FPS to not block camera"""
        while self.running:
            try:
                # Check if displays are initialized
                if not self.display1 or not self.display2:
                    time.sleep(0.1)
                    continue
                
                # Smooth eye movement
                self.smooth_eye_movement()
                
                # Update idle animation if in idle mode
                self.update_idle_animation()
                
                # Smooth eye size animation
                self.update_eye_size_smoothly()
                
                # Handle blinking (more natural, human-like)
                current_time = time.time()
                if not self.is_blinking and (current_time - self.last_blink_time) >= self.next_blink_delay:
                    # Start blink
                    self.is_blinking = True
                    self.blink_state = 1.0
                    self.blink_direction = -1  # Start closing
                
                if self.is_blinking:
                    # Animate blink with smooth, natural timing
                    # Human blink: ~100-150ms total (close faster than open)
                    if self.blink_direction == -1:
                        # Closing phase (faster)
                        self.blink_state -= 0.25  # Close in ~4 frames (200ms at 20fps)
                        if self.blink_state <= 0.0:
                            self.blink_state = 0.0
                            self.blink_direction = 1  # Switch to opening
                    else:
                        # Opening phase (slightly slower)
                        self.blink_state += 0.2  # Open in ~5 frames (250ms at 20fps)
                        if self.blink_state >= 1.0:
                            self.blink_state = 1.0
                            self.is_blinking = False
                            self.last_blink_time = current_time
                            # More realistic timing: 3-8 seconds between blinks
                            self.next_blink_delay = np.random.uniform(3, 8)
                
                # Update eye color smoothly
                self.update_eye_color()
                
                # Update both displays
                self._update_both_displays()
                
                # Pi 5 optimized: 60 FPS for smoother eye movement
                time.sleep(1.0/60.0)
                
            except Exception as e:
                print(f"Display thread error: {e}")
                time.sleep(0.1)
    
    def _update_both_displays(self):
        """Update both displays with current eye positions"""
        # Get current eye positions
        left_eye_x, left_eye_y = self.current_left_eye
        right_eye_x, right_eye_y = self.current_right_eye
        
        # Check if we need to update (optimization)
        left_rounded_pos = (round(left_eye_x / 5) * 5, round(left_eye_y / 5) * 5, round(self.blink_state * 10) / 10)
        right_rounded_pos = (round(right_eye_x / 5) * 5, round(right_eye_y / 5) * 5, round(self.blink_state * 10) / 10)
        
        # Check if positions changed significantly
        left_changed = left_rounded_pos != self.last_rendered_pos_left
        right_changed = right_rounded_pos != self.last_rendered_pos_right
        blink_changed = self.is_blinking and (self.blink_state != getattr(self, 'last_blink_state', 1.0))
        
        if left_changed or blink_changed:
            t0 = time.time()
            
            # Use separate blink states if in idle mode
            if self.idle_mode and hasattr(self, 'left_blink_state'):
                left_blink_value = self.left_blink_state
            else:
                left_blink_value = self.blink_state
            
            # Generate left eye image
            rgb565_bytes_left = self.create_eye_image(int(left_eye_x), int(left_eye_y), left_blink_value, self.eye_cache_left)
            
            # Update left display
            self._send_to_display(self.display1, rgb565_bytes_left)
            
            self.last_rendered_pos_left = left_rounded_pos
        
        if right_changed or blink_changed:
            t0 = time.time()
            
            # Use separate blink states if in idle mode
            if self.idle_mode and hasattr(self, 'right_blink_state'):
                right_blink_value = self.right_blink_state
            else:
                right_blink_value = self.blink_state
            
            # Generate right eye image
            rgb565_bytes_right = self.create_eye_image(int(right_eye_x), int(right_eye_y), right_blink_value, self.eye_cache_right)
            
            # Update right display
            self._send_to_display(self.display2, rgb565_bytes_right)
            
            self.last_rendered_pos_right = right_rounded_pos
        
        if left_changed or right_changed or blink_changed:
            display_time = (time.time() - t0) * 1000  # ms
            self.timing_display.append(display_time)
            self.last_blink_state = self.blink_state
    
    def _send_to_display(self, display, rgb565_bytes):
        """Send RGB565 data to a specific display"""
        send_to_display(display, rgb565_bytes)
                

    def start(self):
        """Start the eye tracker - uses external run function"""
        from eye_tracker_main import run_eye_tracker
        run_eye_tracker(self)
    
    def stop(self):
        """Stop the eye tracker"""
        self.running = False
        
        if self.display1:
            self.display1.close()
        if self.display2:
            self.display2.close()
        if self.camera:
            self.camera.close()
        cv2.destroyAllWindows()
        print("Dual Eye Tracker stopped")

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Dual Eye Tracker with GC9A01 Displays')
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
        print("Dual display mode")
        print("=" * 50)
    else:
        print("=" * 50)
        print("DUAL EYE TRACKER MODE")
        print("Both displays will track motion together")
        print("=" * 50)
    
    eye_tracker.start()

if __name__ == "__main__":
    main()

