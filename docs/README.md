# CareArm Documentation Index

Welcome to the documentation for **CareArm (Team 6)** — our voice-controlled assistive feeding robot built on the NormaCore ElRobot 7+1 DOF arm for the **2nd Edition Berlin Robotics & AI Hackathon (HackLab × BRISA)**.

---

## Demo & Presentation
- [Demo video (YouTube)](https://youtu.be/h6ilZ18guAE)
- [pitch/CareArm_Presentation.pdf](pitch/CareArm_Presentation.pdf) — final 9-slide presentation shown at the hackathon

## Architecture Diagrams & Illustrations (`docs/diagrams/`, `docs/assets/`)
- **System Overview (4-Layer Architecture):** [PNG](diagrams/carearm_overview.png) · [PDF](diagrams/carearm_overview.pdf) · [PlantUML](diagrams/carearm_overview.puml)
- **End-to-End Safe Feeding & E-Stop Flow:** [PNG](diagrams/carearm_feeding_sequence.png) · [PDF](diagrams/carearm_feeding_sequence.pdf) · [PlantUML](diagrams/carearm_feeding_sequence.puml)
- **Editorial Use-Case Storyboard:** [`docs/assets/scene_01_need.png`](assets/scene_01_need.png) through [`scene_06_carehome.png`](assets/scene_06_carehome.png)

## Engineering, Safety & Calibration Guides (`docs/`)
- [FEEDING_ASSISTANT_PLAN.md](FEEDING_ASSISTANT_PLAN.md) — Core design (*"Claude decides, local code acts fast"*), safety rules & milestones
- [GUARDRAILS_AND_TRACE.md](GUARDRAILS_AND_TRACE.md) — 3-layer AI scope guardrails (`<1 ms` pre-LLM gatekeeper) & live Developer Action Trace
- [FEEDING_FSM_MEDIAPIPE_PLAN.md](FEEDING_FSM_MEDIAPIPE_PLAN.md) — OBSBOT MediaPipe lip-MAR mouth-open gate & deterministic safety FSM
- [GRIPPER_CAMERA_ROADMAP.md](GRIPPER_CAMERA_ROADMAP.md) — Wrist-camera jaw-zone grasp verification & bounded `align_base` nudging
- [tcp_calibration.md](tcp_calibration.md) — AprilTag table frame & URDF Inverse Kinematics calibration (`scripts/calib.py`)
- [feeding_skills.md](feeding_skills.md) — Modular feeding skills (`hover-above-object`, `grip-object`, `drop-in-bowl`)
- [mcp_server.md](mcp_server.md) — 15-tool `elrobot` MCP server & Web Console setup
- [elrobot_hardware_bridge.md](elrobot_hardware_bridge.md) — Hardware-day CLI walkthrough (`./cli.sh hw`)
- [bench_safety.md](bench_safety.md) — Mandatory physical bench safety checklist
- [team_setup.md](team_setup.md) & [hardware_setup_and_usb_serial.md](hardware_setup_and_usb_serial.md) — Machine & USB serial setup

## Historical Day-1 Drafts (`docs/archive/`)
- Earlier hackathon planning & event reference docs preserved in [`docs/archive/`](archive/).
- Draft pitch decks, story-film script and submission checklist (not the final versions) in [`docs/archive/pitch-drafts/`](archive/pitch-drafts/).
