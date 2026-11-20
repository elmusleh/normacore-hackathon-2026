# Progress Tracker

## Phase 1: Pre-Event Scaffolding & Offline Simulation — COMPLETE
- [x] Initialize ai-sync cross-agent synchronization
- [x] Implement offline hardware & Station simulator (`src/mock_station.py`)
- [x] Implement perspective homography calibration and metric grid generator (`src/vision_homography.py`)
- [x] Implement deterministic kinematics safety wrapper & $Z$-floor protection (`src/kinematics_safety.py`)
- [x] Build Model Context Protocol (MCP) server & `.mcp.json` (`src/mcp_server.py`)
- [x] Build autonomous error recovery test runner simulating judge perturbations (`src/agent_prompts.py`)
- [x] Create comprehensive automated test suite (`tests/test_pipeline.py`) - 5/5 passing
- [x] Create Linux USB serial setup guide and installer script (`docs/hardware_setup_and_usb_serial.md`, `scripts/setup_usb_serial.sh`)
- [x] Create instant AprilTag calibration sheet generator (`scripts/generate_apriltags.py`, `docs/apriltags_printable.html`)
- [x] Structure repository (`docs/`, `src/`, `scripts/`, `tests/`, `archive/`)
- [x] Create team onboarding `README.md`, `GUIDELINES.md`, `PREFERENCES.md`

## Phase 2: Saturday Morning Hardware Onboarding — PENDING
- [ ] Connect ElRobot USB serial cable and execute `./scripts/setup_usb_serial.sh`
- [ ] Launch NormaCore Station Web console and verify joint zero positions
- [ ] Place 4 AprilTag markers at workspace corners and calibrate camera
- [ ] First physical hardware move to safe clearance height

## Phase 3: Agent Integration & Tabletop Primitives — PARTIAL
- [x] Joint-level hardware bridge to the Station SDK written (`src/elrobot_hardware.py`), unit-tested offline (44 tests pass in total). Not yet run against a real arm.
- [x] Read-only preflight script (`scripts/hardware_preflight.py`); connection path verified against the real `bin/station` binary (no robot attached, so no frames).
- [x] Run logging with per-run files and `latest` links (`src/elrobot_log.py`), and `logs/` bundles via `./cli.sh hw bundle`
- [x] Hardware-day checklist and safe commands in `./cli.sh hw` (`scripts/hw_day.py`)
- [ ] Run preflight with the ElRobot powered and USB connected; confirm motors 1–8 and calibration
- [x] Motor identification wizard, torque on/off, overload guard, current probe, waypoints (teach/goto), workspace config (`scripts/hw_day.py`, `src/elrobot_hardware.py`, `src/elrobot_config.py`)
- [ ] Identify motors on the arm (`./cli.sh hw identify`) and confirm directions
- [ ] Probe current per motor and save thresholds (`./cli.sh hw probe-current <m>`)
- [ ] Teach home and clear poses, then test goto both ways
- [ ] Measure the table and set `workspace.measured` to true
- [ ] Connect MCP server to live NormaCore Station runtime (`gremlin_py`)
- [ ] Decide how Cartesian tools (`pick_at`, `place_at`) map to joints: needs URDF-based kinematics verified on the physical arm; Station has no Cartesian API
- [ ] Validate camera stream overlay against real table measurements
- [ ] Execute single-object natural language pick-and-place

## Phase 4: Closed-Loop Recovery & Stress Testing — PENDING
- [ ] Tune ST3215 gripper motor load thresholds
- [ ] Rehearse judge perturbation test 5+ times consecutively
- [ ] Run multi-object sorting sequence autonomously

## Phase 5: Demo Polishing & Sunday Pitch — PENDING
- [ ] Build split-screen display
- [ ] Rehearse 3-minute winning stage demo
