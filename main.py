from picamera2 import Picamera2
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
        
        # Check if we have a display
        if 'DISPLAY' in os.environ:
            print("Display detected - starting preview window...")
            picam2.start_preview()
            print("Camera preview window opened. Press Ctrl+C to stop.")
        else:
            print("No display detected (running headless)")
            print("Camera is running but no preview window will show.")
            print("Press Ctrl+C to stop.")
        
        # Keep the camera running until interrupted
        while True:
            pass
                
    except KeyboardInterrupt:
        print("\nStopping camera...")
    except Exception as e:
        print(f"Camera error: {e}")
    finally:
        if picam2 is not None:
            picam2.close()
            print("Camera stopped")
        sys.exit(0)

if __name__ == "__main__":
    main()

