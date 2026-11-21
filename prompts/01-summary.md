# Repo Summary: normacore-hackathon-2026

## What it is

The team's software for the **NormaCore track** ("AI-Powered Robot Control") at the Berlin Robotics & AI Hackathon (HackLab × BRISA, Nov 21–22, 2026). The goal: let Claude / Codex drive the **ElRobot** arm (7 joints + gripper, ST3215 bus servos) through the **NormaCore Station** runtime. The demo tasks are tabletop sorting, kitting and inspection using a camera.

## Core idea

The LLM handles meaning. Deterministic Python code handles motion and safety.

- **Vision:** four AprilTags at the table corners give a homography from camera pixels to table millimetres. A labelled mm grid is drawn over the camera image, so the agent can read coordinates off the picture.
- **High-level tools:** the agent calls `pick_at(x, y)` and `place_at(x, y)` in mm instead of sending joint angles. A safety layer clamps targets to a workspace box (X ±180 mm, Y 90–270 mm) and a table floor (Z ≥ 12 mm).
- **Closed loop:** `verify_grasp` checks gripper load. When an object is moved mid-task (the "judge perturbation" demo), the agent looks again and replans.

## Two layers, at different maturity

### 1. Cartesian / agent layer: simulated only
| File | Role |
| :--- | :--- |
| `src/mock_station.py` | Offline simulator: arm pose, table objects, camera frames, gripper load |
| `src/vision_homography.py` | Pixel↔mm homography (DLT) and grid overlay |
| `src/kinematics_safety.py` | Workspace and floor clamping, pick/place/home sequences (hover → grasp → transit) |
| `src/mcp_server.py` | `NormaCoreMCPServer` class with tools `get_calibrated_view`, `pick_at`, `place_at`, `set_gripper`, `verify_grasp`, `reset_home`, `simulate_perturbation` |
| `src/agent_prompts.py` | System prompt and a scripted perturbation/recovery demo |
| `src/digital_twin_server.py` + `digital_twin.html` | Three.js 3D twin of the mock arm in the browser (`localhost:8080`) |

Caveats found while reading the code:
- **No real inverse kinematics.** `move_end_effector` in the mock places the end effector directly at the target. Nothing maps (x, y, z) to joint angles yet.
- **`mcp_server.py` is not a working MCP server yet.** It defines a plain Python class but never imports the `mcp` SDK and has no `__main__` / stdio entry point. The `.mcp.json` entry (`normacore-robot`) launches it, but the process exits at once. That is why the MCP connection shows "Connection closed" in Claude Code.
- Everything in this layer runs only against `MockStation`. It has not been connected to the live Station.

### 2. Joint-level hardware layer: built, never run on the real arm
| File | Role |
| :--- | :--- |
| `src/elrobot_hardware.py` | Bridge to the Station SDK (ST3215 registers): snapshot, torque on/hold/off, `move_motors`, clamping to calibrated range, overload detector, `move_and_watch`, waypoint goto planning |
| `src/elrobot_config.py` | Loads `config/elrobot.json` (joint map, current thresholds, workspace) and `config/waypoints.json` |
| `src/elrobot_log.py` | Per-run log files in `logs/` |
| `scripts/hardware_preflight.py` | Read-only readiness check (motors present, calibrated, no faults) |
| `scripts/hw_day.py` | Hardware-day checklist and commands behind `./cli.sh hw ...` |
| `docs/elrobot_hardware_bridge.md` | Step-by-step runbook for bringing up the arm |

Safety rules: every motion needs the user to type `MOVE`. Jogs are capped at ±200 steps and gotos at 600 steps per motor (unless `--allow-large`). Targets are clamped to the calibrated range, and motion is refused while torque is off or a motor is faulted. `hw stop` turns torque off on all motors.

**Demo plan for now:** use taught **joint waypoints** (`home`, `clear`, `pick_<n>`, `bin_a`, `bin_b`) instead of Cartesian moves. Vision picks which waypoint to go to.

## Entry point: `./cli.sh`
`test`, `demo`, `digital-twin`, `view-camera`, `apriltags`, `station`, `setup-serial`, `mcp`, `urdf`, `preflight`, `logs`, and `hw <subcommand>` (identify, torque, motors, jog, probe-current, teach, waypoints, goto, workspace, map, bundle, stop).

## Current status (from `.ai-sync/HANDOFF.md`, Nov 20)
- Phase 1 (offline scaffolding) is done. Phase 3 is partly done (hardware tooling).
- **Nothing has run on the physical arm.** The handoff reports 44 offline tests passing. I could not re-run them here because `pytest` is not installed in this Python 3.14 environment.
- The `external/norma-core` SDK checkout and `bin/station` binary are not in the repo, because they are gitignored or downloaded separately. They are needed for anything beyond the mock.

## Next steps on hardware day (from the handoff)
1. `./cli.sh station`, then `./cli.sh hw run 3` (preflight).
2. `hw identify`: map all 8 motors and their directions (check which way the gripper on motor 8 moves).
3. `hw torque on` and a first small `hw jog`.
4. `hw probe-current <m>` per motor, gripper first.
5. Teach the `home` and `clear` waypoints, then test `goto` both ways.
6. Measure the table and set `"measured": true` in `config/elrobot.json`.
7. Still open: connect the MCP server to the live Station, decide on IK for Cartesian tools (or stay with waypoints), validate the camera overlay against real measurements, and rehearse the perturbation demo.

## Other repo contents
- `docs/`: challenge guide, Station SDK reference, repo/tooling overview, event logistics, USB serial setup, printable AprilTags.
- `.ai-sync/`: shared PLAN, PROGRESS and HANDOFF files that every AI agent reads first (see `AGENTS.md`).
- `archive/`: raw event emails and briefings, plus material from other tracks.
