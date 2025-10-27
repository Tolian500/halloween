#!/bin/bash
# Eye Tracker Startup Script - No Preview Mode
# This script runs the eye tracker without the preview window for maximum performance

cd /home/tolian500/Coding/halloween

echo "Starting Dual Eye Tracker (No Preview Mode)..."
echo "Performance optimized for production use"
echo "Press Ctrl+C to stop"
echo ""

# Run the eye tracker without preview
python3 main.py --no-preview

