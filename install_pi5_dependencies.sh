#!/bin/bash

# Installation script for Raspberry Pi 5 dependencies
# This script installs the required system packages and Python dependencies

echo "Installing Raspberry Pi 5 dependencies for GC9A01 display..."

# Update package list
echo "Updating package list..."
sudo apt update

# Install system dependencies
echo "Installing system dependencies..."
sudo apt install -y python3-pil python3-gpiod python3-spidev python3-pip

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Enable SPI interface
echo "Enabling SPI interface..."
sudo raspi-config nonint do_spi 0

# Enable GPIO interface
echo "Enabling GPIO interface..."
sudo raspi-config nonint do_gpio 0

echo "Installation complete!"
echo ""
echo "To test the display, run:"
echo "python3 test_gc9a01.py"
echo ""
echo "Note: You may need to reboot after enabling SPI/GPIO interfaces."
