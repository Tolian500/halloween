#!/bin/bash
# Setup Script for Auto-Start Eye Tracker on Boot

echo "========================================="
echo "Setting up Eye Tracker Auto-Start"
echo "========================================="

# Copy service file to systemd directory
echo "Installing systemd service..."
sudo cp halloween-eye-tracker.service /etc/systemd/system/

# Reload systemd
echo "Reloading systemd..."
sudo systemctl daemon-reload

# Enable the service
echo "Enabling eye tracker service..."
sudo systemctl enable halloween-eye-tracker.service

echo ""
echo "========================================="
echo "Setup complete!"
echo "========================================="
echo ""
echo "The eye tracker will now start automatically on boot."
echo ""
echo "Useful commands:"
echo "  sudo systemctl start halloween-eye-tracker   # Start service now"
echo "  sudo systemctl stop halloween-eye-tracker    # Stop service"
echo "  sudo systemctl status halloween-eye-tracker  # Check status"
echo "  sudo systemctl disable halloween-eye-tracker # Disable auto-start"
echo "  journalctl -u halloween-eye-tracker -f      # View logs in real-time"
echo ""
