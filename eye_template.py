#!/usr/bin/env python3
"""
Eye Template - Simple eye creation function
Just the basic eye creation moved to a separate file for easy customization.
"""

# ==============================================
# Eye Configuration Settings
# ==============================================
EYE_CONFIG = {
    # Iris settings (round)
    'iris_radius': 50,          # Base iris size
    
    # Pupil settings
    # Normal eye (cat-like elliptical pupil)
    'normal_pupil': {
        'width_ratio': 0.2,   # Width ratio for cat-like pupil (0.2 = very narrow)
        'height_ratio': 1.0,  # Height ratio (1.0 = full height)
        'size_ratio': 0.8,    # Pupil size relative to iris (0.8 = 80% of iris)
    },
    # Tracked eye (round pupil)
    'tracked_pupil': {
        'width_ratio': 1.0,   # Width ratio (1.0 = round)
        'height_ratio': 1.0,  # Height ratio (1.0 = round)
        'size_ratio': 0.6,    # Pupil size relative to iris (0.6 = 60% of iris)
    },
    
    # Colors
    'normal_color': [255, 220, 0],   # Yellow (idle/motion detection)
    'tracked_color': [255, 0, 0],    # Red (face tracking)
    
    # Glow effect
    'glow_size': 15,           # How far the glow extends beyond iris
    'glow_intensity': 0.3,     # Glow brightness (0.0 to 1.0)
    
    # Iris gradient
    'iris_gradient': {
        'center_brightness': 1.4,   # Make center brighter (>1.0 brightens, <1.0 darkens)
        'edge_darkness': 0.5,       # Make edges darker (<1.0 darkens, >1.0 brightens)
        'gradient_size': 0.6        # How much of iris radius to use for gradient (0.0 to 1.0)
    },
    
    # Edge highlight (bright line between glow and iris)
    'edge_highlight': {
        'brightness': 1.8,          # How bright the edge highlight is (>1.0 brightens)
        'width': 2,                 # Width of the highlight in pixels
        'alpha': 0.5                # Blend factor (0.0 to 1.0) - higher means more visible
    }
}

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
        'normal_color': EYE_CONFIG['normal_color'],
        'tracked_color': EYE_CONFIG['tracked_color']
    }

