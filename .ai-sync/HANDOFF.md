---
last_agent: claude
timestamp: 2026-11-20T21:30:00Z
status: ready-for-hardware
current_phase: "Phase 3: Agent Integration & Tabletop Primitives (partial)"
current_task: "Hardware bridge written and tested offline; first run on the real arm pending"
stop_reason: needs-physical-arm
---

## What Was Completed

Researched ElRobot online and in the official repo (`norma-core/norma-core`, downloaded in `external/norma-core/`). Findings are in `docs/elrobot_hardware_bridge.md`.

1. **Joint-level hardware bridge** `src/elrobot_hardware.py`:
   - `ElRobotHardware` (async) and `ElRobotHardwareSync` (for the MCP server).
   - Reads motor registers, sets torque, moves motors 1–8.
   - Motion needs `enable_motion=True`. Goals are clamped to calibrated range minus a 20-step margin. Uncalibrated or wrap-around motors are refused. Any fault blocks motion. Speed capped at 800, acceleration at 30.
2. **Read-only preflight** `scripts/hardware_preflight.py`. Checks motors 1–8 are visible, calibrated and fault-free. Never moves the arm.
3. **Tests** `tests/test_elrobot_hardware.py`: 14 new tests. Full suite: 19 pass.
4. **Runbook** `docs/elrobot_hardware_bridge.md`: hardware-day steps, a joint-mapping table to fill in, and emergency stop.
5. **Station connection** verified against the real `bin/station` binary. No robot attached, so the preflight reports no frames. This is the expected result.

## Work In Progress

None in code. Nothing has run on the physical arm yet.

## Next Steps

1. **Power and connect** the ElRobot (12 V supply, data-rated USB to the Waveshare driver). Start `./bin/station --web --tcp`.
2. **Run** `python3 scripts/hardware_preflight.py --server localhost --bus auto`. Expect READY with motors 1–8 listed. Fix any MISSING, UNCALIBRATED or FAULT before moving anything.
3. **Fill in the joint-mapping table** in `docs/elrobot_hardware_bridge.md` (motor ID, URDF joint, direction). Use the Station console, jogging one motor at a time.
4. **First motion** with the example in the runbook: one joint, +100 steps, `max_speed=300`, `max_accel=10`.
5. **Cartesian tools** (`pick_at`, `place_at`) still run on the mock. Mapping them to joints needs a verified kinematics model. The Station has no Cartesian API.
6. **Before the demo:** current-overload guard (SUGGESTIONS item 8), table-size reconciliation (item 9).

## Files Modified/Created

- `src/elrobot_hardware.py` (new)
- `scripts/hardware_preflight.py` (new)
- `tests/test_elrobot_hardware.py` (new)
- `docs/elrobot_hardware_bridge.md` (new)
- `CHANGELOG.md`, `SUGGESTIONS.md`, `.ai-sync/PROGRESS.md`, `.ai-sync/HANDOFF.md`
- Station test run left `station.yaml` and `station_data/` in the project root. A delete was denied, so they remain. Remove them if they are not wanted, then add them to `.gitignore` (SUGGESTIONS item 10).
- `src/digital_twin.html` is still untracked. It was not part of this work and was not committed.

## Blockers

- No physical arm available in this session. Motion code is verified only by offline tests and by reading the SDK source.

## Key Decisions

- **Joint-level only.** The Station exposes motor registers, not Cartesian poses. Cartesian control waits for a verified kinematics model.
- **Motion is opt-in and clamped.** Reads never change torque or position. Default motion is slow.
- **SDK path** comes from `NORMACORE_ROOT`, defaulting to `external/norma-core`. The SDK is imported lazily so the offline tests run without the Station.
- **Motor-to-joint mapping is assumed** (IDs 1–8 in URDF order). Unverified until the arm is jogged.
- Calibration comes from the Station, not the URDF.

## Build Status

- `python3 -m pytest tests/`: 19 passed.
- `scripts/hardware_preflight.py` against the real `bin/station` with no robot: exits 1 with a clear message (no bus frames), as expected.
- No physical verification.

## Source Facts (verified 2026-11-20)

- URDF joints `rev_motor_01`..`08`. Limits in radians, for example `rev_motor_01` ±1.5509, `rev_motor_05` -2.62..3.252. Gripper is `rev_motor_08` plus two prismatic fingers.
- ElRobot BOM: ST3215 12 V / 30 kg on the follower, 8 motors. Waveshare Serial Bus Servo Driver (A). Reach 430 mm.
- Station: TCP 8888, web 8889. Topic `st3215/inference`. Commands go as `DriverCommand` with `STC_ST3215_COMMAND`.
