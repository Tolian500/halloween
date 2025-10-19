#!/usr/bin/env python3
"""
Eye Template - Simple eye creation function
Just the basic eye creation moved to a separate file for easy customization.
"""

import os
# Fix Qt permission warning - set environment variables before importing cv2
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = ''
os.environ['QT_X11_NO_MITSHM'] = '1'
os.environ['QT_LOGGING_RULES'] = '*=false'

import numpy as np
import cv2
# Import display settings - use Windows compatible version if on Windows
import platform
if platform.system() == "Windows":
    from display_settings_windows import WIDTH, HEIGHT
else:
    from display_settings import WIDTH, HEIGHT

def get_eye_colors():
    """Get the current eye colors from the template"""
    return {
        'normal_color': [255, 255, 0],  # Yellow (idle/motion detection)
        'tracked_color': [255, 0, 0]    # Red (face tracking)
    }

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

def preview_eyes():
    """Preview function to show both normal and tracked eyes when run directly"""
    print("Eye Template Preview")
    print("===================")
    print("Showing normal (yellow) and tracked (red) eyes:")
    
    # Eye positions
    left_eye_x, left_eye_y = WIDTH // 2 - 60, HEIGHT // 2
    right_eye_x, right_eye_y = WIDTH // 2 + 60, HEIGHT // 2
    
    # Eye colors (get from template function)
    eye_colors = get_eye_colors()
    normal_color = eye_colors['normal_color']
    tracked_color = eye_colors['tracked_color']
    
    # Eye size
    iris_radius = 50
    
    # Create images directly in BGR format for preview
    def create_eye_preview(eye_x, eye_y, eye_color, iris_radius):
        """Create eye image directly in BGR format for preview"""
        img_array = np.zeros((WIDTH, HEIGHT, 3), dtype=np.uint8)
        
        # Calculate eye position (clamp to bounds with margin)
        render_x = int(max(iris_radius, min(WIDTH - iris_radius, eye_x)))
        render_y = int(max(iris_radius, min(HEIGHT - iris_radius, eye_y)))
        
        pupil_radius = iris_radius // 2
        
        # Create coordinate grids
        y, x = np.ogrid[:WIDTH, :HEIGHT]
        
        # Add glow effect around iris
        glow_radius = iris_radius + 15
        mask_glow = (x - render_x)**2 + (y - render_y)**2 <= glow_radius**2
        glow_color = [int(c * 0.3) for c in eye_color]
        img_array[mask_glow] = glow_color
        
        # Draw iris
        mask_iris = (x - render_x)**2 + (y - render_y)**2 <= iris_radius**2
        img_array[mask_iris] = eye_color
        
        # Draw pupil
        mask_pupil = (x - render_x)**2 + (y - render_y)**2 <= pupil_radius**2
        img_array[mask_pupil] = [255, 255, 255]  # White pupil
        
        # Convert RGB to BGR for OpenCV
        return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    # Create both eyes
    left_eye_bgr = create_eye_preview(left_eye_x, left_eye_y, normal_color, iris_radius)
    right_eye_bgr = create_eye_preview(right_eye_x, right_eye_y, tracked_color, iris_radius)
    
    # Combine both eyes side by side
    combined = np.hstack([left_eye_bgr, right_eye_bgr])
    
    # Add labels
    cv2.putText(combined, "Normal (Yellow)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(combined, "Tracked (Red)", (WIDTH + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Show the preview
    cv2.imshow("Eye Template Preview", combined)
    
    # Wait for any key press to close
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    print("Preview closed.")

if __name__ == "__main__":
    preview_eyes()
