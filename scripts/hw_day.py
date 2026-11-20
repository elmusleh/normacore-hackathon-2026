#!/usr/bin/env python3
"""Hardware-day checklist and safe tools for the ElRobot. Run via `./cli.sh hw ...`.

Keeps progress in logs/hw_day_state.json so you can stop and resume.
Every command writes its own log under logs/ (see `./cli.sh logs`).

Motion commands (`jog`) need a typed confirmation. `stop` always works.
"""

import argparse
import datetime as dt
import json
import os
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from elrobot_log import LOG_DIR, setup_logging  # noqa: E402
from elrobot_hardware import (  # noqa: E402
    DEFAULT_MAX_ACCEL,
    ELROBOT_MOTOR_IDS,
    ElRobotHardwareSync,
    clamp_goal,
    DEFAULT_SAFETY_MARGIN_STEPS,
)

STATE_FILE = LOG_DIR / "hw_day_state.json"
STATION = os.environ.get("ELROBOT_STATION", "localhost")
BUS = os.environ.get("ELROBOT_BUS", "auto")
JOG_MAX_STEPS = 200          # about 17 degrees on a 4096-step encoder
JOG_DEFAULT_SPEED = 300
JOG_MAX_SPEED = 800          # same ceiling as the bridge default

# Each step: id, title, kind, text. kind "manual" needs a y/n answer,
# "auto" runs a command and passes on exit code 0, "check" passes when state says so.
STEPS = [
    {"id": 1, "title": "Power and cable", "kind": "manual",
     "text": "12 V / 4 A supply into the follower arm. Data-rated USB cable from the arm's\n"
             "    Waveshare bus servo driver (A) to this laptop. Keep one hand near the power switch."},
    {"id": 2, "title": "Start the Station", "kind": "manual",
     "text": "In a SEPARATE terminal run:  ./cli.sh station\n"
             "    Leave it running. Web console: http://localhost:8889"},
    {"id": 3, "title": "Preflight (read only)", "kind": "auto",
     "cmd": [sys.executable, "scripts/hardware_preflight.py", "--server", STATION, "--bus", BUS],
     "text": "Checks motors 1-8 are visible, calibrated and fault-free. Moves nothing."},
    {"id": 4, "title": "Calibrate if needed", "kind": "manual",
     "text": "Only if preflight showed UNCALIBRATED. In the Station console, move each joint\n"
             "    through its full travel when prompted. Then re-run step 3."},
    {"id": 5, "title": "Map motors to joints", "kind": "check",
     "text": "Jog each motor at low speed and record it:\n"
             "    ./cli.sh hw map <motor> <joint> <+/-direction> [note]\n"
             "    Joints are rev_motor_01..08 in the URDF; motor 8 is the gripper.\n"
             "    This step passes when all 8 motors are mapped."},
    {"id": 6, "title": "First small move", "kind": "manual",
     "text": "Move one joint away from the table, slowly:\n"
             "    ./cli.sh hw jog 2 100 --speed 300\n"
             "    Confirm it moved the expected joint and direction, then mark this done."},
    {"id": 7, "title": "Clearance pose", "kind": "manual",
     "text": "Move to a safe height above the table through joint targets. Cartesian moves\n"
             "    are NOT ready; see docs/elrobot_hardware_bridge.md, 'What is NOT ready'."},
]


# ---------------------------------------------------------------- state ----

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            logger_warn(f"state file is corrupt, starting fresh: {STATE_FILE}")
    return {"done": {}, "joint_map": {}}


