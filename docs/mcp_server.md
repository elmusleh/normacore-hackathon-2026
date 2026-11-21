# ElRobot MCP server

Lets Claude Code see the table and move the real ElRobot through the NormaCore Station.
Server: [src/robot_mcp_server.py](../src/robot_mcp_server.py). Tool logic: [src/robot_tools.py](../src/robot_tools.py).

## Setup (once per laptop)

```bash
python3 -m venv .venv
.venv/bin/pip install "mcp>=2" pytest numpy pillow
```

The NormaCore SDK must be in `external/norma-core` (`git clone --depth 1 https://github.com/norma-core/norma-core external/norma-core`).

## Run

1. Start the Station from the repo root: `./cli.sh station` (cameras are found in `./station_data/usbvideo/`).
2. With two arms connected (teleop), tell the server which one is the follower. Put it in `.mcp.json` under `env`:
   `"ELROBOT_BUS": "<follower serial>"`.
3. Open Claude Code in this folder. It reads `.mcp.json` and asks to enable the `elrobot` server. Check with `/mcp`.
4. Ask Claude: "look at the table and tell me what you see".

## Motion is off until you turn it on

`.mcp.json` sets `ELROBOT_ALLOW_MOTION` to `"0"`. Claude can look, read the arm and plan, but every
motion tool returns `dry_run` with the plan. When the arm is clear and someone has a hand on the
power plug, set it to `"1"` and restart the server (`/mcp` → reconnect).

## Tools

| Tool | What it does | Moves? |
| :--- | :--- | :--- |
| `look(camera)` | Newest JPEG from a camera (`table`, `gripper`, a queue id, or default) | No |
| `list_cameras` | Camera queues with product names | No |
| `get_robot_state` | Joints as % of calibrated range, torque, current, faults, gripper opening, nearest waypoint | No |
| `list_waypoints` | Taught poses | No |
| `go_to_waypoint(name, via_clear=True)` | Move to a taught pose, through `clear` by default | Yes |
| `nudge_joint(motor, delta_percent)` | Small move of one joint, max 5% of its range | Yes |
| `set_gripper(open_percent)` | 100 open, 0 closed. Reports `holding_object` or `closed_empty` | Yes |
| `enable_torque` | Torque on, holding the current pose | Holds |
| `stop` | Hold every motor where it is. Always allowed | Holds |
| `teach_waypoint(name)` | Save the current pose | No |

Claude cannot turn torque off. Do that yourself with `./cli.sh hw torque off` (support the arm).

## Before the first real session

1. **Camera names.** Run `list_cameras` (or ask Claude), wave at each camera, then name them in
   `config/elrobot.json`: `"cameras": {"table": "usbvideo/<hash>", "gripper": "usbvideo/<hash>"}`.
2. **Frame size.** `station.yaml` stores frames at `resize_target: 224` px. Too small to spot
   small objects; try `480` and restart the Station.
3. **Gripper direction.** `config/elrobot.json` → `gripper.open_at` (`"max"` or `"min"`) says which
   end of motor 8's range is open. Check with `./cli.sh hw identify 8`, fix if needed, set `"verified": true`.
4. **Waypoints.** Teach at least `clear` (above the table, gripper open), then the pick spots and bins
   (`./cli.sh hw teach <name>` with torque off, or ask Claude to `teach_waypoint` after you pose the arm).
   For a pick, teach a hover pose and a grasp pose (`pick_1_hover`, `pick_1`), so Claude can do
   hover → grasp with `via_clear=false`.
5. **Current thresholds.** The overload guard uses `current_threshold` per motor. Probe with
   `./cli.sh hw probe-current <m>`, the gripper first.

## Limits (config/elrobot.json → `agent`)

- `max_speed` 500: speed cap for every move Claude requests.
- `max_waypoint_delta_steps` 600: any motor moving further in one leg is refused.
- `max_nudge_percent` 5: largest single nudge.
- `clear_waypoint` "clear": the routing pose.

## Troubleshooting

Logs: `logs/mcp-latest.log`. Errors come back to Claude as `{"ok": false, "error": ...}`.

| Error | Fix |
| :--- | :--- |
| `cannot reach the ElRobot through the Station` | Start `./cli.sh station`; check power and USB |
| `--bus auto needs exactly one bus` | Set `ELROBOT_BUS` to the follower serial in `.mcp.json` |
| `torque is off on motors [...]` | Ask Claude to `enable_torque`, or `./cli.sh hw torque on` |
| `no cameras found` | Camera unplugged, or Station not run from this repo (set `ELROBOT_STATION_DATA` or `ELROBOT_CAMERA_QUEUES`) |
| `frame is old` | Camera stalled. Replug it and restart the Station |
| `moves larger than 600 steps are refused` | Go to `clear` first, or move the arm closer by hand |

Offline check: `.venv/bin/python -m pytest tests/test_robot_mcp.py`.
