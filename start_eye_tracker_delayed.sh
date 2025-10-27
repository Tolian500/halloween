#!/bin/bash
# Eye Tracker Auto-Start Script with Delay
# This script waits 10 seconds for hardware to initialize, then starts the eye tracker

cd /home/tolian500/Coding/halloween

# Wait 10 seconds for hardware to warm up
sleep 10

# Start the eye tracker in background
/usr/bin/python3 /home/tolian500/Coding/halloween/main.py --no-preview > /tmp/eye_tracker.log 2>&1 &
