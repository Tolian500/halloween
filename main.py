from picamera2 import Picamera2, Preview
import sys
import os
import time

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
            try:
                # Try to start preview with Qt backend
                picam2.start_preview(Preview.QTGL)
                print("Camera preview window opened. Press Ctrl+C to stop.")
            except Exception as e:
                print(f"Qt preview failed: {e}")
                try:
                    # Fallback to DRM preview
                    picam2.start_preview(Preview.DRM)
                    print("Camera preview window opened (DRM). Press Ctrl+C to stop.")
                except Exception as e2:
                    print(f"DRM preview also failed: {e2}")
                    print("Camera is running but no preview window will show.")
                    print("Press Ctrl+C to stop.")
        else:
            print("No display detected (running headless)")
            print("Camera is running but no preview window will show.")
            print("Press Ctrl+C to stop.")
        
        # Keep the camera running until interrupted
        while True:
            time.sleep(0.1)  # Small sleep to prevent busy waiting
                
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

