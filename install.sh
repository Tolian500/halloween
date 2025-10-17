#!/bin/bash
# Single Installation Script for Dual Eye Tracker with GC9A01 Displays
# Supports both Raspberry Pi 4 and Pi 5

echo "=========================================="
echo "Dual Eye Tracker Installation Script"
echo "=========================================="

# Detect Raspberry Pi model
PI_MODEL=$(cat /proc/device-tree/model 2>/dev/null | tr -d '\0')
echo "Detected: $PI_MODEL"

# Update package list
echo "Updating package list..."
sudo apt update

# Install system dependencies
echo "Installing system dependencies..."
sudo apt install -y python3-pil python3-pip python3-opencv python3-numpy

# Detect Pi 5 and install appropriate GPIO library
if [[ "$PI_MODEL" == *"Pi 5"* ]]; then
    echo "Raspberry Pi 5 detected - installing rpi-lgpio..."
    sudo apt install -y python3-gpiod python3-rpi-lgpio
    echo "Pi 5 GPIO libraries installed"
else
    echo "Raspberry Pi 4 or earlier - installing RPi.GPIO..."
    sudo apt install -y python3-rpi.gpio
    echo "RPi.GPIO installed"
fi

# Install SPI support
echo "Installing SPI support..."
sudo apt install -y python3-spidev

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install picamera2 pillow numpy opencv-python

# Enable SPI interface
echo "Enabling SPI interface..."
sudo raspi-config nonint do_spi 0

# Enable GPIO interface
echo "Enabling GPIO interface..."
sudo raspi-config nonint do_gpio 0

# Enable camera interface
echo "Enabling camera interface..."
sudo raspi-config nonint do_camera 0

# Create requirements.txt for future reference
echo "Creating requirements.txt..."
cat > requirements.txt << EOF
picamera2>=0.3.12
Pillow>=9.0.0
numpy>=1.21.0
opencv-python>=4.5.0
spidev>=3.5
EOF

# Create a simple test script
echo "Creating test script..."
cat > test_installation.py << 'EOF'
#!/usr/bin/env python3
"""
Test script to verify installation
"""

def test_imports():
    """Test all required imports"""
    try:
        import picamera2
        print("✓ picamera2 imported successfully")
    except ImportError as e:
        print(f"✗ picamera2 import failed: {e}")
        return False
    
    try:
        import cv2
        print("✓ opencv-python imported successfully")
    except ImportError as e:
        print(f"✗ opencv-python import failed: {e}")
        return False
    
    try:
        import numpy as np
        print("✓ numpy imported successfully")
    except ImportError as e:
        print(f"✗ numpy import failed: {e}")
        return False
    
    try:
        from PIL import Image
        print("✓ Pillow imported successfully")
    except ImportError as e:
        print(f"✗ Pillow import failed: {e}")
        return False
    
    try:
        import spidev
        print("✓ spidev imported successfully")
    except ImportError as e:
        print(f"✗ spidev import failed: {e}")
        return False
    
    # Test GPIO libraries
    try:
        import RPi.GPIO as GPIO
        print("✓ RPi.GPIO imported successfully")
    except ImportError:
        try:
            from gpiozero import DigitalOutputDevice
            print("✓ gpiozero imported successfully")
        except ImportError:
            print("✗ No GPIO library available")
            return False
    
    return True

def test_camera():
    """Test camera functionality"""
    try:
        from picamera2 import Picamera2
        camera = Picamera2()
        print("✓ Camera initialized successfully")
        camera.close()
        return True
    except Exception as e:
        print(f"✗ Camera test failed: {e}")
        return False

def test_spi():
    """Test SPI functionality"""
    try:
        import spidev
        spi = spidev.SpiDev()
        spi.open(0, 0)
        print("✓ SPI device opened successfully")
        spi.close()
        return True
    except Exception as e:
        print(f"✗ SPI test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing installation...")
    print("=" * 40)
    
    all_tests_passed = True
    
    print("Testing imports...")
    if not test_imports():
        all_tests_passed = False
    
    print("\nTesting camera...")
    if not test_camera():
        all_tests_passed = False
    
    print("\nTesting SPI...")
    if not test_spi():
        all_tests_passed = False
    
    print("\n" + "=" * 40)
    if all_tests_passed:
        print("✓ All tests passed! Installation successful.")
        print("\nYou can now run:")
        print("  python3 main.py              # Start dual eye tracker")
        print("  python3 dual_display_test.py  # Test displays")
        print("  python3 testing/previev_test.py  # Test camera preview")
    else:
        print("✗ Some tests failed. Please check the errors above.")
        print("You may need to reboot your Raspberry Pi.")
EOF

chmod +x test_installation.py

# Create a quick start script
echo "Creating quick start script..."
cat > start_eye_tracker.sh << 'EOF'
#!/bin/bash
echo "Starting Dual Eye Tracker..."
echo "Press Ctrl+C to stop"
python3 main.py
EOF

chmod +x start_eye_tracker.sh

echo ""
echo "=========================================="
echo "Installation completed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Reboot your Raspberry Pi: sudo reboot"
echo "2. After reboot, test installation: python3 test_installation.py"
echo "3. Test displays: python3 dual_display_test.py"
echo "4. Start eye tracker: python3 main.py"
echo ""
echo "Available commands:"
echo "  ./start_eye_tracker.sh    # Quick start"
echo "  python3 main.py --no-preview  # No preview window"
echo "  python3 main.py --fps-test    # Performance test mode"
echo ""
echo "Hardware connections:"
echo "  Display 1: CS=GPIO8, DC=GPIO25, RST=GPIO27"
echo "  Display 2: CS=GPIO7, DC=GPIO24, RST=GPIO23"
echo "  Shared: MOSI=GPIO10, SCLK=GPIO11, VCC=3.3V, GND=GND"
echo ""
echo "Note: You may need to reboot for SPI/GPIO changes to take effect."