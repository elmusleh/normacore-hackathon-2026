# NormaCore Challenge: AI-Powered Robot Control
**HackLab × BRISA — Berlin Robotics & AI Hackathon (November 21–22, 2026)**

---

## 1. Challenge Overview & Vision

- **Track Title:** AI-Powered Robot Control
- **Sponsor:** **NormaCore** (Physical AI runtime and open-source data infrastructure)
- **Primary Goal:** Connect vision-language AI models (**Claude** or **Codex**) to real manipulation hardware via the **NormaCore Station API** to create an autonomous tabletop robotic assistant.
- **The Core Problem:** High-latency Vision-Language Models (VLMs) excel at semantic spatial reasoning and planning, but fail if forced to output raw low-level motor signals. The goal is to build an intelligent orchestration pipeline: the VLM perceives the workspace through cameras and commands high-level cartesian actions, while a deterministic Python control layer enforces inverse kinematics, workspace bounds, and real-time safety.

---

## 2. Hardware & Software Stack

| Layer | Technology | Specification / Role |
| :--- | :--- | :--- |
| **Hardware** | **ElRobot** | 3D-printable 7+1 DOF robotic arm designed for teleoperation and demonstration recording. |
| **Perception** | **USB Cameras** | Synchronized workspace and overhead cameras streaming live video frames. |
| **Runtime Layer** | **NormaCore Station** | Unified open-source physical operations runtime exposing motor/joint endpoints via Python/Protobuf interfaces. |
| **Agent / Reasoning** | **Claude / Codex** | Vision-language foundation models operating via function calling / Model Context Protocol (MCP) loops. |
| **Control & Safety** | **Python Kinematics** | Inverse Kinematics (IK) solver, workspace bounding boxes, speed/acceleration clamps, and visual calibration. |

---

## 3. End-to-End System Architecture

```
                       +-------------------------+
                       |    Workspace Cameras    |
                       +------------+------------+
                                    | (Live Video / Snapshots)
                                    v
+------------------+       +-------------------+       +-------------------------+
| Human Instructor | ----> |   Claude / Codex  | <---> |   NormaCore Station     |
| (Natural Lang)   |       |   Agent / VLM     |       |   Unified Runtime       |
+------------------+       +--------+----------+       +------------+------------+
                                    |                               | (Protobuf / Python SDK)
                                    | (Cartesian Tool Calls)        |
                                    v                               v
                       +---------------------------------------------------------+
                       |               Python Safety & Control Layer             |
                       |  - Inverse Kinematics (IK) Solver                       |
                       |  - Workspace Bounding Box & Collision Guardrails        |
                       |  - Velocity, Acceleration & Torque Clamps               |
                       |  - Camera-to-Arm Coordinate Calibration (ArUco/Tags)    |
                       +----------------------------+----------------------------+
                                                    | (Safe Joint Angles & Torques)
                                                    v
                                       +-------------------------+
                                       |   ElRobot (7+1 DOF Arm) |
                                       |   Tabletop Manipulation |
                                       +-------------------------+
```

---

## 4. 48-Hour Implementation Plan

### Phase 1: Unified Runtime & Hardware Setup
- Launch **NormaCore Station** on the control machine.
- Establish reliable communication with the 7+1 DOF ElRobot arm.
- Verify camera video streams and test basic motor/gripper endpoints over the Python/Protobuf interface.

### Phase 2: Agent Tool / MCP Integration Layer
Expose clean, high-level cartesian abstractions to Claude/Codex instead of raw joint positions:
- `capture_camera_image()`: Captures and encodes high-resolution workspace frames for VLM inspection.
- `get_arm_state()`: Queries current end-effector position $(x, y, z)$, orientation (roll, pitch, yaw), and gripper status.
- `move_end_effector(x, y, z, roll, pitch, yaw)`: Targets a 3D coordinate in the calibrated tabletop workspace.
- `set_gripper(state)`: Actuates the gripper between open, closed, or compliant grip states.

> **Crucial Rule:** Never allow the LLM to guess 7 DOF joint angles directly. Let the agent reason strictly in 3D cartesian coordinates $(x, y, z)$ and task semantics.

### Phase 3: Deterministic Kinematics & Safety Guardrails
- **Inverse Kinematics (IK):** Solve cartesian targets into valid joint trajectories using a Python IK solver.
- **Bounding Boxes:** Enforce a hard virtual floor (e.g., $z \ge z_{\text{table}} + 1\text{cm}$) and boundary perimeter to prevent table gouging or arm self-collisions.
- **Velocity Clamping:** Smooth transitions and enforce maximum joint velocity to prevent servo burnout.

### Phase 4: Closed-Loop Visual Recovery
- Calibrate camera-to-base transforms using visual reference markers (e.g., ArUco markers or fixed landmarks).
- Implement a post-action visual inspection loop:
  1. Agent predicts object position and executes grasp.
  2. Agent captures a fresh camera frame post-grasp.
  3. If the object was missed, dropped, or moved by a human, the agent detects the anomaly and automatically recalculates recovery moves without failing.

---

## 5. Expected Deliverable & Judging Demo

- **Interactive Tabletop Assistant:** A live demo where judges give plain-English instructions (e.g., *"Pick up the green marker and place it in the pen holder, then sort the blue cubes into the tray"*).
- **Autonomous Recovery (The Winning Edge):** The system must handle real-world disturbances. If a judge moves an object while the robot is moving, the agent inspects the camera, remarks on the change, and successfully re-plans.

---

## 6. Team Roles & Skill Distribution

| Role | Key Focus Areas | Recommended Skills |
| :--- | :--- | :--- |
| **Robotics Kinematics & Control** | Python IK solver, safety boundary limits, camera-to-robot coordinate calibration. | Python, ROS/kinematics, transforms, spatial math. |
| **AI Agent & SDK Integration** | NormaCore Station Python SDK, Claude / Codex API, MCP / function-calling loop, prompts. | LLM/VLM APIs, tool-calling architectures, Python. |
| **Demo Design & Validation** | Designing repeatable tabletop test tasks, edge-case recovery testing, pitch deck & live demo script. | System integration, UX, presentation, testing. |
