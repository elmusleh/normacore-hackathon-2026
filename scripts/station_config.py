#!/usr/bin/env python3
"""Make sure the local station.yaml asks the cameras for HD frames.

station.yaml is gitignored, so every laptop has its own copy. The Station
writes it with `formats: []`, which makes the KD-USB cameras capture at
320x240. The AprilTag table frame and the grip skills need 1920x1080 frames
(`./cli.sh calib pixel U V --size 1920x1080`), so `./cli.sh station` and
`./cli.sh start` run this first.

What it does:
  - station.yaml missing: writes a working one with the HD camera list.
  - `usb-video.formats` empty or missing: adds the HD camera list and sets
    `resize_target` to 1080. The old file is kept as station.yaml.bak.
  - Anything else: leaves the file alone (you chose your own formats).

Set ELROBOT_KEEP_STATION_YAML=1 to skip it. See docs/mcp_server.md
("Frame size") and docs/FINDINGS.md for why the cameras end up at 1280x720
captured and 1920x1080 stored.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
STATION_YAML = ROOT / "station.yaml"

# First mode each camera can open wins. All cameras share one USB 2.0 link, so
# the KD-USB cameras usually fail 1920x1080 (libuvc -51) and take 1280x720.
HD_FORMATS = [
    {"format": "1920x1080@30fps,mjpeg"},
    {"format": "1280x720@30fps,mjpeg"},
    {"format": "640x480@30fps,mjpeg"},
    {"format": "640x480@maxfps,yuyv"},
]
HD_RESIZE_TARGET = 1080

DEFAULT_STATION_YAML: Dict[str, Any] = {
    "drivers": {
        "st3215": {"enabled": True, "current-threshold": 100, "deadband": 20},
        "vesc-trampa": {"enabled": True, "port-baud-rate": 115200},
        "system-info": True,
        "usb-video": {
            "enabled": True,
            "resize_target": HD_RESIZE_TARGET,
            "formats": HD_FORMATS,
            "frame-skip": 0,
        },
    },
    "inference": [{
        "queue-id": "inference/normvla",
        "shm": "/dev/shm/normvla",
        "shm-size-mb": 12,
        "format": "normvla",
        "st3215-bus": "auto",
        "update-interval": "100ms",
    }],
}


def ensure_hd_cameras(cfg: Dict[str, Any]) -> bool:
    """Add the HD camera list when no formats are set. Returns True if cfg changed."""
    drivers = cfg.setdefault("drivers", {}) or {}
    cfg["drivers"] = drivers
    usb = drivers.get("usb-video")
    if not isinstance(usb, dict):
        usb = {"enabled": True, "frame-skip": 0}
        drivers["usb-video"] = usb
    if usb.get("formats"):
        return False
    usb["formats"] = [dict(f) for f in HD_FORMATS]
    usb["resize_target"] = HD_RESIZE_TARGET
    usb.pop("resize-target", None)
    return True


def main(path: Path = STATION_YAML) -> int:
    if os.environ.get("ELROBOT_KEEP_STATION_YAML") == "1":
        return 0
    try:
        import yaml
    except ImportError:
        print("[!] PyYAML is not installed; cannot check station.yaml. "
              "Install it with: .venv/bin/pip install -r requirements.txt")
        return 1

    if not path.exists():
        path.write_text(yaml.safe_dump(DEFAULT_STATION_YAML, sort_keys=False))
        print(f"[OK] Wrote {path.name} with HD camera formats (1920x1080 stored frames).")
        return 0

    cfg = yaml.safe_load(path.read_text()) or {}
    if not ensure_hd_cameras(cfg):
        return 0
    shutil.copy2(path, path.with_name(path.name + ".bak"))
    path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    print(f"[OK] {path.name}: added HD camera formats and resize_target {HD_RESIZE_TARGET} "
          f"(old file kept as {path.name}.bak).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
