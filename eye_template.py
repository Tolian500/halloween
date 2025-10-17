#!/usr/bin/env python3
"""
Eye Template - Simple eye creation function
Just the basic eye creation moved to a separate file for easy customization.
"""

import numpy as np
from display_settings import WIDTH, HEIGHT

def create_eye_image(eye_x, eye_y, blink_state=1.0, eye_cache=None, cache_size=50, eye_color=None, iris_radius=None):
    """Create eye image with blinking support + RGB565 pre-conversion + dynamic sizing"""
    # Default eye color if not provided
    if eye_color is None:
        eye_color = [200, 50, 25]  # Red
    
    # Dynamic iris radius (default 50 if not provided)
    if iris_radius is None:
        iris_radius = 50  # Default size
    pupil_radius = iris_radius // 2  # Pupil is half the iris size
    
    # Round to nearest 5 pixels for smoother movement (still good caching)
    cache_x = round(eye_x / 5) * 5
    cache_y = round(eye_y / 5) * 5
    blink_key = round(blink_state * 10) / 10  # Cache different blink states
    color_key = tuple(eye_color)  # Add color to cache key
    size_key = iris_radius  # Add iris size to cache key
    cache_key = (cache_x, cache_y, blink_key, color_key, size_key)
    
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
    
    # Dynamic eye sizes based on face size
    # iris_radius and pupil_radius are now calculated above
    
    # Calculate eye position (clamp to render bounds with margin)
    render_x = int(max(iris_radius, min(render_size - iris_radius, render_x)))
    render_y = int(max(iris_radius, min(render_size - iris_radius, render_y)))
    
    # Apply blink (compress vertically)
    y, x = np.ogrid[:render_size, :render_size]
    
    if blink_state < 1.0:
        # Create eyelid effect (close from top and bottom)
        eyelid_top = render_y - iris_radius + (iris_radius * (1 - blink_state))
        eyelid_bottom = render_y + iris_radius - (iris_radius * (1 - blink_state))
        
        # Draw iris (only visible part)
        mask_iris = ((x - render_x)**2 + (y - render_y)**2 <= iris_radius**2) & (y >= eyelid_top) & (y <= eyelid_bottom)
        img_array[mask_iris] = eye_color  # Dynamic eye color
        
        # Draw pupil (only visible part)
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
