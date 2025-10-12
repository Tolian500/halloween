#!/usr/bin/env python3
"""
Main loop for the eye tracker - separated to avoid indentation issues
"""

import cv2
import queue


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
    
    print("Eye Tracker started! Press Ctrl+C to stop.")
    
    try:
        # Main loop for OpenCV display (optional)
        while eye_tracker.running:
            try:
                frame, motion_boxes = eye_tracker.frame_queue.get(timeout=1.0)
                
                # Draw motion rectangles on frame
                for (x, y, w, h) in motion_boxes:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    # Draw center point
                    center_x = x + w//2
                    center_y = y + h//2
                    cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
                
                # Convert RGB to BGR for OpenCV
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Display frame at full resolution (already 640x480)
                cv2.imshow('Motion Detection', frame_bgr)
                
                # Check for 'q' key press to quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
            except queue.Empty:
                continue
                
    except KeyboardInterrupt:
        print("\nStopping Eye Tracker...")
    finally:
        eye_tracker.stop()

