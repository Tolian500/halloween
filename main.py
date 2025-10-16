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
        
        # Motion detection variables
        self.prev_frame = None
        self.motion_threshold = 35  # Higher threshold to reduce false motion
        self.min_motion_area = 800  # Larger area to reduce sensitivity
        self.camera_width = 80  # EXTREME-LOW: 80x80 for maximum speed
        self.camera_height = 80  # Square format
        
        # Pre-rendered eye cache (optimization #1)
        self.eye_cache = {}
        self.cache_size = 50  # Cache 50 eye positions (more aggressive)
        self.last_rendered_pos = None
        
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
        """Initialize the GC9A01 display"""
        try:
            self.display = GC9A01()
            print("GC9A01 display initialized successfully!")
            return True
        except Exception as e:
            print(f"Failed to initialize display: {e}")
            return False
    
    def init_camera(self):
        """Initialize camera with EXTREME-LOW 80×80 resolution + grayscale optimization"""
        try:
            self.camera = Picamera2()
            
            # EXTREME-LOW resolution: 80×80 - NO raw sensor (too slow!)
            # Use grayscale format for 25% faster processing
            config = self.camera.create_video_configuration(
                main={"size": (self.camera_width, self.camera_height), "format": "YUV420"}
                # YUV420 gives us grayscale Y channel directly - no conversion needed!
            )
            self.camera.configure(config)
            
            self.camera.start()
            print(f"Camera: {self.camera_width}x{self.camera_height} (Grayscale/YUV, ultra-fast mode)")
            print(f"Sensor resolution: {self.camera.sensor_resolution}")
            print("NOTE: Using grayscale format + cropped FOV for maximum speed!")
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
    
    def create_eye_image(self, eye_x, eye_y, blink_state=1.0):
        """Create eye image with blinking support + RGB565 pre-conversion"""
        # Round to nearest 5 pixels for smoother movement (still good caching)
        cache_x = round(eye_x / 5) * 5
        cache_y = round(eye_y / 5) * 5
        blink_key = round(blink_state * 10) / 10  # Cache different blink states
        cache_key = (cache_x, cache_y, blink_key)
        
        # Check cache first (cache stores RGB565 bytes directly!)
        if cache_key in self.eye_cache:
            return self.eye_cache[cache_key]
        
        # OPTIMIZATION 8: Reduce rendered image resolution (120x120 instead of 240x240)
        # Render at half resolution then scale up - 4x faster!
        render_size = 120
        scale_factor = WIDTH // render_size  # 2x scale
        
        # Create smaller image for rendering
        img_array = np.zeros((render_size, render_size, 3), dtype=np.uint8)
        
        # Scale eye position to render coordinates
        render_x = int(eye_x // scale_factor)
        render_y = int(eye_y // scale_factor)
        
        # Smaller eye for faster display (40% size reduction)
        iris_radius = 25  # Scaled down from 50
        pupil_radius = 12  # Scaled down from 25
        
        # Calculate eye position (clamp to render bounds with margin)
        render_x = int(max(iris_radius, min(render_size - iris_radius, render_x)))
        render_y = int(max(iris_radius, min(render_size - iris_radius, render_y)))
        
        # Apply blink (compress vertically)
        y, x = np.ogrid[:render_size, :render_size]
        
        if blink_state < 1.0:
            # Create eyelid effect (close from top and bottom)
            eyelid_top = int(render_size//2 - (render_size//2) * blink_state)
            eyelid_bottom = int(render_size//2 + (render_size//2) * blink_state)
            
            # Only draw eye in visible area
            if eyelid_bottom > eyelid_top:
                # Draw iris (red circle) with blink mask
                mask_iris = ((x - render_x)**2 + (y - render_y)**2 <= iris_radius**2) & (y >= eyelid_top) & (y <= eyelid_bottom)
                img_array[mask_iris] = [200, 50, 25]  # Red iris
                
                # Draw pupil (black circle) with blink mask
                mask_pupil = ((x - render_x)**2 + (y - render_y)**2 <= pupil_radius**2) & (y >= eyelid_top) & (y <= eyelid_bottom)
                img_array[mask_pupil] = [0, 0, 0]  # Black pupil
                
                # Draw highlight (white circle) - offset, with blink mask
                highlight_x = render_x + 6
                highlight_y = render_y - 4
                mask_highlight = ((x - highlight_x)**2 + (y - highlight_y)**2 <= 6**2) & (y >= eyelid_top) & (y <= eyelid_bottom)
                img_array[mask_highlight] = [255, 255, 255]  # White highlight
        else:
            # Fully open eye
            mask_iris = (x - render_x)**2 + (y - render_y)**2 <= iris_radius**2
            img_array[mask_iris] = [200, 50, 25]  # Red iris
            
            mask_pupil = (x - render_x)**2 + (y - render_y)**2 <= pupil_radius**2
            img_array[mask_pupil] = [0, 0, 0]  # Black pupil
            
            highlight_x = render_x + 6
            highlight_y = render_y - 4
            mask_highlight = (x - highlight_x)**2 + (y - highlight_y)**2 <= 6**2
            img_array[mask_highlight] = [255, 255, 255]  # White highlight
        
        # Convert RGB888 to RGB565 using NumPy (10x faster than PIL!)
        r = (img_array[:, :, 0] >> 3).astype(np.uint16)  # 5 bits
        g = (img_array[:, :, 1] >> 2).astype(np.uint16)  # 6 bits
        b = (img_array[:, :, 2] >> 3).astype(np.uint16)  # 5 bits
        rgb565_small = (r << 11) | (g << 5) | b
        
        # Scale up to full resolution using NumPy broadcasting (much faster!)
        rgb565_full = np.zeros((HEIGHT, WIDTH), dtype=np.uint16)
        
        # Use NumPy's repeat function for efficient scaling
        rgb565_full = np.repeat(np.repeat(rgb565_small, scale_factor, axis=0), scale_factor, axis=1)
        
        # Convert to bytes (big-endian for SPI)
        rgb565_bytes = rgb565_full.astype('>u2').tobytes()
        
        # Cache management - keep only recent entries
        if len(self.eye_cache) >= self.cache_size:
            # Remove oldest entry
            self.eye_cache.pop(next(iter(self.eye_cache)))
        
        # Cache the RGB565 bytes directly!
        self.eye_cache[cache_key] = rgb565_bytes
        return rgb565_bytes
    
    def detect_motion(self, frame):
        """EXTREME-FAST motion detection at 32×32 pixels with grayscale optimization!"""
        # Extract Y channel from YUV420 (already grayscale!)
        if len(frame.shape) == 3:
            # YUV420 - extract Y channel (grayscale)
            gray = frame[:, :, 0]  # Y channel is first
        else:
            # Already grayscale
            gray = frame
        
        # Extreme downsample to 32x32 (1024 pixels!) - even smaller for speed
        tiny = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_NEAREST)
        
        # Initialize previous frame
        if self.prev_frame is None:
            self.prev_frame = tiny
            return None
        
        # NO BLUR - saves 5-10ms
        # Direct difference (in-place operation)
        frame_delta = cv2.absdiff(self.prev_frame, tiny)
        _, thresh = cv2.threshold(frame_delta, self.motion_threshold, 255, cv2.THRESH_BINARY)
        
        # Update previous frame (reuse buffer)
        self.prev_frame = tiny
        
        # Use moments instead of contours (MUCH faster)
        moments = cv2.moments(thresh)
        
        if moments["m00"] > 25:  # Higher threshold to reduce false motion
            # Calculate centroid
            cx = int(moments["m10"] / moments["m00"])
            cy = int(moments["m01"] / moments["m00"])
            
            # Scale from 32x32 to 80x80 (2.5x)
            x = int(cx * 2.5)
            y = int(cy * 2.5)
            
            # Return fake bounding box
            return [(x, y, 16, 16)]
        
        return []
    
    def update_eye_position(self, motion_boxes):
        """Update eye position with BIGGER movement range + return to center + smoothing"""
        if motion_boxes and len(motion_boxes) > 0:
            # Motion detected!
            self.last_motion_time = time.time()
            
            # Use the first detected motion
            x, y, w, h = motion_boxes[0]
            motion_center_x = x + w//2
            motion_center_y = y + h//2
            
            # Normalize motion position (-1 to 1)
            norm_x = (motion_center_x - self.camera_width//2) / (self.camera_width//2)
            norm_y = (motion_center_y - self.camera_height//2) / (self.camera_height//2)
            
            # Map to display coordinates with MUCH larger range (margin to margin)
            eye_x = WIDTH//2 - norm_x * (WIDTH//2 - 10)  # Inverted X, less margin
            eye_y = HEIGHT//2 + norm_y * (HEIGHT//2 - 10)  # Less margin
            
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
            else:
                self.target_eye_position = (eye_x, eye_y)
        else:
            # No motion detected - check timeout
            if time.time() - self.last_motion_time > self.motion_timeout:
                # Return to center after timeout
                self.target_eye_position = (WIDTH//2, HEIGHT//2)
                self.motion_history.clear()  # Clear history when returning to center
    
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
        
        # Calculate data transfer (full screen update)
        full_screen_bytes = WIDTH * HEIGHT * 2  # Full screen RGB565
        
        print("=" * 60)
        print(f"FPS: {self.current_fps:.1f} | Frame Time: {avg_total:.1f}ms")
        print(f"  Camera Capture:   {avg_capture:.2f}ms (80x80 grayscale)")
        print(f"  Motion Detection: {avg_motion:.2f}ms (32x32 pixels)")
        print(f"  Display Update:    {avg_display:.2f}ms (full screen)")
        print(f"  Other/Overhead:   {(avg_total - avg_capture - avg_motion):.2f}ms")
        print(f"  Data Transfer:     {full_screen_bytes:,} bytes (full screen)")
        print(f"  Camera Resolution: {self.camera_width}x{self.camera_height} (YUV420)")
        print(f"  Motion Resolution: 32x32 (grayscale)")
        print(f"  Display Resolution: 120x120 → 240x240 (2x scale)")
        print(f"  Display FPS:       20 Hz (proven)")
        print(f"  SPI Speed:         80 MHz (stable)")
        print(f"  Frame Skipping:    Every {self.frame_skip_interval + 1} frames")
        print(f"  Motion Detection:  Every {self.motion_check_interval} frames")
        
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
                
                # Capture frame with skipping (optimization #3)
                t0 = time.time()
                
                # Skip frames when system overloaded - grab without decoding
                self.frame_skip_counter += 1
                if self.frame_skip_counter >= self.frame_skip_interval:
                    self.frame_skip_counter = 0
                    frame = self.camera.capture_array()
                else:
                    # Skip this frame - reuse previous frame
                    if not hasattr(self, 'last_frame'):
                        frame = self.camera.capture_array()
                    else:
                        frame = self.last_frame
                
                self.last_frame = frame
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
                
                # OPTIMIZATION 11: Skip updates if eye position hasn't changed significantly
                eye_x, eye_y = self.current_eye_position
                rounded_pos = (round(eye_x / 5) * 5, round(eye_y / 5) * 5, round(self.blink_state * 10) / 10)
                
                # Only update if moved significantly or blink state changed
                position_changed = rounded_pos != self.last_rendered_pos
                blink_changed = self.is_blinking and (self.blink_state != getattr(self, 'last_blink_state', 1.0))
                
                if position_changed or blink_changed:
                    t0 = time.time()
                    
                    # Generate eye image
                    rgb565_bytes = self.create_eye_image(int(eye_x), int(eye_y), self.blink_state)
                    
                    # SIMPLE: Full screen update - no smart clearing, no windows
                    self.display._write_command(0x2A)  # Column address set
                    self.display._write_data([0x00, 0x00, 0x00, 0xEF])  # 0 to 239
                    self.display._write_command(0x2B)  # Row address set
                    self.display._write_data([0x00, 0x00, 0x00, 0xEF])  # 0 to 239
                    self.display._write_command(0x2C)  # Memory write
                    
                    # Send full screen data
                    GPIO.output(self.display.dc_pin, GPIO.HIGH)
                    
                    # Send data in larger chunks for better performance
                    chunk_size = 8192  # Larger chunks for faster transfer
                    for i in range(0, len(rgb565_bytes), chunk_size):
                        chunk = rgb565_bytes[i:i+chunk_size]
                        self.display.spi.writebytes(chunk)  # SPI handles CS automatically
                    
                    display_time = (time.time() - t0) * 1000  # ms
                    self.timing_display.append(display_time)
                    self.last_rendered_pos = rounded_pos
                    self.last_blink_state = self.blink_state
                
                # 30 FPS for faster eye movement
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

