---
last_agent: antigravity
timestamp: 2026-11-21T11:35:00Z
status: hardware-verified-teleop-active
current_phase: "Phase 3: Agent Integration & Tabletop Primitives (teleop complete)"
current_task: "Master/Slave Teleoperation Sync verified live; cameras probed"
hardware_owner: "steve"
---

## What Was Completed

1. **Hardware Onboarding & Verification:**
   - Identified follower arm bus `5B61037051` and leader/master arm bus `5B61034962`.
   - Confirmed all 8 motors are visible, calibrated, and in clean 0x0 status via live Station.
   - Updated `config/elrobot.json` with bus `5B61037051`.
2. **Master -> Slave Real-time Teleop Sync:**
   - Implemented `scripts/teleop_sync.py` and `./cli.sh teleop`.
   - Tested live at 50Hz: mirrors joints 1-8 from Master (`5B61034962`) to Slave (`5B61037051`) with overload current protection (`threshold=150`).
3. **Cameras & Environment:**
   - Downgraded user numpy to `numpy<2` (1.26.4) to resolve OpenCV ABI compatibility.
   - Probed UVC cameras on `/dev/video2` and `/dev/video4`.
   - Generated 4-corner AprilTags calibration sheet (`docs/NormaCore Hackathon - 4-Corner AprilTags.pdf`).

## Work In Progress

- Tabletop camera homography calibration (place AprilTags in view of `/dev/video2` or `/dev/video4` and run `scripts/calibrate_camera.py`).
- Teaching Cartesian pick/place waypoints for autonomous Claude/Codex agent execution.

## Next Steps

1. Run `./cli.sh teleop` for master-slave teleoperation demonstration.
2. Place AprilTags on tabletop and complete homography calibration.
3. Teach `home`, `pick`, and `place` waypoints using `./cli.sh hw teach <name>`.
4. Test MCP server (`./cli.sh mcp`) connected to live Station runtime.

## Files Modified/Created

- `scripts/teleop_sync.py` (new): 50Hz master/slave mirroring with current overload guard.
- `cli.sh`: added `teleop` command.
- `config/elrobot.json`: locked follower bus serial to `5B61037051`.
- `docs/NormaCore Hackathon - 4-Corner AprilTags.pdf`: printable marker sheet.
- `.ai-sync/HANDOFF.md`, `.ai-sync/PROGRESS.md`, `CHANGELOG.md`, `SUGGESTIONS.md`.

## Build Status

- `python3 -m pytest tests/`: 44 passed.
- `bash -n cli.sh`: OK.
- `py_compile scripts/teleop_sync.py`: OK.

## What Was Completed

Hardware bridge, preflight, run logging and the hardware-day tool are all in place. This pass covered the four "not ready" items from the previous summary:

1. **Motor identification:** `./cli.sh hw identify` nudges each motor 30 steps, returns it, and records the joint and physical direction.
2. **Torque:** `./cli.sh hw torque on` holds the current pose (goal set before torque is enabled). `hw torque off` and `hw stop` release the arm. Moves are refused while torque is off.
3. **Overload guard:** `move_and_watch` watches each motor until it arrives, overloads, faults or times out, and holds the motors still moving. `./cli.sh hw probe-current <m>` measures peak current and offers `2 × peak` as the threshold. The default threshold (100) is from the NormaCore teleop example and is **not measured on this arm**.
4. **Waypoints:** `hw teach <name>` saves all 8 motor positions. `hw goto <name>` shows a per-motor plan, refuses moves over 600 steps unless `--allow-large`, clamps to calibrated range, asks for `MOVE`, and checks arrival.
5. **Workspace:** limits moved to `config/elrobot.json`. `SafetyLimits` and the MCP server read them. Defaults equal the old values. `measured` stays false until the table is measured.

Config is separate from progress: `config/` (committed) holds the joint map, thresholds, workspace and waypoints; `data/hw_day_state.json` holds checklist progress (local).

## Work In Progress

None in code. Nothing has run on the physical arm.

## Next Steps (hardware day, follow docs/elrobot_hardware_bridge.md)

1. Power on, start the Station (`./cli.sh station`), run `./cli.sh hw run 3` (preflight), expect READY.
2. `./cli.sh hw identify`: record all 8 motors. Check whether motor 8 opens or closes the gripper on +30.
3. `./cli.sh hw torque on`, then `./cli.sh hw jog 2 60 --speed 200`, then `./cli.sh hw done 7`.
4. `./cli.sh hw probe-current <m>` for each motor you will use. Gripper first.
5. Move the arm by hand (torque off), `./cli.sh hw teach home` and `hw teach clear`. Torque on, then `hw goto clear` and `hw goto home`.
6. Measure the table (step 11 of the runbook), set `"measured": true`, then `./cli.sh hw workspace`.
7. Commit `config/elrobot.json` and `config/waypoints.json` after hardware day.

## Files Modified/Created

- `src/elrobot_config.py` (new): config, waypoints, state, defaults
- `src/elrobot_hardware.py`: torque checks, `hold`, `torque_on_hold`, `move_and_watch`, `OverloadDetector`, `plan_goto`
- `scripts/hw_day.py`: rewritten. Identify, torque, probe-current, teach, waypoints, goto, workspace
- `src/kinematics_safety.py`, `src/mcp_server.py`: workspace limits read from config
- `config/elrobot.json`, `config/waypoints.json` (new, defaults)
- `tests/test_hw_day.py` (new, fake bridge flow tests), `tests/test_elrobot_hardware.py` (extended)
- `docs/elrobot_hardware_bridge.md`: rewritten as a walkthrough
- `cli.sh`, `.gitignore`, `CHANGELOG.md`, `SUGGESTIONS.md`, `.ai-sync/PROGRESS.md`, `.ai-sync/HANDOFF.md`
- Untracked, not committed: `src/digital_twin.html` (predates this work). `station.yaml`/`station_data/` now gitignored; they still exist from a Station test run.

## Blockers

- No physical arm in this session. Tested offline: 44 tests pass, including flow tests for identify, jog, probe, teach, goto, torque and stop against a fake bridge. Live Station frames have not been exercised.

## Key Decisions

- Joint-level only. Waypoints replace Cartesian moves for the demo. Cartesian IK waits for on-arm verification.
- Motion needs typed `MOVE`. Goto is capped at 600 steps per motor unless `--allow-large`.
- Overload guard holds rather than reverses. Thresholds come from probing, not defaults.
- Config (committed) and progress (local) are separate files.

## Build Status

- `python3 -m pytest tests/`: 44 passed.
- `bash -n cli.sh`, `py_compile` on changed Python: OK.
- Offline CLI paths checked: status, workspace, waypoints, teach/goto with no Station, identify with no TTY, invalid waypoint name.

## Source Facts (verified 2026-11-20)

- URDF joints `rev_motor_01`..`08`. Limits in radians (for example `rev_motor_01` ±1.5509). Gripper is `rev_motor_08` plus two prismatic fingers.
- ElRobot BOM: ST3215 12 V / 30 kg on the follower, 8 motors. Waveshare Serial Bus Servo Driver (A). Reach 430 mm.
- Station: TCP 8888, web 8889. Topic `st3215/inference`. Commands go as `DriverCommand` with `STC_ST3215_COMMAND`.
