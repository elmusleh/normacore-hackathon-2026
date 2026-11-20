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

You can test the entire pipeline on your laptop **right now** before touching physical hardware:

### 1. Clone & Install Dependencies
```bash
# Clone the repository
git clone <repo-url>
cd "AI & Robotics Hackathon"

# Install requirements
pip install -r requirements.txt
```

### 2. Run the Offline Verification Suite
```bash
# Run all unit and integration tests
python3 -m pytest tests/test_pipeline.py -v
```

### 3. Run the Autonomous Perturbation Demo
```bash
# Runs the simulated judge perturbation and self-healing recovery loop
python3 src/agent_prompts.py
```

### 4. Connect to Claude Code / Cursor / Codex via MCP
This repo includes a pre-configured `.mcp.json` file. When you open this folder in Claude Code or Cursor, the tools (`get_calibrated_view`, `pick_at`, `place_at`, `verify_grasp`, `reset_home`) are automatically registered!

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
