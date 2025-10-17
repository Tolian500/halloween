#!/usr/bin/env python3
"""
Idle Eye Animations Test
Test various idle animations for the eye tracker before integrating into main code.
"""

import time
import math
import random
from display_settings import WIDTH, HEIGHT, create_eye_image, GC9A01, send_to_display

class IdleAnimations:
    def __init__(self):
        self.current_animation = 0
        self.animation_start_time = time.time()
        self.animation_duration = 10.0  # Each animation runs for 10 seconds
        
        # Initialize displays
        print("Initializing displays...")
        self.left_display = GC9A01(spi_bus=0, spi_device=0, cs_pin=8, dc_pin=25, rst_pin=27)
        self.right_display = GC9A01(spi_bus=0, spi_device=0, cs_pin=7, dc_pin=24, rst_pin=23)
        
        # Animation parameters
        self.orbit_radius = 20  # Reduced radius to stay within bounds
        self.scan_speed = 0.5
        self.blink_duration = 0.2
        self.sleep_duration = 3.0
        
        # State variables
        self.last_blink_time = time.time()
        self.blink_interval = random.uniform(2.0, 5.0)  # Random blink interval
        self.is_blinking = False
        self.blink_start_time = 0
        
        # Eye positions (centered on each display)
        self.left_eye_pos = (WIDTH//2, HEIGHT//2)   # Center of left display
        self.right_eye_pos = (WIDTH//2, HEIGHT//2)  # Center of right display
        
        print("Idle Animations Test Started!")
        print("Animations:")
        print("1. Rolling eyes around orbit")
        print("2. Scanning horizontally")
        print("3. Scanning vertically with random horizontal")
        print("4. Separate blinking")
        print("5. Hate eyes rolling to top")
        print("6. Slow closing eyes like sleeping")
        print("Press Ctrl+C to exit")
    
    def get_animation_name(self, animation_num):
        """Get the name of the current animation"""
        animations = [
            "Rolling Eyes Around Orbit",
            "Horizontal Scanning",
            "Vertical Scanning (Random X)",
            "Blinking",
            "Hate Eyes (Roll to Top)",
            "Sleeping Eyes (Slow Close)"
        ]
        return animations[animation_num % len(animations)]
    
    def animation_1_rolling_orbit(self, t):
        """Rolling eyes around orbit"""
        # Circular motion around center
        angle = t * 2 * math.pi  # Full circle every second
        offset_x = self.orbit_radius * math.cos(angle)
        offset_y = self.orbit_radius * math.sin(angle)
        
        left_x = self.left_eye_pos[0] + offset_x
        left_y = self.left_eye_pos[1] + offset_y
        right_x = self.right_eye_pos[0] + offset_x
        right_y = self.right_eye_pos[1] + offset_y
        
        return (left_x, left_y), (right_x, right_y)
    
    def animation_2_horizontal_scan(self, t):
        """Horizontal scanning"""
        # Smooth horizontal movement
        scan_range = 20  # Reduced range to stay within bounds
        offset_x = scan_range * math.sin(t * self.scan_speed * math.pi)
        
        left_x = self.left_eye_pos[0] + offset_x
        left_y = self.left_eye_pos[1]
        right_x = self.right_eye_pos[0] + offset_x
        right_y = self.right_eye_pos[1]
        
        return (left_x, left_y), (right_x, right_y)
    
    def animation_3_vertical_scan_random_x(self, t):
        """Vertical scanning with random horizontal position"""
        # Vertical movement
        scan_range = 20  # Reduced range to stay within bounds
        
        offset_y = scan_range * math.sin(t * self.scan_speed * math.pi)
        
        # Random horizontal offset (changes every animation cycle)
        if int(t) != getattr(self, '_last_second', -1):
            self._last_second = int(t)
            self._random_x_offset = random.uniform(-15, 15)  # Reduced range
        
        offset_x = getattr(self, '_random_x_offset', 0)
        
        left_x = self.left_eye_pos[0] + offset_x
        left_y = self.left_eye_pos[1] + offset_y
        right_x = self.right_eye_pos[0] + offset_x
        right_y = self.right_eye_pos[1] + offset_y
        
        return (left_x, left_y), (right_x, right_y)
    
    def animation_4_blinking(self, t):
        """Separate blinking animation"""
        # Eyes stay centered but blink
        left_pos = self.left_eye_pos
        right_pos = self.right_eye_pos
        
        return left_pos, right_pos
    
    def animation_5_hate_eyes(self, t):
        """Hate eyes rolling to top"""
        # Eyes roll to the top
        roll_progress = min(t / 2.0, 1.0)  # Roll over 2 seconds
        offset_y = -20 * roll_progress  # Move up (reduced range)
        
        left_x = self.left_eye_pos[0]
        left_y = self.left_eye_pos[1] + offset_y
        right_x = self.right_eye_pos[0]
        right_y = self.right_eye_pos[1] + offset_y
        
        return (left_x, left_y), (right_x, right_y)
    
    def animation_6_sleeping_eyes(self, t):
        """Slow closing eyes like sleeping"""
        # Eyes stay centered but slowly close
        left_pos = self.left_eye_pos
        right_pos = self.right_eye_pos
        
        return left_pos, right_pos
    
    def should_blink(self, current_time):
        """Check if eyes should blink"""
        if current_time - self.last_blink_time > self.blink_interval:
            self.last_blink_time = current_time
            self.blink_interval = random.uniform(2.0, 5.0)  # Next blink interval
            return True
        return False
    
    def get_blink_state(self, current_time):
        """Get current blink state"""
        if self.is_blinking:
            if current_time - self.blink_start_time > self.blink_duration:
                self.is_blinking = False
                return False  # Eyes open
            else:
                return True  # Eyes closed
        return False  # Eyes open
    
    def start_blink(self, current_time):
        """Start a blink"""
        self.is_blinking = True
        self.blink_start_time = current_time
    
    def render_eyes(self, left_pos, right_pos, blink_state=False, sleep_state=False):
        """Render eyes at given positions"""
        try:
            # Clamp positions to valid display bounds
            left_x = max(40, min(WIDTH - 40, left_pos[0]))
            left_y = max(40, min(HEIGHT - 40, left_pos[1]))
            right_x = max(40, min(WIDTH - 40, right_pos[0]))
            right_y = max(40, min(HEIGHT - 40, right_pos[1]))
            
            # Determine iris radius based on state
            iris_radius = 40
            if blink_state:
                iris_radius = 2  # Almost closed
            elif sleep_state:
                iris_radius = 15  # Half closed
            
            # Create eye images
            left_eye_bytes = create_eye_image(left_x, left_y, iris_radius=iris_radius)
            right_eye_bytes = create_eye_image(right_x, right_y, iris_radius=iris_radius)
            
            # Check if eye creation was successful
            if left_eye_bytes is None or right_eye_bytes is None:
                print(f"Eye creation failed - positions: L({left_x},{left_y}) R({right_x},{right_y})")
                return False
            
            # Send to displays
            send_to_display(self.left_display, left_eye_bytes)
            send_to_display(self.right_display, right_eye_bytes)
            
            return True
            
        except Exception as e:
            print(f"Render error: {e}")
            return False
    
    def run_animation_test(self):
        """Run the animation test"""
        try:
            while True:
                current_time = time.time()
                animation_time = current_time - self.animation_start_time
                
                # Switch animation every 10 seconds
                if animation_time > self.animation_duration:
                    self.animation_start_time = current_time
                    self.current_animation = (self.current_animation + 1) % 6
                    animation_time = 0
                    print(f"\n--- Switching to Animation {self.current_animation + 1}: {self.get_animation_name(self.current_animation)} ---")
                
                # Get eye positions based on current animation
                if self.current_animation == 0:
                    left_pos, right_pos = self.animation_1_rolling_orbit(animation_time)
                elif self.current_animation == 1:
                    left_pos, right_pos = self.animation_2_horizontal_scan(animation_time)
                elif self.current_animation == 2:
                    left_pos, right_pos = self.animation_3_vertical_scan_random_x(animation_time)
                elif self.current_animation == 3:
                    left_pos, right_pos = self.animation_4_blinking(animation_time)
                elif self.current_animation == 4:
                    left_pos, right_pos = self.animation_5_hate_eyes(animation_time)
                elif self.current_animation == 5:
                    left_pos, right_pos = self.animation_6_sleeping_eyes(animation_time)
                
                # Handle blinking (except during blinking animation)
                blink_state = False
                if self.current_animation != 3:  # Not during blinking animation
                    if self.should_blink(current_time):
                        self.start_blink(current_time)
                    blink_state = self.get_blink_state(current_time)
                
                # Handle sleep state
                sleep_state = False
                if self.current_animation == 5:  # Sleeping eyes
                    sleep_progress = min(animation_time / self.sleep_duration, 1.0)
                    sleep_state = sleep_progress > 0.5  # Start closing halfway through
                
                # Render eyes
                self.render_eyes(left_pos, right_pos, blink_state, sleep_state)
                
                # Print status every second
                if int(animation_time) != getattr(self, '_last_print_second', -1):
                    self._last_print_second = int(animation_time)
                    remaining = self.animation_duration - animation_time
                    print(f"Animation {self.current_animation + 1}: {self.get_animation_name(self.current_animation)} - {remaining:.1f}s remaining")
                
                time.sleep(1.0/30.0)  # 30 FPS
                
        except KeyboardInterrupt:
            print("\nAnimation test stopped by user")
        except Exception as e:
            print(f"Animation test error: {e}")

def main():
    """Main function to run the animation test"""
    print("Starting Idle Eye Animations Test...")
    
    # Initialize animations
    animations = IdleAnimations()
    
    # Run the test
    animations.run_animation_test()
    
    print("Animation test completed!")

if __name__ == "__main__":
    main()
