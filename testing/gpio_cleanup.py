#!/usr/bin/env python3
"""
GPIO Cleanup Script for Raspberry Pi 5
Releases all GPIO pins held by lgpio
"""

import RPi.GPIO as GPIO

print("Cleaning up GPIO pins...")

try:
    # This will release all pins
    GPIO.cleanup()
    print("GPIO cleanup successful!")
except Exception as e:
    print(f"Cleanup completed (some pins may not have been in use): {e}")

print("Done. You can now run your script.")

