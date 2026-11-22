"""Apply fixed exposure to the cameras, so the Station's frames are not washed out.

The Station captures through libuvc, and with the camera's auto exposure the frames
come out nearly white. A fixed (manual) exposure set here stays in the camera until
it loses power, and the Station then uses it.

The cameras only appear as /dev/video* while the Station is NOT running (libuvc
takes them over). So: stop the Station, run this, start the Station.

  ./cli.sh cameras            apply config/elrobot.json -> camera_settings
  ./cli.sh cameras --show     show each camera's port and current settings

Run it again after replugging a camera or rebooting.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from elrobot_config import camera_targets, load_config  # noqa: E402

V4L = Path("/sys/class/video4linux")


def video_devices_by_port() -> dict:
    """USB port (e.g. '3-2.4') -> first /dev/videoN of that camera (the capture node)."""
    found = {}
    for node in sorted(V4L.glob("video*"), key=lambda p: int(p.name[5:])):
        # .../usb3/3-2/3-2.4/3-2.4:1.0/video4linux/video2 -> interface '3-2.4:1.0' -> port '3-2.4'
        iface = (node / "device").resolve().name
        port = iface.split(":")[0]
        found.setdefault(port, f"/dev/{node.name}")
    return found


def station_running() -> bool:
    return subprocess.run(["pgrep", "-x", "station"], capture_output=True).returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--show", action="store_true", help="only show cameras and current settings")
    args = ap.parse_args()

    cfg = load_config()
    devices = video_devices_by_port()
    if not devices:
        if station_running():
            print("The Station is running and holds the cameras. Stop it (Ctrl+C), run this again, then restart it.")
        else:
            print("No cameras found (/dev/video*). Plug them in.")
        return 1

    names = {t.split(":", 1)[1]: k for k, targets in camera_targets(cfg).items()
             for t in targets if t.startswith("port:")}
    status = 0
    for port, dev in devices.items():
        name = names.get(port, "(unnamed)")
        settings = cfg["camera_settings"].get(name, {}) if name != "(unnamed)" else {}
        if settings and not args.show:
            ctrls = ["auto_exposure=1", "exposure_dynamic_framerate=0",
                     f"exposure_time_absolute={int(settings['exposure'])}"]
            res = subprocess.run(["v4l2-ctl", "-d", dev] + sum((["-c", c] for c in ctrls), []),
                                 capture_output=True, text=True)
            if res.returncode != 0:
                print(f"{name} ({port}, {dev}): failed: {res.stderr.strip()}")
                status = 1
                continue
        cur = subprocess.run(["v4l2-ctl", "-d", dev, "-C", "auto_exposure,exposure_time_absolute"],
                             capture_output=True, text=True).stdout.replace("\n", "  ").strip()
        print(f"{name:<10} port {port:<8} {dev:<12} {cur}")
    unknown = set(names) - set(devices)
    for port in sorted(unknown):
        print(f"{names[port]:<10} port {port:<8} NOT PLUGGED IN")
    return status


if __name__ == "__main__":
    sys.exit(main())
