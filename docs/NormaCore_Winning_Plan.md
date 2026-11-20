# NormaCore Challenge: The Winning Battle Plan
**HackLab × BRISA Berlin Robotics & AI Hackathon (November 21–22, 2026)**
**Lead Contributor:** Mohammad El-Musleh (Embedded Systems & Robotics Specialist)
**Track:** AI-Powered Robot Control · **Grand Prize:** ElRobot Physical Robotic Arms to Take Home

---

## 1. Executive Summary & Winning Thesis

Most hackathon participants are pure-AI / web developers who will approach this challenge naively: they will pipe raw webcam frames and raw servo joint angles directly into Claude or Codex prompts. 

### Why Opponents Will Fail:
1. **Uncalibrated 2D Depth Hallucination:** 2D cameras lack depth. LLMs guessing 3D positions from raw pixel estimates miss grasps by centimeters or slam the gripper into the table.
2. **Servo Jitter & Kinematic Instability:** Letting an LLM output 7 individual joint angles causes unnatural trajectories, servo torque overload, and table gouging.
3. **Open-Loop Fragility:** If a grasp slips or an object shifts, standard prompt loops proceed blindly and place non-existent objects into target bins.
4. **Time Lost to Setup:** Opponents will spend 4–6 hours on Saturday morning battling USB serial permissions, camera indexing, and basic MCP configuration.

### How We Win First Place:
We decouple **High-Level Agent Reasoning** from **Deterministic Low-Level Robotics**:
- **Arrive Pre-Configured:** We arrive in Berlin with the Station SDK, MCP tool definitions, and simulated test harness pre-built. Time to first physical arm movement: **< 15 minutes**.
- **Metric Tabletop Homography (AprilTags/ArUco):** 4 corner fiducial markers map camera pixels directly to tabletop millimeters $(x, y)$, with a labeled metric coordinate grid drawn directly onto the image sent to Claude/Codex.
- **Cartesian Safety Guardrails & IK:** The agent *never* touches joint angles. It commands $(x, y, z)$ cartesian targets. A deterministic Python inverse kinematics (IK) solver calculates smooth joint paths while enforcing a strict virtual floor $(z \ge z_{\text{table}} + \epsilon)$ and bounding perimeter.
- **Closed-Loop Telemetry & Visual Recovery:** After every pick, we verify gripper motor load via Station and capture a post-action camera crop. If a grasp fails, the agent receives structured telemetry (`"GRASP_MISSED: object at (142mm, -30mm)"`) and self-corrects autonomously.
- **The "Judge Perturbation" Showstopper:** During the live 3-minute stage demo, we invite a judge to slide an object across the table while the robot is running. Claude detects the movement on camera, replans live, and successfully finishes the task.

---

## 2. System Architecture

```
                                  +-----------------------------+
                                  | Human Judge / Verbal Prompt |
                                  +--------------+--------------+
                                                 |
                                                 v
+------------------------+            +---------------------+
| Overhead Camera Feed   | ---------> | Claude / Codex Agent|
| (With Labeled Overlay) |            | (Semantic Planner)  |
+------------------------+            +----------+----------+
                                                 |
                                                 | (High-Level Cartesian Tool Calls)
                                                 v
+---------------------------------------------------------------------------------------+
|                             NormaCore MCP Server Wrapper                              |
|                                                                                       |
|  [ Tool Definitions ]                                                                 |
|   • get_calibrated_view()    ---> Returns annotated camera image + detected object IDs|
|   • pick_at(x_mm, y_mm, yaw) ---> Approach from top -> lower -> grip -> lift to clear|
|   • place_at(x_mm, y_mm)     ---> Move in high plane -> lower -> release -> retreat   |
|   • set_gripper(state)       ---> Commanded grip with force/compliance limits         |
|   • verify_grasp()           ---> Dual check: gripper servo load + visual inspection  |
|   • reset_home()             ---> Safe retraction to neutral home pose                |
|                                                                                       |
|  [ Deterministic Safety & Kinematics Engine ]                                         |
|   • Metric Perspective Homography (AprilTags / OpenCV)                                |
|   • 7-DOF Inverse Kinematics Solver (Cartesian -> Joint Angles)                       |
|   • Bounding Box Clamping (Hard Z-floor: z >= 12mm above tabletop)                    |
|   • Velocity & Acceleration Profiling (S-curve trajectory generation)                 |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            | (Python / Protobuf SDK: gremlin_py)
                                            v
+---------------------------------------------------------------------------------------+
|                              NormaCore Station Runtime                                |
|  - USB Serial Driver for ST3215 Bus Servos                                            |
|  - Real-Time Joint Telemetry & Motor Current/Load Feedback                            |
|  - Synchronized Multi-Camera Stream Pipeline (WebRTC / RTSP / OpenCV)                 |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v
                               +-------------------------+
                               |  ElRobot (7+1 DOF Arm)  |
                               +-------------------------+
```

