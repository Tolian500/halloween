#!/usr/bin/env python3
"""
Test script for GC9A01 1.28" TFT IPS display
Connection diagram:
VCC -> 3.3V (pin 1)
GND -> GND (pin 6)
SCL/CLK -> GPIO 11 (SCLK, pin 23)
SDA/MOSI -> GPIO 10 (MOSI, pin 19)
CS -> GPIO 8 (CE0, pin 24)
DC -> GPIO 25 (pin 22)
RST -> GPIO 27 (pin 13)
"""

import time
import RPi.GPIO as GPIO
import spidev
from PIL import Image, ImageDraw, ImageFont

# Display configuration
CS_PIN = 8   # GPIO 8 (CE0)
DC_PIN = 25  # GPIO 25
RST_PIN = 27 # GPIO 27

# Display dimensions
WIDTH = 240
HEIGHT = 240

class GC9A01:
    """GC9A01 display driver for Raspberry Pi"""
    
    def __init__(self, spi_bus=0, spi_device=0, cs_pin=CS_PIN, dc_pin=DC_PIN, rst_pin=RST_PIN):
        self.cs_pin = cs_pin
        self.dc_pin = dc_pin
        self.rst_pin = rst_pin
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.cs_pin, GPIO.OUT)
        GPIO.setup(self.dc_pin, GPIO.OUT)
        GPIO.setup(self.rst_pin, GPIO.OUT)
        
        # Setup SPI
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        self.spi.max_speed_hz = 8000000  # 8MHz
        
        # Initialize display
        self._init_display()
    
    def _write_command(self, cmd):
        """Write command to display"""
        GPIO.output(self.dc_pin, GPIO.LOW)  # Command mode
        GPIO.output(self.cs_pin, GPIO.LOW)  # Select device
        self.spi.writebytes([cmd])
        GPIO.output(self.cs_pin, GPIO.HIGH)  # Deselect device
    
    def _write_data(self, data):
        """Write data to display"""
        GPIO.output(self.dc_pin, GPIO.HIGH)  # Data mode
        GPIO.output(self.cs_pin, GPIO.LOW)   # Select device
        if isinstance(data, int):
            self.spi.writebytes([data])
        else:
            self.spi.writebytes(data)
        GPIO.output(self.cs_pin, GPIO.HIGH)  # Deselect device
    
    def _init_display(self):
        """Initialize the GC9A01 display"""
        # Reset display
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
        
        # Convert image to RGB565 and send
        pixels = []
        for y in range(HEIGHT):
            for x in range(WIDTH):
                r, g, b = image.getpixel((x, y))
                # Convert RGB888 to RGB565
                rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                pixels.append(rgb565 >> 8)  # High byte
                pixels.append(rgb565 & 0xFF)  # Low byte
        
        # Send data in chunks
        chunk_size = 4096
        for i in range(0, len(pixels), chunk_size):
            chunk = pixels[i:i + chunk_size]
            self._write_data(chunk)
    
    def close(self):
        """Clean up resources"""
        GPIO.cleanup()
        self.spi.close()

def init_display():
    """Initialize the GC9A01 display"""
    try:
        display = GC9A01()
        print("GC9A01 display initialized successfully!")
        return display
        
    except Exception as e:
        print(f"Failed to initialize display: {e}")
        return None

def test_basic_colors(display):
    """Test basic color display"""
    print("Testing basic colors...")
    
    # Create image
    image = Image.new("RGB", (240, 240))
    draw = ImageDraw.Draw(image)
    
    # Test colors
    colors = [
        (255, 0, 0),    # Red
        (0, 255, 0),    # Green
        (0, 0, 255),    # Blue
        (255, 255, 0),  # Yellow
        (255, 0, 255),  # Magenta
        (0, 255, 255),  # Cyan
        (255, 255, 255), # White
        (0, 0, 0)       # Black
    ]
    
    for i, color in enumerate(colors):
        print(f"Displaying {color}...")
        draw.rectangle((0, 0, 240, 240), fill=color)
        display.image(image)
        time.sleep(1)

def test_patterns(display):
    """Test various patterns"""
    print("Testing patterns...")
    
    image = Image.new("RGB", (240, 240))
    draw = ImageDraw.Draw(image)
    
    # Gradient test
    print("Gradient test...")
    for y in range(240):
        color_value = int((y / 240) * 255)
        draw.line([(0, y), (240, y)], fill=(color_value, color_value, color_value))
    display.image(image)
    time.sleep(2)
    
    # Checkerboard pattern
    print("Checkerboard pattern...")
    draw.rectangle((0, 0, 240, 240), fill=(0, 0, 0))
    for x in range(0, 240, 20):
        for y in range(0, 240, 20):
            if (x // 20 + y // 20) % 2 == 0:
                draw.rectangle((x, y, x+20, y+20), fill=(255, 255, 255))
    display.image(image)
    time.sleep(2)
    
    # Circles
    print("Circles test...")
    draw.rectangle((0, 0, 240, 240), fill=(0, 0, 0))
    for i in range(5):
        radius = 20 + i * 20
        color = (255 - i * 50, i * 50, 128)
        draw.ellipse((120-radius, 120-radius, 120+radius, 120+radius), fill=color)
    display.image(image)
    time.sleep(2)

def test_text(display):
    """Test text display"""
    print("Testing text display...")
    
    image = Image.new("RGB", (240, 240))
    draw = ImageDraw.Draw(image)
    
    # Clear screen
    draw.rectangle((0, 0, 240, 240), fill=(0, 0, 0))
    
    # Try to load a font, fallback to default if not available
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except:
        try:
            font = ImageFont.load_default()
        except:
            font = None
    
    # Test text
    texts = [
        "GC9A01 Test",
        "Hello World!",
        "Raspberry Pi",
        "240x240 Display",
        "Test Complete!"
    ]
    
    for i, text in enumerate(texts):
        print(f"Displaying: {text}")
        draw.rectangle((0, 0, 240, 240), fill=(0, 0, 0))
        
        if font:
            # Get text size for centering
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (240 - text_width) // 2
            y = (240 - text_height) // 2
            
            draw.text((x, y), text, font=font, fill=(255, 255, 255))
        else:
            # Fallback without font
            draw.text((10, 110), text, fill=(255, 255, 255))
        
        display.image(image)
        time.sleep(2)

def test_rotation(display):
    """Test display rotation"""
    print("Testing rotation...")
    
    image = Image.new("RGB", (240, 240))
    draw = ImageDraw.Draw(image)
    
    # Draw an arrow pointing up
    draw.rectangle((0, 0, 240, 240), fill=(0, 0, 0))
    draw.polygon([(120, 20), (100, 60), (140, 60)], fill=(255, 255, 255))
    draw.rectangle((115, 60, 125, 220), fill=(255, 255, 255))
    
    display.image(image)
    time.sleep(2)

def main():
    """Main test function"""
    print("GC9A01 1.28\" TFT IPS Display Test")
    print("=" * 40)
    
    # Initialize display
    display = init_display()
    if not display:
        print("Failed to initialize display. Check connections!")
        return
    
    try:
        # Run tests
        test_basic_colors(display)
        test_patterns(display)
        test_text(display)
        test_rotation(display)
        
        print("\nAll tests completed successfully!")
        print("Display is working correctly.")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        # Clear display
        try:
            image = Image.new("RGB", (240, 240), (0, 0, 0))
            display.image(image)
            display.close()
            print("Display cleared")
        except:
            pass

if __name__ == "__main__":
    main()
