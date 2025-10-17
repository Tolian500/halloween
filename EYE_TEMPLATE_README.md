# Eye Template

Simple eye template file for easy customization of eye appearance.

## Files

- `eye_template.py` - Contains the `create_eye_image()` function
- `main.py` - Updated to import from eye template
- `idle_animations.py` - Updated to import from eye template

## Usage

The eye template is automatically imported and used by the main script. To customize the eye appearance, simply edit the `create_eye_image()` function in `eye_template.py`.

## Customization

You can modify the eye template by editing these parameters in `eye_template.py`:

### Eye Colors
```python
# Default eye color (line 8)
eye_color = [200, 50, 25]  # Red

# Glow color intensity (line 75)
glow_color = [int(c * 0.3) for c in eye_color]  # 30% intensity

# Pupil color (line 85)
img_array[mask_pupil] = [255, 255, 255]  # White pupil
```

### Eye Sizes
```python
# Default iris radius (line 12)
iris_radius = 50  # Default size

# Pupil size ratio (line 13)
pupil_radius = iris_radius // 2  # Pupil is half the iris size

# Glow radius (line 74)
glow_radius = iris_radius + 15  # Glow extends 15 pixels beyond iris
```

### Blinking
The blinking animation is handled automatically - no changes needed.

## Examples

### Change Eye Color
```python
# In eye_template.py, line 8:
eye_color = [0, 255, 0]  # Green eyes
```

### Change Eye Size
```python
# In eye_template.py, line 12:
iris_radius = 60  # Larger eyes
```

### Change Glow Effect
```python
# In eye_template.py, line 75:
glow_color = [int(c * 0.5) for c in eye_color]  # Brighter glow (50%)
```

## Integration

The eye template is automatically used by:
- Main eye tracking script
- Idle animations
- Face detection and motion tracking

No additional setup required - just edit `eye_template.py` and restart the script.
