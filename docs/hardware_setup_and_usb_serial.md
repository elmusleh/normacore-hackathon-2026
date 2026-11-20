# Linux USB Serial & Hardware Setup Guide for ElRobot Arm

This guide walks you through connecting the **ElRobot 7+1 DOF arm** (ST3215 serial bus servos) to a Linux (Linux Mint / Ubuntu / Debian) machine with zero permission errors.

---

## 1. How the Hardware Communication Works

- **Actuators:** The ElRobot arm uses **ST3215 serial bus smart servos**. Unlike RC hobby servos that take PWM, ST3215 servos use a half-duplex UART serial bus protocol daisy-chained together.
- **USB Interface:** The robot connects to your computer via a USB-to-UART adapter board (typically featuring an **FTDI**, **CH340**, or **CP2102** bridge chip).
- **Linux Device Node:** When plugged in, Linux kernel drivers create a device node:
  - `/dev/ttyUSB0` (for FTDI, CH340, CP2102)
  - OR `/dev/ttyACM0` (for CDC-ACM USB microcontrollers)
- **Baud Rate:** ST3215 servos operate at high baud rates—typically **1,000,000 baud (1 Mbps)** or **115,200 baud**.

---

## 2. Why Linux Blocks Non-Root Users (The Permission Problem)

On fresh Linux installations:
```bash
$ ls -l /dev/ttyUSB0
crw-rw---- 1 root dialout 188, 0 Nov 21 10:15 /dev/ttyUSB0
```
- The device is owned by `root:dialout` with `0660` permissions.
- If your user account is not in the `dialout` group, NormaCore Station or Python scripts will crash with:
  ```text
  PermissionError: [Errno 13] Permission denied: '/dev/ttyUSB0'
  ```
- **Never run Station with `sudo`:** Running your python environment or MCP server with `sudo` breaks virtualenvs, creates root-locked logs, and introduces security hazards.

---

## 3. Quick Fix (Run the Automated Script)

We have created an automated setup script in `scripts/setup_usb_serial.sh`. Simply run:
```bash
chmod +x scripts/setup_usb_serial.sh
./scripts/setup_usb_serial.sh
```

---

## 4. Manual Step-by-Step Configuration

If you prefer to configure it manually or need to troubleshoot on-site:

### Step 1: Add User to `dialout` Group
```bash
sudo usermod -aG dialout $USER
```
*(Note: Group changes require a logout/login, or running `newgrp dialout` in your current terminal session).*

### Step 2: Install Permanent `udev` Rule (Recommended)
This rule tells the Linux kernel to automatically grant read/write permissions (`0666`) to any USB serial adapter when plugged in:

```bash
sudo tee /etc/udev/rules.d/99-elrobot-servos.rules << 'EOF'
# FTDI, CH340, CP210x USB-to-Serial Bridges for ST3215 Servos
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", MODE="0666", GROUP="dialout"
KERNEL=="ttyUSB*", MODE="0666", GROUP="dialout"
KERNEL=="ttyACM*", MODE="0666", GROUP="dialout"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Step 3: Prevent Ubuntu/Mint `brltty` Conflicts
On Linux Mint and Ubuntu, a background braille daemon named `brltty` often intercepts CH340 / FTDI serial devices and abruptly claims them, causing `/dev/ttyUSB0` to vanish 2 seconds after being plugged in!

To disable `brltty`:
```bash
sudo systemctl stop brltty-udev.service 2>/dev/null || true
sudo systemctl mask brltty-udev.service 2>/dev/null || true
```

---

## 5. Verification Checklist When You Plug In the Arm

When you sit at your hackathon desk and plug the ElRobot USB cable into your laptop:

1. **Check Kernel Messages:**
   ```bash
   dmesg | tail -n 20
   ```
   *Expected output:* You should see `ch341-uart converter now attached to ttyUSB0` or `ftdi_sio converter now attached to ttyUSB0`.

2. **Verify Device Permissions:**
   ```bash
   ls -l /dev/ttyUSB* /dev/ttyACM*
   ```
   *Expected output:* `crw-rw-rw- 1 root dialout ... /dev/ttyUSB0`

3. **Test Serial Port in Python:**
   ```bash
   python3 -c "
   import serial.tools.list_ports
   ports = list(serial.tools.list_ports.comports())
   print('Available Serial Ports:', [p.device for p in ports])
   "
   ```

4. **Launch NormaCore Station:**
   Point Station to `/dev/ttyUSB0` (or leave it on auto-detect). The Web console will light up green for all 7 joints and the gripper.