---

## 3. 4-Person Team Role Split & Responsibilities

Since HackLab confirmed teams of 4, dividing ownership before kickoff prevents duplicate work and ensures every aspect is polished:

| Member | Primary Title | Core Deliverables | Focus Areas |
| :--- | :--- | :--- | :--- |
| **Member 1**<br>*(Mohammad)* | **Systems, Kinematics & Safety Lead** | • Python IK solver & safety wrapper<br>• Station SDK (`gremlin_py`) integration<br>• Joint limits, velocity clamps, Z-floor guardrails | Ensures the arm moves smoothly and never slams into the table or burns out servos. |
| **Member 2** | **Computer Vision & Calibration Lead** | • AprilTag / ArUco 4-corner homography<br>• Real-time camera calibration script<br>• Annotated metric grid overlay on image feeds | Translates camera pixels into exact real-world millimeter coordinates $(x, y)$. |
| **Member 3** | **AI Agent & Prompt Engineering Lead** | • MCP server configuration (`.mcp.json`)<br>• Claude / Codex tool schemas & prompt design<br>• Closed-loop failure recovery logic | Designs the autonomous agent loop, task decomposition, and error-handling prompts. |
| **Member 4** | **Demo Design, UI & Stage Pitch Lead** | • Tabletop task props (sorting bins, color-coded parts)<br>• Split-screen live monitoring UI (camera + terminal logs)<br>• 3-minute winning pitch deck & live demo script | Crafts the commercial narrative and runs stress testing to ensure 100% demo reliability. |

---

## 4. Pre-Hackathon Scaffolding (Ready Before Kickoff)

To avoid losing Saturday morning, the following components are prepared and tested in this repository:

1. **`src/mock_station.py`**: A simulated NormaCore Station runtime that generates synthetic camera frames, simulates ST3215 servo responses, and reports realistic motor telemetry. This allows full agent testing offline.
2. **`src/vision_homography.py`**: OpenCV script that detects 4 AprilTags at the workspace corners, computes the $3 \times 3$ perspective transform matrix, and projects a millimeter coordinate grid onto the camera feed.
3. **`src/kinematics_safety.py`**: The deterministic cartesian kinematics engine with workspace boundaries, virtual floor clamping, and pick-and-place primitive trajectory generation.
4. **`src/mcp_server.py`**: The Model Context Protocol server exposing `get_calibrated_view()`, `pick_at()`, `place_at()`, `verify_grasp()`, and `reset_home()`.
5. **`src/agent_loop.py`**: The complete autonomous execution loop running Claude Code / Codex with visual verification and automatic re-planning.

---

## 5. Minute-by-Minute 48-Hour Sprint Roadmap

### Friday Night (Tonight)
- [x] Review architecture and confirm team strategy.
- [ ] Send reply to HackLab confirming team roster and introduce teammates.
- [ ] Test local mock MCP server and OpenCV AprilTag homography scripts on laptop.

### Saturday Morning (09:00 – 13:00) — Zero-Downtime Hardware Onboarding
- **09:00 – 10:00:** Check-in, table assignment, and track briefing from NormaCore engineers.
- **10:00 – 10:30:** Hardware setup: Plug in ElRobot power supply and USB serial cable; connect USB cameras.
- **10:30 – 11:30:** Launch NormaCore Station Web Console: verify servo communication, home all 7 joints, test gripper actuation.
- **11:30 – 12:30:** Mount overhead camera, place 4 printed AprilTags at table corners, and run `vision_homography.py` to establish the millimeter coordinate system.
- **12:30 – 13:00:** **Milestone 1:** First end-to-end cartesian move on real hardware (`move_to(x=150, y=0, z=50)`).

