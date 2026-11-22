# CareArm — Assistive Feeding Robot (Team 6)
**2nd Edition Berlin Robotics & AI Hackathon (HackLab × BRISA — November 21–22, 2026)**
**Track:** NormaCore — *"AI-Powered Robot Control"* · **Hardware:** ElRobot 7+1 DOF Arm (`ST3215` Servos) + 3-Camera Vision

> **Submission & Pitch:** [Final Pitch Deck (PPTX)](docs/Assistive_Feeding_Robot_Pitch.pptx) · [Hackathon Submission Sheet](docs/Hackathon_submission_requirements.md) · [Team Plan](docs/FEEDING_ASSISTANT_PLAN.md)

---

## Overview

**CareArm** is a hands-free, voice-controlled assistive feeding robot built on the **NormaCore ElRobot (7+1 DOF)** arm to restore mealtime independence for people with upper-limb mobility impairments.

A diner simply speaks what they want to eat (*"Give me a grape"*, *"Now some chocolate"*) in English or German. The system inspects the table, selects the right recorded trajectory, verifies the grasp with a wrist camera and servo load, pauses at a safe **5–10 cm standoff** in front of the person's face, and waits for a real-time **MediaPipe Mouth-Open confirmation** before handing over the bite.

### Core Engineering Principle: *"Claude Decides, Local Code Acts Fast"*
Most LLM-to-robot prototypes send raw camera images and raw joint angles straight through a cloud model—which is too slow (2–4 s) and unsafe near a human face. We strictly decouple **semantic reasoning** from **real-time perception and deterministic safety**:

- **Semantic Brain (Claude + 15-Tool MCP Server):** Natural-language understanding, visual food inspection (`look`), trajectory selection (`play_sequence`), bounded visual alignment (`align_base`), and closed-loop recovery—protected by **3-layer scope guardrails** (`<1 ms` pre-LLM prompt-injection/off-topic gatekeeper, XML transcript isolation, and whitelisted MCP schemas) with a live **Developer Action Trace**.
- **3-Camera Closed-Loop Vision (~30 FPS):**
  - **Table Camera (Overhead):** Detects bowls and food zones for Claude scene context.
  - **Gripper Camera (Wrist):** Runs a `<5 ms` LAB color-contrast jaw-zone ROI check + ST3215 servo load verification to prevent empty grasps, with bounded `±2%` base nudges.
  - **Person Camera (OBSBOT Meet SE):** Runs MediaPipe Face Landmarker (`landmarks 13, 14, 61, 291`) to compute smoothed Mouth Aspect Ratio (**MAR**) with 1-click per-user calibration, 3-frame debounce, and a **0.6 s face-loss watchdog**.
- **Deterministic Hardware Safety:** Calibrated joint clamps, velocity and per-leg step caps, ST3215 current overload protection, verified 4× torque-off readback retries, a **<0.5 s bypass-LLM Emergency Stop** (voice `"Stop!"` or red button holds pose so the arm never drops), and a physical 12 V power cutoff.

---

## System Architecture

```text
+-----------------------------------------------------------------------------+
|  LAYER 1 · HUMAN INTERFACE — Hands-Free Web Console (http://localhost:8890) |
|  • OpenAI gpt-transcribe (EN/DE) · TTS spoken cues & Web Audio chimes       |
|  • 3 Tabs: Demo Console | Developer Trace (/api/trace) | Guardrails         |
|  • Direct Bypass-LLM Emergency Stop ("Stop!" / Red Button -> hold <0.5 s)   |
+--------------------------------------+--------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------+
|  LAYER 2 · SEMANTIC BRAIN — Claude Agent + 15-Tool MCP Server               |
|  • Layer 1 Guardrail: <1 ms classify_intent() (blocks injections/off-topic) |
|  • Layer 2 Guardrail: <user_voice_transcript> XML delimiter isolation       |
|  • Layer 3 Guardrail: 15 whitelisted MCP tools (src/robot_mcp_server.py)    |
+--------------------------------------+--------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------+
|  LAYER 3 · REAL-TIME LOCAL VISION (~30 FPS, src/feeding_vision.py)          |
|  • Table Cam (bowl & food boxes) · Gripper Cam (<5 ms LAB jaw-zone ROI)     |
|  • OBSBOT Person Cam (MediaPipe MAR mouth-open gate + 0.6 s watchdog)       |
+--------------------------------------+--------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------+
|  LAYER 4 · DETERMINISTIC SAFETY & HARDWARE (NormaCore Station v0.1.0-b10)   |
|  • ElRobot Follower (5B61034962, 12 V) + Leader (5B61037051, 5 V)           |
|  • Calibrated joint clamps · Speed/step caps · Overload guard · 12 V cutoff |
+-----------------------------------------------------------------------------+
```

---

## Verified Results & Benchmarks

| Area | Metric / Benchmark | Verified Result |
| :--- | :--- | :--- |
| **Automated Test Suite** | `.venv/bin/python -m pytest tests/` (offline + fake-arm) | **123 / 123 passing (100%)** |
| **AI Scope Guardrails** | `classify_intent()` pre-LLM prompt-injection & off-topic block | **< 1 ms latency · 0 API calls** |
| **Emergency Stop** | Voice `"Stop!"` or red button (`stop_now()` bypasses Claude) | **< 0.5 s pose-hold halt** |
| **Mouth-Open Safety Gate** | OBSBOT MediaPipe MAR (`Closed ~0.01 → Open ~0.35+`) | **30 FPS · 0.6 s face-loss watchdog** |
| **Gripper Grasp Check** | Wrist jaw-zone LAB contrast ROI + servo load verification | **< 5 ms visual check** |
| **Multi-Food Feeding** | Voice selection (`grapes` / `chocolate`) + 9-waypoint sequences | **Hands-free EN/DE (~1.5 s STT)** |

