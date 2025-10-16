#!/usr/bin/env python3
"""
GC9A01 Display Test for Raspberry Pi 5
Uses rpi-lgpio for Pi 5 compatibility
"""

import time
import spidev
from PIL import Image, ImageDraw, ImageFont

# Use rpi-lgpio (Pi 5 compatible drop-in replacement for RPi.GPIO)
try:
    import RPi.GPIO as GPIO
    print("Using RPi.GPIO library (should be rpi-lgpio on Pi 5)")
except ImportError:
    print("ERROR: RPi.GPIO (rpi-lgpio) not installed")
    print("Install with: sudo apt install python3-rpi-lgpio")
    exit(1)

# Display configuration
CS_PIN = 8   # GPIO 8 (CE0) - SPI hardware CS
DC_PIN = 25  # GPIO 25
RST_PIN = 27 # GPIO 27

# Display dimensions
WIDTH = 240
HEIGHT = 240

class GC9A01_Pi5:
    """Simple GC9A01 driver for Raspberry Pi 5"""
    
    def __init__(self):
        print("Initializing GC9A01 for Raspberry Pi 5...")
        
        # Force cleanup first to release any held pins
        try:
            GPIO.cleanup()
            print("Released previously held GPIO pins")
        except:
            pass
        
        # Setup GPIO first (DC and RST only - CS is handled by SPI)
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup control pins (NOT CS - that's controlled by SPI hardware)
        GPIO.setup(DC_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(RST_PIN, GPIO.OUT, initial=GPIO.HIGH)
        print(f"GPIO configured: DC={DC_PIN}, RST={RST_PIN}")
        
        # Setup SPI (SPI will control CS automatically)
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)  # Bus 0, Device 0
        self.spi.max_speed_hz = 16000000  # 16 MHz - slower for stability
        self.spi.mode = 0
        self.spi.bits_per_word = 8
        self.spi.lsbfirst = False
        print(f"SPI configured: 16 MHz (hardware CS on GPIO {CS_PIN})")
        
        # Initialize display
        self._reset()
        self._init_display()
        print("Display initialized successfully!")
    
    def _reset(self):
        """Hardware reset"""
        GPIO.output(RST_PIN, GPIO.LOW)
        time.sleep(0.01)
        GPIO.output(RST_PIN, GPIO.HIGH)
        time.sleep(0.01)
    
    def _write_cmd(self, cmd):
        """Write command"""
        GPIO.output(DC_PIN, GPIO.LOW)
        self.spi.xfer2([cmd])  # xfer2 keeps CS low during transfer
    
    def _write_data(self, data):
        """Write data"""
        GPIO.output(DC_PIN, GPIO.HIGH)
        if isinstance(data, int):
            self.spi.writebytes([data])
        else:
            # Use writebytes for better performance with larger data
            self.spi.writebytes(data)
    
    def _init_display(self):
        """Initialize GC9A01"""
        # Basic init sequence
        init_cmds = [
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
            (0x3A, [0x05]),  # RGB565
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
            (0x35, None),  # Tearing effect on
            (0x21, None),  # Display inversion on
            (0x11, None),  # Sleep out
            (0x29, None),  # Display on
        ]
        
        for cmd, data in init_cmds:
            self._write_cmd(cmd)
            if data:
                self._write_data(data)
        
        time.sleep(0.12)
    
    def display_image(self, image):
        """Display PIL image"""
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Set window
        self._write_cmd(0x2A)  # Column
        self._write_data([0x00, 0x00, 0x00, 0xEF])  # 0-239
        self._write_cmd(0x2B)  # Row
        self._write_data([0x00, 0x00, 0x00, 0xEF])  # 0-239
        self._write_cmd(0x2C)  # Memory write
        
        # Convert to RGB565
        pixels = []
        for r, g, b in image.getdata():
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            pixels.append(rgb565 >> 8)
            pixels.append(rgb565 & 0xFF)
        
        # Send data
        GPIO.output(DC_PIN, GPIO.HIGH)
        
        # Send in moderate chunks (too large = memory issues, too small = CS toggling)
        chunk_size = 4096
        for i in range(0, len(pixels), chunk_size):
            self.spi.writebytes(pixels[i:i+chunk_size])
    
    def fill(self, color):
        """Fill screen with color (r, g, b)"""
        img = Image.new('RGB', (WIDTH, HEIGHT), color)
        self.display_image(img)
    
    def close(self):
        """Cleanup"""
        self.spi.close()
        GPIO.cleanup()


def test_display():
    """Run display tests"""
    print("=" * 50)
    print("GC9A01 Display Test for Raspberry Pi 5")
    print("=" * 50)
    
    # Initialize
    display = GC9A01_Pi5()
    
    try:
        # Test 1: Solid colors
        print("\nTest 1: Solid colors")
        colors = [
            ("Red", (255, 0, 0)),
            ("Green", (0, 255, 0)),
            ("Blue", (0, 0, 255)),
            ("White", (255, 255, 255)),
            ("Black", (0, 0, 0))
        ]
        
        for name, color in colors:
            print(f"  {name}...")
            display.fill(color)
            time.sleep(1)
        
        # Test 2: Simple pattern
        print("\nTest 2: Pattern test")
        img = Image.new('RGB', (WIDTH, HEIGHT), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw circles
        for i in range(5):
            radius = 20 + i * 20
            color = (255 - i * 50, i * 50, 128)
            draw.ellipse((120-radius, 120-radius, 120+radius, 120+radius), 
                        fill=color)
        
        display.display_image(img)
        time.sleep(2)
        
        # Test 3: Text
        print("\nTest 3: Text display")
        img = Image.new('RGB', (WIDTH, HEIGHT), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        text = "Pi 5 Works!"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (240 - text_width) // 2
        y = (240 - text_height) // 2
        
        draw.text((x, y), text, font=font, fill=(0, 255, 0))
        display.display_image(img)
        time.sleep(3)
        
        print("\n" + "=" * 50)
        print("All tests passed! Display is working!")
        print("=" * 50)
        
    except KeyboardInterrupt:
        print("\nTest interrupted")
    except Exception as e:
        print(f"\nError during test: {e}")
    finally:
        # Clear and cleanup
        display.fill((0, 0, 0))
        display.close()
        print("Cleanup complete")


if __name__ == "__main__":
    test_display()

