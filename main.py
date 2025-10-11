from picamera2 import Picamera2
import cv2
import numpy as np
import sys
import os

def main():
    picam2 = None
    
    try:
        # Initialize camera
        print("Starting camera...")
        picam2 = Picamera2()
        
        # Create preview configuration
        config = picam2.create_preview_configuration()
        picam2.configure(config)
        picam2.start()
        
        print("Camera preview window opened. Press 'q' to quit.")
        
        # Main loop to display frames
        while True:
            # Capture frame from camera
            frame = picam2.capture_array()
            
            # Convert from RGB to BGR for OpenCV
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Display the frame
            cv2.imshow('Camera Preview', frame_bgr)
            
            # Check for 'q' key press to quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("\nStopping camera...")
    except Exception as e:
        print(f"Camera error: {e}")
    finally:
        if picam2 is not None:
            picam2.close()
        cv2.destroyAllWindows()
        print("Camera stopped")
        sys.exit(0)

if __name__ == "__main__":
    main()

