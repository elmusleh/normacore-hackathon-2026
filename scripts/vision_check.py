#!/usr/bin/env python3
"""Say whether real face/mouth detection (MediaPipe) is available.

Without MediaPipe and data/face_landmarker.task the person camera has no
trustworthy mouth detector: the OpenCV fallbacks find "mouths" on walls and
windows, so the dashboard, console and MCP tools show no mouth at all.
Fix with `./cli.sh setup-vision`.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from feeding_vision import mediapipe_status  # noqa: E402


def main() -> int:
    status = mediapipe_status()
    for key in ("python", "mediapipe", "face_model"):
        print(f"  {key:<11} {status[key]}")
    if status["ok"]:
        print("[OK] MediaPipe face detection is available.")
        return 0
    print(f"[!] {status['problem']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
