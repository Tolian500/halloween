#!/usr/bin/env python3
"""
Camera Preview Testing Script
Shows full camera sensor resolution with live resolution changing
"""

import cv2
import numpy as np
import time
from picamera2 import Picamera2
import threading
import queue

class CameraPreviewTester:
    def __init__(self):
        self.camera = None
        self.running = False
        self.current_resolution = (640, 480)
        self.sensor_resolution = None
        self.frame_queue = queue.Queue(maxsize=2)
        
        # Available resolutions to test
        self.resolutions = [
            (640, 480),    # VGA
            (800, 600),    # SVGA
            (1024, 768),   # XGA
            (1280, 720),   # HD
            (1280, 960),   # SXGA
            (1600, 1200),  # UXGA
            (1920, 1080),  # Full HD
            (2048, 1536),  # QXGA
            (2592, 1944),  # 5MP
            (3280, 2464),  # 8MP
        ]
        
        # Current resolution index
        self.resolution_index = 0
        
    def init_camera(self):
        """Initialize camera with current resolution"""
        try:
            if self.camera:
                self.camera.stop()
                self.camera.close()
            
            self.camera = Picamera2()
            
            # Get sensor resolution first
            self.sensor_resolution = self.camera.sensor_resolution
            print(f"Sensor resolution: {self.sensor_resolution}")
            
            # Create configuration with current resolution
            config = self.camera.create_video_configuration(
                main={"size": self.current_resolution, "format": "RGB888"}
            )
            self.camera.configure(config)
            self.camera.start()
            
            print(f"Camera initialized: {self.current_resolution[0]}x{self.current_resolution[1]}")
            return True
            
        except Exception as e:
            print(f"Camera init failed: {e}")
            return False
    
    def camera_thread(self):
        """Camera capture thread"""
        while self.running:
            try:
                if self.camera:
                    frame = self.camera.capture_array()
                    
                    # Add frame to queue
                    try:
                        self.frame_queue.put_nowait(frame)
                    except queue.Full:
                        # Remove old frame and add new one
                        try:
                            self.frame_queue.get_nowait()
                            self.frame_queue.put_nowait(frame)
                        except:
                            pass
                
                time.sleep(0.033)  # ~30 FPS
                
            except Exception as e:
                print(f"Camera thread error: {e}")
                time.sleep(0.1)
    
    def create_control_window(self):
        """Create control window with resolution buttons"""
        cv2.namedWindow('Camera Controls', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Camera Controls', 400, 300)
        
        # Create control image
        control_img = np.zeros((300, 400, 3), dtype=np.uint8)
        
        # Title
        cv2.putText(control_img, 'Camera Resolution Controls', (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Current resolution
        cv2.putText(control_img, f'Current: {self.current_resolution[0]}x{self.current_resolution[1]}', 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        # Sensor resolution
        if self.sensor_resolution:
            cv2.putText(control_img, f'Sensor: {self.sensor_resolution[0]}x{self.sensor_resolution[1]}', 
                       (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Instructions
        cv2.putText(control_img, 'Controls:', (10, 110), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        cv2.putText(control_img, 'UP/DOWN: Change resolution', (10, 130), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(control_img, 'SPACE: Next resolution', (10, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(control_img, 'R: Reset to sensor resolution', (10, 170), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(control_img, 'ESC: Exit', (10, 190), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Resolution list
        cv2.putText(control_img, 'Available Resolutions:', (10, 220), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        # Show current resolution index
        if 0 <= self.resolution_index < len(self.resolutions):
            res = self.resolutions[self.resolution_index]
            cv2.putText(control_img, f'[{self.resolution_index}] {res[0]}x{res[1]}', 
                       (10, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        # Show next resolution
        next_idx = (self.resolution_index + 1) % len(self.resolutions)
        if next_idx < len(self.resolutions):
            next_res = self.resolutions[next_idx]
            cv2.putText(control_img, f'Next: {next_res[0]}x{next_res[1]}', 
                       (10, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (128, 128, 128), 1)
        
        cv2.imshow('Camera Controls', control_img)
    
    def change_resolution(self, new_resolution):
        """Change camera resolution"""
        try:
            print(f"Changing resolution to {new_resolution[0]}x{new_resolution[1]}...")
            
            # Stop camera
            self.camera.stop()
            
            # Create new configuration
            config = self.camera.create_video_configuration(
                main={"size": new_resolution, "format": "RGB888"}
            )
            self.camera.configure(config)
            self.camera.start()
            
            self.current_resolution = new_resolution
            print(f"Resolution changed to: {new_resolution[0]}x{new_resolution[1]}")
            
            # Clear frame queue
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except:
                    break
                    
        except Exception as e:
            print(f"Failed to change resolution: {e}")
    
    def run(self):
        """Main testing loop"""
        print("Camera Preview Tester")
        print("=" * 50)
        
        # Initialize camera
        if not self.init_camera():
            print("Failed to initialize camera!")
            return
        
        self.running = True
        
        # Start camera thread
        camera_thread = threading.Thread(target=self.camera_thread, daemon=True)
        camera_thread.start()
        
        # Create windows
        cv2.namedWindow('Camera Preview', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Camera Preview', 800, 600)
        
        print("Camera preview started!")
        print("Use the control window to change resolution")
        print("Press ESC to exit")
        
        try:
            while self.running:
                # Update control window
                self.create_control_window()
                
                # Get frame from camera
                try:
                    frame = self.frame_queue.get(timeout=0.1)
                    
                    # Add resolution info to frame
                    info_text = f"{self.current_resolution[0]}x{self.current_resolution[1]}"
                    cv2.putText(frame, info_text, (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
                    # Add FPS info
                    fps_text = f"FPS: {len(self.frame_queue.queue) * 10}"
                    cv2.putText(frame, fps_text, (10, 70), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Show frame
                    cv2.imshow('Camera Preview', frame)
                    
                except queue.Empty:
                    pass
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                
                if key == 27:  # ESC
                    break
                elif key == ord(' '):  # SPACE - next resolution
                    self.resolution_index = (self.resolution_index + 1) % len(self.resolutions)
                    self.change_resolution(self.resolutions[self.resolution_index])
                elif key == ord('r') or key == ord('R'):  # R - reset to sensor resolution
                    if self.sensor_resolution:
                        self.change_resolution(self.sensor_resolution)
                elif key == 82:  # UP arrow
                    self.resolution_index = (self.resolution_index - 1) % len(self.resolutions)
                    self.change_resolution(self.resolutions[self.resolution_index])
                elif key == 84:  # DOWN arrow
                    self.resolution_index = (self.resolution_index + 1) % len(self.resolutions)
                    self.change_resolution(self.resolutions[self.resolution_index])
                
        except KeyboardInterrupt:
            print("\nStopping camera preview...")
        
        finally:
            self.running = False
            if self.camera:
                self.camera.stop()
                self.camera.close()
            cv2.destroyAllWindows()
            print("Camera preview stopped")

def main():
    """Main function"""
    tester = CameraPreviewTester()
    tester.run()

if __name__ == "__main__":
    main()