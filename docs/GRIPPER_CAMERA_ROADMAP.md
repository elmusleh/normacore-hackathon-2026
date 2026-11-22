# Gripper (Eye-in-Hand) Camera Roadmap & Stage 0–2 Execution Plan

This document defines the 5-stage evolution of the ElRobot **gripper (eye-in-hand) camera** — from a zero-risk hackathon demo baseline (**Stage 0**) up to a clinical-grade assistive feeding architecture (**Stage 4**) — along with the concrete implementation plan for **Stages 0–2**.

> **Related spec:** See [prompts/05-nudging-before-gripping.md](../prompts/05-nudging-before-gripping.md) for the original team specification on pre-grasp base nudging and post-grasp verification.

---

## Part 1: 5-Stage Engineering Roadmap

| Stage | Name | Core Capability | Hardware Calibration Needed | Target Horizon |
|---|---|---|---|---|
| **Stage 0** | **Demo-Ready Baseline** | Center crosshair + jaw-zone ROI overlay on `gripper` feed in `http://localhost:8890` + `Developer Trace` logging | None (zero arm motion changes) | Today (15 min) |
| **Stage 1** | **Closed-Loop Grasp Verification** | Split `play_sequence` (`start_at` / `stop_after`) + dual-signal check (`holding_object` + `look("gripper")`) so an empty gripper never goes to the mouth | Verified `gripper.open_at` + true open-jaw `approach` pose | Bench session (30–45 min) |
| **Stage 2** | **Bounded Pre-Grasp Alignment** | Bounded `align_base(delta_percent)` MCP tool (`±2%`/step, `±6%` max) + optional fast jaw-ROI offset helper (`{in_jaws, offset_x_pct}`) | Base motor in `joint_map` + camera-to-motor sign | Bench session (1–2 h) |
| **Stage 3** | **Deterministic Eye-in-Hand Visual Servoing** | Separate 1 Hz LLM intent planning from 20–30 Hz local IBVS or LeRobot ACT/Diffusion Policy + full hand-eye calibration + food-aware primitives | Full hand-eye calibration (AprilTag + URDF) | Post-hackathon prototype |
| **Stage 4** | **Clinical / Production Assistive Robotics** | Wrist RGB-D/ToF depth, compliant admittance control, independent hardware safety watchdog, on-device TensorRT perception, bite-transfer verification, redacted audit logs | RGB-D wrist sensor + safety relay | Production (ISO 13482) |

### Reference Research & Open-Source Projects
- **`personalrobotics/ada_feeding`** (UW Personal Robotics Lab): Open-source ROS 2 assistive feeding stack separating *bite acquisition* (eye-in-hand wrist cam) from *bite transfer* (person/mouth cam).
- **Robot-Assisted Feeding Datasets (`robotfeeding.github.io`) & SPANet / AVIL**: Multimodal wrist RGB-D + force/torque datasets validating visual + proprioceptive grasp verification.
- **Voice-Driven Assistive Feeding Arm (SO-101 + Wrist Webcam + MediaPipe + CLIP)**: Low-cost 5-DOF reference architecture closely matching ElRobot's hardware class.
- **`huggingface/lerobot` & `TheRobotStudio/SO-ARM100`**: Feetech ST3215 drivers, 3D-printable wrist camera mounts, and ACT/Diffusion Policy training pipelines.
- **`brukg/SO-100-arm` & `hsp-iit/visual-servoing`**: ROS 2 + MoveIt2 + Image-Based Visual Servoing (IBVS) controllers for Stage 3+.

---

## Part 2: Concrete Execution Plan (Stages 0 → 2)

> **Safety Rule (Non-Negotiable):** Offline code and unit tests can be built and verified with `FakeArm` at any time. **Never guess physical hardware facts** (gripper direction, base motor ID, camera sign, or waypoints) and **never move the real arm** without the hardware owner present, typed confirmation, and hand on the 12 V switch.

### Stage 0 — Demo-Ready Gripper Overlay & Trace (Offline, Safe Now)
**Goal:** Give judges, Claude, and developers a crisp alignment reference on the `gripper` camera feed without changing arm motion.

1. **Gripper Crosshair & Jaw-Zone Overlay (`src/web_console.py`):**
   - Extend `_annotate_bgr(bgr, role)` to support `role == "gripper"`:
     - Draw a subtle vertical center guide line (`x = W // 2`) and a centered dashed/thin jaw-zone ROI rectangle in the lower-middle frame (`GRIPPER_ROI`).
     - Label `CENTER / JAW ZONE` cleanly so both Claude (`look("gripper")`) and developers in `http://localhost:8890` can instantly judge left/center/right alignment.
   - Apply `_annotate_jpeg(jpeg, name)` for `name in ("person", "table", "gripper")` in `GET /api/frame/{camera}`.
2. **Verification:**
   - Offline unit tests (`tests/test_web_console.py` + `tests/test_pipeline.py`) pass with zero regressions.
   - Live check on `http://localhost:8890` when `./cli.sh station` is running confirms `gripper` feed shows the crosshair cleanly.

---

### Stage 1 — Split Sequences & Dual-Signal Grasp Verification
**Goal:** Guarantee the robot never carries an empty gripper to the person's mouth.

