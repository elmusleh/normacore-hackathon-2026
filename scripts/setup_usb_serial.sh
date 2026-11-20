#!/usr/bin/env bash
# ==============================================================================
# setup_usb_serial.sh - Linux USB Serial & udev setup for ST3215 ElRobot Servos
# ==============================================================================
set -e

echo "=== ElRobot Linux USB Serial Setup ==="

# 1. Check if user is in dialout group
CURRENT_USER=$(whoami)
if groups "$CURRENT_USER" | grep &>/dev/null '\bdialout\b'; then
    echo "[OK] User '$CURRENT_USER' is already in 'dialout' group."
else
    echo "[+] Adding '$CURRENT_USER' to 'dialout' group..."
    sudo usermod -aG dialout "$CURRENT_USER"
    echo "[!] Added to dialout. Note: run 'newgrp dialout' if current shell cannot open /dev/ttyUSB*."
fi

# 2. Check and disable brltty conflict
if systemctl is-active --quiet brltty-udev.service 2>/dev/null; then
    echo "[+] Disabling conflicting brltty service..."
    sudo systemctl stop brltty-udev.service 2>/dev/null || true
    sudo systemctl mask brltty-udev.service 2>/dev/null || true
    echo "[OK] brltty service disabled."
else
    echo "[OK] No conflicting brltty service active."
fi

# 3. Create udev rules for FTDI, CH340, CP210x, CDC-ACM
RULE_PATH="/etc/udev/rules.d/99-elrobot-servos.rules"
echo "[+] Writing udev rules to $RULE_PATH..."
sudo tee "$RULE_PATH" > /dev/null << 'EOF'
# ElRobot ST3215 Bus Servos - Serial Bridge Permissions
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", MODE="0666", GROUP="dialout"
KERNEL=="ttyUSB*", MODE="0666", GROUP="dialout"
KERNEL=="ttyACM*", MODE="0666", GROUP="dialout"
EOF

echo "[+] Reloading udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger
echo "[OK] udev rules reloaded."

# 4. Detect currently connected serial devices
echo "--------------------------------------------------"
echo "Currently connected serial devices:"
SERIAL_DEVICES=$(ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || true)
if [ -n "$SERIAL_DEVICES" ]; then
    ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
else
    echo "  (No USB serial adapters currently plugged in. Plug in the ElRobot cable and run again)."
fi
echo "=================================================="
echo "Setup complete! ElRobot ST3215 serial is ready."