def save_state(state: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(STATE_FILE)


def logger_warn(msg: str) -> None:
    import logging
    logging.getLogger("elrobot.hwday").warning(msg)


def step_done(step: dict, state: dict) -> bool:
    if step["kind"] == "check" and step["id"] == 5:
        return len(state["joint_map"]) == len(ELROBOT_MOTOR_IDS)
    return state["done"].get(str(step["id"]), False)


def next_step(state: dict):
    for s in STEPS:
        if not step_done(s, state):
            return s
    return None


# ------------------------------------------------------------- commands ----

def cmd_status(args, state):
    nxt = next_step(state)
    print("ElRobot hardware-day checklist\n")
    for s in STEPS:
        mark = "[x]" if step_done(s, state) else ("[>]" if s is nxt else "[ ]")
        print(f"  {mark} {s['id']}. {s['title']}")
    if nxt:
        print(f"\nNext: step {nxt['id']} - {nxt['title']}. Run:  ./cli.sh hw next")
    else:
        print("\nAll steps done. Keep ./cli.sh hw stop ready.")
    if state["joint_map"]:
        print("\nJoint map:")
        for mid in sorted(state["joint_map"], key=int):
            j = state["joint_map"][mid]
            note = f"  ({j['note']})" if j.get("note") else ""
            print(f"  motor {mid}: {j['joint']}  dir {j['direction']}{note}")
    return 0


def _find(step_id: int):
    for s in STEPS:
        if s["id"] == step_id:
            return s
    return None


def cmd_next(args, state):
    s = next_step(state)
    if s is None:
        print("All steps are done.")
        return 0
    return _do_step(s, state, log_name="hw-step")


def cmd_run(args, state):
    s = _find(args.step)
    if s is None:
        print(f"No step {args.step}. Valid: 1-{len(STEPS)}")
        return 2
    return _do_step(s, state, log_name="hw-step")


def _do_step(s, state, log_name):
    import logging
    log = logging.getLogger("elrobot.hwday")
    print(f"\nStep {s['id']}: {s['title']}\n    {s['text']}\n")
    log.info("step %d started: %s (%s)", s["id"], s["title"], s["kind"])
    if s["kind"] == "auto":
        import subprocess
        rc = subprocess.call(s["cmd"], cwd=ROOT)
        log.info("step %d command exit code %d", s["id"], rc)
        if rc == 0:
            state["done"][str(s["id"])] = True
            save_state(state)
            print(f"\nStep {s['id']} passed.")
            return 0
        print(f"\nStep {s['id']} FAILED (exit {rc}). Fix the problem above, then run ./cli.sh hw run {s['id']} again.")
        print(f"Full log: ./cli.sh logs")
        return rc
    if s["kind"] == "check":
        if step_done(s, state):
            print("Already satisfied.")
            return 0
        print(f"Not done yet: map all 8 motors first ({len(state['joint_map'])}/8 mapped).")
        return 1
    answer = input("Done with this step? [y/N] ").strip().lower()
    if answer == "y":
        state["done"][str(s["id"])] = True
        save_state(state)
        log.info("step %d marked done", s["id"])
        print(f"Marked step {s['id']} done.")
        return 0
    print("Left open.")
    return 0


def cmd_done(args, state):
    if _find(args.step) is None:
        print(f"No step {args.step}")
        return 2
    state["done"][str(args.step)] = not args.undo
    save_state(state)
    print(f"Step {args.step} marked {'open' if args.undo else 'done'}.")
    return 0


def cmd_map(args, state):
    if args.motor not in ELROBOT_MOTOR_IDS:
        print(f"Motor must be 1-8, got {args.motor}")
        return 2
    state["joint_map"][str(args.motor)] = {
        "joint": args.joint, "direction": args.direction, "note": args.note or "",
        "recorded": dt.datetime.now().isoformat(timespec="seconds"),
    }
    save_state(state)
    import logging
    logging.getLogger("elrobot.hwday").info("joint map: motor %d -> %s dir %s", args.motor, args.joint, args.direction)
    print(f"Mapped motor {args.motor} -> {args.joint} ({args.direction}). {len(state['joint_map'])}/8 mapped.")
    return 0


class StationDown(RuntimeError):
    """The Station is not reachable or has no bus. Message is for the operator."""


def _with_station(fn):
    hw = ElRobotHardwareSync(server=STATION, bus=BUS)
    try:
        try:
            hw.connect(timeout_s=10)
        except Exception as exc:  # noqa: BLE001 - turned into a clear operator message in main()
            raise StationDown(
                f"cannot use the Station at {STATION} ({exc}). Start it in another terminal with "
                "./cli.sh station, check the USB cable, then retry."
            ) from exc
        return fn(hw)
    finally:
        hw.close()


def cmd_motors(args, state):
    def go(hw):
        readings = hw.snapshot()
        print(f"{'ID':>3} {'present':>8} {'goal':>6} {'range':>12} {'torque':>7} {'status':>7} {'current':>8}  joint")
        for mid in ELROBOT_MOTOR_IDS:
            r = readings.get(mid)
            joint = state["joint_map"].get(str(mid), {}).get("joint", "-")
            if r is None:
                print(f"{mid:>3}  MISSING")
                continue
            print(f"{mid:>3} {r.present:>8} {r.goal:>6} {r.range_min:>5}..{r.range_max:<6} "
                  f"{'on' if r.torque_on else 'off':>7} {r.status:>#7x} {r.current:>8}  {joint}")
        return 0
    return _with_station(go)


def cmd_jog(args, state):
    import logging
    log = logging.getLogger("elrobot.hwday")
    if args.motor not in ELROBOT_MOTOR_IDS:
        print(f"Motor must be 1-8, got {args.motor}")
        return 2
    if abs(args.steps) > JOG_MAX_STEPS:
        print(f"Refusing {args.steps} steps: the limit for jog is {JOG_MAX_STEPS} (about 17 degrees).")
        return 2
    speed = min(args.speed, JOG_MAX_SPEED)

    def plan(hw):
        r = hw.snapshot().get(args.motor)
        if r is None:
            print(f"Motor {args.motor} is not on the bus. Run ./cli.sh hw run 3.")
            return 1
        if not r.calibrated:
            print(f"Motor {args.motor} is not calibrated ({r.range_min}..{r.range_max}). Calibrate in the Station console.")
            return 1
        if r.faulted:
            print(f"Motor {args.motor} reports fault 0x{r.status:02x}. Not moving.")
            return 1
        target = r.present + args.steps
        try:
            clamped, was_clamped = clamp_goal(target, r.range_min, r.range_max, DEFAULT_SAFETY_MARGIN_STEPS)
        except ValueError as exc:
            print(f"Refused: {exc}")
            return 1
        joint = state["joint_map"].get(str(args.motor), {}).get("joint", "UNMAPPED")
        print(f"\nMotor {args.motor} ({joint}): present {r.present} -> target {clamped}"
              f" ({clamped - r.present:+d} steps, speed {speed}, accel {DEFAULT_MAX_ACCEL})")
        if was_clamped:
            print(f"  NOTE: target was clamped from {target} to stay inside the calibrated range.")
        if joint == "UNMAPPED":
            print("  NOTE: this motor is not in the joint map yet.")
        if not args.yes:
            if not sys.stdin.isatty():
                print("Not a terminal, and --yes not given. Refusing to move.")
                return 1
            typed = input("Type MOVE to continue, anything else to cancel: ").strip()
            if typed != "MOVE":
                print("Cancelled. Nothing moved.")
                return 0
        log.info("jog confirmed: motor %d present=%d target=%d speed=%d", args.motor, r.present, clamped, speed)
        hw.move_motors({args.motor: target}, enable_motion=True, max_speed=speed, max_accel=DEFAULT_MAX_ACCEL)
        time.sleep(2.0)
        after = hw.snapshot().get(args.motor)
        if after:
            print(f"After move: present {after.present} (goal {clamped}), current {after.current}, status 0x{after.status:02x}")
            log.info("after jog: motor %d present=%d current=%d status=0x%02x",
                     args.motor, after.present, after.current, after.status)
        return 0
    return _with_station(plan)


def cmd_stop(args, state):
    import logging
    logging.getLogger("elrobot.hwday").warning("STOP requested: torque OFF on all ElRobot motors")

    def go(hw):
        hw.set_torque(list(ELROBOT_MOTOR_IDS), enable=False)
        print("Torque is OFF on motors 1-8. The arm will go limp; support it first.")
        return 0
    try:
        return _with_station(go)
    except Exception as exc:  # noqa: BLE001 - stop must report, never hide, failures
        print(f"STOP FAILED: {exc}")
        print("Use the Station console's stop, or cut power to the driver board.")
        return 1


def cmd_logs(args, state):
    latest = LOG_DIR / "hw-latest.log"
    if not latest.exists():
        print("No hardware log yet. Run any ./cli.sh hw command first.")
        return 1
    lines = latest.read_text(errors="replace").splitlines()
    print(f"--- {latest.resolve().name} (last {args.lines} lines) ---")
    print("\n".join(lines[-args.lines:]))
    return 0


def cmd_bundle(args, state):
    """Pack the latest logs, state, and config into one file to share when debugging."""
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = LOG_DIR / "bundles"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"hw-debug-{stamp}.tar.gz"
    # Newest run logs (not the -latest links), plus latest copies, plus state and config.
    # dereference=True stores file contents, so the bundle still works when unpacked elsewhere.
    run_logs = sorted((p for p in LOG_DIR.glob("hw-*.log") if not p.is_symlink()
                       and p.name != "hw-latest.log"))[-5:]
    picked = []
    with tarfile.open(out, "w:gz", dereference=True) as tar:
        for p in run_logs + [LOG_DIR / "hw-latest.log"]:
            if p.exists() and p.name not in picked:
                tar.add(p, arcname=p.name)
                picked.append(p.name)
        if STATE_FILE.exists():
            tar.add(STATE_FILE, arcname=STATE_FILE.name)
            picked.append(STATE_FILE.name)
        cfg = ROOT / "station.yaml"
        if cfg.exists():
            tar.add(cfg, arcname="station.yaml")
            picked.append("station.yaml")
    print(f"Bundle written: {out}")
    print("Contents: " + ", ".join(picked))
    print("Check the bundle before sharing: it contains logs and the Station config.")
    return 0


def cmd_reset(args, state):
    if not sys.stdin.isatty() and not args.yes:
        print("Not a terminal. Pass --yes to reset.")
        return 1
    if not args.yes and input("Clear all hardware-day progress and joint map? [y/N] ").strip().lower() != "y":
        print("Kept.")
        return 0
    save_state({"done": {}, "joint_map": {}})
    print("Progress cleared.")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="cli.sh hw", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--debug", action="store_true", help="show DEBUG output on the console too")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("status", help="show the checklist and joint map (default)")
    sub.add_parser("next", help="run or show the next open step")
    r = sub.add_parser("run", help="run a specific step")
    r.add_argument("step", type=int)
    d = sub.add_parser("done", help="mark a step done (or --undo)")
    d.add_argument("step", type=int)
    d.add_argument("--undo", action="store_true")
    m = sub.add_parser("map", help="record which joint a motor drives")
    m.add_argument("motor", type=int)
    m.add_argument("joint", help="e.g. rev_motor_02 or 'shoulder lift'")
    m.add_argument("direction", help="e.g. '+' or 'up'")
    m.add_argument("note", nargs="?", default="")
    sub.add_parser("motors", help="live read-only table of motors 1-8")
    j = sub.add_parser("jog", help="move one motor by N steps (confirmed)")
    j.add_argument("motor", type=int)
    j.add_argument("steps", type=int, help=f"relative steps, max +/-{JOG_MAX_STEPS}")
    j.add_argument("--speed", type=int, default=JOG_DEFAULT_SPEED)
    j.add_argument("--yes", action="store_true", help="skip the MOVE prompt (not recommended)")
    sub.add_parser("stop", help="torque OFF on all motors (always available)")
    lg = sub.add_parser("logs", help="show the last lines of the latest hardware log")
    lg.add_argument("--lines", type=int, default=60)
    sub.add_parser("bundle", help="pack logs, state and config for sharing")
    rs = sub.add_parser("reset", help="clear checklist progress and joint map")
    rs.add_argument("--yes", action="store_true")
    return p


COMMANDS = {
    "status": cmd_status, "next": cmd_next, "run": cmd_run, "done": cmd_done,
    "map": cmd_map, "motors": cmd_motors, "jog": cmd_jog, "stop": cmd_stop,
    "logs": cmd_logs, "bundle": cmd_bundle, "reset": cmd_reset,
}


HARDWARE_COMMANDS = {"run", "next", "jog", "stop", "motors"}


def main(argv=None) -> int:
    import logging
    parser = build_parser()
    args = parser.parse_args(argv)
    cmd = args.cmd or "status"
    # Every command logs to logs/hw-<time>.log (and hw-latest.log). The console stays quiet
    # for read-only commands and shows INFO for anything that talks to the arm.
    console_level = logging.DEBUG if args.debug else (
        logging.INFO if cmd in HARDWARE_COMMANDS else logging.WARNING)
    log_path = setup_logging("hw", debug=args.debug, argv=sys.argv, console_level=console_level)
    log = logging.getLogger("elrobot.hwday")
    log.debug("command: %s", cmd)
    state = load_state()
    try:
        return COMMANDS[cmd](args, state)
    except KeyboardInterrupt:
        print("\nInterrupted. Nothing further was sent.")
        return 130
    except StationDown as exc:
        print(f"ERROR: {exc}")
        log.debug("station down: %s", exc, exc_info=True)
        return 1
    except Exception as exc:  # noqa: BLE001 - last resort: short message, full trace in the log
        print(f"ERROR: {exc}")
        print(f"Full trace: ./cli.sh logs   (file: {log_path.name})")
        log.debug("unexpected failure in '%s': %r", cmd, exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
