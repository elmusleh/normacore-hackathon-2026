# Team Setup: New Machine

Read this before the first run on a new computer. Owner: the team. Last reviewed 2026-11-22.

## 1. Get the code (with the NormaCore submodule)
```bash
git clone --recurse-submodules https://github.com/elmusleh/carearm-feeding-robot.git
cd carearm-feeding-robot
git checkout main && git pull --rebase
```
`--recurse-submodules` fetches the NormaCore SDK at `external/norma-core/`, pinned to commit `5f4f805`.

Already cloned without it? Run `git submodule update --init --recursive`. `./cli.sh sync` also does this after each pull.

## 2. Python environment (Python 3.10 or newer)
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./cli.sh setup-vision            # MediaPipe + face model into data/ (needed for real mouth detection)
```
`.venv/` and `data/` are gitignored, so every laptop needs this once. Every `./cli.sh` command runs with `.venv/bin/python` automatically, so you do not need to activate the venv for them. If you run a script directly (`python3 src/...`), use `.venv/bin/python` instead, or the person camera loses MediaPipe and shows no mouth.

Check it any time with `.venv/bin/python scripts/vision_check.py`.

## 3. Offline check (no hardware needed)
```bash
python3 -m pytest tests/ -q
```
Expect all tests to pass (144 at the last review, about 1 min). If not, stop and fix before going further.

## 4. NormaCore SDK and Station binary (must match)
Both must come from NormaCore release **0.1.0-beta.10 (build 5f4f805)**. A mismatch can cause protocol or protobuf errors that look like hardware faults.

**a. SDK (`external/norma-core/`)**
This is a git submodule pinned in `.gitmodules`. Step 1 fetched it. Nothing to download or extract.

The submodule is the only supported SDK source. An old unpacked copy (no `.git` inside `external/norma-core/`) is not the same code and must not be used. If you have one, move it aside before you run `git submodule update --init`:
```bash
mv external/norma-core ~/norma-core-old-unpacked
git submodule update --init --recursive
```
- To change the SDK version, change the pin in its own commit, approved by the owner (see `AGENTS.md` Team Workflow). Do not edit files inside `external/norma-core/`. Do not regenerate `target/gen_python` (the generated protobuf code).

**b. Station binary (`bin/station`)**
`bin/` is gitignored, so the binary is not in the repo. Download release v0.1.0-beta.10 as described in [NormaCore_Repositories_and_Tooling.md](NormaCore_Repositories_and_Tooling.md), place it at `bin/station`, then run `chmod +x bin/station`. Check it with `./bin/station --version`. It must print `0.1.0-beta.10 (5f4f805)`.

**c. Verify both together**
```bash
./cli.sh sdk-check        # must end with RESULT: PASS
```
Run this after any SDK or Station change, and before a bench session. Do not start the Station if it fails. Record the result in `HANDOFF.md` if it fails.

## 5. Serial permissions (once per machine)
```bash
./cli.sh setup-serial            # asks for your sudo password
```
This adds you to the `dialout` group and installs the udev rule that makes the USB serial adapters readable. Then unplug and replug the adapters (or run `sudo udevadm trigger`). If `groups` does not show `dialout` yet, log out and back in.

Do not run robot scripts with `sudo` (see GUIDELINES.md §5). Only the setup script uses it.

Check it worked:
```bash
ls -l /dev/ttyACM*               # group should be dialout, mode rw-rw-rw-
```

## 6. Cameras
Camera numbers (`/dev/video0`, `/dev/video2`, ...) change after replugging. Do not hard-code them. Use `/dev/v4l/by-path/` to find the stable port path for each camera. Two of our cameras share the same USB name, so the port path is the only reliable way to tell them apart. Confirm each one with a test frame before you assign it as overhead or wrist.

**Frame size.** `./cli.sh station` and `./cli.sh start` check the local, gitignored `station.yaml` first (`scripts/station_config.py`). If it has no camera `formats`, they add the HD list and `resize_target: 1080` (old file kept as `station.yaml.bak`), so table and gripper frames are stored at 1920x1080, which the calibration and grip skills expect. The KD-USB cameras share one USB 2.0 link, so they capture at 1280x720 and the Station scales up. To keep your own `station.yaml` untouched, set `ELROBOT_KEEP_STATION_YAML=1`.

**Exposure.** Washed-out (nearly white) table or gripper frames: stop the Station, run `./cli.sh cameras`, then start it again.

## 7. Bench check (read-only)
1. In its own terminal: `./cli.sh station` (leave it running). It listens on port 8888.
2. `./cli.sh preflight --bus <serial>`. This only reads; it never moves the arm.

Always pass `--bus` explicitly when two serial adapters are plugged in. `--bus auto` works only with exactly one.

Record which serial number is which arm in `HANDOFF.md` once it is confirmed. Confirmed 2026-11-21: follower `5B61034962`, leader `5B61037051` (`config/elrobot.json` `station.bus` / `station.leader_bus`).

## 8. Web console: cameras and voice chat (optional)
1. With the Station running: `./cli.sh console`, then open http://localhost:8890 on the same laptop (the microphone only works on `localhost`).
2. The chat goes to Claude, which needs a Claude API key: `export ANTHROPIC_API_KEY=sk-ant-...` in that terminal before step 1. Never put the key in the repo. Without it, the cameras and speech-to-text still work.
3. The first start downloads the speech model (about 1.6 GB on an NVIDIA GPU, 500 MB on CPU), so do it once while online.
4. The console starts its own copy of the `elrobot` MCP server from `.mcp.json`, so `ELROBOT_ALLOW_MOTION` there decides whether Claude's moves are real. Typing or saying only "stop", or the red STOP button, holds the arm without going through Claude. Details: `docs/mcp_server.md` → Web console.

## 9. Common problems

| Symptom | Cause and fix |
|---|---|
| `Permission denied` on `/dev/ttyACM*` | Step 5 not done, or the group change is not active yet. |
| `--bus auto needs exactly one bus` | Two adapters are plugged in. Pass `--bus <serial>`. |
| Every motor shows MISSING | Usually the permission error above. Check the Station log in `logs/station/`. |
| Cameras missing after a USB drop | Reseat the cable, or try another port. Then restart the Station, because it does not recover on its own. |
| `./cli.sh cameras` says table/gripper NOT PLUGGED IN right after stopping the Station | The Station takes the cameras from the kernel driver and does not hand them back. Unplug and replug just the two camera cables (not the hub: the arm adapters are on it), then run `./cli.sh cameras` again. |
| Table/gripper frames are 320x240 | `station.yaml` has `formats: []`. Restart with `./cli.sh station`, which adds the HD formats. |
| Person camera shows a mouth box with nobody there, or never shows a mouth | MediaPipe or `data/face_landmarker.task` is missing, or a tool was started with plain `python3`. Run `./cli.sh setup-vision` and start tools through `./cli.sh`. |
| Dashboard shows no Station cameras, log says `bus ... not on station` | `station.bus` in `config/elrobot.json` names an arm that is not plugged in. Start with `ELROBOT_BUS=<serial> ./cli.sh start` and tell the arm's owner. |
| Station exited | Restart it with `./cli.sh station`. Check `logs/station/` for the last error. |
| Port 8888 not listening | The Station is not running. |
| `external/norma-core/` is empty | Run `git submodule update --init --recursive`. |
| `sdk-check`: "is an old unpacked copy, not the submodule" | Move the folder aside (step 4a), then run `git submodule update --init --recursive`. |
| `./cli.sh sdk-check` fails on the SDK pin or local changes | Run `git submodule update --init --recursive`. If local changes are listed, reset that folder. Do not commit them. |
| `./cli.sh sdk-check` fails on the Station build | Replace `bin/station` with release v0.1.0-beta.10 (see step 4b). |

If none of these fix it, record the symptom and the log path in `HANDOFF.md` under Blockers.
