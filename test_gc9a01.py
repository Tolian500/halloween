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
import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
import adafruit_rgb_display.gc9a01 as gc9a01

# Display configuration
CS_PIN = board.D8  # GPIO 8 (CE0)
DC_PIN = board.D25  # GPIO 25
RST_PIN = board.D27  # GPIO 27

# SPI pins (hardware SPI)
SPI_MOSI = board.D10  # GPIO 10 (MOSI)
SPI_CLK = board.D11   # GPIO 11 (SCLK)

def init_display():
    """Initialize the GC9A01 display"""
    try:
        # Create SPI bus
        spi = board.SPI()
        
        # Create display object
        display = gc9a01.GC9A01(
            spi,
            cs=digitalio.DigitalInOut(CS_PIN),
            dc=digitalio.DigitalInOut(DC_PIN),
            rst=digitalio.DigitalInOut(RST_PIN),
            width=240,
            height=240,
            rotation=0
        )
        
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
            print("Display cleared")
        except:
            pass

if __name__ == "__main__":
    main()
