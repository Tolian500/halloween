#!/bin/bash

# Simple Raspberry Pi Camera Installation Script

echo "🎃 Simple Camera Setup for Raspberry Pi"
echo "======================================="

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
    echo "⚠️  Warning: This script is designed for Raspberry Pi"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system packages
echo "📦 Updating system packages..."
sudo apt update

# Install Python and picamera2
echo "🐍 Installing Python and camera dependencies..."
sudo apt install -y python3 python3-pip python3-picamera2

# Enable camera interface
echo "📷 Enabling camera interface..."
sudo raspi-config nonint do_camera 0

# Create virtual environment
echo "🏗️  Creating virtual environment..."
python3 -m venv camera_env
source camera_env/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Installation completed!"
echo ""
echo "🚀 To run the camera:"
echo "   1. Activate virtual environment: source camera_env/bin/activate"
echo "   2. Run the camera: python3 main.py"
echo "   3. Press 'q' in camera window or Ctrl+C to stop"
echo "   4. Deactivate when done: deactivate"
echo ""
echo "🎃 Happy Halloween!"