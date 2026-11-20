# ElRobot Hardware Bridge — Runbook

Purpose: bring the ElRobot up on the real arm through the NormaCore Station, safely, on Saturday.

Sources checked (2026-11-20):
- Official repo `norma-core/norma-core` (pushed 2026-11-10), downloaded to `external/norma-core/`.
- ElRobot README: `external/norma-core/hardware/elrobot/README.md`.
- URDF joint limits: `external/norma-core/hardware/elrobot/simulation/elrobot_follower.urdf`.
- Teleop example (reference for register map and safety margins): `external/norma-core/software/station/examples/st3215-remote-teleop-py/`.

## What is ready

| Piece | File | State |
| :--- | :--- | :--- |
| Joint-level bridge (read, torque, move) | `src/elrobot_hardware.py` | Written, 19 offline tests pass. Not yet run on the arm. |
| Read-only preflight | `scripts/hardware_preflight.py` | Connection path checked against the real `bin/station` (no robot attached). |
| Safety helper tests | `tests/test_elrobot_hardware.py` | Pass. No hardware needed. |

## What is NOT ready

- **Cartesian moves.** The Station has no Cartesian API. It only speaks motor registers (goal position, speed, acceleration, torque). `pick_at` and `place_at` still run on the mock. Mapping them to joints needs a verified kinematics model (see Step 3).
- **Joint mapping is assumed.** The URDF names `rev_motor_01` to `rev_motor_08`. The code assumes these map to ST3215 IDs 1 to 8, in order. Not yet checked on the arm.
- **Calibration is taken from the Station.** Motion limits come from each motor's calibrated range, as stored by the Station. They are not taken from the URDF.
- **Current-overload guard is missing.** See SUGGESTIONS.md item 8.

## Hardware-day steps

1. **Power and cable.** 12 V / 4 A supply on the follower arm. USB data cable to the Waveshare bus servo driver (A). Data-rated cable only.
2. **Start the Station.** From the project root: `./bin/station --web --tcp`. Web console at `http://localhost:8889`. TCP API on port 8888.
3. **Preflight (read only).**
   ```bash
   python3 scripts/hardware_preflight.py --server localhost --bus auto
   ```
   Expect `READY` with motors 1–8 listed. If anything is `MISSING`, `UNCALIBRATED` or `FAULT`, fix that first. Do not move the arm.
4. **Calibrate in the Station console** if any motor is uncalibrated. Move each joint through its full travel when prompted.
5. **Map joints (SUGGESTIONS item 7).** In the console, jog one motor at a time at low speed. Record motor ID, joint name, and direction in the table below.

   | Motor ID | URDF joint | Positive direction | Notes |
   | :--- | :--- | :--- | :--- |
   | 1 | rev_motor_01 | | |
   | 2 | rev_motor_02 | | |
   | 3 | rev_motor_03 | | |
   | 4 | rev_motor_04 | | |
   | 5 | rev_motor_05 | | |
   | 6 | rev_motor_06 | | |
   | 7 | rev_motor_07 | | |
   | 8 | rev_motor_08 (gripper) | | |

6. **First motion.** Use the Python bridge with `enable_motion=True`. Move one joint a small amount, away from the table, with low `max_speed`. Example:
   ```python
   import asyncio
   from src.elrobot_hardware import ElRobotHardware

   async def main():
       hw = ElRobotHardware(server="localhost", bus="auto")
       await hw.connect()
       readings = await hw.read()
       start = readings[2].present                     # motor 2, a shoulder joint
       result = await hw.move_motors(
           {2: start + 100},                           # about 9 degrees on a 4096-step encoder
           enable_motion=True, max_speed=300, max_accel=10,
       )
       print(result)
       await hw.close()

   asyncio.run(main())
   ```
   Keep one hand near the power switch. Check `result[2]["clamped"]` before trusting the move.
7. **Safe clearance height.** Once single joints behave, move to the clearance pose from `PLAN.md` (end effector at (0, 140, 70) mm). This needs the Cartesian mapping from step 5 first, so do it through joint targets until then.

## Safety rules in the code

- Motion needs `enable_motion=True`. Reads never move the arm.
- Goals are clamped to `[range_min + margin, range_max - margin]` (default margin 20 steps). The result reports `clamped`.
- Uncalibrated or wrap-around motors are refused. Recalibrate in the Station console.
- Any motor status other than under-voltage blocks the move.
- Defaults are slow on purpose: `max_speed=800`, `max_accel=30`. Raise only after watching a test move.

## Emergency stop

Disable torque on all motors so the arm goes limp:
```python
await hw.set_torque([1, 2, 3, 4, 5, 6, 7, 8], enable=False)
```
Or close the Station process. Power is the last resort.

## Known gaps to close before the demo

See `SUGGESTIONS.md` items 7–9 and `.ai-sync/PROGRESS.md` Phase 3.
