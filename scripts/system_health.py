#!/usr/bin/env python3
"""System & Hardware Diagnostics Check for NormaCore & ElRobot.
Reports connected devices, missing dependencies, udev rules, permissions,
and station status in a clear, formatted summary.
"""

from __future__ import annotations

import glob
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

# Terminal colors
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_BLUE = "\033[34m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_CYAN = "\033[36m"

def check_tcp_port(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

def get_connected_cameras() -> list[str]:
    return sorted(glob.glob("/dev/video*"))

def get_connected_serials() -> list[str]:
    serials = glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")
    return sorted(serials)

def main() -> int:
    print(f"{C_BOLD}{C_BLUE}================================================================{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}         NormaCore & ElRobot Hardware Health Check             {C_RESET}")
    print(f"{C_BOLD}{C_BLUE}================================================================{C_RESET}")

    missing_items = []
    warnings = []

    # 1. Station Daemon Status
    tcp_8888 = check_tcp_port(8888)
    web_8889 = check_tcp_port(8889)
    if tcp_8888:
        print(f"[{C_GREEN}CONNECTED{C_RESET}] NormaCore Station TCP Daemon: listening on port 8888")
    else:
        print(f"[{C_YELLOW}STOPPED{C_RESET}]   NormaCore Station TCP Daemon: not running (port 8888)")
        warnings.append("Station daemon stopped (run './cli.sh start' or './cli.sh station')")

    if web_8889:
        print(f"[{C_GREEN}ACTIVE{C_RESET}]    NormaCore Station Web Console: http://localhost:8889")
    else:
        print(f"[{C_YELLOW}STOPPED{C_RESET}]   NormaCore Station Web Console: port 8889 inactive")

    # 2. Serial Arms Bus Connections
    serials = get_connected_serials()
    if serials:
        print(f"[{C_GREEN}CONNECTED{C_RESET}] Serial Port(s) Detected: {', '.join(serials)}")
    else:
        print(f"[{C_RED}MISSING{C_RESET}]   Serial Port(s): No /dev/ttyACM* or /dev/ttyUSB* detected.")
        missing_items.append("ElRobot USB serial cables not detected (check 12V power & USB cables)")

    # 3. Cameras
    cams = get_connected_cameras()
    if cams:
        print(f"[{C_GREEN}CONNECTED{C_RESET}] Camera Nodes Detected: {', '.join(cams)}")
    else:
        print(f"[{C_YELLOW}MISSING{C_RESET}]   Camera Nodes: No /dev/video* devices found.")
        warnings.append("No USB cameras connected (plug in the cameras)")

    # 4. Udev Permissions & Camera Rules
    camera_rule = Path("/etc/udev/rules.d/99-normacore-cameras.rules")
    if camera_rule.exists():
        print(f"[{C_GREEN}INSTALLED{C_RESET}] Camera udev Rule: {camera_rule}")
    else:
        print(f"[{C_YELLOW}MISSING{C_RESET}]   Camera udev Rule: {camera_rule} not found.")
        print(f"            -> Required for Station to show cameras in http://localhost:8889")
        print(f"            -> Fix: sudo cp scripts/99-normacore-cameras.rules /etc/udev/rules.d/ && sudo udevadm trigger")
        warnings.append("Camera udev rule not installed (run: sudo cp scripts/99-normacore-cameras.rules /etc/udev/rules.d/ && sudo udevadm trigger)")

    servo_rule = Path("/etc/udev/rules.d/99-elrobot-servos.rules")
    if servo_rule.exists():
        print(f"[{C_GREEN}INSTALLED{C_RESET}] Servo udev Rule: {servo_rule}")
    else:
        print(f"[{C_YELLOW}MISSING{C_RESET}]   Servo udev Rule: {servo_rule} not found.")
        warnings.append("Servo udev rule not installed (run './cli.sh setup-serial')")

    # 5. Calibration Files
    calib_desktop = Path("/home/steve/Desktop/AI & Robotics Hackathon/calibration")
    f_follower = calib_desktop / "elrobot_follower_5B61034962.json"
    f_leader = calib_desktop / "elrobot_leader_5B61037051.json"
    station_data = Path("station_data")

    if f_follower.exists() and f_leader.exists():
        print(f"[{C_GREEN}FOUND{C_RESET}]     Desktop Calibration Snapshots: Follower & Leader verified.")
    else:
        print(f"[{C_YELLOW}NOTICE{C_RESET}]    Desktop Calibration Files: Missing snapshot files.")

    if station_data.exists() and any(station_data.iterdir()):
        print(f"[{C_GREEN}ACTIVE{C_RESET}]    Station Database: Active calibration state in station_data/")
    else:
        print(f"[{C_YELLOW}NOTICE{C_RESET}]    Station Database: station_data/ is empty.")

    # 6. Tools & Binary Dependencies
    for tool in ["v4l2-ctl", "gnome-terminal"]:
        if shutil.which(tool):
            print(f"[{C_GREEN}FOUND{C_RESET}]     System Utility: {tool}")
        else:
            print(f"[{C_YELLOW}OPTIONAL{C_RESET}]  System Utility: {tool} not found.")

    print(f"{C_BOLD}{C_BLUE}================================================================{C_RESET}")
    if missing_items:
        print(f"{C_BOLD}{C_RED}Action Required (Missing Items):{C_RESET}")
        for item in missing_items:
            print(f"  ❌ {item}")
    elif warnings:
        print(f"{C_BOLD}{C_YELLOW}Status Notices:{C_RESET}")
        for w in warnings:
            print(f"  ⚠️  {w}")
    else:
        print(f"{C_BOLD}{C_GREEN}All hardware, permissions, and services are fully ready!{C_RESET}")
    print(f"{C_BOLD}{C_BLUE}================================================================{C_RESET}\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
