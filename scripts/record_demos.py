#!/usr/bin/env python3
"""Record teleop demonstrations for ACT training. Reads only; teleop moves the arm.

Usage (via ./cli.sh demos):
  ./cli.sh demos record --skill pick --food grape      # one session, many episodes
  ./cli.sh demos list

Before recording: Station running, teleop ON (Station viewer: follower card -> leader serial),
web console and any Claude session that can move the arm CLOSED.

Each episode: put the food in a new spot, bring the arm to its start pose with the leader,
press Enter to start, do the task once (slow and smooth, same style every time), press Enter to
stop, then keep or discard it. See src/demo_recorder.py for what is stored.
"""

from __future__ import annotations

import argparse
import os
import select
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from demo_recorder import (  # noqa: E402
    NAME,
    Frame,
    episode_folder,
    list_episodes,
    record_episode,
    task_text,
)
from elrobot_camera import MAX_LOOKBACK, decode_frame  # noqa: E402
from elrobot_config import load_config  # noqa: E402
from elrobot_hardware import ElRobotHardwareSync  # noqa: E402
from elrobot_log import setup_logging  # noqa: E402
from robot_tools import RobotTools  # noqa: E402

DEMO_ROOT = ROOT / "data" / "demos"


def _connect(server: str, bus: str, what: str) -> ElRobotHardwareSync:
    hw = ElRobotHardwareSync(server=server, bus=bus)
    try:
        hw.connect(timeout_s=10)
    except Exception as exc:  # noqa: BLE001
        hw.close()
        raise SystemExit(f"ERROR: cannot read the {what} arm (bus {bus}) at {server}: {exc}\n"
                         "Is ./cli.sh station running and the arm plugged in and powered?")
    return hw


def _enter_pressed() -> bool:
    """True if a line was typed (non-blocking)."""
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if ready:
        sys.stdin.readline()
        return True
    return False


def cmd_record(args) -> int:
    if not NAME.match(args.skill) or (args.food and not NAME.match(args.food)):
        print("skill/food: lowercase letters, digits, - or _")
        return 2
    if not sys.stdin.isatty():
        print("record is interactive; run it in a terminal.")
        return 2
    cfg = load_config()
    server = os.environ.get("ELROBOT_STATION", cfg["station"]["server"])
    follower_bus = os.environ.get("ELROBOT_BUS", cfg["station"]["bus"])
    leader_bus = os.environ.get("ELROBOT_LEADER_BUS", cfg["station"].get("leader_bus", ""))
    if not leader_bus:
        print("No leader bus: set station.leader_bus in config/elrobot.json.")
        return 2
    cameras = [c for c in args.cameras.split(",") if c]

    follower = _connect(server, follower_bus, "follower")
    leader = _connect(server, leader_bus, "leader")
    try:
        tools = RobotTools(lambda: follower)
        queues = {}
        for cam in cameras:
            queue, err = tools.camera_queue(cam)
            if err:
                print(f"ERROR: camera {cam!r}: {err['error']}")
                return 1
            queues[cam] = queue

        def read_frames():
            out = {}
            for cam, queue in queues.items():
                out[cam] = None
                for back in range(1, MAX_LOOKBACK + 1):
                    data = follower.read_recent(queue, back=back, timeout_s=0.5)
                    if data is None:
                        break
                    fr = decode_frame(data)
                    if fr is not None:
                        out[cam] = Frame(fr.jpeg, fr.local_stamp_ns, fr.width, fr.height)
                        break
            return out

        ranges = {str(m): [r.range_min, r.range_max] for m, r in follower.snapshot().items()}
        task = task_text(args.skill, args.food)
        kept = len([e for e in list_episodes(DEMO_ROOT) if e["skill"] == args.skill and e["food"] == args.food])
        print(f"\nRecording '{task}' at {args.fps:g} per second, cameras {', '.join(cameras)}. "
              f"Already recorded: {kept}.")
        print("Teleop must be ON. This only reads; it sends nothing to either arm.\n")
        while True:
            answer = input(f"[{task} #{kept + 1}] Arm at start, food placed? Enter = start, q = quit: ").strip()
            if answer.lower() == "q":
                break
            print("  RECORDING... do the task, then press Enter to stop.")
            result = record_episode(follower.snapshot, leader.snapshot, read_frames, cameras, args.fps,
                                    _enter_pressed, max_seconds=args.max_seconds)
            writer = result["writer"]
            dur = writer.t[-1] if writer.t else 0.0
            print(f"  {result['ticks']} ticks in {dur:.1f} s ({result['achieved_fps']} per second, "
                  f"{result['late_ticks']} late), camera frames per second {writer.camera_fps()}")
            if result["achieved_fps"] < 0.8 * args.fps:
                print(f"  WARNING: only {result['achieved_fps']} per second; try --fps {int(result['achieved_fps'])}.")
            if not writer.action_changed():
                print("  WARNING: the follower's goal never changed. Was teleop on? Discard this one.")
            if len(writer) < 10:
                print("  Too short; discarded.")
                continue
            choice = input("  Keep it? [Y/n, or type a note to keep with it]: ").strip()
            if choice.lower() in ("n", "no"):
                print("  Discarded.")
                continue
            meta = {"skill": args.skill, "food": args.food, "task": task, "fps": args.fps,
                    "achieved_fps": result["achieved_fps"], "late_ticks": result["late_ticks"],
                    "cameras": queues, "follower_bus": follower_bus, "leader_bus": leader_bus,
                    "follower_ranges": ranges, "note": "" if choice.lower() in ("", "y", "yes") else choice}
            folder = writer.save(episode_folder(DEMO_ROOT, args.skill, args.food), meta)
            kept += 1
            print(f"  Saved {folder.relative_to(ROOT)}  ({kept} for '{task}')")
        return 0
    finally:
        follower.close()
        leader.close()


def cmd_list(args) -> int:
    eps = list_episodes(DEMO_ROOT)
    if not eps:
        print("No demonstrations recorded yet (data/demos/).")
        return 0
    counts = {}
    for e in eps:
        key = task_text(e["skill"] or "?", e["food"] or "")
        counts.setdefault(key, []).append(e["duration_s"] or 0)
    for key, durs in sorted(counts.items()):
        print(f"  {key:<20} {len(durs):>4} episodes, mean {sum(durs) / len(durs):.1f} s")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="cli.sh demos", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")
    r = sub.add_parser("record", help="record episodes of one skill (teleop on)")
    r.add_argument("--skill", required=True, help="e.g. pick")
    r.add_argument("--food", default="", help="e.g. grape, chocolate")
    r.add_argument("--fps", type=float, default=30.0)
    r.add_argument("--cameras", default="table,gripper", help="camera names from config/elrobot.json")
    r.add_argument("--max-seconds", type=float, default=90.0, help="an episode stops by itself after this")
    sub.add_parser("list", help="count recorded episodes per skill and food")
    args = p.parse_args(argv)
    setup_logging("demos", argv=sys.argv)
    if args.cmd == "record":
        return cmd_record(args)
    return cmd_list(args)


if __name__ == "__main__":
    sys.exit(main())
