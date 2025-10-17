#!/usr/bin/env python3
"""
Display Settings and GC9A01 Driver
Contains all display-related configuration and driver code
"""

import time
import spidev
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

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

def create_eye_image(eye_x, eye_y, blink_state=1.0, eye_cache=None, cache_size=50, eye_color=None):
    """Create eye image with blinking support + RGB565 pre-conversion"""
    # Default eye color if not provided
    if eye_color is None:
        eye_color = [200, 50, 25]  # Red
    
    # Round to nearest 5 pixels for smoother movement (still good caching)
    cache_x = round(eye_x / 5) * 5
    cache_y = round(eye_y / 5) * 5
    blink_key = round(blink_state * 10) / 10  # Cache different blink states
    color_key = tuple(eye_color)  # Add color to cache key
    cache_key = (cache_x, cache_y, blink_key, color_key)
    
    # Check cache first (cache stores RGB565 bytes directly!)
    if cache_key in eye_cache:
        return eye_cache[cache_key]
    
    # Render directly at full resolution for better quality
    render_size = WIDTH  # 240x240 full resolution
    
    # Create full resolution image for rendering
    img_array = np.zeros((render_size, render_size, 3), dtype=np.uint8)
    
    # Use full resolution coordinates
    render_x = int(eye_x)
    render_y = int(eye_y)
    
    # Full size eye for better quality
    iris_radius = 50  # Full size
    pupil_radius = 25  # Full size
    
    # Calculate eye position (clamp to render bounds with margin)
    render_x = int(max(iris_radius, min(render_size - iris_radius, render_x)))
    render_y = int(max(iris_radius, min(render_size - iris_radius, render_y)))
    
    # Apply blink (compress vertically)
    y, x = np.ogrid[:render_size, :render_size]
    
    if blink_state < 1.0:
        # Create eyelid effect (close from top and bottom)
        eyelid_top = int(render_size//2 - (render_size//2) * blink_state)
        eyelid_bottom = int(render_size//2 + (render_size//2) * blink_state)
        
        # Only draw eye in visible area
        if eyelid_bottom > eyelid_top:
            # Add glow effect around iris with blink mask
            glow_radius = iris_radius + 15  # Glow extends 15 pixels beyond iris
            mask_glow = ((x - render_x)**2 + (y - render_y)**2 <= glow_radius**2) & (y >= eyelid_top) & (y <= eyelid_bottom)
            # Create glow with reduced intensity
            glow_color = [int(c * 0.3) for c in eye_color]  # 30% intensity for glow
            img_array[mask_glow] = glow_color
            
            # Draw iris with blink mask
            mask_iris = ((x - render_x)**2 + (y - render_y)**2 <= iris_radius**2) & (y >= eyelid_top) & (y <= eyelid_bottom)
            img_array[mask_iris] = eye_color  # Dynamic eye color
            
            # Draw pupil (white circle) with blink mask
            mask_pupil = ((x - render_x)**2 + (y - render_y)**2 <= pupil_radius**2) & (y >= eyelid_top) & (y <= eyelid_bottom)
            img_array[mask_pupil] = [255, 255, 255]  # White pupil
    else:
        # Fully open eye
        # Add glow effect around iris
        glow_radius = iris_radius + 15  # Glow extends 15 pixels beyond iris
        mask_glow = (x - render_x)**2 + (y - render_y)**2 <= glow_radius**2
        # Create glow with reduced intensity
        glow_color = [int(c * 0.3) for c in eye_color]  # 30% intensity for glow
        img_array[mask_glow] = glow_color
        
        # Draw iris
        mask_iris = (x - render_x)**2 + (y - render_y)**2 <= iris_radius**2
        img_array[mask_iris] = eye_color  # Dynamic eye color
        
        # Draw pupil
        mask_pupil = (x - render_x)**2 + (y - render_y)**2 <= pupil_radius**2
        img_array[mask_pupil] = [255, 255, 255]  # White pupil
    
    # Convert RGB888 to RGB565 using NumPy (direct conversion - no scaling needed!)
    r = (img_array[:, :, 0] >> 3).astype(np.uint16)  # 5 bits
    g = (img_array[:, :, 1] >> 2).astype(np.uint16)  # 6 bits
    b = (img_array[:, :, 2] >> 3).astype(np.uint16)  # 5 bits
    rgb565_full = (r << 11) | (g << 5) | b
    
    # Convert to bytes (big-endian for SPI) - no scaling needed!
    rgb565_bytes = rgb565_full.astype('>u2').tobytes()
    
    # Cache management - keep only recent entries
    if len(eye_cache) >= cache_size:
        # Remove oldest entry
        eye_cache.pop(next(iter(eye_cache)))
    
    # Cache the RGB565 bytes directly!
    eye_cache[cache_key] = rgb565_bytes
    return rgb565_bytes

def send_to_display(display, rgb565_bytes):
    """Send RGB565 data to a specific display"""
    # Set display window
    display._write_command(0x2A)  # Column address set
    display._write_data([0x00, 0x00, 0x00, 0xEF])  # 0 to 239
    display._write_command(0x2B)  # Row address set
    display._write_data([0x00, 0x00, 0x00, 0xEF])  # 0 to 239
    display._write_command(0x2C)  # Memory write
    
    # Send full screen data using display's own GPIO handling
    # Set data mode
    if USE_GPIOZERO:
        display.dc_device.on()  # Data mode
    else:
        GPIO.output(display.dc_pin, GPIO.HIGH)  # Data mode
    
    # Send data in optimized chunks (4096 is max safe size)
    chunk_size = 4096  # Maximum safe chunk size for SPI
    for i in range(0, len(rgb565_bytes), chunk_size):
        chunk = rgb565_bytes[i:i+chunk_size]
        display.spi.writebytes(chunk)  # SPI handles CS automatically
