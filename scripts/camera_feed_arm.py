#!/usr/bin/env python3
"""Camera-Guided Assistive Feeding Controller for the ElRobot Slave Arm.

Uses the overhead tabletop camera (/dev/video4 by default) to identify:
  1. The bowl with grapes (or food bowl + spoon)
  2. The person's mouth target (stopping at a safe 5-10 cm standoff)

And drives the slave arm (5B61034962 / configured bus) accordingly.
By default, runs in safe dry-run / visual preview mode unless ELROBOT_ALLOW_MOTION=1
and --live-motion are explicitly passed by the hardware owner.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from feeding_vision import run_camera_feeding_cycle  # noqa: E402
from mcp_server import NormaCoreMCPServer  # noqa: E402


def _build_robot_tools():
    """Build RobotTools connected to Station if reachable, else None."""
    try:
        from robot_mcp_server import tools
        return tools
    except Exception:  # noqa: BLE001
        return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Camera-guided assistive feeding (grapes or spoon) for the ElRobot slave arm."
    )
    parser.add_argument(
        "--mode",
        choices=["grapes", "spoon"],
        default="grapes",
        help="Feeding mode: 'grapes' (pick grape from bowl -> mouth) or 'spoon' (pick spoon -> scoop bowl -> mouth)",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=4,
        help="V4L2 camera index for tabletop camera (default: 4 for /dev/video4)",
    )
    parser.add_argument(
        "--save-frame",
        default="sample_feeding_view.jpg",
        help="Path to save the annotated camera detection frame (default: sample_feeding_view.jpg)",
    )
    parser.add_argument(
        "--live-motion",
        action="store_true",
        help="Enable live slave arm motion (also sets ELROBOT_ALLOW_MOTION=1 for this run)",
    )
    args = parser.parse_args(argv)

    if args.live_motion:
        os.environ["ELROBOT_ALLOW_MOTION"] = "1"

    print("=" * 70)
    print("  NORMACORE ASSISTIVE FEEDING — CAMERA-TO-SLAVE ARM CONTROLLER")
    print("=" * 70)
    print(f"  Mode:            {args.mode.upper()}")
    print(f"  Tabletop Camera: /dev/video{args.camera}")
    print(f"  Motion Gate:     {'LIVE MOTION ENABLED' if os.environ.get('ELROBOT_ALLOW_MOTION') == '1' else 'SAFE DRY-RUN (set --live-motion to move physical arm)'}")
    print("=" * 70)

    mcp = NormaCoreMCPServer()
    rtools = _build_robot_tools()

    result = run_camera_feeding_cycle(
        mode=args.mode,
        mcp_server=mcp,
        robot_tools=rtools,
        preferred_camera=args.camera,
    )

    print(f"\n[+] Camera Source Used: {result['camera_source']}")
    det = result["detections"]
    if det.get("grape_bowl"):
        gb = det["grape_bowl"]
        print(f"[+] Bowl with Grapes:   pixel=({gb['u_px']}, {gb['v_px']}) -> table=({gb['x_mm']:.1f}, {gb['y_mm']:.1f}) mm (conf={gb['confidence']})")
    if det.get("spoon"):
        sp = det["spoon"]
        print(f"[+] Spoon Holder:       pixel=({sp['u_px']}, {sp['v_px']}) -> table=({sp['x_mm']:.1f}, {sp['y_mm']:.1f}) mm (conf={sp['confidence']})")
    if det.get("mouth"):
        mo = det["mouth"]
        print(f"[+] Person Mouth:       pixel=({mo['u_px']}, {mo['v_px']}) -> target=({mo['x_mm']:.1f}, {mo['y_mm']:.1f}) mm (standoff={mo['extra']['standoff_cm']} cm)")

    print("\n[+] Execution Trajectory Steps:")
    for idx, step in enumerate(result["steps"], 1):
        print(f"    {idx}. {step}")

    if result["hardware_plan"]:
        print("\n[+] Slave Arm Joint/Waypoint Plan:")
        for item in result["hardware_plan"]:
            print(f"    - {json.dumps(item)}")

    if args.save_frame and result.get("annotated_image_base64"):
        out_path = ROOT / args.save_frame
        out_path.write_bytes(base64.b64decode(result["annotated_image_base64"]))
        print(f"\n[OK] Saved annotated camera detection view to: {out_path}")

    print("\n" + "=" * 70)
    print(f"  STATUS: {result['status']}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
