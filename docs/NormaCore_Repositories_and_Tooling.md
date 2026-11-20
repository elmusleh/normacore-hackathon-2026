# NormaCore Repositories & Tooling Guide

This document breaks down every public repository in the **NormaCore GitHub Organization** (`https://github.com/orgs/norma-core/repositories`), explains what you need (and what you can safely ignore), and documents the local pre-built tools configured in this project.

---

## 1. Breakdown of NormaCore's 6 GitHub Repositories

| Repository | Tech Stack | What It Does | Do We Need to Clone It? | Action / Status in Our Project |
| :--- | :--- | :--- | :--- | :--- |
| **`norma-core/norma-core`** | Go / Python / JS / C++ | **The Main Physical Operations Platform.** Contains Station runtime, Web console, ElRobot CAD/URDF hardware files, Protobuf definitions, and Python SDK (`gremlin_py`). | **YES (100% Essential)** | **Downloaded & unpacked in `external/norma-core/`** |
| **`norma-core/normfs`** | Rust | High-performance persistent write-ahead-log (WAL) queue storage for robotics and sensor streams. | **NO** | Built directly into the compiled `bin/station` binary. No Rust development needed for our track. |
| **`norma-core/gremlin.zig`** | Zig | Zero-dependency Google Protocol Buffers implementation in pure Zig with single allocation. | **NO** | Embedded firmware tool for microcontrollers. We interact via the Python SDK. |
| **`norma-core/gremlin.c`** | C | C Protocol Buffers implementation. | **NO** | Internal C driver dependency bundled into Station. |
| **`norma-core/libuvc`** | C | Cross-platform library for USB video devices. | **NO** | Handled natively by Station and OpenCV. |
| **`norma-core/libuvc-rs`** | Rust | Rust binding around `libuvc`. | **NO** | Internal Station dependency. |

> **Summary:** The **only** repository required for the hackathon is `norma-core/norma-core`. Everything else is internal lower-level infrastructure already compiled into the Station runtime.

---

## 2. Pre-Configured Local Assets in This Project

Everything has been downloaded and verified on your laptop:

### A. Compiled Station Binary (`bin/station`)
- **Version:** `v0.1.0-beta.10` (Linux x86_64)
- **Status:** Verified working locally (`./bin/station --help`).
- **Ports & Protocols:**
  - **TCP Server (Protobuf/Gremlin):** Port `8888` (Default `0.0.0.0:8888`)
  - **Web / WebSocket Server:** Port `8889` (Default `0.0.0.0:8889` $\to$ browse to `http://localhost:8889`)
  - **Config file:** `station.yaml`

To start Station on Saturday morning:
```bash
./bin/station --web --tcp
```

### B. Full Source & Hardware Blueprints (`external/norma-core/`)
- **Assembly Manual:** `external/norma-core/hardware/elrobot/manual-follower.pdf`
- **Leader Manual:** `external/norma-core/hardware/elrobot/manual-leader.pdf`
- **Simulation Models (URDF):** `external/norma-core/hardware/elrobot/simulation/`
- **ST3215 Teleoperation Example:** `external/norma-core/software/station/examples/st3215-remote-teleop-py/`
- **Protobuf Python SDK:** `external/norma-core/shared/gremlin_py/`

### C. ElRobot Hardware Specifications (From Official BOM)
- **Total Reach:** **430 mm** (horizontal table plane)
- **Degrees of Freedom:** **7 articulated joints + 1 parallel gripper = 8 servos total**
- **Motors:** **ST3215 serial bus smart servos (12V / 30kg torque)**
- **USB Interface:** **Waveshare Serial Bus Servo Driver Board (A)** (FTDI/CH340 USB-UART bridge)
- **Power Supply:** **12V / 4A DC** power brick for the follower arm

---

## 3. How to Start Working Right Now

1. **Test the Station Binary:**
   Run `./bin/station --help` to confirm the binary executes cleanly on your Linux Mint machine.
2. **Review the Hardware Manual:**
   Open `external/norma-core/hardware/elrobot/manual-follower.pdf` to see the exact joint axis layout, zero-home calibration positions, and motor ID assignments (IDs 1 through 8).
3. **Inspect the Web Playground:**
   Open [https://normacore.dev/elrobot-urdf/](https://normacore.dev/elrobot-urdf/) to move joints virtually and verify angle limits before running code on physical hardware.
4. **Run Our Test Suite:**
   ```bash
   python3 -m pytest tests/test_pipeline.py -v
   ```
   Our mock simulator already models these exact 8 degrees of freedom, coordinate bounds ($Y \in [90, 270]\text{mm}$), and gripper load feedback!
