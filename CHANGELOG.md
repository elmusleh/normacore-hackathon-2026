# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- `AGENTS.md`: every finished change is committed before reporting back (explicit paths, CHANGELOG entry, Conventional Commits). Added a team workflow: feature branches, pull requests, single hardware owner, calibration commits, and shared handoffs.

### Added
- Master CLI runner `cli.sh` providing commands for `test`, `demo`, `digital-twin`, `station`, `setup-serial`, `apriltags`, `view-camera`, `mcp`, and `urdf`.
- Interactive 3D WebGL Digital Twin (`src/digital_twin.html` and `src/digital_twin_server.py`) with Three.js tabletop visualization, live camera feeds, kinematics telemetry, and perturbation triggers.
- Unit test for Digital Twin assets in `tests/test_pipeline.py`.
- Downloaded and verified pre-built Station binary `bin/station` (v0.1.0-beta.10 Linux x86_64).
- Unpacked official source tree and ElRobot hardware manuals into `external/norma-core/`.
- NormaCore GitHub Repositories & Tooling Guide `docs/NormaCore_Repositories_and_Tooling.md`.
- Official Station & ElRobot SDK Reference Guide `docs/NormaCore_Station_SDK_Reference.md` with release binaries, `station --web --tcp` CLI options, Protobuf topics (`st3215/inference`), and ST3215 register structures.
- Direct link to NormaCore's online 3D URDF interactive viewer `https://normacore.dev/elrobot-urdf/`.

- Real-hardware joint-level bridge `src/elrobot_hardware.py` for the ST3215 bus via the NormaCore Station (`ElRobotHardware` async client and `ElRobotHardwareSync` facade). Reads motor registers, sets torque, and moves motors 1–8. Motion is refused without `enable_motion=True`, goals are clamped to calibrated range minus a margin, wrap-around or uncalibrated motors are refused, and any motor fault blocks motion.
- Read-only hardware preflight `scripts/hardware_preflight.py`: confirms all 8 ElRobot motors are visible, calibrated and fault-free. It never moves the arm or changes torque.
- Unit tests `tests/test_elrobot_hardware.py` (14 tests) for the safety helpers: sign-bit decoding, goal clamping, calibration refusal, fault detection, and motion-enable gating. No hardware needed.
- Run logging `src/elrobot_log.py`: each run writes a full DEBUG log to `logs/<tool>-<timestamp>.log` and updates `logs/<tool>-latest.log`. Each log starts with a header (git commit, Python, platform, arguments, SDK path). Uncaught exceptions are written with tracebacks. The console stays short.
- Hardware-day tool `scripts/hw_day.py`, exposed as `./cli.sh hw ...`: a persistent checklist (`status`, `next`, `run <n>`, `done <n>`), joint map (`map`), live table (`motors`), confirmed single-motor move (`jog`, requires typing `MOVE`, max ±200 steps), `stop` (torque off, always available), `logs`, `bundle` (packs logs, state and config for sharing), and `reset`.
- `./cli.sh preflight` (read-only readiness check) and `./cli.sh logs [-f]` (newest run log).
- Runbook `docs/elrobot_hardware_bridge.md` now covers the commands, a common-failures table, and a recommended order for what is not ready yet.
- Config and state are separate. `config/elrobot.json` (joint map, current thresholds, workspace limits) and `config/waypoints.json` are committed. Checklist progress moved to `data/hw_day_state.json` (gitignored), so clearing progress never deletes calibration data.
- Guided motor identification `./cli.sh hw identify`: nudges each motor 30 steps, returns it, and records the joint and physical direction.
- Torque commands `./cli.sh hw torque on|off`. Torque on holds the current pose (goal set before torque is enabled, so there is no jump). Moves are refused while torque is off, with a clear message.
- Overload guard in `move_and_watch`: watches each motor until it arrives, overloads, faults or times out. On overload, fault or timeout it holds the motors still moving. `OverloadDetector` is pure and unit-tested.
- Current probe `./cli.sh hw probe-current <m>`: small move with the guard off. Reports peak current out and back, and offers to save `2 x peak` as the threshold.
- Named waypoints: `./cli.sh hw teach <name>`, `hw waypoints`, `hw goto <name>`. Goto shows a per-motor plan, clamps to calibrated range, refuses moves over 600 steps per motor unless `--allow-large`, and checks arrival afterwards.
- Workspace limits moved to `config/elrobot.json` (`workspace`). `SafetyLimits` and the MCP server read them. Defaults equal the previous hardcoded values. `./cli.sh hw workspace` shows whether they were measured.
- `.gitignore`: `data/`, `station.yaml`, `station_data/`.
- Tests: `tests/test_hw_day.py` runs the identify, jog, probe, teach, goto, torque and stop flows against a fake bridge and in-memory config. 44 tests pass in total.
- Runbook rewritten as a step-by-step walkthrough for each item that was not ready.

### Changed
- Expanded `.gitignore` with comprehensive rules for Python bytecode, virtualenvs, robotics runtime logs, secrets, testing caches, and IDE artifacts.

## [0.2.0] - 2026-11-20

### Added
- Comprehensive team onboarding `README.md` with 5-minute quickstart, architecture diagram, 4-person role split, and hardware instructions.
- Model Context Protocol configuration `.mcp.json` for automatic tool discovery in Claude Code and Cursor.
- Offline simulation engine `src/mock_station.py` simulating Station runtime, ElRobot kinematics, ST3215 servo loads, table objects, and camera feed.
- Perspective homography and metric grid generator `src/vision_homography.py` mapping camera pixels to tabletop millimeters.
- Deterministic Cartesian safety guardrails `src/kinematics_safety.py` enforcing $Z \ge 12\text{mm}$ table floor clamp and workspace boundaries.
- Standard MCP tool server `src/mcp_server.py` exposing `get_calibrated_view`, `pick_at`, `place_at`, `verify_grasp`, `reset_home`.
- Autonomous error recovery orchestrator `src/agent_prompts.py` proving closed-loop re-planning after a simulated judge perturbation.
- Automated test suite `tests/test_pipeline.py` (5/5 unit and integration tests passing).
- Linux USB serial hardware guide `docs/hardware_setup_and_usb_serial.md` and one-click setup script `scripts/setup_usb_serial.sh`.
- AprilTag 36h11 generator `scripts/generate_apriltags.py` generating printable and screen-displayable calibration sheets `docs/apriltags_printable.html`.
- Standard project dependencies file `requirements.txt`.
- Project guidelines `GUIDELINES.md` and preferences `PREFERENCES.md`.
- Implementation plan `.ai-sync/PLAN.md`, progress tracker `.ai-sync/PROGRESS.md`, and handoff `.ai-sync/HANDOFF.md`.

### Changed
- Reorganized documentation files into `docs/` (`NormaCore_Winning_Plan.md`, `NormaCore_Challenge_Guide.md`, `Hackathon_Event_Logistics.md`).
- Restructured workspace into standardized directories (`docs/`, `scripts/`, `src/`, `tests/`, `archive/`).
- Updated `SUGGESTIONS.md` based on user feedback.

## [0.1.0] - 2026-11-20

### Added
- Initial project scaffold with `.ai-sync/`, `AGENTS.md`, `CHANGELOG.md`, `GUIDELINES.md`, `PREFERENCES.md`, `SUGGESTIONS.md`, `README.md`.
