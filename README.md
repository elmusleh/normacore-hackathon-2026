# NormaCore Physical AI & Tabletop Robotics Assistant
**2nd Edition Berlin Robotics & AI Hackathon (HackLab × BRISA — November 21–22, 2026)**
**Track:** NormaCore — *"AI-Powered Robot Control"* · **Target:** ElRobot 7+1 DOF Robotic Arm

---

## 🚀 Overview

This repository contains the complete production-grade software stack, Model Context Protocol (MCP) tool server, and testing harness for the **NormaCore Hackathon Track**.

Our objective is to integrate **Claude / Codex** with the **NormaCore Station API** to command the **ElRobot** 7+1 DOF arm in autonomous tabletop manipulation tasks (sorting, kitting, inspection) through live camera perception.

### The Winning Differentiator:
Most hackathon teams naively feed raw 2D camera images and raw joint angles into an LLM, causing arm collisions, servo burnout, and uncalibrated depth errors. We decouple **Agent Semantic Reasoning** from **Deterministic Robotics Control**:
- **Metric Homography (AprilTags):** 4 corner fiducial markers map camera pixels directly to tabletop millimeters $(x, y)$, overlaying a labeled coordinate grid onto the camera view.
- **Cartesian Safety Envelope:** Claude commands high-level millimeter coordinates (`pick_at`, `place_at`). A deterministic Python kinematics engine computes smooth trajectories and enforces a hard virtual floor ($Z \ge 12\text{ mm}$) to prevent table collisions.
- **Closed-Loop Visual Recovery:** The system verifies every grasp via gripper servo load and camera feedback. If an object is bumped or moved by a human/judge mid-task, the agent catches the disturbance and replans autonomously without crashing.

---

## ⚡ 5-Minute Team Quickstart

You can test the entire pipeline on your laptop **right now** before touching physical hardware using our master CLI runner (`./cli.sh`):

### 1. Run the Test Suite
```bash
./cli.sh test
```

### 2. Launch the Interactive 3D Digital Twin
```bash
# Opens the interactive 3D WebGL Digital Twin and live telemetry in your browser
./cli.sh digital-twin
```

### 3. Run the Autonomous Perturbation Demo
```bash
# Runs the simulated judge perturbation and self-healing recovery loop in the terminal
./cli.sh demo
```

### 4. Connect to Claude Code / Cursor / Codex via MCP
`.mcp.json` registers the `elrobot` server ([src/robot_mcp_server.py](src/robot_mcp_server.py)) for the **real arm**: `look`, `get_robot_state`, `go_to_waypoint`, `set_gripper`, `nudge_joint`, `stop` and more. It needs `.venv` with `mcp>=2` and a running Station. Motion is off until `ELROBOT_ALLOW_MOTION=1`. Setup and tool list: [docs/mcp_server.md](docs/mcp_server.md). The Cartesian simulator tools (`pick_at`, `place_at`) live in `src/mcp_server.py` and run only in the offline demo.

---

## 🛠️ Master CLI Commands (`./cli.sh`)

| Command | Action |
| :--- | :--- |
| `./cli.sh test [name]` | Run full test suite or filter by test name |
| `./cli.sh digital-twin` | Start 3D Three.js Digital Twin server at `http://localhost:8080` |
| `./cli.sh demo` | Run autonomous judge perturbation simulation in terminal |
| `./cli.sh view-camera` | Capture fresh calibrated camera snapshot with metric grid |
| `./cli.sh apriltags` | Generate 4-corner AprilTags sheet for printing/screen calibration |
| `./cli.sh station` | Launch official Station binary (`./bin/station --web --tcp`) |
| `./cli.sh setup-serial` | Run Linux USB serial & udev permissions setup for ElRobot |
| `./cli.sh mcp` | Launch MCP server over stdin/stdout |
| `./cli.sh urdf` | Open official NormaCore online 3D URDF interactive viewer |

---

## 🏗️ System Architecture

```
                       +-------------------------+
                       |    Workspace Cameras    |
                       +------------+------------+
                                    | (Annotated Metric Grid Feed)
                                    v
+------------------+       +-------------------+       +-------------------------+
| Human / Judge    | ----> |   Claude / Codex  | <---> |   NormaCore Station     |
| (Natural Lang)   |       |   Agent / VLM     |       |   Unified Runtime       |
+------------------+       +--------+----------+       +------------+------------+
                                    | (Cartesian MCP Tools)         | (Protobuf / Python SDK)
                                    v                               v
                       +---------------------------------------------------------+
                       |         Deterministic Kinematics & Safety Layer         |
                       |  - Inverse Kinematics (IK) Trajectory Generator         |
                       |  - Workspace Bounding Box (X: ±180mm, Y: 90..270mm)     |
                       |  - Virtual Table Floor Clamp (Z >= 12mm)                |
                       |  - Dual Grasp Verification (Motor Load + Visual Crop)   |
                       +----------------------------+----------------------------+
                                                    | (Safe ST3215 Joint Commands)
                                                    v
                                       +-------------------------+
                                       |  ElRobot (7+1 DOF Arm)  |
                                       +-------------------------+
```