---

## Quickstart

### 1. Run the Automated Test Suite (No Hardware Required)
```bash
.venv/bin/python -m pytest tests/
```

### 2. Launch the 3-Tab Voice & Vision Web Console
```bash
# Terminal 1: Start NormaCore Station (TCP 8888, Web Viewer 8889)
./cli.sh station

# Terminal 2: Launch Hands-Free Console (http://localhost:8890)
./cli.sh console 8890
```

### 3. Hardware Preflight & Bench Recovery (Read-Only / Safe)
```bash
./cli.sh preflight --bus 5B61034962   # Verify 8/8 ST3215 motors, calibration & fault status
./cli.sh reset                        # Relax leader torque / apply manual camera exposure
./cli.sh hw stop                      # Emergency torque-off (verified with 4x readback)
```

---

## Master CLI Commands (`./cli.sh`)

| Command | Action |
| :--- | :--- |
| `./cli.sh console [port]` | Launch 3-tab Web Console (`Demo Console`, `Developer Trace`, `Guardrails`) at `http://localhost:8890` |
| `./cli.sh start [port]` | Launch Mission Control Web Dashboard (per-user mouth calibration & live feeds) at `http://localhost:8080` |
| `./cli.sh station` | Start NormaCore Station runtime (`./bin/station --web --tcp`) |
| `./cli.sh mcp` | Run the 15-tool `elrobot` MCP server over stdio (`src/robot_mcp_server.py`) |
| `./cli.sh test [filter]` | Run offline pytest suite (123 unit & integration tests) |
| `./cli.sh preflight` | Read-only 8-motor ElRobot readiness check (writes `logs/`) |
| `./cli.sh hw record / play` | Record waypoint trajectories and play sequences with overload & settle guards |
| `./cli.sh hw stop` | Emergency stop on all 8 ST3215 motors |
| `./cli.sh teleop` | 50 Hz Leader (`5B61037051`) → Follower (`5B61034962`) mirroring |
| `./cli.sh cameras` | Apply fixed manual exposure to KD-USB cameras (Station stopped) |
| `./cli.sh reset` | Quick bench recovery (relaxes leader torque / applies camera exposure) |
| `./cli.sh sync` | Safe git sync + pinned NormaCore submodule check |

---

## Team 6 Roster

| Member | Contact |
| :--- | :--- |
| **Jan Schulz** | `jan.schulz@cileria.com` |
| **Jafer Sharfeddin** | `j.sharfeddin@gmail.com` |
| **Mohammad El-Musleh** | `elmusleh.mohammad@gmail.com` |

---

## Repository Structure & Key Docs

```text
├── src/
│   ├── console_agent.py        # Claude Messages API loop, 3-layer guardrails & live Developer Trace
│   ├── web_console.py          # Starlette/Uvicorn server (3-camera streams, STT, TTS, /api/trace, /api/mouth_status)
│   ├── web/console.html        # 3-tab Hands-Free Voice Console UI + live Mouth badge & Dev Log toggle
│   ├── robot_mcp_server.py     # 15-tool stdio MCP server (elrobot)
│   ├── robot_tools.py          # Hardware-safe robot actions, partial sequence playback, align_base, mouth gate
│   ├── sequence_player.py      # Multi-waypoint trajectory runner with settle checks & after_leg hooks
│   ├── feeding_vision.py       # 3-camera vision: MediaPipe FaceLandmarker MAR, table bowl/food, gripper LAB ROI
│   ├── elrobot_hardware.py     # NormaCore Station SDK bridge, joint clamps, overload guard, 4x torque readback
│   ├── elrobot_camera.py       # Cross-platform (Linux/macOS) USB-port camera discovery & decoding
│   ├── speech.py               # OpenAI gpt-transcribe bilingual (EN/DE) STT
│   └── digital_twin_server.py  # Mission Control dashboard & 1-click per-user mouth calibration
├── config/
│   ├── elrobot.json            # Hardware bus serials, camera ports, food map, calibrated thresholds
│   ├── waypoints.json          # Recorded 8-joint feeding poses
│   └── sequences.json          # Named multi-step feeding trajectories (grapes, choc, feed)
├── scripts/
│   ├── generate_pitch_deck.py  # Reproducible 10-slide pitch deck generator
│   ├── hw_day.py               # Hardware-day CLI (identify, teach, goto, record, play, probe-current)
│   ├── hardware_preflight.py   # Read-only 8-motor preflight verification
│   ├── teleop_sync.py          # 50 Hz Leader -> Follower teleoperation sync
│   └── reset_bench.py          # 1-command bench recovery
├── tests/                      # 123 offline unit & integration tests (zero hardware required)
├── docs/
│   ├── Assistive_Feeding_Robot_Pitch.pptx  # Final 10-slide presentation deck with speaker notes
│   ├── Hackathon_submission_requirements.md # Team 6 Tally submission inputs & checklist
│   ├── FEEDING_ASSISTANT_PLAN.md           # System plan, safety rules & milestones
│   ├── GUARDRAILS_AND_TRACE.md             # 3-layer AI guardrails & Developer Trace reference
│   ├── GRIPPER_CAMERA_ROADMAP.md           # Eye-in-hand gripper camera verification & alignment stages
│   ├── FEEDING_FSM_MEDIAPIPE_PLAN.md       # MediaPipe lip tracking & safety FSM design
│   ├── mcp_server.md                       # 15 MCP tools & setup guide
│   └── bench_safety.md                     # Mandatory physical bench safety checklist
└── FINDINGS.md                 # Verified hardware, SDK & calibration observations
```
