# NormaCore Station & ElRobot SDK Reference Guide

This reference document compiles real implementation details extracted from NormaCore's official website (`https://normacore.dev/opensource/`) and public repositories (`https://github.com/norma-core/norma-core`).

---

## 1. Official Web Resources & Repositories

| Resource | URL | Description |
| :--- | :--- | :--- |
| **Open Source Portal** | [https://normacore.dev/opensource/](https://normacore.dev/opensource/) | Overview of ElRobot, Leader-Follower teleop, and open-source roadmap |
| **ElRobot Web Playground** | [https://normacore.dev/elrobot-urdf/](https://normacore.dev/elrobot-urdf/) | Web-based 3D URDF viewer to inspect joints, links, and kinematics in the browser |
| **GitHub Organization** | [https://github.com/norma-core](https://github.com/norma-core) | All open-source repositories |
| **Main Repository** | [https://github.com/norma-core/norma-core](https://github.com/norma-core/norma-core) | Core Physical Operations Platform (Station, ElRobot, Gremlin Protobuf SDK) |
| **Community Discord** | [https://discord.gg/Z4Ytw3QfHP](https://discord.gg/Z4Ytw3QfHP) | Real-time support channel with NormaCore developers |

---

## 2. Station Runtime Architecture

NormaCore **Station** is a single compiled binary (Go/Rust/C) that runs on the control laptop. It connects to the ST3215 bus servos over USB serial and exposes:
1. **Web Dashboard:** UI for joint calibration, motor diagnostics, and video stream monitoring.
2. **TCP / Protobuf Server:** High-speed streaming interface for Python and Go clients.

### Downloading the Pre-Built Binary
Binaries are published on GitHub Releases (`v0.1.0-beta.10`+):
- **Linux AMD64 (x86_64):** `station-linux-amd64.tar.gz` (the asset name is amd64, checked 2026-11-21)
- **Linux ARM64 (aarch64 / Pi5):** `station-linux-aarch64.tar.gz`
- **macOS ARM64 (Apple Silicon):** `station-macos-arm64.dmg` / `.zip`

### Launching Station on Linux
```bash
# Extract and launch with web UI and TCP server enabled
tar -xzf station-linux-*.tar.gz
./station --web --tcp
```

---

## 3. Python SDK & Communication Protocol (`station_py`)

NormaCore provides a Python client (`software.station.shared.station_py`) that interacts with the running Station binary over TCP.

### Client Connection
```python
from software.station.shared.station_py import new_station_client

# Connect to local or remote Station instance
client = new_station_client("127.0.0.1:8000")  # or configured TCP port
```

### Subscribing to Real-Time Telemetry
Station publishes real-time joint positions and sensor telemetry to internal streaming topics:
```python
import asyncio
from target.gen_python.protobuf.drivers.st3215 import st3215

queue = asyncio.Queue()
error_queue = client.follow("st3215/inference", queue)

# Draining the queue for latest frame:
entry = await queue.get()
frame = st3215.InferenceStateReader(entry.Data)
# frame contains: motor IDs, current positions, speeds, loads, temperatures
```

### Sending ST3215 Bus Commands
Motor registers on the ST3215 half-duplex bus:
- `RAM_GOAL_POSITION`: Commanded target position (2 bytes, little-endian)
- `RAM_GOAL_SPEED`: Speed limit (2 bytes, little-endian)
- `RAM_ACC`: Acceleration limit (1 byte)
- `RAM_TORQUE_ENABLE`: 1 = active torque, 0 = free compliant movement

```python
from software.station.shared.station_py import send_commands
from target.gen_python.protobuf.station import commands as station_commands, drivers
from target.gen_python.protobuf.drivers.st3215 import st3215

# Batch sync_write command across multiple arm joints:
cmd = st3215.Command(
    target_bus_serial=bus_serial,
    sync_write=st3215.ST3215SyncWriteCommand(
        address=RAM_GOAL_POSITION,
        motors=[
            st3215.ST3215SyncWriteCommand_MotorWrite(motor_id=1, value=pos1_bytes),
            st3215.ST3215SyncWriteCommand_MotorWrite(motor_id=2, value=pos2_bytes),
            st3215.ST3215SyncWriteCommand_MotorWrite(motor_id=3, value=pos3_bytes),
        ],
    ),
)
driver_cmd = station_commands.DriverCommand(
    type=drivers.StationCommandType.STC_ST3215_COMMAND,
    body=cmd.encode(),
)
await send_commands(client, [driver_cmd])
```

---

## 4. Key Takeaways for our Hackathon Strategy

1. **Pre-Download the Binary Tonight:** Download `station-linux-amd64.tar.gz` from the GitHub release page before traveling so you don't fight venue bandwidth.
2. **Explore the 3D URDF in Browser:** Open [https://normacore.dev/elrobot-urdf/](https://normacore.dev/elrobot-urdf/) to visually verify the 7 joint axes and parallel gripper range.
3. **Seamless Switch to Real Hardware:** Our `src/mcp_server.py` and `src/kinematics_safety.py` currently plug into `MockStation`. On Saturday morning, we replace the mock with `new_station_client("127.0.0.1:8000")` and `client.follow("st3215/inference", queue)`—the high-level Claude MCP tools (`pick_at`, `place_at`, `get_calibrated_view`, `verify_grasp`) remain **100% identical**!
