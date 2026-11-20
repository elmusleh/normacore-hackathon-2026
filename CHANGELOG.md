# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Official Station & ElRobot SDK Reference Guide `docs/NormaCore_Station_SDK_Reference.md` with release binaries, `station --web --tcp` CLI options, Protobuf topics (`st3215/inference`), and ST3215 register structures.
- Direct link to NormaCore's online 3D URDF interactive viewer `https://normacore.dev/elrobot-urdf/`.

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
