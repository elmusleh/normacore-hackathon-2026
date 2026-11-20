# ElRobot Hardware Bridge: Runbook

This is the walkthrough for bringing the ElRobot up on the real arm through the NormaCore Station. Work top to bottom. `./cli.sh hw` always shows where you are.

Sources (checked 2026-11-20): official repo `norma-core/norma-core` in `external/norma-core/`. ElRobot README, URDF joint limits (`hardware/elrobot/simulation/elrobot_follower.urdf`), and the teleop example for register map and safety margins.

## Where things live

| File | What | In git? |
| :--- | :--- | :--- |
| `config/elrobot.json` | joint map, current thresholds, workspace limits | Yes. Commit after hardware day |
| `config/waypoints.json` | named poses from `hw teach` | Yes. Commit after hardware day |
| `data/hw_day_state.json` | checklist progress on this machine | No (gitignored) |
| `logs/` | one log per run, `hw-latest.log` | No (gitignored) |

Config is separate from progress, so clearing progress never deletes your joint map or waypoints.

## Commands

| Command | What it does | Moves the arm? |
| :--- | :--- | :--- |
| `./cli.sh hw` | Checklist, joint map, waypoints, workspace status | No |
| `./cli.sh hw next` / `run <n>` / `done <n>` | Work through the checklist | Only `run` on an auto step, which is read-only |
| `./cli.sh hw identify [m...]` | Guided: nudge each motor 30 steps, record which joint moved | Yes, small nudges. Type `MOVE` each time |
| `./cli.sh hw torque on` | Turn torque on, holding the current pose | Holds only |
| `./cli.sh hw torque off` (or `hw stop`) | Torque off on all motors. Arm goes limp | Releases the arm |
| `./cli.sh hw motors` | Live table of motors 1–8 | No |
| `./cli.sh hw jog <m> <steps> [--speed N]` | Move one motor, max ±200 steps. Type `MOVE` | Yes |
| `./cli.sh hw probe-current <m>` | Small move with overload protection off, reports peak current | Yes, small. Type `MOVE` |
| `./cli.sh hw teach <name>` | Save the current pose of all 8 motors | No |
| `./cli.sh hw waypoints` | List waypoints | No |
| `./cli.sh hw goto <name> [--speed N]` | Move all 8 motors to a waypoint, shows the plan first. Type `MOVE` | Yes |
| `./cli.sh hw workspace` | Show workspace limits and whether they were measured | No |
| `./cli.sh hw map <m> <joint> <dir>` | Record one motor by hand, instead of `identify` | No |
| `./cli.sh preflight` | Read-only readiness check | No |
| `./cli.sh logs [-f]` / `hw logs` | Newest log, or follow it | No |
| `./cli.sh hw bundle` | Pack logs, config and state for sharing | No |

Add `--debug` to any `hw` command for DEBUG output on the console. The log file always has it.

Every motion asks you to type `MOVE`. Moves are refused if torque is off, or if a motor is uncalibrated, faulted or missing. A target outside the calibrated range is clamped to the range minus 20 steps, and the tool shows the clamp before you confirm. `hw stop` always works.

## Step 1–4: Power, Station, preflight, calibration

