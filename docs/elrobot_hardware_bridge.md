# ElRobot Hardware Bridge — Runbook

Purpose: bring the ElRobot up on the real arm through the NormaCore Station, safely.

Sources checked (2026-11-20):
- Official repo `norma-core/norma-core` (pushed 2026-11-10), in `external/norma-core/`.
- ElRobot README: `external/norma-core/hardware/elrobot/README.md`.
- URDF joint limits: `external/norma-core/hardware/elrobot/simulation/elrobot_follower.urdf`.
- Teleop example (register map, safety margins): `external/norma-core/software/station/examples/st3215-remote-teleop-py/`.

## Quick commands

All hardware-day work goes through `./cli.sh`. Progress is saved in `logs/hw_day_state.json`, so you can stop and resume.

| Command | What it does | Moves the arm? |
| :--- | :--- | :--- |
| `./cli.sh hw` | Checklist, next step, joint map | No |
| `./cli.sh hw next` | Run or show the next open step | No. Manual steps only ask y/N. Motion happens only through `jog` |
| `./cli.sh hw run <n>` | Run step n. Auto steps run a command; manual steps ask y/N | No |
| `./cli.sh hw done <n> [--undo]` | Mark a manual step done or open again | No |
| `./cli.sh hw map <m> <joint> <dir> [note]` | Record which joint motor m drives | No |
| `./cli.sh hw motors` | Live table of motors 1–8 | No |
| `./cli.sh hw jog <m> <steps> [--speed N]` | Move one motor. Max ±200 steps. You type `MOVE` to confirm | **Yes** |
| `./cli.sh hw stop` | Torque OFF on all motors | Releases the arm |
| `./cli.sh preflight` | Read-only readiness check | No |
| `./cli.sh logs [-f]` | Newest run log (`-f` follows it live) | No |
| `./cli.sh hw logs` | Last lines of the latest hardware log | No |
| `./cli.sh hw bundle` | Pack logs, state and `station.yaml` for debugging | No |
| `./cli.sh hw reset --yes` | Clear progress and joint map | No |

Add `--debug` to any `hw` command to see DEBUG output on the console. The log file always has DEBUG.

## Logs and debugging

- Each run writes `logs/<tool>-<timestamp>.log` with full DEBUG detail, and `logs/<tool>-latest.log` points at it.
- Every log starts with a header: git commit, Python version, platform, arguments, SDK path.
- The file records every move request, each clamp, each register write (hex), and full tracebacks.
- The console shows INFO for anything that talks to the arm, and one short line on failure.
- If something fails, run `./cli.sh logs`. Then, if you need help, run `./cli.sh hw bundle` and share the file it prints. Check the bundle first: it contains logs and `station.yaml`.

### Common failures and what they mean

| Console message | Likely cause | Fix |
| :--- | :--- | :--- |
| `cannot use the Station at localhost` | Station not running, or wrong port | Start `./cli.sh station` in another terminal |
| `no st3215/inference frame ... Usually the Station is not running, no bus is connected...` | Station is up but sees no bus | Check the USB cable and the driver board's power |
| `--bus auto needs exactly one bus` | More than one bus on the station | Set `ELROBOT_BUS=<serial>` |
| `motor N: goal clamped` (warning) | Target was outside the safe range | Expected near the calibrated ends. Repeated clamps mean the calibration or target is wrong |
| `motor N: calibration invalid` | Motor not calibrated, or its range wraps past zero | Calibrate in the Station console |
| `motor N reports fault status 0x..` | Servo error, e.g. overheating or overload | Stop, let it cool, check the cable. Do not force it |
| `SDK import failed` | `external/norma-core` missing or `target/gen_python` not generated | Set `NORMACORE_ROOT`, or re-check the download |

## Hardware-day steps

The checklist is built into the tool. Run `./cli.sh hw` at any time.

1. **Power and cable.** 12 V / 4 A supply on the follower arm. Data-rated USB cable to the Waveshare bus servo driver (A). Keep one hand near the power switch.
2. **Start the Station.** In a separate terminal: `./cli.sh station`. Web console at `http://localhost:8889`.
3. **Preflight.** `./cli.sh hw run 3` (or `./cli.sh preflight`). Expect READY with motors 1–8 listed. Fix any MISSING, UNCALIBRATED or FAULT first. Moves nothing.
4. **Calibrate if needed.** Only when preflight showed UNCALIBRATED. Move each joint through its full travel in the Station console, then re-run step 3.
5. **Map motors to joints.** Jog each motor at low speed in the Station console, then record it:
   `./cli.sh hw map 2 rev_motor_02 "+" "shoulder lift"`
   Step 5 passes when all 8 motors are mapped. Fill in the table below as you go.

   | Motor | URDF joint | Positive direction | Notes |
   | :--- | :--- | :--- | :--- |
   | 1 | rev_motor_01 | | |
   | 2 | rev_motor_02 | | |
   | 3 | rev_motor_03 | | |
   | 4 | rev_motor_04 | | |
   | 5 | rev_motor_05 | | |
   | 6 | rev_motor_06 | | |
   | 7 | rev_motor_07 | | |
   | 8 | rev_motor_08 (gripper) | | |

6. **First small move.** `./cli.sh hw jog 2 100 --speed 300`. Check the printed target, type `MOVE`, then watch the joint. Mark step 6 done with `./cli.sh hw done 6`.
7. **Clearance pose.** Move to a safe height above the table using joint targets. Cartesian moves are not ready (see below).

## Safety rules in the code

- Motion needs explicit enabling. `jog` asks you to type `MOVE`. Reads never move the arm.
- Goals are clamped to `[range_min + 20, range_max - 20]` steps. Clamps are logged as warnings.
- Uncalibrated or wrap-around motors are refused.
- Any motor status other than under-voltage blocks the move.
- Jog is limited to ±200 steps (about 17°) per command and 800 speed. Defaults are slow on purpose.
- `hw stop` always runs. It turns torque off, so **support the arm first**.

## What is NOT ready, and what to do about it

1. **Motor-to-joint mapping (unverified).** The code assumes motor IDs 1–8 follow URDF joints 01–08. *Do this first, on the arm.* It is low risk: jog one motor a few steps at a time and write down what moves. Step 5 of the checklist tracks it.
2. **Cartesian moves (`pick_at`, `place_at`) are not ready.** The Station only has motor-level control. Real IK needs the URDF geometry checked against the physical arm. *Do not build on this for the demo.* Instead:
   - **Teach joint waypoints.** Move the arm by hand or with `jog` to the poses you need (home, above the cube, grasp, bin A, bin B). Record each as a list of 8 joint targets in a file.
   - The agent then calls named waypoints, and only the vision layer decides *which* waypoint to use. This works without IK and is easy to debug.
   - Add IK later only if there is time after the demo works.
3. **No current-overload guard yet.** A blocked servo can strain its gears. *Before any gripper test on a real object*, read the current while moving slowly and set per-motor thresholds, as the teleop example does (`config.py`). Until then, keep gripper tests slow and short.
4. **Workspace limits disagree.** The mock table is 400 × 300 mm, the MCP server uses Y 90–270 mm, and the README gives 430 mm reach. *Measure the real table with a tape measure* and update the constants in one place.
5. **Station runtime files.** `station.yaml` and `station_data/` are created in the project root and not yet in `.gitignore`.

Suggested order for the next session: 1 → 3 → 4 → 2 (waypoints) → 5 → 6 (only once the gripper overload guard exists).
