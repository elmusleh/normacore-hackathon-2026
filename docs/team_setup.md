# Team Setup: New Machine

Read this before the first run on a new computer. Owner: the team. Last reviewed 2026-11-21.

## 1. Get the code
```bash
git clone https://github.com/elmusleh/normacore-hackathon-2026.git
cd normacore-hackathon-2026
git checkout main && git pull --rebase
```

## 2. Python environment (Python 3.10 or newer)
```bash
python3 -m venv .venv
source .venv/bin/activate        # run this in every new terminal
pip install -r requirements.txt
```
`.venv/` is gitignored. Activate it before any `./cli.sh` command, because `cli.sh` calls `python3`.

## 3. Offline check (no hardware needed)
```bash
python3 -m pytest tests/ -q
```
Expect all tests to pass (44 at the last review). If not, stop and fix before going further.

## 4. Station binary
`bin/` is gitignored, so the binary is not in the repo. Download the Station release as described in [NormaCore_Repositories_and_Tooling.md](NormaCore_Repositories_and_Tooling.md) and place it at `bin/station`, then make it executable with `chmod +x bin/station`.

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

## 7. Bench check (read-only)
1. In its own terminal: `./cli.sh station` (leave it running). It listens on port 8888.
2. `./cli.sh preflight --bus <serial>`. This only reads; it never moves the arm.

Always pass `--bus` explicitly when two serial adapters are plugged in. `--bus auto` works only with exactly one.

Record which serial number is which arm in `HANDOFF.md` once it is confirmed. As of 2026-11-21 the two adapters were `5B61034962` and `5B61037051`. Their arm assignment was not yet confirmed.

## 8. Common problems

| Symptom | Cause and fix |
|---|---|
| `Permission denied` on `/dev/ttyACM*` | Step 5 not done, or the group change is not active yet. |
| `--bus auto needs exactly one bus` | Two adapters are plugged in. Pass `--bus <serial>`. |
| Every motor shows MISSING | Usually the permission error above. Check the Station log in `logs/station/`. |
| Cameras missing after a USB drop | Reseat the cable, or try another port. Then restart the Station, because it does not recover on its own. |
| Station exited | Restart it with `./cli.sh station`. Check `logs/station/` for the last error. |
| Port 8888 not listening | The Station is not running. |

If none of these fix it, record the symptom and the log path in `HANDOFF.md` under Blockers.