1. 12 V / 4 A supply on the follower arm. Data-rated USB cable to the Waveshare bus servo driver (A). Keep a hand near the power switch.
2. In a separate terminal: `./cli.sh station`. Leave it running.
3. `./cli.sh hw run 3`. Expect READY with motors 1–8 listed. Anything MISSING, UNCALIBRATED or FAULT: fix it first.
4. Uncalibrated? Calibrate in the Station console (web: http://localhost:8889) by moving each joint through its full travel. Re-run step 3.

## Step 5: Which motor drives which joint (not ready until done)

`./cli.sh hw identify` walks through motors 1–8. For each motor:
- Type `MOVE` to nudge it +30 steps (about 2.6°). It then returns to where it started.
- The tool prints the encoder movement. If it reads 0, nothing moved: check torque and the cable. The motor is not recorded.
- Name the joint it moved (e.g. `shoulder_lift`, `base`, `gripper`) and the physical direction (e.g. `up`, `left`, `close`).
- Type `s` to skip a motor, or `q` to stop and resume later.

Watch the arm for each nudge. Stop with `hw stop` if anything looks wrong. The result lands in `config/elrobot.json`.

Motor 8 is the gripper. Check whether +30 opens or closes it, and record that.

Once all 8 are mapped, step 5 passes automatically.

## Step 6–7: Torque on, first small move

- `./cli.sh hw torque on` holds the current pose. Nothing else moves.
- `./cli.sh hw jog 2 60 --speed 200`. Check the joint and direction match the map, then `./cli.sh hw done 7`.

## Step 8: Current probe and the overload guard

The guard stops a move when a motor draws high current and does not move. The stop holds it in place. It works like this:
- Threshold: per motor, from `config/elrobot.json` (`current_threshold`). The default is 100 raw units, copied from the NormaCore teleop example. **That default is not measured on this arm.**
- Trigger: three polls in a row with current above the threshold and less than 3 steps of movement.
- Response: hold all motors that are still moving, log `OVERLOAD`, and report the status.

To set a real threshold: `./cli.sh hw probe-current 2`. It makes a 60-step move with the guard off, reports the peak current going out and back, and suggests `2 × peak` (never below the current threshold). Answer `y` to save it. Repeat for each motor you will use. Do this before any gripper test on a real object.

The gripper (motor 8) is where this matters most. Probe it while it closes on nothing, then while it closes on a light object, before using it for real.

## Step 9–10: Waypoints (replaces Cartesian moves for the demo)

Cartesian moves (`pick_at`, `place_at`) are not ready. The Station only takes joint targets, and the kinematics have not been checked on the arm. The demo approach is named joint waypoints:

1. **Teach.** Set the arm to a pose by hand, or with `jog`:
   - Torque off (`./cli.sh hw torque off`). Support the arm, then move it by hand.
   - `./cli.sh hw teach home`. Teaching reads positions with torque off.
   - Turn torque back on before any `goto`: `./cli.sh hw torque on`.
2. **Teach a clear pose first.** Keep one waypoint above the table with the gripper open (`clear`). Route every move through it, so the arm never sweeps across the table.
3. **Goto.** `./cli.sh hw goto clear`, then `./cli.sh hw goto <target>`. The tool prints the per-motor plan (present, target, delta, and whether clamped). Check the path is clear, then type `MOVE`.
4. **Limits.** A single goto refuses any motor moving more than 600 steps unless you pass `--allow-large`. Keep large moves through `clear`.
5. **Check.** After each goto the tool reports each motor's status. Any motor more than 12 steps from its target is listed and the command exits with an error. Look for an obstacle, then `./cli.sh logs`.

Suggested waypoints for the sorting demo: `home`, `clear`, `pick_<n>` (one per object spot), `bin_a`, `bin_b`. Teach them in that order and test each with goto before the demo.

Vision decides which waypoint to use. Waypoints are joint positions, so they only stay valid while the arm base and the table do not move. Re-teach after any move of the arm or table.

## Step 11: Measure the workspace

The current limits (x ±180, y 90–270, floor 12, transit 70 mm) are defaults, not measurements. The MCP server and `SafetyLimits` read them from `config/elrobot.json`.

1. Define the frame: origin at the arm base, X sideways, Y forward (away from the arm). Confirm this against the manual or the URDF before you measure. Check it on the arm by reading the joint positions at a known spot.
2. Measure with a tape from the base to the table edges:
   - `x_min_mm` / `x_max_mm`: the table's left and right limits.
   - `y_min_mm` / `y_max_mm`: the nearest and farthest reachable points.
3. Measure the floor: move the gripper tip down until it touches the table. Measure the height above the table surface at the grasp point. Set `z_table_floor_mm` a few mm above that.
4. Set `z_transit_mm` above any object you may carry, and `z_hover_mm`, `z_grasp_mm` for the pick.
5. Edit `config/elrobot.json`, set `"measured": true`, then run `./cli.sh hw workspace` to check.
6. Run the tests: `python3 -m pytest tests/`.

The mock table is still 400 × 300 mm. That is a separate simulation and does not change with this file.

## Emergency

- `./cli.sh hw stop`: torque off on all motors. The arm goes limp, so support it first.
- Station console stop, or cut power to the driver board.
- Always keep one hand near the power switch while anything is moving.

## Still unverified (check on the arm)

1. Motor-to-joint mapping and directions (step 5).
2. Whether +30 steps on motor 8 opens or closes the gripper.
3. The current threshold for each motor (step 8).
4. The workspace frame and measurements (step 11).
5. Waypoint routes through `clear` (step 10).
6. Cartesian control: not ready. Use waypoints for the demo.

## Troubleshooting

| Message | Likely cause | Fix |
| :--- | :--- | :--- |
| `cannot use the Station at localhost` | Station not running | `./cli.sh station` in another terminal |
| `no st3215/inference frame ...` | Station up, no bus seen | Check the USB cable and the driver board power |
| `--bus auto needs exactly one bus` | More than one bus | `ELROBOT_BUS=<serial>` |
| `has torque OFF` | Torque off | `./cli.sh hw torque on` |
| `goal clamped` (warning) | Target outside the safe range | Expected near the ends. Repeated clamps mean wrong calibration or target |
| `calibration invalid` | Uncalibrated, or range wraps past zero | Calibrate in the Station console |
| `reports fault status` | Servo error | `hw stop`, let it cool, check the cable. Don't force it |
| `OVERLOAD` | Stalled under high current | Something is in the way, or the threshold is too low. Check, then probe again |
| `moves larger than 600 steps` | Waypoint too far away | Route through `clear`, or `--allow-large` after checking |
| `SDK import failed` | `external/norma-core` missing | Set `NORMACORE_ROOT`, or re-check the download |

Share a failure: `./cli.sh hw bundle`, then send the file it prints. It contains logs, config and state. Check it first, since it includes `station.yaml`.
