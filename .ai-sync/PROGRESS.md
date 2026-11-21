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

## Phase 2: Saturday Morning Hardware Onboarding — COMPLETE
- [x] Connect ElRobot USB serial cable and execute `./scripts/setup_usb_serial.sh`
- [x] Launch NormaCore Station Web console and verify joint zero positions
- [x] First physical hardware move to safe clearance height / live teleoperation
- [ ] Place 4 AprilTag markers at workspace corners and calibrate camera

## Phase 3: Agent Integration & Tabletop Primitives — IN PROGRESS
- [x] Joint-level hardware bridge to the Station SDK written (`src/elrobot_hardware.py`), unit-tested offline (44 tests pass in total).
- [x] Read-only preflight script (`scripts/hardware_preflight.py`); verified against live follower arm `5B61037051` and leader arm `5B61034962`.
- [x] Live master/slave 50Hz teleoperation sync tool implemented and tested (`scripts/teleop_sync.py`, `./cli.sh teleop`).
- [x] Run logging with per-run files and `latest` links (`src/elrobot_log.py`), and `logs/` bundles via `./cli.sh hw bundle`
- [x] Hardware-day checklist and safe commands in `./cli.sh hw` (`scripts/hw_day.py`)
- [ ] Run preflight with the ElRobot powered and USB connected; confirm motors 1–8 and calibration
- [x] Motor identification wizard, torque on/off, overload guard, current probe, waypoints (teach/goto), workspace config (`scripts/hw_day.py`, `src/elrobot_hardware.py`, `src/elrobot_config.py`)
- [ ] Identify motors on the arm (`./cli.sh hw identify`) and confirm directions
- [ ] Probe current per motor and save thresholds (`./cli.sh hw probe-current <m>`)
- [ ] Teach home and clear poses, then test goto both ways
- [ ] Measure the table and set `workspace.measured` to true
- [x] Real MCP server for the live Station (`src/robot_mcp_server.py`, `src/robot_tools.py`): camera, state, waypoints, gripper, nudge, stop. Tested offline and over stdio; not yet run against the arm
- [x] Cameras on the real Station: udev rule, named by USB port, fixed exposure (`./cli.sh cameras`)
- [x] Calibration of follower and leader exported to `calibration/`
- [ ] First MCP session on the real arm: verify gripper direction, teach `clear` + pick/bin waypoints, then ELROBOT_ALLOW_MOTION=1
- [ ] Decide how Cartesian tools (`pick_at`, `place_at`) map to joints: needs URDF-based kinematics verified on the physical arm; Station has no Cartesian API
- [ ] Validate camera stream overlay against real table measurements
- [ ] Execute single-object natural language pick-and-place

- [x] Web console `./cli.sh console` (`src/web_console.py`, `src/web/console.html`): table + gripper cameras on the left, chat with microphone (local faster-whisper STT) on the right. Tested offline; not yet with live camera frames
- [ ] Connect the console chat to Claude: MCP `listen`/`say` tools reading/writing `/api/messages` (plan 3.2/3.4, owner D)

## Phase 4: Closed-Loop Recovery & Stress Testing — PENDING
- [ ] Tune ST3215 gripper motor load thresholds
- [ ] Rehearse judge perturbation test 5+ times consecutively
- [ ] Run multi-object sorting sequence autonomously

## Phase 5: Demo Polishing & Sunday Pitch — PENDING
- [ ] Build split-screen display
- [ ] Rehearse 3-minute winning stage demo
