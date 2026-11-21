#!/usr/bin/env python3
"""One-command bench recovery and Master/Slave role manager for the team.

Prevents the three most common hackathon blockers:
  1. Leftover Station/Dashboard processes locking USB cameras
  2. Washed-out KD-USB exposure (runs manual exposure when Station is stopped)
  3. Stiff Leader (Master) arm caused by leftover torque ON

Usage:
  python3 scripts/reset_bench.py --status
  python3 scripts/reset_bench.py --relax-leader
  python3 scripts/reset_bench.py --swap-arms
  python3 scripts/reset_bench.py --set-arms <leader_serial> <follower_serial>
  python3 scripts/reset_bench.py --clean-cameras   # stop Station, apply exposure, ready for ./cli.sh start
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from elrobot_config import load_config, save_config  # noqa: E402


def show_status() -> None:
    cfg = load_config()
    st = cfg.get("station", {})
    cams = cfg.get("cameras", {})
    print("=== ElRobot Bench Configuration (config/elrobot.json) ===")
    print(f"  Follower (Slave / 12V): {st.get('bus', '(unset)')}")
    print(f"  Leader   (Master / 5V): {st.get('leader_bus', '(unset)')}")
    print(f"  Cameras:                {cams}")
    procs = subprocess.run(
        ["pgrep", "-af", "bin/station|digital_twin_server.py"],
        capture_output=True,
        text=True,
    )
    lines = [l for l in procs.stdout.splitlines() if "pgrep" not in l]
    print(f"  Running daemons:        {len(lines)}")
    for line in lines:
        print(f"    - {line}")


def set_arms(leader: str, follower: str) -> None:
    cfg = load_config()
    cfg.setdefault("station", {})
    cfg["station"]["leader_bus"] = leader
    cfg["station"]["bus"] = follower
    save_config(cfg)
    print(f"Updated config/elrobot.json: Leader (Master)={leader}, Follower (Slave)={follower}")


def swap_arms() -> None:
    cfg = load_config()
    st = cfg.get("station", {})
    old_follower = st.get("bus", "5B61034962")
    old_leader = st.get("leader_bus", "5B61037051")
    set_arms(leader=old_follower, follower=old_leader)


def relax_leader() -> int:
    cfg = load_config()
    leader = cfg.get("station", {}).get("leader_bus", "5B61037051")
    print(f"Disabling torque on Leader (Master) arm {leader}...")
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "hw_day.py"), "--bus", leader, "torque", "off"],
        cwd=str(ROOT),
    )
    return res.returncode


def clean_cameras() -> int:
    print("Stopping any running Station / Mission Control processes...")
    subprocess.run(["pkill", "-f", "bin/station"], capture_output=True)
    subprocess.run(["pkill", "-f", "digital_twin_server.py"], capture_output=True)
    time.sleep(1.0)
    print("Applying manual camera exposure via ./cli.sh cameras...")
    res = subprocess.run([str(ROOT / "cli.sh"), "cameras"], cwd=str(ROOT))
    print("\nIf 'table' or 'gripper' says NOT PLUGGED IN, unplug & replug the USB hub once and re-run:")
    print("  ./cli.sh cameras && ./cli.sh start")
    return res.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Team bench reset & Master/Slave role manager")
    parser.add_argument("--status", action="store_true", help="Show current roles, cameras, and running daemons")
    parser.add_argument("--relax-leader", action="store_true", help="Turn torque OFF on the Leader (Master) arm")
    parser.add_argument("--swap-arms", action="store_true", help="Swap Master (Leader) and Slave (Follower) serials")
    parser.add_argument("--set-arms", nargs=2, metavar=("LEADER", "FOLLOWER"), help="Set Leader and Follower serials")
    parser.add_argument("--clean-cameras", action="store_true", help="Stop leftover daemons and apply camera exposure")
    args = parser.parse_args()

    if not any([args.status, args.relax_leader, args.swap_arms, args.set_arms, args.clean_cameras]):
        # Default quick reset (no arguments needed):
        # 1. Show current bench config & daemons
        # 2. If Station is running, relax Leader torque; otherwise apply manual camera exposure
        show_status()
        procs = subprocess.run(["pgrep", "-f", "bin/station"], capture_output=True)
        if procs.returncode == 0:
            print("\nStation is running -> ensuring Leader (Master) torque is OFF...")
            return relax_leader()
        print("\nStation is stopped -> applying manual camera exposure...")
        return clean_cameras()

    if args.set_arms:
        set_arms(args.set_arms[0], args.set_arms[1])
    if args.swap_arms:
        swap_arms()
    if args.relax_leader:
        rc = relax_leader()
        if rc != 0:
            return rc
    if args.clean_cameras:
        rc = clean_cameras()
        if rc != 0:
            return rc
    if args.status:
        show_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
