#!/usr/bin/env python3
"""
Dual GC9A01 Display Test Script
Tests both displays individually and together
Connection diagram:
Display 1 (Left Eye):
VCC -> 3.3V (pin 1)
GND -> GND (pin 6)
SDA -> GPIO 10 (MOSI, pin 19)
SCL -> GPIO 11 (SCLK, pin 23)
CS  -> GPIO 8 (CE0, pin 24)
DC  -> GPIO 25 (pin 22)
RST -> GPIO 27 (pin 13)

Display 2 (Right Eye):
VCC -> 3.3V (pin 1)
GND -> GND (pin 6)
SDA -> GPIO 10 (MOSI, pin 19)  [SHARED]
SCL -> GPIO 11 (SCLK, pin 23)  [SHARED]
CS  -> GPIO 7 (CE1, pin 26)
DC  -> GPIO 24 (pin 18)
RST -> GPIO 23 (pin 16)
"""

import time
import spidev
from PIL import Image, ImageDraw, ImageFont
import os
import numpy as np

# Try RPi.GPIO first for Pi 5 (more reliable), fallback to gpiozero
try:
    import RPi.GPIO as GPIO
    USE_GPIOZERO = False
    print("Using RPi.GPIO library")
except ImportError:
    try:
        from gpiozero import DigitalOutputDevice
        USE_GPIOZERO = True
        print("Using gpiozero library")
    except ImportError:
        raise ImportError("Neither RPi.GPIO nor gpiozero is available. Please install one of them.")

# Display configuration
# Display 1 (Left Eye)
DISPLAY1_CS_PIN = 8   # GPIO 8 (CE0)
DISPLAY1_DC_PIN = 25  # GPIO 25
DISPLAY1_RST_PIN = 27 # GPIO 27

# Display 2 (Right Eye)
DISPLAY2_CS_PIN = 7   # GPIO 7 (CE1)
DISPLAY2_DC_PIN = 24  # GPIO 24
DISPLAY2_RST_PIN = 23 # GPIO 23

# Display dimensions
WIDTH = 240
HEIGHT = 240

