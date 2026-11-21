# ElRobot MCP server

Lets Claude Code see the table and move the real ElRobot through the NormaCore Station.
Server: [src/robot_mcp_server.py](../src/robot_mcp_server.py). Tool logic: [src/robot_tools.py](../src/robot_tools.py).

## Setup (once per laptop)

`bin/`, `external/`, `.venv/`, `station.yaml` and `station_data/` are gitignored, so a fresh clone needs these steps.

```bash
# Python env
python3 -m venv .venv
.venv/bin/pip install "mcp>=2" pytest numpy pillow

# NormaCore SDK
git clone --depth 1 https://github.com/norma-core/norma-core external/norma-core

# Station binary: GitHub release v0.1.0-beta.10 of norma-core/norma-core,
# asset station-linux-amd64.tar.gz (not "x86_64"). Unpack so the binary is bin/station.

# Camera access for the Station (libuvc), then replug the cameras
sudo cp scripts/99-normacore-cameras.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger

# v4l2-ctl, used by ./cli.sh cameras (exposure fix)
sudo apt install v4l-utils

# Check: all tests pass
.venv/bin/python -m pytest tests/
```

Serial permissions for the arm: `./cli.sh setup-serial`.

Calibration lives in `station_data/` (local, per laptop). On a new laptop, calibrate in the Station
viewer again; [calibration/](../calibration/) holds the ranges measured on 2026-11-21 for comparison.

## Run

1. Start the Station from the repo root: `./cli.sh station` (cameras are found in `./station_data/usbvideo/`).
2. With two arms connected (teleop), tell the server which one is the follower. Put it in `.mcp.json` under `env`:
   `"ELROBOT_BUS": "<follower serial>"`.
3. Open Claude Code in this folder. It reads `.mcp.json` and asks to enable the `elrobot` server. Check with `/mcp`.
4. Ask Claude: "look at the table and tell me what you see".

## Web console (cameras + voice chat)

`./cli.sh console`, then open http://localhost:8890 in Chrome or Firefox on the same laptop.

- Left: the `table` and `gripper` cameras, read from the Station like `look` (about 8 fps each).
  Each shows its frame age; amber means the camera has stalled. Needs the Station running.
- Right: a chat box with a big microphone button. Click to talk, click again to stop (or hold Space).
  The text goes into the box to check, then Send/Enter. Tick "Send right after speaking" to skip that.
- Speech-to-text runs locally with faster-whisper: `large-v3-turbo` on an NVIDIA GPU, `small.en` on CPU
  (about 1 s per sentence). The first start downloads the model (~1.6 GB / ~500 MB) from Hugging Face, so
  do it once while online. Override with `WEB_CONSOLE_STT_MODEL=<name>`. Whisper is told which words to
  expect (`WEB_CONSOLE_STT_PROMPT`, default: the demo foods and commands); add new foods there.
  The server log prints what it heard (`heard 2.1 s of audio: '...'`). Without faster-whisper (or with
  `--no-stt`) the page uses the browser's speech recognition, which sends audio online (Chrome only).
- The microphone only works when the page is opened as `localhost` (browsers block it on plain http
  from another machine).
- Read-only: nothing on the page moves the arm. Chat messages are kept in memory at `/api/messages`
  (GET `?after=<id>`, POST `{"role": "user"|"robot", "text": ...}`) for a future `listen`/`say` tool.

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

1. **Camera names.** Cameras are named by the USB socket they are plugged into, because the Station
   makes a new queue (new hash) every time a camera is replugged. `list_cameras` shows each live
   camera's `port`. Set `config/elrobot.json`: `"cameras": {"table": "port:3-2.4", "gripper": "port:3-2.2"}`.
   Keep each camera in the same socket; if you move one, update its port.
2. **Exposure.** Under the Station the cameras' auto exposure gives near-white frames. Fixed exposure per camera is in
   `config/elrobot.json` → `camera_settings` (table 160, gripper 14, tuned 2026-11-21 in daylight). Apply with the Station
   stopped: `./cli.sh cameras`, then start the Station. Repeat after replugging a camera or rebooting, or if the light changes.
3. **Frame size.** `station.yaml` stores frames at `resize_target: 224` px. Too small to spot
   small objects; try `480` and restart the Station.
4. **Gripper direction.** `config/elrobot.json` → `gripper.open_at` (`"max"` or `"min"`) says which
   end of motor 8's range is open. Check with `./cli.sh hw identify 8`, fix if needed, set `"verified": true`.
5. **Waypoints.** Teach at least `clear` (above the table, gripper open), then the pick spots and bins
   (`./cli.sh hw teach <name>` with torque off, or ask Claude to `teach_waypoint` after you pose the arm).
   For a pick, teach a hover pose and a grasp pose (`pick_1_hover`, `pick_1`), so Claude can do
   hover → grasp with `via_clear=false`.
6. **Current thresholds.** The overload guard uses `current_threshold` per motor. Probe with
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
| Camera icon greyed out / `no cameras found`, but `ls /dev/video*` shows cameras | The Station uses libuvc (raw USB), which needs write access to `/dev/bus/usb/...`. Install `scripts/99-normacore-cameras.rules` (instructions inside), replug the cameras, restart the Station |
| `no cameras found` | Camera unplugged, or Station not run from this repo (set `ELROBOT_STATION_DATA` or `ELROBOT_CAMERA_QUEUES`) |
| `frame is old` | Camera stalled. Replug it and restart the Station |
| `moves larger than 600 steps are refused` | Go to `clear` first, or move the arm closer by hand |

Offline check: `.venv/bin/python -m pytest tests/test_robot_mcp.py`.
