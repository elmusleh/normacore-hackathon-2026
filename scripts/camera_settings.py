"""Apply fixed exposure (and other V4L2 controls) to the cameras, so the Station's frames are not washed out.

The Station captures through libuvc, and with the camera's auto exposure the frames
come out nearly white. A fixed (manual) exposure set here stays in the camera until
it loses power, and the Station then uses it.

The cameras only appear as /dev/video* while the Station is NOT running (libuvc
takes them over). So: stop the Station, run this, start the Station.

  ./cli.sh cameras                  apply config/elrobot.json -> camera_settings
  ./cli.sh cameras --show           show each camera's port and current settings
  ./cli.sh cameras --tune [table]   try exposures, measure each picture, recommend one
  ./cli.sh cameras --tune --write   ... and write the recommendation to config/elrobot.json

camera_settings per camera:
  "exposure": 70                    exposure_time_absolute, with auto exposure off
  "controls": {"gain": 0, ...}      any other V4L2 control by name (v4l2-ctl -d /dev/videoN -L
                                    lists them). Controls the camera does not have are skipped.
Example for a white table:
  "table": {"exposure": 70, "controls": {"gain": 0, "white_balance_automatic": 0,
            "white_balance_temperature": 4600, "backlight_compensation": 0}}

Run it again after replugging a camera or rebooting.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from elrobot_config import camera_targets, load_config, save_config  # noqa: E402

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


CONTROL_LINE = re.compile(r"^\s*(\w+)\s+0x[0-9a-f]+\s+\(", re.MULTILINE)

# Exposure measurement for --tune. Luminance at or above CLIPPED_LEVEL counts as blown out,
# at or below DARK_LEVEL as crushed black. TARGET_MEAN is the mid-grey --tune aims for.
CLIPPED_LEVEL = 250
DARK_LEVEL = 5
OVEREXPOSED_SHARE = 0.10
UNDEREXPOSED_SHARE = 0.25
TARGET_MEAN = 115.0

# Exposures tried by --tune (exposure_time_absolute, units of 100 us on UVC cameras).
TUNE_EXPOSURES = [5, 10, 14, 20, 30, 40, 50, 70, 100, 130, 160, 200, 250]


def ordered_controls(settings: dict) -> list:
    """V4L2 'name=value' strings for one camera. Auto switches go first, so manual values that
    depend on them (white_balance_temperature after white_balance_automatic=0) are accepted."""
    ctrls = []
    if "exposure" in settings:
        ctrls += ["auto_exposure=1", "exposure_dynamic_framerate=0",
                  f"exposure_time_absolute={int(settings['exposure'])}"]
    extra = settings.get("controls", {}) or {}
    autos = [k for k in extra if "auto" in k]
    ctrls += [f"{k}={int(extra[k])}" for k in autos]
    ctrls += [f"{k}={int(v)}" for k, v in extra.items() if k not in autos]
    return ctrls


def supported_controls(dev: str) -> set:
    """Control names the camera at dev has (from v4l2-ctl -l)."""
    out = subprocess.run(["v4l2-ctl", "-d", dev, "-l"], capture_output=True, text=True).stdout
    # Lines look like "                     brightness 0x00980900 (int)    : min=-64 max=64 ..."
    return {m.group(1) for m in CONTROL_LINE.finditer(out)}


def exposure_stats(bgr) -> dict:
    """Mean luminance and the share of blown-out and black pixels of a BGR frame, with a verdict."""
    import cv2  # noqa: WPS433
    import numpy as np  # noqa: WPS433

    y = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    total = float(y.size) or 1.0
    clipped = float(np.count_nonzero(y >= CLIPPED_LEVEL)) / total
    dark = float(np.count_nonzero(y <= DARK_LEVEL)) / total
    if clipped > OVEREXPOSED_SHARE:
        verdict = "overexposed"
    elif dark > UNDEREXPOSED_SHARE:
        verdict = "underexposed"
    else:
        verdict = "ok"
    return {"mean": round(float(y.mean()), 1), "clipped_share": round(clipped, 3),
            "dark_share": round(dark, 3), "verdict": verdict}


def score_exposure(stats: dict) -> float:
    """Lower is better: distance of the mean from mid-grey, with a heavy cost for blown-out
    pixels (food on a white table disappears there) and a smaller one for black pixels."""
    return abs(stats["mean"] - TARGET_MEAN) + 400.0 * stats["clipped_share"] + 150.0 * stats["dark_share"]


def pick_exposure(results: dict) -> int:
    """Best exposure from {exposure: stats}."""
    return min(results, key=lambda e: (score_exposure(results[e]), e))


def tune(dev: str, name: str) -> dict:
    """Try each exposure on one camera and return {exposure: stats}. Needs OpenCV."""
    import cv2  # noqa: WPS433

    cap = cv2.VideoCapture(dev, cv2.CAP_V4L2)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {dev}")
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    results = {}
    try:
        for exp in TUNE_EXPOSURES:
            subprocess.run(["v4l2-ctl", "-d", dev, "-c", "auto_exposure=1", "-c", "exposure_dynamic_framerate=0",
                            "-c", f"exposure_time_absolute={exp}"], capture_output=True)
            frame = None
            for _ in range(8):  # let the new exposure reach the sensor output
                ok, img = cap.read()
                if ok:
                    frame = img
            if frame is None:
                continue
            results[exp] = exposure_stats(frame)
            st = results[exp]
            print(f"  {name:<8} exposure {exp:>4}: mean {st['mean']:>5}  white {st['clipped_share']:>6.1%}  "
                  f"black {st['dark_share']:>6.1%}  {st['verdict']}")
    finally:
        cap.release()
    return results


def station_running() -> bool:
    return subprocess.run(["pgrep", "-x", "station"], capture_output=True).returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--show", action="store_true", help="only show cameras and current settings")
    ap.add_argument("--tune", action="store_true",
                    help="try a range of exposures on the named cameras and recommend one each")
    ap.add_argument("--write", action="store_true", help="with --tune: save the recommendations to config")
    ap.add_argument("names", nargs="*", help="with --tune: camera names (default: all with a port)")
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
    if args.tune:
        return run_tune(cfg, devices, names, args.names, args.write)
    status = 0
    for port, dev in devices.items():
        name = names.get(port, "(unnamed)")
        settings = cfg["camera_settings"].get(name, {}) if name != "(unnamed)" else {}
        if settings and not args.show:
            have = supported_controls(dev)
            ctrls = ordered_controls(settings)
            skipped = [c for c in ctrls if have and c.split("=")[0] not in have]
            ctrls = [c for c in ctrls if c not in skipped]
            if skipped:
                print(f"{name}: this camera has no {', '.join(c.split('=')[0] for c in skipped)}; skipped")
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


def run_tune(cfg: dict, devices: dict, names: dict, wanted: list, write: bool) -> int:
    """--tune: sweep exposures per camera, print the best, optionally save it."""
    # A name can list several ports (one per laptop); tune the one that is plugged in here.
    by_name: dict = {}
    for p, n in names.items():
        if p in devices or n not in by_name:
            by_name[n] = p
    targets = wanted or sorted(by_name)
    status = 0
    print("Point each camera at the real scene (table, bowl, food) under the real light.")
    for name in targets:
        port = by_name.get(name)
        if port is None or port not in devices:
            print(f"{name}: not configured or not plugged in")
            status = 1
            continue
        try:
            results = tune(devices[port], name)
        except (RuntimeError, ImportError) as exc:
            print(f"{name}: {exc}")
            status = 1
            continue
        if not results:
            print(f"{name}: no frames read")
            status = 1
            continue
        best = pick_exposure(results)
        print(f"{name}: recommended exposure {best} ({results[best]['verdict']})")
        cfg.setdefault("camera_settings", {}).setdefault(name, {})["exposure"] = best
        subprocess.run(["v4l2-ctl", "-d", devices[port], "-c", f"exposure_time_absolute={best}"],
                       capture_output=True)
    if write and status == 0:
        save_config(cfg)
        print("Saved to config/elrobot.json. Commit it as a calibration commit, e.g.\n"
              "  chore(elrobot): record camera exposure measured <date>")
    elif write:
        print("NOT saved: a camera above failed. Fix it, or tune only the cameras that work, "
              "e.g. ./cli.sh cameras --tune gripper --write")
    else:
        print("Applied for now. Add --write to save, or edit config/elrobot.json -> camera_settings.")
    return status


if __name__ == "__main__":
    sys.exit(main())