---

## 👥 4-Person Team Role Split

To maximize velocity and avoid duplicate work during the 48-hour sprint:

| Role | Lead | Key Responsibilities | Primary Files |
| :--- | :--- | :--- | :--- |
| **Systems, Kinematics & Safety** | Mohammad | • ST3215 servo communications & Station SDK<br>• Inverse kinematics & velocity limits<br>• Hard table floor guardrails & trajectory profiles | `src/kinematics_safety.py`<br>`docs/hardware_setup_and_usb_serial.md` |
| **Vision & Calibration** | Teammate 2 | • 4-Corner AprilTag / ArUco detection<br>• Perspective homography matrix computation<br>• Real-time metric grid overlay on camera feed | `src/vision_homography.py`<br>`scripts/generate_apriltags.py` |
| **AI Agent & Prompts** | Teammate 3 | • MCP server integration (`.mcp.json`)<br>• Claude / Codex tool schemas & system prompts<br>• Closed-loop failure recovery & re-planning logic | `src/mcp_server.py`<br>`src/agent_prompts.py` |
| **Demo Design & Pitch** | Teammate 4 | • Physical tabletop props & task scenarios<br>• Split-screen live monitoring UI<br>• 3-Minute winning stage pitch deck | `docs/NormaCore_Winning_Plan.md`<br>`docs/Hackathon_Event_Logistics.md` |

---

## 📁 Repository Directory Structure

```
├── .ai-sync/                   # Cross-agent workflow synchronization
│   ├── HANDOFF.md              # Current sprint state & next steps
│   ├── PLAN.md                 # 48-Hour technical implementation plan
│   └── PROGRESS.md             # Milestone checklist
├── docs/                       # Comprehensive documentation
│   ├── NormaCore_Winning_Plan.md        # Master strategy & judge perturbation demo script
│   ├── NormaCore_Challenge_Guide.md     # Detailed technical challenge & Station specs
│   ├── NormaCore_Station_SDK_Reference.md # Official Station runtime, binary & Protobuf SDK docs
│   ├── NormaCore_Repositories_and_Tooling.md # Breakdown of all 6 GitHub repos & local assets
│   ├── Hackathon_Event_Logistics.md     # Event dates, Berlin venue, links, contacts
│   ├── hardware_setup_and_usb_serial.md # Linux USB serial & ST3215 bus servo setup guide
│   └── apriltags_printable.html         # Instant printable/screen calibration tags
├── scripts/                    # Automation utilities
│   ├── setup_usb_serial.sh     # One-click Linux USB permissions & udev installer
│   └── generate_apriltags.py   # SVG/HTML AprilTag generator (Tags 0, 1, 2, 3)
├── src/                        # Core Python codebase
│   ├── mock_station.py         # Offline hardware simulator (arm, cameras, objects)
│   ├── vision_homography.py    # Metric coordinate calibration & grid overlay
│   ├── kinematics_safety.py    # Cartesian boundaries, Z-floor clamp, trajectory generator
│   ├── mcp_server.py           # Model Context Protocol server for Claude / Codex
│   └── agent_prompts.py        # System prompt, recovery loop & automated test runner
├── tests/                      # Automated test suite
│   └── test_pipeline.py        # Unit & integration tests for kinematics, vision & recovery
├── archive/                    # Backed-up raw documents & unrelated track materials
├── .mcp.json                   # Ready-to-use MCP configuration file
├── GUIDELINES.md               # Coding standards & robotics safety guidelines
├── PREFERENCES.md              # Project preferences & conventions
├── CHANGELOG.md                # Project version history
└── requirements.txt            # Python dependencies
```

---

## 🔌 Hardware Setup: Connecting the ElRobot Arm on Linux

1. Connect the ElRobot USB serial cable to your Linux laptop.
2. Run our automated setup script to configure serial permissions without requiring `sudo`:
   ```bash
   ./scripts/setup_usb_serial.sh
   ```
3. Read the complete troubleshooting guide in [docs/hardware_setup_and_usb_serial.md](file:///home/steve/Notebooks/Projects/AI%20%26%20Robotics%20Hackathon/docs/hardware_setup_and_usb_serial.md).

---

## 🎯 The Sunday Live Demo ("Judge Perturbation")

Our stage pitch is designed around **real-world robustness**:
1. We give Claude a natural-language sorting command.
2. While the arm is in motion, we invite a judge to physically slide a target object across the table.
3. The robot senses that the target is missing (`verify_grasp() == EMPTY_GRIP`), triggers its visual recovery loop, recalculates the new coordinates from the overhead camera, and successfully completes the pick-and-place.
4. Full demo script and choreography: [docs/NormaCore_Winning_Plan.md](file:///home/steve/Notebooks/Projects/AI%20%26%20Robotics%20Hackathon/docs/NormaCore_Winning_Plan.md).