class DualGC9A01:
    """Dual GC9A01 display driver for Raspberry Pi"""
    
    def __init__(self):
        self.display1 = None
        self.display2 = None
        self.initialized = False
        
        # Initialize both displays
        self._init_displays()
    
    def _init_displays(self):
        """Initialize both displays"""
        try:
            print("Initializing Display 1 (Left Eye)...")
            self.display1 = GC9A01(
                spi_bus=0, spi_device=0,
                cs_pin=DISPLAY1_CS_PIN,
                dc_pin=DISPLAY1_DC_PIN,
                rst_pin=DISPLAY1_RST_PIN
            )
            print("Display 1 initialized successfully!")
            
            print("Initializing Display 2 (Right Eye)...")
            self.display2 = GC9A01(
                spi_bus=0, spi_device=1,
                cs_pin=DISPLAY2_CS_PIN,
                dc_pin=DISPLAY2_DC_PIN,
                rst_pin=DISPLAY2_RST_PIN
            )
            print("Display 2 initialized successfully!")
            
            self.initialized = True
            print("Both displays initialized successfully!")
            
        except Exception as e:
            print(f"Failed to initialize displays: {e}")
            self.initialized = False
    
    def test_display1_only(self):
        """Test Display 1 individually"""
        if not self.display1:
            print("Display 1 not initialized!")
            return False
        
        print("Testing Display 1 (Left Eye) only...")
        
        # Test basic colors on Display 1
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)]
        color_names = ["Red", "Green", "Blue", "White"]
        
        for i, (color, name) in enumerate(zip(colors, color_names)):
            print(f"Display 1: Showing {name}...")
            image = Image.new("RGB", (WIDTH, HEIGHT), color)
            self.display1.image(image)
            time.sleep(1)
        
        # Test pattern on Display 1
        print("Display 1: Testing pattern...")
        image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw circles
        for i in range(5):
            radius = 20 + i * 20
            color = (255 - i * 50, i * 50, 128)
            draw.ellipse((120-radius, 120-radius, 120+radius, 120+radius), fill=color)
        
        self.display1.image(image)
        time.sleep(2)
        
        print("Display 1 test completed!")
        return True
    
    def test_display2_only(self):
        """Test Display 2 individually"""
        if not self.display2:
            print("Display 2 not initialized!")
            return False
        
        print("Testing Display 2 (Right Eye) only...")
        
        # Test basic colors on Display 2
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)]
        color_names = ["Red", "Green", "Blue", "White"]
        
        for i, (color, name) in enumerate(zip(colors, color_names)):
            print(f"Display 2: Showing {name}...")
            image = Image.new("RGB", (WIDTH, HEIGHT), color)
            self.display2.image(image)
            time.sleep(1)
        
        # Test pattern on Display 2
        print("Display 2: Testing pattern...")
        image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw squares
        for i in range(5):
            size = 20 + i * 20
            color = (i * 50, 255 - i * 50, 128)
            draw.rectangle((120-size//2, 120-size//2, 120+size//2, 120+size//2), fill=color)
        
        self.display2.image(image)
        time.sleep(2)
        
        print("Display 2 test completed!")
        return True
    
    def test_both_displays(self):
        """Test both displays simultaneously"""
        if not self.display1 or not self.display2:
            print("Both displays not initialized!")
            return False
        
        print("Testing both displays simultaneously...")
        
        # Test 1: Same color on both displays
        print("Test 1: Same colors on both displays...")
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
        color_names = ["Red", "Green", "Blue", "Yellow"]
        
        for color, name in zip(colors, color_names):
            print(f"Both displays: Showing {name}...")
            image = Image.new("RGB", (WIDTH, HEIGHT), color)
            self.display1.image(image)
            self.display2.image(image)
            time.sleep(1)
        
        # Test 2: Different colors on each display
        print("Test 2: Different colors on each display...")
        color_pairs = [
            ((255, 0, 0), (0, 255, 0)),    # Red/Green
            ((0, 0, 255), (255, 255, 0)),  # Blue/Yellow
            ((255, 0, 255), (0, 255, 255)), # Magenta/Cyan
            ((255, 255, 255), (0, 0, 0))   # White/Black
        ]
        
        for i, (color1, color2) in enumerate(color_pairs):
            print(f"Display 1: {color1}, Display 2: {color2}")
            image1 = Image.new("RGB", (WIDTH, HEIGHT), color1)
            image2 = Image.new("RGB", (WIDTH, HEIGHT), color2)
            self.display1.image(image1)
            self.display2.image(image2)
            time.sleep(1)
        
        # Test 3: Animated pattern
        print("Test 3: Animated pattern...")
        for frame in range(20):
            # Create moving circles
            image1 = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
            image2 = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
            draw1 = ImageDraw.Draw(image1)
            draw2 = ImageDraw.Draw(image2)
            
            # Moving circle on Display 1
            x1 = int(120 + 80 * np.sin(frame * 0.3))
            y1 = int(120 + 80 * np.cos(frame * 0.3))
            draw1.ellipse((x1-20, y1-20, x1+20, y1+20), fill=(255, 100, 100))
            
            # Moving circle on Display 2 (opposite direction)
            x2 = int(120 + 80 * np.sin(frame * 0.3 + np.pi))
            y2 = int(120 + 80 * np.cos(frame * 0.3 + np.pi))
            draw2.ellipse((x2-20, y2-20, x2+20, y2+20), fill=(100, 100, 255))
            
            self.display1.image(image1)
            self.display2.image(image2)
            time.sleep(0.1)
        
        print("Both displays test completed!")
        return True
    
    def test_eye_tracking_simulation(self):
        """Simulate eye tracking with both displays"""
        if not self.display1 or not self.display2:
            print("Both displays not initialized!")
            return False
        
        print("Testing eye tracking simulation...")
        
        # Eye parameters
        eye_radius = 50
        pupil_radius = 25
        highlight_radius = 6
        
        # Simulate eye movement
        for frame in range(100):
            # Calculate eye positions (synchronized movement)
            time_factor = frame * 0.1
            eye1_x = int(120 + 60 * np.sin(time_factor))
            eye1_y = int(120 + 40 * np.cos(time_factor * 0.7))
            eye2_x = int(120 + 60 * np.sin(time_factor + np.pi * 0.5))
            eye2_y = int(120 + 40 * np.cos(time_factor * 0.7 + np.pi * 0.5))
            
            # Create eye images
            image1 = self._create_eye_image(eye1_x, eye1_y, eye_radius, pupil_radius, highlight_radius)
            image2 = self._create_eye_image(eye2_x, eye2_y, eye_radius, pupil_radius, highlight_radius)
            
            # Display both eyes
            self.display1.image(image1)
            self.display2.image(image2)
            time.sleep(0.05)
        
        print("Eye tracking simulation completed!")
        return True
    
    def _create_eye_image(self, eye_x, eye_y, eye_radius, pupil_radius, highlight_radius):
        """Create an eye image"""
        image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw iris (red circle)
        draw.ellipse((eye_x-eye_radius, eye_y-eye_radius, eye_x+eye_radius, eye_y+eye_radius), 
                    fill=(200, 50, 25))
        
        # Draw pupil (black circle)
        draw.ellipse((eye_x-pupil_radius, eye_y-pupil_radius, eye_x+pupil_radius, eye_y+pupil_radius), 
                    fill=(0, 0, 0))
        
        # Draw highlight (white circle)
        highlight_x = eye_x + 6
        highlight_y = eye_y - 4
        draw.ellipse((highlight_x-highlight_radius, highlight_y-highlight_radius, 
                     highlight_x+highlight_radius, highlight_y+highlight_radius), 
                    fill=(255, 255, 255))
        
        return image
    
    def clear_both_displays(self):
        """Clear both displays"""
        if self.display1:
            image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
            self.display1.image(image)
        if self.display2:
            image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
            self.display2.image(image)
    
    def close(self):
        """Clean up resources"""
        if self.display1:
            self.display1.close()
        if self.display2:
            self.display2.close()

class GC9A01:
    """GC9A01 display driver for Raspberry Pi"""
    
    def __init__(self, spi_bus=0, spi_device=0, cs_pin=8, dc_pin=25, rst_pin=27):
        self.cs_pin = cs_pin
        self.dc_pin = dc_pin
        self.rst_pin = rst_pin
        
        # Setup GPIO
        try:
            if USE_GPIOZERO:
                print(f"Setting up GPIO using gpiozero: DC={dc_pin}, RST={rst_pin}")
                self.dc_device = DigitalOutputDevice(self.dc_pin, initial_value=False)
                self.rst_device = DigitalOutputDevice(self.rst_pin, initial_value=True)
            else:
                print(f"Setting up GPIO using RPi.GPIO: DC={dc_pin}, RST={rst_pin}")
                GPIO.setwarnings(False)
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.dc_pin, GPIO.OUT, initial=GPIO.LOW)
                GPIO.setup(self.rst_pin, GPIO.OUT, initial=GPIO.HIGH)
        except Exception as e:
            raise Exception(f"GPIO setup failed: {e}")
        
        # Setup SPI
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        self.spi.max_speed_hz = 100000000  # 100 MHz
        self.spi.mode = 0
        
        # Initialize display
        self._init_display()
    
    def _write_command(self, cmd):
        """Write command to display"""
        if USE_GPIOZERO:
            self.dc_device.off()  # Command mode
        else:
            GPIO.output(self.dc_pin, GPIO.LOW)  # Command mode
        self.spi.writebytes([cmd])
    
    def _write_data(self, data):
        """Write data to display"""
        if USE_GPIOZERO:
            self.dc_device.on()  # Data mode
        else:
            GPIO.output(self.dc_pin, GPIO.HIGH)  # Data mode
        if isinstance(data, int):
            self.spi.writebytes([data])
        else:
            self.spi.writebytes(data)
    
    def _init_display(self):
        """Initialize the GC9A01 display"""
        # Reset display
        if USE_GPIOZERO:
            self.rst_device.off()
            time.sleep(0.01)
            self.rst_device.on()
            time.sleep(0.01)
        else:
            GPIO.output(self.rst_pin, GPIO.LOW)
            time.sleep(0.01)
            GPIO.output(self.rst_pin, GPIO.HIGH)
            time.sleep(0.01)
        
        # GC9A01 initialization sequence
        init_commands = [
            (0xEF, None),
            (0xEB, [0x14]),
            (0xFE, None),
            (0xEF, None),
            (0xEB, [0x14]),
            (0x84, [0x40]),
            (0x85, [0xFF]),
            (0x86, [0xFF]),
            (0x87, [0xFF]),
            (0x88, [0x0A]),
            (0x89, [0x21]),
            (0x8A, [0x00]),
            (0x8B, [0x80]),
            (0x8C, [0x01]),
            (0x8D, [0x01]),
            (0x8E, [0xFF]),
            (0x8F, [0xFF]),
            (0xB6, [0x00, 0x20]),
            (0x36, [0x08]),
            (0x3A, [0x05]),
            (0x90, [0x08, 0x08, 0x08, 0x08]),
            (0xBD, [0x06]),
            (0xBC, [0x00]),
            (0xFF, [0x60, 0x01, 0x04]),
            (0xC3, [0x13]),
            (0xC4, [0x13]),
            (0xC9, [0x22]),
            (0xBE, [0x11]),
            (0xE1, [0x10, 0x0E]),
            (0xDF, [0x21, 0x0C, 0x02]),
            (0xF0, [0x45, 0x09, 0x08, 0x08, 0x26, 0x2A]),
            (0xF1, [0x43, 0x70, 0x72, 0x36, 0x37, 0x6F]),
            (0xF2, [0x45, 0x09, 0x08, 0x08, 0x26, 0x2A]),
            (0xF3, [0x43, 0x70, 0x72, 0x36, 0x37, 0x6F]),
            (0xED, [0x1B, 0x0B]),
            (0xAE, [0x77]),
            (0xCD, [0x63]),
            (0x70, [0x07, 0x07, 0x04, 0x0E, 0x0F, 0x09, 0x07, 0x08, 0x03]),
            (0xE8, [0x34]),
            (0x62, [0x18, 0x0D, 0x71, 0xED, 0x70, 0x70, 0x18, 0x0F, 0x71, 0xEF, 0x70, 0x70]),
            (0x63, [0x18, 0x11, 0x71, 0xF1, 0x70, 0x70, 0x18, 0x13, 0x71, 0xF3, 0x70, 0x70]),
            (0x64, [0x28, 0x29, 0xF1, 0x01, 0xF1, 0x00, 0x07]),
            (0x66, [0x3C, 0x00, 0xCD, 0x67, 0x45, 0x45, 0x10, 0x00, 0x00, 0x00]),
            (0x67, [0x00, 0x3C, 0x00, 0x00, 0x00, 0x01, 0x54, 0x10, 0x32, 0x98]),
            (0x74, [0x10, 0x85, 0x80, 0x00, 0x00, 0x4E, 0x00]),
            (0x98, [0x3E, 0x07]),
            (0x35, None),
            (0x21, None),
            (0x11, None),
            (0x29, None),
        ]
        
        for cmd, data in init_commands:
            self._write_command(cmd)
            if data:
                self._write_data(data)
        
        time.sleep(0.1)
    
    def image(self, image):
        """Display PIL image on screen"""
        # Convert PIL image to RGB565 format
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Set display window
        self._write_command(0x2A)  # Column address set
        self._write_data([0x00, 0x00, 0x00, 0xEF])  # 0 to 239
        
        self._write_command(0x2B)  # Row address set
        self._write_data([0x00, 0x00, 0x00, 0xEF])  # 0 to 239
        
        self._write_command(0x2C)  # Memory write
        
        # Convert image to RGB565 and send efficiently
        pixels = []
        pixel_data = list(image.getdata())
        
        for r, g, b in pixel_data:
            # Convert RGB888 to RGB565
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            pixels.append(rgb565 >> 8)  # High byte
            pixels.append(rgb565 & 0xFF)  # Low byte
        
        # Send data in optimized chunks
        if USE_GPIOZERO:
            self.dc_device.on()  # Data mode
        else:
            GPIO.output(self.dc_pin, GPIO.HIGH)  # Data mode
        
        # Use maximum safe chunk size for best performance
        chunk_size = 4096
        for i in range(0, len(pixels), chunk_size):
            chunk = pixels[i:i + chunk_size]
            self.spi.writebytes(chunk)
    
    def close(self):
        """Clean up resources"""
        # Clean up GPIO
        if USE_GPIOZERO:
            try:
                if hasattr(self, 'dc_device'):
                    self.dc_device.close()
                if hasattr(self, 'rst_device'):
                    self.rst_device.close()
            except:
                pass
        else:
            try:
                GPIO.cleanup()
            except:
                pass
        # Close SPI
        if hasattr(self, 'spi'):
            self.spi.close()

def main():
    """Main test function"""
    print("Dual GC9A01 Display Test")
    print("=" * 50)
    
    # Initialize dual display system
    dual_display = DualGC9A01()
    if not dual_display.initialized:
        print("Failed to initialize displays. Check connections!")
        return
    
    try:
        print("\nStarting tests...")
        
        # Test 1: Individual display tests
        print("\n" + "="*50)
        print("TEST 1: Individual Display Tests")
        print("="*50)
        
        if dual_display.test_display1_only():
            print("✓ Display 1 test passed")
        else:
            print("✗ Display 1 test failed")
        
        time.sleep(1)
        
        if dual_display.test_display2_only():
            print("✓ Display 2 test passed")
        else:
            print("✗ Display 2 test failed")
        
        # Test 2: Both displays together
        print("\n" + "="*50)
        print("TEST 2: Both Displays Together")
        print("="*50)
        
        if dual_display.test_both_displays():
            print("✓ Both displays test passed")
        else:
            print("✗ Both displays test failed")
        
        # Test 3: Eye tracking simulation
        print("\n" + "="*50)
        print("TEST 3: Eye Tracking Simulation")
        print("="*50)
        
        if dual_display.test_eye_tracking_simulation():
            print("✓ Eye tracking simulation passed")
        else:
            print("✗ Eye tracking simulation failed")
        
        print("\n" + "="*50)
        print("All tests completed!")
        print("="*50)
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        # Clear displays and cleanup
        try:
            dual_display.clear_both_displays()
            dual_display.close()
            print("Displays cleared and resources cleaned up")
        except:
            pass

if __name__ == "__main__":
    main()
