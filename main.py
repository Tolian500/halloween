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
        
        # Face detection and tracking
        self.face_detection_counter = 0
        self.face_detection_interval = 60  # Run face detection every 60 frames
        self.face_tracking_mode = False
        self.current_face_center = None
        self.face_tracking_timeout = 5.0  # Stop face tracking after 5 seconds of no face
        self.last_face_time = time.time()
        
        # Eye color system
        self.base_eye_color = [200, 50, 25]  # Red (motion detection)
        self.face_eye_color = [255, 165, 0]  # Orange (face tracking)
        self.current_eye_color = self.base_eye_color.copy()
        self.color_transition_speed = 0.05  # How fast colors change
        self.target_eye_color = self.base_eye_color.copy()  
        
        # Pre-rendered eye cache (optimization #1) - separate for each eye
        self.eye_cache_left = {}
        self.eye_cache_right = {}
        self.cache_size = 50  # Cache 50 eye positions (more aggressive)
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
        """Initialize camera with optimized resolution for motion detection"""
        try:
            self.camera = Picamera2()
            
            # Use optimized resolution for motion detection
            config = self.camera.create_video_configuration(
                main={"size": (self.camera_width, self.camera_height), "format": "YUV420"}
            )
            self.camera.configure(config)
            
            self.camera.start()
            print(f"Camera: {self.camera_width}x{self.camera_height} (YUV420, motion detection mode)")
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
        """Create eye image with blinking support + RGB565 pre-conversion"""
        return create_eye_image(eye_x, eye_y, blink_state, eye_cache, self.cache_size, self.current_eye_color)
    
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
    
    def update_face_tracking(self, faces):
        """Update face tracking mode based on detected faces"""
        current_time = time.time()
        
        if len(faces) > 0:
            # Face detected!
            self.last_face_time = current_time
            
            if not self.face_tracking_mode:
                print("Face detected! Switching to face tracking mode...")
                self.face_tracking_mode = True
                self.target_eye_color = self.face_eye_color.copy()
            
            # Use the largest face (most prominent)
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest_face
            
            # Calculate face center
            face_center_x = x + w//2
            face_center_y = y + h//2
            
            self.current_face_center = (face_center_x, face_center_y)
            
        else:
            # No face detected
            if self.face_tracking_mode:
                # Check if we should exit face tracking mode
                if current_time - self.last_face_time > self.face_tracking_timeout:
                    print("No face detected for 5 seconds. Switching back to motion detection...")
                    self.face_tracking_mode = False
                    self.target_eye_color = self.base_eye_color.copy()
                    self.current_face_center = None
    
    def update_eye_color(self):
        """Smoothly transition eye color"""
        # Smooth color transition
        for i in range(3):  # RGB
            diff = self.target_eye_color[i] - self.current_eye_color[i]
            self.current_eye_color[i] += diff * self.color_transition_speed
            
            # Ensure values stay within valid range
            self.current_eye_color[i] = max(0, min(255, self.current_eye_color[i]))
    
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
    
    def update_eye_position(self, motion_boxes, faces=None):
        """Update eye position based on motion detection or face tracking"""
        if self.face_tracking_mode and self.current_face_center:
            # Face tracking mode - use face position
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
        print(f"  Display FPS:       30 Hz")
        print(f"  SPI Speed:         100 MHz")
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
                    
                    # Update face tracking mode
                    self.update_face_tracking(faces)
                
                # Update eye position based on motion detection or face tracking
                self.update_eye_position(motion_boxes, faces)
                
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
                
                # 30 FPS for faster eye movement
                time.sleep(1.0/30.0)
                
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
            
            # Generate left eye image
            rgb565_bytes_left = self.create_eye_image(int(left_eye_x), int(left_eye_y), self.blink_state, self.eye_cache_left)
            
            # Update left display
            self._send_to_display(self.display1, rgb565_bytes_left)
            
            self.last_rendered_pos_left = left_rounded_pos
        
        if right_changed or blink_changed:
            t0 = time.time()
            
            # Generate right eye image
            rgb565_bytes_right = self.create_eye_image(int(right_eye_x), int(right_eye_y), self.blink_state, self.eye_cache_right)
            
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

