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
                frame, motion_boxes = eye_tracker.frame_queue.get(timeout=1.0)
                
                # Convert to BGR for OpenCV first (handle grayscale)
                if len(frame.shape) == 3:
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                else:
                    # Grayscale - convert to BGR for display
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                
                # Draw motion rectangles on frame
                for (x, y, w, h) in motion_boxes:
                    cv2.rectangle(frame_bgr, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    # Draw center point
                    center_x = x + w//2
                    center_y = y + h//2
                    cv2.circle(frame_bgr, (center_x, center_y), 5, (0, 0, 255), -1)
                
                # Resize for display if needed (keep aspect ratio)
                display_height = 480
                display_width = int(frame_bgr.shape[1] * (display_height / frame_bgr.shape[0]))
                if display_width > 1280:
                    display_width = 1280
                    display_height = int(frame_bgr.shape[0] * (display_width / frame_bgr.shape[1]))
                
                display_frame = cv2.resize(frame_bgr, (display_width, display_height))
                cv2.imshow('Motion Detection', display_frame)
                
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

