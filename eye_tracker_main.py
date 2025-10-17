#!/usr/bin/env python3
"""
Main loop for the eye tracker - separated to avoid indentation issues
"""

import cv2
import queue
import time


def run_eye_tracker(eye_tracker):
    """
    Main loop for running the eye tracker
    
    Args:
        eye_tracker: EyeTracker instance
    """
    print("Starting Eye Tracker...")
    
    # Initialize components
    if not eye_tracker.init_display():
        return False
    if not eye_tracker.init_camera():
        return False
    if not eye_tracker.init_face_detection():
        return False
    
    eye_tracker.running = True
    
    # Start threads
    import threading
    display_thread = threading.Thread(target=eye_tracker.display_thread_func, daemon=True)
    display_thread.start()
    
    camera_thread = threading.Thread(target=eye_tracker.camera_thread, daemon=True)
    camera_thread.start()
    
    if eye_tracker.enable_preview:
        print("Eye Tracker started with preview! Press 'q' in preview window to quit.")
    else:
        print("Eye Tracker started (no preview - max performance)! Press Ctrl+C to stop.")
    
    try:
        # Main loop for OpenCV display (only if preview enabled)
        while eye_tracker.running and eye_tracker.enable_preview:
            try:
                frame, motion_boxes, faces = eye_tracker.frame_queue.get(timeout=1.0)
                
                # Convert to BGR for OpenCV (handle YUV420)
                if len(frame.shape) == 3:
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_YUV2BGR)
                else:
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                
                # Draw motion detection rectangles on frame
                if motion_boxes is not None and len(motion_boxes) > 0:  # Check if not None and not empty
                    for (x, y, w, h) in motion_boxes:
                        cv2.rectangle(frame_bgr, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        # Draw center point
                        center_x = x + w//2
                        center_y = y + h//2
                        cv2.circle(frame_bgr, (center_x, center_y), 5, (0, 0, 255), -1)
                        # Add motion label
                        cv2.putText(frame_bgr, 'Motion', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                # Draw face detection rectangles on frame
                if faces is not None and len(faces) > 0:  # Check if not None and not empty
                    for (x, y, w, h) in faces:
                        cv2.rectangle(frame_bgr, (x, y), (x+w, y+h), (0, 165, 255), 2)  # Orange color
                        # Draw center point
                        center_x = x + w//2
                        center_y = y + h//2
                        cv2.circle(frame_bgr, (center_x, center_y), 5, (0, 165, 255), -1)  # Orange color
                        # Add face label
                        cv2.putText(frame_bgr, 'Face', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
                
                # Add mode indicator
                mode_text = "Face Tracking" if eye_tracker.face_tracking_mode else "Motion Detection"
                mode_color = (0, 165, 255) if eye_tracker.face_tracking_mode else (0, 255, 0)
                cv2.putText(frame_bgr, mode_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, mode_color, 2)
                
                # Show at full resolution for better visibility
                cv2.imshow('Motion Detection', frame_bgr)
                
                # Check for 'q' key press to quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
            except queue.Empty:
                continue
        
        # If no preview, just wait for Ctrl+C
        if not eye_tracker.enable_preview:
            while eye_tracker.running:
                time.sleep(0.1)
                
    except KeyboardInterrupt:
        print("\nStopping Eye Tracker...")
    finally:
        eye_tracker.stop()

