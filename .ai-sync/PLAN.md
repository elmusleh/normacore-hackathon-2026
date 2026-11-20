# NormaCore Tabletop Manipulation Implementation Plan

## Phase 1: Pre-Event Scaffolding & Offline Simulation — COMPLETE
- [x] Create offline Station simulator (`src/mock_station.py`) simulating ElRobot kinematics, camera stream, table objects, and ST3215 servo load.
- [x] Implement perspective homography calibration and metric grid generator (`src/vision_homography.py`).
- [x] Implement deterministic kinematics safety wrapper with $Z \ge 12\text{mm}$ table floor clamp (`src/kinematics_safety.py`).
- [x] Build Model Context Protocol (MCP) server exposing tools to Claude Code / Codex (`src/mcp_server.py`, `.mcp.json`).
- [x] Build autonomous error recovery test runner simulating judge perturbations (`src/agent_prompts.py`).
- [x] Create comprehensive automated test suite (`tests/test_pipeline.py`).
- [x] Write Linux USB serial setup guide and automation script (`docs/hardware_setup_and_usb_serial.md`, `scripts/setup_usb_serial.sh`).
- [x] Write instant printable/screen AprilTag generator (`scripts/generate_apriltags.py`, `docs/apriltags_printable.html`).

## Phase 2: Saturday Morning Hardware Onboarding (09:00 – 13:00)
- [ ] Connect ElRobot arm over USB and execute `./scripts/setup_usb_serial.sh`.
- [ ] Launch NormaCore Station Web console: verify ST3215 servo communication, home all joints, test gripper.
- [ ] Place 4 AprilTag markers at workspace corners and run calibration to lock in camera-to-table millimeters.
- [ ] First physical hardware move: command end-effector to $(0, 140, 70)$ safely.

## Phase 3: Agent Integration & Tabletop Primitives (13:00 – 18:00)
- [ ] Switch `mcp_server.py` from `MockStation` to live NormaCore Station SDK (`gremlin_py`).
- [ ] Test live `get_calibrated_view()` and verify grid overlay matches real table coordinates.
- [ ] Test physical pick-and-place with single colored cube via Claude Code CLI.

## Phase 4: Closed-Loop Recovery & Stress Testing (18:00 – 23:00)
- [ ] Calibrate ST3215 gripper motor load thresholds for real physical objects.
- [ ] Rehearse judge perturbation: physically slide object mid-run and verify autonomous visual re-planning.
- [ ] Test multi-object sorting sequence (e.g. 3 objects into 2 bins) end-to-end.

## Phase 5: Demo Polishing & Sunday Pitch (09:00 – 15:00)
- [ ] Set up split-screen live presentation (Camera feed + Claude reasoning terminal).
- [ ] Rehearse 3-minute pitch deck and perturbation demonstration with team.