### Saturday Afternoon (13:00 – 18:00) — Agent Tooling & Kinematic Primitives
- **13:00 – 15:00:** Connect MCP server to NormaCore Station runtime. Test `get_calibrated_view()` and `pick_at()` directly via Claude Code CLI.
- **15:00 – 17:00:** Implement pick-and-place state machine with approach vectors (vertical descent, grasp, lift before transit).
- **17:00 – 18:00:** **Milestone 2:** Autonomous pick-and-place of a single colored cube from natural language command.

### Saturday Evening (18:00 – 23:00) — Closed-Loop Recovery & Stress Testing
- **18:00 – 20:00:** Implement grasp verification: check gripper motor load + capture post-grasp crop to confirm item presence.
- **20:00 – 22:00:** Add dynamic re-planning prompt: if grasp misses, re-capture image, detect shifted coordinate, and execute second attempt.
- **22:00 – 23:00:** **Milestone 3:** Full multi-step task completion (sorting 3 objects into separate bins) without human intervention.

### Sunday Morning (09:00 – 13:00) — Demo Polishing & Rehearsal
- **09:00 – 11:00:** Rehearse the live demo 10 times consecutively under venue lighting conditions.
- **11:00 – 12:00:** Build split-screen display (Left: Live camera feed + coordinate grid overlay; Right: Live Claude reasoning stream & tool calls).
- **12:00 – 13:00:** Finalize 3-minute pitch deck (Problem $\to$ Physical AI Solution $\to$ Live Perturbation Demo $\to$ Commercial Value).

### Sunday Afternoon (13:00 – 17:00) — Live Pitch & Judging
- Execute the winning live demo in front of the judges.
- Collect feedback from NormaCore engineers and network for 2027 *Werkstudent* / R&D robotics opportunities.

---

## 6. The Winning 3-Minute Live Stage Demo Script

### Setup: Split-Screen Projection
- **Screen Left:** Full-screen video stream of the tabletop with AprilTag markers, detected object bounding boxes, and millimeter coordinate labels.
- **Screen Right:** Live Claude Code / Codex terminal output showing tool calls (`pick_at`, `verify_grasp`), reasoning tokens, and telemetry logs.

### Minute 0:00 – 0:45: The Problem & Solution Pitch
> *"Most Physical AI demos are brittle: LLMs hallucinate coordinates and arms slam into tables. Today, using NormaCore Station, we built a zero-training, self-healing tabletop assistant with deterministic kinematics and closed-loop visual verification."*

### Minute 0:45 – 1:45: Complex Multi-Step Natural Language Task
- Speaker speaks prompt into microphone:
  > *"Inspect the workstation, sort all blue components into the left tray, and place the green tool into the assembly fixture."*
- Claude inspects image, identifies objects, logs exact millimeter coordinates, and executes smooth pick-and-place moves on the ElRobot arm.

### Minute 1:45 – 2:30: The Showstopper — The Live Judge Perturbation
- While the arm is moving toward the green tool, the presenter turns to a judge:
  > *"Please slide this green tool across the table or bump it."*
- Judge moves the tool by 10 cm.
- The robot arrives at the old coordinate, detects that the object shifted, triggers `verify_grasp()`, and outputs:
  `[RECOVERY LOOP] Object absent at expected coordinate. Re-inspecting workspace...`
- The camera captures the new scene, re-computes the new $(x, y)$ coordinate, moves directly to the updated location, grips the tool, and completes the placement!
- **Audience & Judge Reaction:** Proves real autonomous intelligence, not a hardcoded trajectory replay.

### Minute 2:30 – 3:00: Architecture & Commercial Pitch
- Show 1 slide highlighting:
  - NormaCore Station Python/Protobuf SDK integration
  - 4-Corner AprilTag homography (sub-millimeter precision)
  - Virtual safety envelope (0 collisions, 0 servo stalls)
- Closing sentence:
  > *"By combining NormaCore's runtime with agentic closed-loop recovery, any workshop or lab can automate precision manipulation tasks on Day 1 without training new models."*
