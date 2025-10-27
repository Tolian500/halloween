# Auto-Start Setup for Halloween Eye Tracker

This guide will help you set up the eye tracker to start automatically on boot, with a 15-second delay to allow hardware initialization.

## Installation Steps

1. **Copy the service file to systemd directory:**
   ```bash
   sudo cp halloween-eye-tracker.service /etc/systemd/system/
   ```

2. **Reload systemd to recognize the new service:**
   ```bash
   sudo systemctl daemon-reload
   ```

3. **Enable the service to start on boot:**
   ```bash
   sudo systemctl enable halloween-eye-tracker.service
   ```

4. **Start the service immediately (optional):**
   ```bash
   sudo systemctl start halloween-eye-tracker.service
   ```

5. **Check the service status:**
   ```bash
   sudo systemctl status halloween-eye-tracker.service
   ```

## Managing the Service

- **Stop the service:**
  ```bash
  sudo systemctl stop halloween-eye-tracker.service
  ```

- **Restart the service:**
  ```bash
  sudo systemctl restart halloween-eye-tracker.service
  ```

- **Disable auto-start on boot:**
  ```bash
  sudo systemctl disable halloween-eye-tracker.service
  ```

- **View service logs:**
  ```bash
  sudo journalctl -u halloween-eye-tracker.service -f
  ```

## Features

- **15-second delay**: Waits for hardware to fully initialize (camera, displays, GPIO)
- **No preview mode**: Maximum performance for production use
- **Auto-restart**: Automatically restarts if the service crashes
- **Proper user**: Runs as your user (tolian500)

## Troubleshooting

If the service keeps failing to start:

1. **Check the logs:**
   ```bash
   sudo journalctl -u halloween-eye-tracker.service -n 50
   ```

2. **Test manually first:**
   ```bash
   python3 main.py --no-preview
   ```

3. **Increase delay if needed** - Edit the service file:
   ```bash
   sudo nano /etc/systemd/system/halloween-eye-tracker.service
   ```
   Change `ExecStartPre=/bin/sleep 15` to a longer delay like 30 or 45 seconds.

4. **Disable the service and use manual start:**
   ```bash
   sudo systemctl disable halloween-eye-tracker.service
   sudo systemctl stop halloween-eye-tracker.service
   ./start_eye_tracker.sh
   ```

## Power Bank Issues

If you're experiencing reboot loops when using a power bank:

1. **Check power bank capacity** - Pi 5 needs 5V @ 5A minimum
2. **Use a quality power bank** - Look for "Raspberry Pi compatible" or laptop power banks
3. **Try underclocking** - Add to `/boot/config.txt`:
   ```
   arm_freq=1200
   gpu_freq=400
   ```
4. **Disable unnecessary services**:
   ```bash
   sudo systemctl disable bluetooth
   sudo systemctl disable wifi  # if not needed
   sudo systemctl disable avahi-daemon
   ```

## Alternative: Manual Start Script

If auto-start causes issues, you can manually start the tracker:

```bash
./start_eye_tracker.sh
```

Or add to `/etc/rc.local` (before `exit 0`):
```bash
su tolian500 -c "cd /home/tolian500/Coding/halloween && /usr/bin/python3 main.py --no-preview &"
```
