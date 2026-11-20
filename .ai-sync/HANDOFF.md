---
last_agent: claude
timestamp: 2026-11-20T22:40:00Z
status: ready-for-hardware
current_phase: "Phase 3: Agent Integration & Tabletop Primitives (partial)"
current_task: "Hardware-day tooling and logging done; first run on the real arm pending"
stop_reason: needs-physical-arm
---

## What Was Completed

Earlier this session: the joint-level hardware bridge (`src/elrobot_hardware.py`), the read-only preflight, offline tests, and the runbook. Committed as `769ee66`.

This pass (not yet committed at time of writing; see Files):

1. **Run logging** `src/elrobot_log.py`:
   - Each run writes `logs/<tool>-<timestamp>.log` at DEBUG, and `logs/<tool>-latest.log` points at it.
   - The header records git commit, Python, platform, arguments and SDK path.
   - Uncaught exceptions are logged with tracebacks.
   - The console shows INFO for commands that talk to the arm, and WARNING for read-only commands.
2. **Bridge tracing** `src/elrobot_hardware.py`: connection steps, bus serials seen, each move request, clamp, sent command (with register hex at DEBUG), and every refusal with its reason. Connection failures give one clear console line. Shutdown cancels leftover tasks.
3. **Hardware-day tool** `scripts/hw_day.py`, exposed as `./cli.sh hw ...`:
   - Checklist with saved progress (`logs/hw_day_state.json`): `status`, `next`, `run <n>`, `done <n> [--undo]`, `reset`.
   - Joint map: `map <motor> <joint> <dir> [note]`.
   - Read-only table: `motors`.
   - Motion: `jog <motor> <steps> [--speed N]`. Max ±200 steps and speed 800. Requires typing `MOVE`.
   - Safety: `stop` (torque OFF, always available).
   - Debugging: `logs [--lines N]`, `bundle` (packs latest logs, state, `station.yaml`).
4. **cli.sh**: `hw ...`, `preflight`, and `logs [-f]` commands added. The help text lists them.
5. **Runbook** `docs/elrobot_hardware_bridge.md`: commands table, logs and common-failures table, hardware-day steps, and a recommended order for what is not ready.

## Work In Progress

None in code. Nothing has run on the physical arm yet.

## Next Steps

1. Power and connect the ElRobot. Start the Station with `./cli.sh station` in a separate terminal.
2. Run `./cli.sh hw` to see the checklist. Then `./cli.sh hw run 3` (or `./cli.sh preflight`) and expect READY.
3. If preflight shows UNCALIBRATED, calibrate in the Station console, then re-run step 3.
4. Map all 8 motors with `./cli.sh hw map <m> <joint> <dir>`. Use the Station console and jog at low speed to find each one.
5. First move: `./cli.sh hw jog 2 100 --speed 300`. Type `MOVE` to confirm. Then `./cli.sh hw done 6`.
6. If anything fails: `./cli.sh logs`. To share a debug bundle: `./cli.sh hw bundle`.
7. Not ready (see runbook): Cartesian moves, gripper overload guard, workspace numbers. Recommended approach: teach joint waypoints and replay them.

## Files Modified/Created

- `src/elrobot_log.py` (new)
- `src/elrobot_hardware.py` (tracing, clean shutdown)
- `scripts/hw_day.py` (new)
- `scripts/hardware_preflight.py` (run logging, `--debug`)
- `cli.sh` (`hw`, `preflight`, `logs`)
- `docs/elrobot_hardware_bridge.md` (rewritten)
- `CHANGELOG.md`, `SUGGESTIONS.md`, `.ai-sync/PROGRESS.md`, `.ai-sync/HANDOFF.md`
- Untracked, not committed: `station.yaml` and `station_data/` (created by a Station test run; a delete was denied, so they remain). Also `src/digital_twin.html`, which predates this work.
- Runtime files in `logs/` are gitignored.

## Blockers

- No physical arm available in this session. Motion code is verified only by offline tests and by reading the SDK source.

## Key Decisions

- **Joint-level only.** Cartesian control waits for a verified kinematics model. Recommended instead: teach joint waypoints.
- **Motion needs typed confirmation.** `jog` requires `MOVE`. `--yes` exists but is not recommended.
- **Logs are per run** so a failure can be traced to one run. `bundle` gathers what is needed to share it.
- **Checklist state is local** (`logs/`, gitignored), so each machine has its own progress.

## Build Status

- `python3 -m pytest tests/`: 19 passed.
- `bash -n cli.sh`, `py_compile` on all new and changed Python files: OK.
- `./cli.sh hw` (status, map, reset), `./cli.sh hw stop`, `./cli.sh hw jog` and `./cli.sh hw run 3` with no Station: each fails with one clear console line and a log file.
- Not verified against a live Station with frames (the Station here has no bus attached).

## Source Facts (verified 2026-11-20)

- URDF joints `rev_motor_01`..`08`. Limits in radians, for example `rev_motor_01` ±1.5509. Gripper is `rev_motor_08` plus two prismatic fingers.
- ElRobot BOM: ST3215 12 V / 30 kg on the follower, 8 motors. Waveshare Serial Bus Servo Driver (A). Reach 430 mm.
- Station: TCP 8888, web 8889. Topic `st3215/inference`. Commands go as `DriverCommand` with `STC_ST3215_COMMAND`.
