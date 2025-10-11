from picamera2 import Picamera2
import sys

def main():
    picam2 = None
    
    try:
        # Initialize camera
        print("Starting camera...")
        picam2 = Picamera2()
        picam2.configure(picam2.create_preview_configuration())
        picam2.start()
        
        print("Camera view started. Press Ctrl+C to stop.")
        
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

