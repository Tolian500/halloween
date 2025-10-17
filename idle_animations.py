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
        self.animation_duration = 5.0  # Each animation runs for 10 seconds
        
        # Initialize displays
        print("Initializing displays...")
        self.left_display = GC9A01(spi_bus=0, spi_device=0, cs_pin=8, dc_pin=25, rst_pin=27)
        self.right_display = GC9A01(spi_bus=0, spi_device=1, cs_pin=7, dc_pin=24, rst_pin=23)
        
        # Animation parameters
        self.orbit_radius = 80  # Large radius to move eyes near screen edge
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
        
        # Eye color (same as main.py idle color)
        self.eye_color = [255, 255, 0]  # Yellow (idle color)
        
        # Smoothing variables to reduce shaking
        self.left_target_pos = (WIDTH//2, HEIGHT//2)
        self.right_target_pos = (WIDTH//2, HEIGHT//2)
        self.movement_speed = 0.15  # Smooth movement speed for smoother animation
        
        # Frame skipping to prevent overlapping
        self.frame_skip_counter = 0
        self.frame_skip_interval = 1  # Update display every frame for smoother animation
        
        print("Idle Animations Test Started!")
        print("Animations:")
        print("1. Rolling eyes around orbit")
        print("2. Scanning horizontally")
        print("3. Scanning vertically with random horizontal")
        print("4. Separate blinking")
        print("5. Hate eyes rolling to top")
        print("6. Slow closing eyes like sleeping")
        print("7. Arch movement (left-top-right)")
        print("Press Ctrl+C to exit")
    
    def get_animation_name(self, animation_num):
        """Get the name of the current animation"""
        animations = [
            "Rolling Eyes Around Orbit",
            "Horizontal Scanning",
            "Vertical Scanning (Random X)",
            "Blinking",
            "Hate Eyes (Roll to Top)",
            "Sleeping Eyes (Slow Close)",
            "Arch Movement (Left-Top-Right)"
        ]
        return animations[animation_num % len(animations)]
    
    def smooth_eye_movement(self):
        """Smoothly interpolate eye movement to reduce shaking"""
        # Smooth left eye movement
        current_left_x, current_left_y = self.left_eye_pos
        target_left_x, target_left_y = self.left_target_pos
        
        new_left_x = current_left_x + (target_left_x - current_left_x) * self.movement_speed
        new_left_y = current_left_y + (target_left_y - current_left_y) * self.movement_speed
        
        self.left_eye_pos = (new_left_x, new_left_y)
        
        # Smooth right eye movement
        current_right_x, current_right_y = self.right_eye_pos
        target_right_x, target_right_y = self.right_target_pos
        
        new_right_x = current_right_x + (target_right_x - current_right_x) * self.movement_speed
        new_right_y = current_right_y + (target_right_y - current_right_y) * self.movement_speed
        
        self.right_eye_pos = (new_right_x, new_right_y)
    
    def animation_1_rolling_orbit(self, t):
        """Rolling eyes around orbit - smooth circular motion"""
        # Animation parameters
        orbit_radius = 80  # Large radius to move eyes near screen edge
        
        # Simple smooth circular motion
        angle = t * 0.5 * math.pi  # Slow, smooth rotation
        
        # Calculate position
        offset_x = orbit_radius * math.cos(angle)
        offset_y = orbit_radius * math.sin(angle)
        
        center_x, center_y = WIDTH//2, HEIGHT//2
        left_x = center_x + offset_x
        left_y = center_y + offset_y
        right_x = center_x + offset_x
        right_y = center_y + offset_y
        
        # Set target positions for smooth movement
        self.left_target_pos = (left_x, left_y)
        self.right_target_pos = (right_x, right_y)
        
        return self.left_eye_pos, self.right_eye_pos
    
    def animation_2_horizontal_scan(self, t):
        """Horizontal scanning from edge to edge with holds"""
        # Edge-to-edge scanning with holds
        scan_range = 80  # Large range to reach screen edges
        hold_time = 2.0  # Hold at each edge for 2 seconds (doubled)
        move_time = 0.25  # Move between edges in 0.25 seconds (faster)
        
        # Calculate cycle time (move + hold + move + hold)
        cycle_time = 2 * (move_time + hold_time)  # Total cycle time
        
        # Normalize time within cycle
        cycle_t = t % cycle_time
        
        if cycle_t < move_time:
            # Moving from left edge to right edge
            progress = cycle_t / move_time
            offset_x = scan_range * (2 * progress - 1)  # -80 to +80
        elif cycle_t < move_time + hold_time:
            # Holding at right edge
            offset_x = scan_range  # +80 (right edge)
        elif cycle_t < 2 * move_time + hold_time:
            # Moving from right edge to left edge
            progress = (cycle_t - move_time - hold_time) / move_time
            offset_x = scan_range * (1 - 2 * progress)  # +80 to -80
        else:
            # Holding at left edge
            offset_x = -scan_range  # -80 (left edge)
        
        center_x, center_y = WIDTH//2, HEIGHT//2
        left_x = center_x + offset_x
        left_y = center_y
        right_x = center_x + offset_x
        right_y = center_y
        
        # Set target positions for smooth movement
        self.left_target_pos = (left_x, left_y)
        self.right_target_pos = (right_x, right_y)
        
        return self.left_eye_pos, self.right_eye_pos
    
    def animation_3_vertical_scan_random_x(self, t):
        """Vertical scanning: left or right half, 3 up-down cycles"""
        # Animation parameters
        scan_range = 80  # Large range to reach screen edges
        hold_time = 1.0  # Hold at each position for 1 second
        move_time = 0.25  # Move between positions in 0.25 seconds
        cycles = 3  # Do exactly 3 up-down cycles
        
        # Calculate cycle time (move + hold + move + hold)
        cycle_time = 2 * (move_time + hold_time)  # Time for one up-down cycle
        total_time = cycles * cycle_time  # Total time for all cycles
        
        # Check if animation should end
        if t >= total_time:
            # Animation finished, stay at center
            center_x, center_y = WIDTH//2, HEIGHT//2
            self.left_target_pos = (center_x, center_y)
            self.right_target_pos = (center_x, center_y)
            return self.left_eye_pos, self.right_eye_pos
        
        # Pick left or right half (set once at start of animation)
        if not hasattr(self, '_animation3_half'):
            # Randomly choose left or right half
            self._animation3_half = random.choice(['left', 'right'])
        
        # Set horizontal offset based on chosen half
        if self._animation3_half == 'left':
            offset_x = -40  # Left half of display
        else:
            offset_x = 40   # Right half of display
        
        # Calculate which cycle we're in
        cycle_num = int(t / cycle_time)
        cycle_t = t % cycle_time
        
        center_x, center_y = WIDTH//2, HEIGHT//2
        
        if cycle_t < move_time:
            # Moving up
            progress = cycle_t / move_time
            offset_y = -scan_range * progress  # 0 to -80
        elif cycle_t < move_time + hold_time:
            # Holding at top
            offset_y = -scan_range  # -80 (top edge)
        elif cycle_t < 2 * move_time + hold_time:
            # Moving down
            progress = (cycle_t - move_time - hold_time) / move_time
            offset_y = -scan_range * (1 - progress)  # -80 to 0
        else:
            # Holding at bottom
            offset_y = 0  # Center vertically
        
        left_x = center_x + offset_x
        left_y = center_y + offset_y
        right_x = center_x + offset_x
        right_y = center_y + offset_y
        
        # Set target positions for smooth movement
        self.left_target_pos = (left_x, left_y)
        self.right_target_pos = (right_x, right_y)
        
        return self.left_eye_pos, self.right_eye_pos
    
    def animation_4_blinking(self, t):
        """Separate eye blinking: close right eye, then left eye, 2 cycles"""
        # Animation parameters
        blink_duration = 0.25  # Time to close/open each eye (2x faster)
        hold_duration = 0.15  # Time to hold eye closed (2x faster)
        cycles = 2  # Do exactly 2 cycles
        
        # Calculate cycle time (right blink + left blink)
        right_blink_time = blink_duration + hold_duration + blink_duration  # close + hold + open
        left_blink_time = blink_duration + hold_duration + blink_duration   # close + hold + open
        cycle_time = right_blink_time + left_blink_time  # Time for one complete cycle
        total_time = cycles * cycle_time  # Total time for all cycles
        
        # Check if animation should end
        if t >= total_time:
            # Animation finished, both eyes open
            center_x, center_y = WIDTH//2, HEIGHT//2
            self.left_target_pos = (center_x, center_y)
            self.right_target_pos = (center_x, center_y)
            return self.left_eye_pos, self.right_eye_pos
        
        # Calculate which cycle we're in and position within cycle
        cycle_num = int(t / cycle_time)
        cycle_t = t % cycle_time
        
        center_x, center_y = WIDTH//2, HEIGHT//2
        
        # Determine blink states for each eye
        left_blink_state = 1.0  # Default: open
        right_blink_state = 1.0  # Default: open
        
        if cycle_t < right_blink_time:
            # Right eye blinking phase
            if cycle_t < blink_duration:
                # Closing right eye
                progress = cycle_t / blink_duration
                right_blink_state = 1.0 - progress  # 1.0 to 0.0
            elif cycle_t < blink_duration + hold_duration:
                # Holding right eye closed
                right_blink_state = 0.0  # Closed
            else:
                # Opening right eye
                progress = (cycle_t - blink_duration - hold_duration) / blink_duration
                right_blink_state = progress  # 0.0 to 1.0
        else:
            # Left eye blinking phase
            left_cycle_t = cycle_t - right_blink_time
            if left_cycle_t < blink_duration:
                # Closing left eye
                progress = left_cycle_t / blink_duration
                left_blink_state = 1.0 - progress  # 1.0 to 0.0
            elif left_cycle_t < blink_duration + hold_duration:
                # Holding left eye closed
                left_blink_state = 0.0  # Closed
            else:
                # Opening left eye
                progress = (left_cycle_t - blink_duration - hold_duration) / blink_duration
                left_blink_state = progress  # 0.0 to 1.0
        
        # Set positions (both eyes stay centered)
        self.left_target_pos = (center_x, center_y)
        self.right_target_pos = (center_x, center_y)
        
        # Store blink states for rendering
        self.left_blink_state = left_blink_state
        self.right_blink_state = right_blink_state
        
        return self.left_eye_pos, self.right_eye_pos
    
    def animation_5_hate_eyes(self, t):
        """Hate eyes rolling to top-side edge and holding"""
        # Animation parameters
        roll_duration = 1.0  # Time to roll up to top
        slide_duration = 1.0  # Time to slide to side
        hold_duration = 4.0  # Time to hold at top-side edge
        total_duration = roll_duration + slide_duration + hold_duration
        
        # Check if animation should end
        if t >= total_duration:
            # Animation finished, stay at center
            center_x, center_y = WIDTH//2, HEIGHT//2
            self.left_target_pos = (center_x, center_y)
            self.right_target_pos = (center_x, center_y)
            return self.left_eye_pos, self.right_eye_pos
        
        center_x, center_y = WIDTH//2, HEIGHT//2
        
        if t < roll_duration:
            # Rolling up phase
            progress = t / roll_duration
            offset_y = -80 * progress  # Move up to top edge
            offset_x = 0  # Stay centered horizontally
        elif t < roll_duration + slide_duration:
            # Sliding to side phase
            slide_progress = (t - roll_duration) / slide_duration
            offset_y = -80  # Stay at top edge
            # Slide to right side edge
            offset_x = 60 * slide_progress  # Slide to right side edge
        else:
            # Holding at top-side edge
            offset_y = -80  # Stay at top edge
            offset_x = 60   # Stay at right side edge
        
        left_x = center_x + offset_x
        left_y = center_y + offset_y
        right_x = center_x + offset_x
        right_y = center_y + offset_y
        
        # Set target positions for smooth movement
        self.left_target_pos = (left_x, left_y)
        self.right_target_pos = (right_x, right_y)
        
        return self.left_eye_pos, self.right_eye_pos
    
    def animation_6_sleeping_eyes(self, t):
        """Slow closing eyes like sleeping"""
        # Eyes stay centered
        center_x, center_y = WIDTH//2, HEIGHT//2
        self.left_target_pos = (center_x, center_y)
        self.right_target_pos = (center_x, center_y)
        
        return self.left_eye_pos, self.right_eye_pos
    
    def animation_7_arch_movement(self, t):
        """Arch movement: 2 full cycles closer to edges, faster movement, longer holds on sides"""
        # Animation parameters
        arch_radius = 100  # Much closer to edges (was 60)
        side_hold_time = 0.8  # Hold longer on sides
        move_time = 0.2  # Faster movement between positions
        cycles = 2  # 2 full cycles
        
        # Calculate timing
        # Each cycle: move to side + hold + move to other side + hold
        cycle_time = 2 * (move_time + side_hold_time)  # Time for one complete cycle
        total_arch_time = cycles * cycle_time  # Time for all cycles
        return_duration = 0.5  # Quick return to center
        total_duration = total_arch_time + return_duration
        
        # Check if animation should end
        if t >= total_duration:
            # Animation finished, stay at center
            center_x, center_y = WIDTH//2, HEIGHT//2
            self.left_target_pos = (center_x, center_y)
            self.right_target_pos = (center_x, center_y)
            return self.left_eye_pos, self.right_eye_pos
        
        center_x, center_y = WIDTH//2, HEIGHT//2
        
        if t < total_arch_time:
            # Calculate which cycle and phase we're in
            cycle_t = t % cycle_time
            cycle_num = int(t / cycle_time)
            
            if cycle_t < move_time:
                # Moving from left to right
                progress = cycle_t / move_time
                offset_x = arch_radius * (2 * progress - 1)  # -100 to +100
                offset_y = -arch_radius * 0.3  # Stay high up
            elif cycle_t < move_time + side_hold_time:
                # Holding at right side
                offset_x = arch_radius  # +100 (right edge)
                offset_y = -arch_radius * 0.3  # Stay high up
            elif cycle_t < 2 * move_time + side_hold_time:
                # Moving from right to left
                progress = (cycle_t - move_time - side_hold_time) / move_time
                offset_x = arch_radius * (1 - 2 * progress)  # +100 to -100
                offset_y = -arch_radius * 0.3  # Stay high up
            else:
                # Holding at left side
                offset_x = -arch_radius  # -100 (left edge)
                offset_y = -arch_radius * 0.3  # Stay high up
        else:
            # Return to center
            return_progress = (t - total_arch_time) / return_duration
            # Smoothly return to center from wherever we ended
            offset_x = -arch_radius * (1 - return_progress)  # Current position to 0
            offset_y = 0  # Stay at center vertically
        
        left_x = center_x + offset_x
        left_y = center_y + offset_y
        right_x = center_x + offset_x
        right_y = center_y + offset_y
        
        # Set target positions for smooth movement
        self.left_target_pos = (left_x, left_y)
        self.right_target_pos = (right_x, right_y)
        
        return self.left_eye_pos, self.right_eye_pos
    
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
            # Frame skipping to prevent overlapping
            self.frame_skip_counter += 1
            if self.frame_skip_counter < self.frame_skip_interval:
                return True  # Skip this frame
            
            self.frame_skip_counter = 0  # Reset counter
            
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
            # Check if we have separate blink states (animation 4)
            if hasattr(self, 'left_blink_state') and hasattr(self, 'right_blink_state'):
                left_blink_value = self.left_blink_state
                right_blink_value = self.right_blink_state
            else:
                # Use normal blink state for both eyes
                blink_value = 0.0 if blink_state else 1.0
                left_blink_value = blink_value
                right_blink_value = blink_value
            
            # Debug: print color being used
            if int(time.time()) != getattr(self, '_last_color_debug', -1):
                self._last_color_debug = int(time.time())
                print(f"Using eye color: {self.eye_color}")
            
            left_eye_bytes = create_eye_image(left_x, left_y, left_blink_value, {}, 50, self.eye_color, iris_radius)
            right_eye_bytes = create_eye_image(right_x, right_y, right_blink_value, {}, 50, self.eye_color, iris_radius)
            
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
                    self.current_animation = (self.current_animation + 1) % 7
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
                elif self.current_animation == 6:
                    left_pos, right_pos = self.animation_7_arch_movement(animation_time)
                
                # Smooth eye movement to reduce shaking
                self.smooth_eye_movement()
                
                # Debug: print positions occasionally
                if int(time.time()) != getattr(self, '_last_pos_debug', -1):
                    self._last_pos_debug = int(time.time())
                    print(f"Left eye: {self.left_eye_pos}, Right eye: {self.right_eye_pos}")
                
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
                
                # Render eyes using smoothed positions
                self.render_eyes(self.left_eye_pos, self.right_eye_pos, blink_state, sleep_state)
                
                # Print status every second
                if int(animation_time) != getattr(self, '_last_print_second', -1):
                    self._last_print_second = int(animation_time)
                    remaining = self.animation_duration - animation_time
                    print(f"Animation {self.current_animation + 1}: {self.get_animation_name(self.current_animation)} - {remaining:.1f}s remaining")
                
                time.sleep(1.0/20.0)  # 20 FPS (reduced to prevent overlapping)
                
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