#### Step 1A: Offline Code & Tests (Can be built before bench session)
1. **Partial Sequence Playback (`src/robot_tools.py`, `src/robot_mcp_server.py`):**
   - Extend `play_sequence(name, start_at: Optional[str] = None, stop_after: Optional[str] = None)`:
     - Validate that `start_at` and `stop_after` (when given) exist in `seqs[name]` and `start_index <= stop_index`.
     - Slice the waypoint list before calling `sequence_player.run_legs(...)`.
     - Keep default behavior (`start_at=None, stop_after=None`) 100% backward-compatible with existing sequences and `./cli.sh hw play`.
2. **Optional `grasp` Config Block (`config/elrobot.json`, `list_sequences()`):**
   - Support an optional per-food `grasp` spec:
     ```json
     "grapes": {
       "sequence": "grapes",
       "grasp": { "approach": "grape_open", "close_percent": 30, "continue_at": "feed_1" },
       "note": "picks one grape from the bowl and brings it to the person's mouth, then returns"
     }
     ```
   - `list_sequences()` validates that `approach` appears before `continue_at` in the sequence and exposes `grasp` to Claude. Foods without `grasp` continue running in one shot.
3. **Agent Prompt Update (`src/console_agent.py`, `src/robot_mcp_server.py`):**
   - For foods with `grasp`: run `play_sequence(name, stop_after=approach)` → `set_gripper(close_percent)` → `look("gripper")`.
   - Continue `play_sequence(name, start_at=continue_at)` **only** if `set_gripper` reports `holding_object` **and** `look("gripper")` visually confirms food in the jaws.
   - On empty grasp: `set_gripper(100)` → safe pose (`clear`) → inform the user → allow at most **1 retry**.
4. **Offline Tests (`tests/test_robot_mcp.py`, `tests/test_console_agent.py`):**
   - Test `start_at` / `stop_after` slicing, invalid step names, reversed order, and `list_sequences()` `grasp` validation.
   - Test empty-grasp abort flow with `FakeClaude` + `FakeArm`.

#### Step 1B: Physical Bench Calibration (Hardware Owner Required)
1. Run `./cli.sh hw identify 8` to confirm `gripper.open_at` and set `gripper.verified: true` in `config/elrobot.json`.
2. Re-teach a true open-jaw `grape_open` pose (currently identical to `grape_close` in `config/waypoints.json`).
3. Measure `set_gripper(30)` closing on empty air vs closing on a real grape and record the observed current/stall behavior in `FINDINGS.md`.

---

### Stage 2 — Bounded Pre-Grasp Alignment (`align_base` + Jaw-ROI Telemetry)
**Goal:** Correct ±1–2 cm food offset automatically before closing the jaws.

#### Step 2A: Offline Code & Tests
1. **Bounded MCP Tool `align_base(delta_percent: float)` (`src/robot_tools.py`, `src/robot_mcp_server.py`):**
   - Reads `grasp_alignment` config from `config/elrobot.json`:
     - `motor`: base rotation motor ID (from `joint_map`)
     - `max_step_percent`: `2.0`
     - `max_total_percent`: `6.0`
     - `camera_sign`: `+1` or `-1` (measured on bench; documented in tool response so Claude knows which sign moves food left/right)
   - Enforces hard safety invariants in code:
     - Refuses if `grasp_alignment.motor` is unconfigured.
     - Refuses if the arm is not within `AT_WAYPOINT_TOLERANCE` of the last `approach` pose.
     - Clamps/refuses `|delta_percent| > max_step_percent` and `|cumulative_delta + delta_percent| > max_total_percent`.
     - Resets `cumulative_delta = 0.0` at the start of every `play_sequence(..., stop_after=approach)`.
     - Respects `ELROBOT_ALLOW_MOTION` (`dry_run` when `0`) and `stop_now()`.
2. **Optional Lightweight Jaw-ROI Helper (`src/feeding_vision.py`):**
   - Add `analyze_gripper_roi(bgr)` (<5 ms OpenCV LAB chroma/contrast check inside the jaw-zone box) returning `{"in_jaws": bool, "offset_x_pct": float, "coverage": float}` for deterministic logging in **Developer Trace**.
3. **Agent Alignment Loop (`src/console_agent.py`):**
   - At `approach`: `look("gripper")` → if off-center, call `align_base(...)` → `look("gripper")` (max 3 corrections).
   - Never call `grape_close` after nudging (that would undo the base correction); close with `set_gripper(close_percent)`, verify grasp, then continue `play_sequence(name, start_at=continue_at)`.
4. **Offline Tests (`tests/test_robot_mcp.py`, `tests/test_pipeline.py`):**
   - Test `align_base`: rejects unconfigured motor, rejects away from `approach`, enforces per-step (`±2%`) and cumulative (`±6%`) bounds, resets on new sequence, honors `dry_run`.
   - Test `analyze_gripper_roi` on synthetic empty vs centered vs off-center frames.

#### Step 2B: Physical Bench Verification (Hardware Owner Required)
1. Run `./cli.sh hw identify 1` (confirm base motor ID) and record in `config/elrobot.json` under `joint_map` and `grasp_alignment`.
2. At `grape_open`, run one `+2%` base nudge while viewing `gripper` camera to record `camera_sign` in `config/elrobot.json`.
3. Run the 4 bench acceptance tests (hand on 12 V switch):
   - Grape centered → grasps with 0 nudges.
   - Grape shifted 1 cm left → aligns and grasps.
   - Grape shifted 1 cm right → aligns and grasps.
   - Grape removed → detects empty grasp and **does not** move toward the mouth.