def create_eye_image(eye_x, eye_y, blink_state=1.0, eye_cache=None, cache_size=50, eye_color=None, iris_radius=None, face_tracked=False, pupil_size_factor=1.0):
    """Create eye image with blinking support + RGB565 pre-conversion + dynamic sizing"""
    # Default eye color if not provided
    if eye_color is None:
        eye_color = [200, 50, 25]  # Red
    
    # Dynamic iris radius (default from config if not provided)
    if iris_radius is None:
        iris_radius = EYE_CONFIG['iris_radius']
    
    # Iris is round (no width/height ratios)
    
    # Determine which pupil settings to use based on face tracking state (not color)
    pupil_config = EYE_CONFIG['tracked_pupil'] if face_tracked else EYE_CONFIG['normal_pupil']
    
    # Calculate pupil dimensions with face size influence
    base_pupil_radius = int(iris_radius * pupil_config['size_ratio'])  # Base pupil size
    pupil_radius = int(base_pupil_radius * pupil_size_factor)  # Apply face size factor
    pupil_width = int(pupil_radius * pupil_config['width_ratio'])  # Width (1.0 for round, <1.0 for elliptical)
    pupil_height = int(pupil_radius * pupil_config['height_ratio'])  # Height
    
    # Round to nearest 5 pixels for smoother movement (still good caching)
    cache_x = round(eye_x / 5) * 5
    cache_y = round(eye_y / 5) * 5
    blink_key = round(blink_state * 10) / 10  # Cache different blink states
    color_key = tuple(eye_color)  # Add color to cache key
    size_key = iris_radius  # Add iris size to cache key
    face_key = face_tracked  # Add face tracking state to cache key
    pupil_size_key = round(pupil_size_factor * 10) / 10  # Add pupil size factor to cache key
    cache_key = (cache_x, cache_y, blink_key, color_key, size_key, face_key, pupil_size_key)
    
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
        
        # Add glow effect around iris (only visible part) - round shape for outer glow
        glow_radius = iris_radius + EYE_CONFIG['glow_size']
        mask_glow = ((x - render_x)**2 + (y - render_y)**2 <= glow_radius**2) & (y >= eyelid_top) & (y <= eyelid_bottom)
        # Create glow with configurable intensity
        glow_color = [int(c * EYE_CONFIG['glow_intensity']) for c in eye_color]
        img_array[mask_glow] = glow_color
        
        # Add bright edge highlight between glow and iris (only visible part)
        highlight_width = EYE_CONFIG['edge_highlight']['width']
        highlight_brightness = EYE_CONFIG['edge_highlight']['brightness']
        highlight_alpha = EYE_CONFIG['edge_highlight']['alpha']
        
        # Create ring mask for the highlight
        dist_squared = (x - render_x)**2 + (y - render_y)**2
        outer_edge = iris_radius + highlight_width/2
        inner_edge = iris_radius - highlight_width/2
        mask_highlight = ((dist_squared >= inner_edge**2) & (dist_squared <= outer_edge**2)) & (y >= eyelid_top) & (y <= eyelid_bottom)
        
        # Create bright highlight color
        highlight_color = np.clip(np.array(eye_color) * highlight_brightness, 0, 255).astype(np.uint8)
        
        # Blend highlight with existing colors
        img_array[mask_highlight] = (
            (1 - highlight_alpha) * img_array[mask_highlight] + 
            highlight_alpha * highlight_color
        ).astype(np.uint8)
        
        # Draw iris with gradient (only visible part) - round shape
        mask_iris = ((x - render_x)**2 + (y - render_y)**2 <= iris_radius**2) & (y >= eyelid_top) & (y <= eyelid_bottom)
        
        # Calculate normalized distance from center (0.0 at center, 1.0 at edge)
        dist_squared_iris = (x - render_x)**2 + (y - render_y)**2
        dist_normalized = np.sqrt(dist_squared_iris[mask_iris]) / iris_radius
        
        # Create gradient multiplier (1.0 means no change)
        gradient_size = EYE_CONFIG['iris_gradient']['gradient_size']
        center_brightness = EYE_CONFIG['iris_gradient']['center_brightness']
        edge_darkness = EYE_CONFIG['iris_gradient']['edge_darkness']
        
        # Smooth transition from center brightness to edge darkness
        gradient_mult = np.ones_like(dist_normalized)
        center_mask = dist_normalized <= gradient_size
        gradient_mask = (dist_normalized > gradient_size)
        
        # Bright center
        gradient_mult[center_mask] = center_brightness
        
        # Gradient from center to edge
        gradient_range = dist_normalized[gradient_mask]
        gradient_mult[gradient_mask] = center_brightness + (edge_darkness - center_brightness) * ((gradient_range - gradient_size) / (1.0 - gradient_size))
        
        # Apply gradient to each color channel
        iris_color = np.array(eye_color)
        gradient_colors = np.clip(iris_color.reshape(1, 3) * gradient_mult.reshape(-1, 1), 0, 255).astype(np.uint8)
        img_array[mask_iris] = gradient_colors  # Apply gradient colors
        
        # Draw pupil (only visible part) - elliptical shape with BLACK color
        mask_pupil = (((x - render_x)**2 / (pupil_width**2)) + ((y - render_y)**2 / (pupil_height**2)) <= 1) & (y >= eyelid_top) & (y <= eyelid_bottom)
        img_array[mask_pupil] = [0, 0, 0]  # Black pupil
    else:
        # Fully open eye
        # Add glow effect around iris - round shape for outer glow
        glow_radius = iris_radius + EYE_CONFIG['glow_size']
        mask_glow = (x - render_x)**2 + (y - render_y)**2 <= glow_radius**2
        # Create glow with configurable intensity
        glow_color = [int(c * EYE_CONFIG['glow_intensity']) for c in eye_color]
        img_array[mask_glow] = glow_color
        
        # Add bright edge highlight between glow and iris
        highlight_width = EYE_CONFIG['edge_highlight']['width']
        highlight_brightness = EYE_CONFIG['edge_highlight']['brightness']
        highlight_alpha = EYE_CONFIG['edge_highlight']['alpha']
        
        # Create ring mask for the highlight
        dist_squared = (x - render_x)**2 + (y - render_y)**2
        outer_edge = iris_radius + highlight_width/2
        inner_edge = iris_radius - highlight_width/2
        mask_highlight = (dist_squared >= inner_edge**2) & (dist_squared <= outer_edge**2)
        
        # Create bright highlight color
        highlight_color = np.clip(np.array(eye_color) * highlight_brightness, 0, 255).astype(np.uint8)
        
        # Blend highlight with existing colors
        img_array[mask_highlight] = (
            (1 - highlight_alpha) * img_array[mask_highlight] + 
            highlight_alpha * highlight_color
        ).astype(np.uint8)
        
        # Draw iris with gradient - round shape
        dist_squared = (x - render_x)**2 + (y - render_y)**2
        mask_iris = dist_squared <= iris_radius**2
        
        # Calculate normalized distance from center (0.0 at center, 1.0 at edge)
        dist_normalized = np.sqrt(dist_squared[mask_iris]) / iris_radius
        
        # Create gradient multiplier (1.0 means no change)
        gradient_size = EYE_CONFIG['iris_gradient']['gradient_size']
        center_brightness = EYE_CONFIG['iris_gradient']['center_brightness']
        edge_darkness = EYE_CONFIG['iris_gradient']['edge_darkness']
        
        # Smooth transition from center brightness to edge darkness
        gradient_mult = np.ones_like(dist_normalized)
        center_mask = dist_normalized <= gradient_size
        gradient_mask = (dist_normalized > gradient_size)
        
        # Bright center
        gradient_mult[center_mask] = center_brightness
        
        # Gradient from center to edge
        gradient_range = dist_normalized[gradient_mask]
        gradient_mult[gradient_mask] = center_brightness + (edge_darkness - center_brightness) * ((gradient_range - gradient_size) / (1.0 - gradient_size))
        
        # Apply gradient to each color channel
        iris_color = np.array(eye_color)
        gradient_colors = np.clip(iris_color.reshape(1, 3) * gradient_mult.reshape(-1, 1), 0, 255).astype(np.uint8)
        img_array[mask_iris] = gradient_colors  # Apply gradient colors
        
        # Draw pupil - elliptical shape with BLACK color
        mask_pupil = ((x - render_x)**2 / (pupil_width**2)) + ((y - render_y)**2 / (pupil_height**2)) <= 1
        img_array[mask_pupil] = [0, 0, 0]  # Black pupil
    
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
    print("Current Configuration:")
    print(f"Iris Size: {EYE_CONFIG['iris_radius']}")
    print("\nNormal Eye (cat-like pupil):")
    print(f"  Size: {EYE_CONFIG['normal_pupil']['size_ratio']} × iris size")
    print(f"  Width: {EYE_CONFIG['normal_pupil']['width_ratio']} (0.2 = very narrow, 1.0 = round)")
    print(f"  Height: {EYE_CONFIG['normal_pupil']['height_ratio']}")
    print("\nTracked Eye (round pupil):")
    print(f"  Size: {EYE_CONFIG['tracked_pupil']['size_ratio']} × iris size")
    print(f"  Width: {EYE_CONFIG['tracked_pupil']['width_ratio']} (always 1.0 for round)")
    print(f"  Height: {EYE_CONFIG['tracked_pupil']['height_ratio']}")
    print("\nIris Gradient:")
    print(f"  Center Brightness: {EYE_CONFIG['iris_gradient']['center_brightness']} (>1.0 brightens)")
    print(f"  Edge Darkness: {EYE_CONFIG['iris_gradient']['edge_darkness']} (<1.0 darkens)")
    print(f"  Gradient Size: {EYE_CONFIG['iris_gradient']['gradient_size']} (0.0 to 1.0)")
    print("\nEdge Highlight:")
    print(f"  Brightness: {EYE_CONFIG['edge_highlight']['brightness']} (>1.0 brightens)")
    print(f"  Width: {EYE_CONFIG['edge_highlight']['width']} pixels")
    print(f"  Alpha: {EYE_CONFIG['edge_highlight']['alpha']} (0.0 to 1.0)")
    print(f"\nGlow Size: {EYE_CONFIG['glow_size']}")
    print(f"Glow Intensity: {EYE_CONFIG['glow_intensity']}")
    print("\nShowing normal (yellow) and tracked (red) eyes:")
    
    # Eye positions
    left_eye_x, left_eye_y = WIDTH // 2 - 60, HEIGHT // 2
    right_eye_x, right_eye_y = WIDTH // 2 + 60, HEIGHT // 2
    
    # Eye colors (get from template function)
    eye_colors = get_eye_colors()
    normal_color = eye_colors['normal_color']
    tracked_color = eye_colors['tracked_color']
    
    # Create images directly in BGR format for preview
    def create_eye_preview(eye_x, eye_y, eye_color, face_tracked=False):
        """Create eye image directly in BGR format for preview"""
        img_array = np.zeros((WIDTH, HEIGHT, 3), dtype=np.uint8)
        
        iris_radius = EYE_CONFIG['iris_radius']
        
        # Determine which pupil settings to use based on face tracking state (not color)
        pupil_config = EYE_CONFIG['tracked_pupil'] if face_tracked else EYE_CONFIG['normal_pupil']
        
        # Calculate pupil dimensions
        pupil_radius = int(iris_radius * pupil_config['size_ratio'])
        pupil_width = int(pupil_radius * pupil_config['width_ratio'])
        pupil_height = int(pupil_radius * pupil_config['height_ratio'])
        
        # Calculate eye position (clamp to bounds with margin)
        render_x = int(max(iris_radius, min(WIDTH - iris_radius, eye_x)))
        render_y = int(max(iris_radius, min(HEIGHT - iris_radius, eye_y)))
        
        # Create coordinate grids
        y, x = np.ogrid[:WIDTH, :HEIGHT]
        
        # Add glow effect around iris - ROUND shape for outer glow
        glow_radius = iris_radius + EYE_CONFIG['glow_size']
        mask_glow = (x - render_x)**2 + (y - render_y)**2 <= glow_radius**2
        glow_color = [int(c * EYE_CONFIG['glow_intensity']) for c in eye_color]
        img_array[mask_glow] = glow_color
        
        # Add bright edge highlight between glow and iris
        highlight_width = EYE_CONFIG['edge_highlight']['width']
        highlight_brightness = EYE_CONFIG['edge_highlight']['brightness']
        highlight_alpha = EYE_CONFIG['edge_highlight']['alpha']
        
        # Create ring mask for the highlight
        dist_squared = (x - render_x)**2 + (y - render_y)**2
        outer_edge = iris_radius + highlight_width/2
        inner_edge = iris_radius - highlight_width/2
        mask_highlight = (dist_squared >= inner_edge**2) & (dist_squared <= outer_edge**2)
        
        # Create bright highlight color
        highlight_color = np.clip(np.array(eye_color) * highlight_brightness, 0, 255).astype(np.uint8)
        
        # Blend highlight with existing colors
        img_array[mask_highlight] = (
            (1 - highlight_alpha) * img_array[mask_highlight] + 
            highlight_alpha * highlight_color
        ).astype(np.uint8)
        
        # Draw iris with gradient - round shape
        dist_squared = (x - render_x)**2 + (y - render_y)**2
        mask_iris = dist_squared <= iris_radius**2
        
        # Calculate normalized distance from center (0.0 at center, 1.0 at edge)
        dist_normalized = np.sqrt(dist_squared[mask_iris]) / iris_radius
        
        # Create gradient multiplier (1.0 means no change)
        gradient_size = EYE_CONFIG['iris_gradient']['gradient_size']
        center_brightness = EYE_CONFIG['iris_gradient']['center_brightness']
        edge_darkness = EYE_CONFIG['iris_gradient']['edge_darkness']
        
        # Smooth transition from center brightness to edge darkness
        gradient_mult = np.ones_like(dist_normalized)
        center_mask = dist_normalized <= gradient_size
        gradient_mask = (dist_normalized > gradient_size)
        
        # Bright center
        gradient_mult[center_mask] = center_brightness
        
        # Gradient from center to edge
        gradient_range = dist_normalized[gradient_mask]
        gradient_mult[gradient_mask] = center_brightness + (edge_darkness - center_brightness) * ((gradient_range - gradient_size) / (1.0 - gradient_size))
        
        # Apply gradient to each color channel
        iris_color = np.array(eye_color)
        gradient_colors = np.clip(iris_color.reshape(1, 3) * gradient_mult.reshape(-1, 1), 0, 255).astype(np.uint8)
        img_array[mask_iris] = gradient_colors  # Apply gradient colors
        
        # Draw pupil - elliptical shape with BLACK color
        mask_pupil = ((x - render_x)**2 / (pupil_width**2)) + ((y - render_y)**2 / (pupil_height**2)) <= 1
        img_array[mask_pupil] = [0, 0, 0]  # Black pupil
        
        # Convert RGB to BGR for OpenCV
        return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    # Create both eyes
    left_eye_bgr = create_eye_preview(left_eye_x, left_eye_y, normal_color, face_tracked=False)
    right_eye_bgr = create_eye_preview(right_eye_x, right_eye_y, tracked_color, face_tracked=True)
    
    # Combine both eyes side by side
    combined = np.hstack([left_eye_bgr, right_eye_bgr])
    
    # Add labels
    cv2.putText(combined, "Normal (Cat Pupil)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(combined, "Face Tracked (Round Pupil)", (WIDTH + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Show the preview
    cv2.imshow("Eye Template Preview", combined)
    
    # Wait for any key press to close
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    print("Preview closed.")

if __name__ == "__main__":
    preview_eyes()
