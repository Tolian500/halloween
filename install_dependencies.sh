#!/bin/bash
# Install dependencies for GC9A01 display on Raspberry Pi

echo "Installing dependencies for GC9A01 display..."

# Update package list
sudo apt update

# Install system packages
sudo apt install -y python3-pil python3-rpi.gpio python3-spidev

# Install Python packages via pip
pip3 install Pillow RPi.GPIO spidev

# Enable SPI if not already enabled
echo "Checking SPI configuration..."
if ! grep -q "dtparam=spi=on" /boot/config.txt; then
    echo "Enabling SPI..."
    echo "dtparam=spi=on" | sudo tee -a /boot/config.txt
    echo "SPI enabled. Please reboot your Raspberry Pi."
else
    echo "SPI is already enabled."
fi

echo "Installation complete!"
echo "If SPI was just enabled, please reboot your Raspberry Pi."
echo "Then run: python3 test_gc9a01.py"
