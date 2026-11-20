#!/usr/bin/env python3
"""Hardware-day tool for the ElRobot. Run via `./cli.sh hw ...`.

Where things live:
  config/elrobot.json     joint map, current thresholds, workspace limits (commit after hardware day)
  config/waypoints.json   named joint poses from `hw teach` (commit after hardware day)
  data/hw_day_state.json  checklist progress on this machine (local, gitignored)
  logs/                   one log per run; `./cli.sh logs`, `./cli.sh hw bundle`

Every motion needs you to type MOVE. `stop` always works.
"""

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from elrobot_config import (  # noqa: E402
    CONFIG_FILE,
    ROOT as CFG_ROOT,
    STATE_FILE,
    WAYPOINTS_FILE,
    current_threshold_for,
    describe_joint_map,
    load_config,
    load_state,
    load_waypoints,
    save_config,
    save_state,
    save_waypoints,
)
from elrobot_hardware import (  # noqa: E402
    DEFAULT_MAX_ACCEL,
    DEFAULT_SAFETY_MARGIN_STEPS,
    ELROBOT_MOTOR_IDS,
    ElRobotHardwareSync,
    clamp_goal,
    plan_goto,
)
from elrobot_log import LOG_DIR, setup_logging  # noqa: E402

import logging  # noqa: E402

MOTORS = list(ELROBOT_MOTOR_IDS)
JOG_MAX_STEPS = 200          # about 17 degrees on a 4096-step encoder
JOG_DEFAULT_SPEED = 300
JOG_MAX_SPEED = 800
GOTO_MAX_DELTA = 600         # per motor, unless --allow-large
GOTO_DEFAULT_SPEED = 300
IDENT_NUDGE = 30             # about 2.6 degrees: small enough to be safe, big enough to see
IDENT_SPEED = 150
PROBE_STEPS = 60
PROBE_SPEED = 150
WAYPOINT_NAME = re.compile(r"^[a-z0-9_-]{1,40}$")

log = logging.getLogger("elrobot.hwday")

STEPS = [
    {"id": 1, "title": "Power and cable", "kind": "manual",
     "text": "12 V / 4 A supply into the follower arm. Data-rated USB cable from the Waveshare\n"
             "    bus servo driver (A) to this laptop. Keep one hand near the power switch."},
    {"id": 2, "title": "Start the Station", "kind": "manual",
     "text": "In a SEPARATE terminal run:  ./cli.sh station   (leave it running)\n"
             "    Web console: http://localhost:8889"},
    {"id": 3, "title": "Preflight (read only)", "kind": "auto", "cmd": "preflight",
     "text": "Checks motors 1-8 are visible, calibrated and fault-free. Moves nothing."},
    {"id": 4, "title": "Calibrate if needed", "kind": "manual",
     "text": "Only if preflight showed UNCALIBRATED: in the Station console move each joint through\n"
             "    its full travel. Then run step 3 again."},
    {"id": 5, "title": "Identify motors to joints", "kind": "check",
     "check": lambda cfg, st: len(cfg["joint_map"]) == len(MOTORS),
     "text": "./cli.sh hw identify\n"
             "    Nudges each motor 30 steps, then back. You say which joint moved and in what\n"
             "    direction. Passes when all 8 motors are mapped."},
    {"id": 6, "title": "Torque on (hold current pose)", "kind": "manual",
     "text": "./cli.sh hw torque on\n"
             "    Holds the arm where it is. Nothing moves until you command it."},
    {"id": 7, "title": "First small move", "kind": "manual",
     "text": "./cli.sh hw jog 2 60 --speed 200\n"
             "    Check the joint and direction match the joint map. Then: ./cli.sh hw done 7"},
    {"id": 8, "title": "Probe current on a small move", "kind": "manual",
     "text": "./cli.sh hw probe-current 2\n"
             "    Records peak current; offers to save a threshold. Do this before any gripper\n"
             "    or object test."},
    {"id": 9, "title": "Teach the home pose", "kind": "check",
     "check": lambda cfg, st: "home" in load_waypoints(),
     "text": "Put the arm in a safe, known pose (gripper open, above the table).\n"
             "    ./cli.sh hw teach home     Passes when the 'home' waypoint exists."},
    {"id": 10, "title": "Round trip to home", "kind": "manual",
     "text": "./cli.sh hw goto home  (move somewhere else first with jog, then come back)\n"
             "    Check the arm reaches home without hitting anything. Then: ./cli.sh hw done 10"},
    {"id": 11, "title": "Measure the workspace", "kind": "manual",
     "text": "Measure the table with a tape measure. Edit config/elrobot.json 'workspace' and set\n"
             "    \"measured\": true. Run ./cli.sh hw workspace to check the values."},
]


# ------------------------------------------------------------ helpers ----

class StationDown(RuntimeError):
    """The Station is not reachable or has no bus. The message is for the operator."""


def _station(cfg):
    return os.environ.get("ELROBOT_STATION", cfg["station"]["server"]), os.environ.get(
        "ELROBOT_BUS", cfg["station"]["bus"])


def _with_station(fn):
    cfg = load_config()
    server, bus = _station(cfg)
    hw = ElRobotHardwareSync(server=server, bus=bus)
    try:
        try:
            hw.connect(timeout_s=10)
        except Exception as exc:  # noqa: BLE001 - turned into a clear message in main()
            raise StationDown(
                f"cannot use the Station at {server} ({exc}). Start it with ./cli.sh station in another "
                "terminal, check the USB cable, then retry."
            ) from exc
        return fn(hw, cfg)
    finally:
        hw.close()


def _confirm_motion(yes: bool, summary: str) -> bool:
    if yes:
        print("(--yes: skipping the MOVE prompt)")
        return True
    if not sys.stdin.isatty():
        print("Not a terminal and --yes not given. Refusing to move.")
        return False
    print(summary)
    return input("Type MOVE to continue, anything else to cancel: ").strip() == "MOVE"


def _require_torque(readings, motors) -> bool:
    off = [m for m in motors if m in readings and not readings[m].torque_on]
    if off:
        print(f"Torque is OFF on motors {off}. Run ./cli.sh hw torque on first. Nothing moved.")
        return False
    return True


def _joint(cfg, motor) -> str:
    return cfg["joint_map"].get(str(motor), {}).get("joint", "UNMAPPED")


# ----------------------------------------------------------- checklist ----

def _next_open(cfg, state):
    for s in STEPS:
        if not _step_done(s, cfg, state):
            return s
    return None


def _step_done(s, cfg, state) -> bool:
    if "check" in s:
        return bool(s["check"](cfg, state))
    return bool(state["done"].get(str(s["id"])))


def cmd_status(args, cfg, state):
    nxt = _next_open(cfg, state)
    print("ElRobot hardware-day checklist\n")
    for s in STEPS:
        done = _step_done(s, cfg, state)
        mark = "[x]" if done else ("[>]" if s is nxt else "[ ]")
        print(f"  {mark} {s['id']:>2}. {s['title']}")
    print(f"\nNext: {('step ' + str(nxt['id']) + ' - ' + nxt['title'] + '  (./cli.sh hw next)') if nxt else 'all done'}")
    lines = describe_joint_map(cfg)
    print("\nJoint map (config/elrobot.json):")
    print("  " + "\n  ".join(lines) if lines else "  (empty: run ./cli.sh hw identify)")
    wps = sorted(load_waypoints())
    print("\nWaypoints (config/waypoints.json): " + (", ".join(wps) if wps else "(none yet)"))
    ws = cfg["workspace"]
    print(f"\nWorkspace measured: {'yes' if ws.get('measured') else 'NO (using defaults)'}")
    return 0


def cmd_next(args, cfg, state):
    s = _next_open(cfg, state)
    if s is None:
        print("All steps are done.")
        return 0
    return _do_step(s, cfg, state)


def cmd_run(args, cfg, state):
    s = next((x for x in STEPS if x["id"] == args.step), None)
    if s is None:
        print(f"No step {args.step}. Valid: 1-{len(STEPS)}")
        return 2
    return _do_step(s, cfg, state)


def _do_step(s, cfg, state):
    print(f"\nStep {s['id']}: {s['title']}\n    {s['text']}\n")
    log.info("step %d started: %s (%s)", s["id"], s["title"], s["kind"])
    if s["kind"] == "auto":
        server, bus = _station(cfg)
        cmd = [sys.executable, "scripts/hardware_preflight.py", "--server", server, "--bus", bus]
        rc = subprocess.call(cmd, cwd=ROOT)
        log.info("step %d command exit code %d", s["id"], rc)
        if rc == 0:
            state["done"][str(s["id"])] = True
            save_state(state)
            print(f"\nStep {s['id']} passed.")
            return 0
        print(f"\nStep {s['id']} FAILED (exit {rc}). Fix the problem above, then: ./cli.sh hw run {s['id']}")
        print("Details: ./cli.sh logs")
        return rc
    if s["kind"] == "check":
        if _step_done(s, cfg, state):
            print("Already satisfied.")
            return 0
        print("Not done yet. Follow the instructions above; this step passes automatically.")
        return 1
    if sys.stdin.isatty():
        answer = input("Done with this step? [y/N] ").strip().lower()
    else:
        print("Not a terminal: mark it with ./cli.sh hw done " + str(s["id"]))
        return 0
    if answer == "y":
        state["done"][str(s["id"])] = True
        save_state(state)
        log.info("step %d marked done", s["id"])
        print(f"Marked step {s['id']} done.")
    else:
        print("Left open.")
    return 0


def cmd_done(args, cfg, state):
    if not any(x["id"] == args.step for x in STEPS):
        print(f"No step {args.step}")
        return 2
    state["done"][str(args.step)] = not args.undo
    save_state(state)
    print(f"Step {args.step} marked {'open' if args.undo else 'done'}.")
    return 0


def cmd_reset(args, cfg, state):
    if not args.yes:
        if not sys.stdin.isatty() or input("Clear checklist progress? (joint map and waypoints are kept) [y/N] ").strip().lower() != "y":
            print("Kept.")
            return 0
    save_state({"done": {}})
    print("Checklist progress cleared. Joint map and waypoints are untouched.")
    return 0


# -------------------------------------------------------------- arm -------

def cmd_motors(args, cfg, state):
    def go(hw, cfg):
        readings = hw.snapshot()
        print(f"{'ID':>3} {'present':>8} {'goal':>6} {'range':>13} {'torque':>7} {'status':>7} {'current':>8}  joint")
        for mid in MOTORS:
            r = readings.get(mid)
            if r is None:
                print(f"{mid:>3}  MISSING")
                continue
            print(f"{mid:>3} {r.present:>8} {r.goal:>6} {r.range_min:>5}..{r.range_max:<6} "
                  f"{'on' if r.torque_on else 'off':>7} {r.status:>#7x} {r.current:>8}  {_joint(cfg, mid)}")
        return 0
    return _with_station(go)


def cmd_torque(args, cfg, state):
    if args.state == "on":
        def go(hw, cfg):
            hw.torque_on_hold(MOTORS)
            print("Torque ON for motors 1-8, holding the current pose. Nothing else will move.")
            return 0
        return _with_station(go)
    return cmd_stop(args, cfg, state)


def cmd_stop(args, cfg, state):
    def go(hw, cfg):
        hw.set_torque(MOTORS, enable=False)
        print("Torque is OFF on motors 1-8. The arm will go limp: support it first.")
        return 0
    log.warning("STOP requested: torque OFF on all ElRobot motors")
    try:
        return _with_station(go)
    except StationDown as exc:
        print(f"STOP FAILED: {exc}")
        print("Use the Station console's stop, or cut power to the driver board.")
        return 1


def cmd_map(args, cfg, state):
    if args.motor not in MOTORS:
        print(f"Motor must be 1-8, got {args.motor}")
        return 2
    cfg["joint_map"][str(args.motor)] = {
        "joint": args.joint, "direction": args.direction, "note": args.note or "",
        "recorded": dt.datetime.now().isoformat(timespec="seconds"),
    }
    save_config(cfg)
    print(f"Mapped motor {args.motor} -> {args.joint} ({args.direction}). {len(cfg['joint_map'])}/8 mapped.")
    return 0


def cmd_identify(args, cfg, state):
    """Nudge each motor a little, then back, and record which joint moved."""
    motors = args.motors or MOTORS
    if not sys.stdin.isatty():
        print("identify asks questions, so it needs an interactive terminal. Run it directly.")
        return 1

    def go(hw, cfg):
        for m in motors:
            readings = hw.snapshot()
            r = readings.get(m)
            if r is None:
                print(f"Motor {m} is not on the bus; skipping.")
                continue
            if not _require_torque(readings, [m]):
                return 1
            print(f"\nMotor {m}: nudge +{IDENT_NUDGE} steps, then back. Watch the arm.")
            answer = input("  Type MOVE to nudge, s to skip, q to quit: ").strip()
            if answer == "q":
                break
            if answer != "MOVE":
                print("  Skipped.")
                continue
            start = r.present
            hw.move_and_watch({m: start + IDENT_NUDGE}, enable_motion=True,
                              max_speed=IDENT_SPEED, max_accel=DEFAULT_MAX_ACCEL,
                              thresholds={m: current_threshold_for(cfg, m)})
            time.sleep(0.5)
            moved = hw.snapshot()[m].present - start
            print(f"  encoder moved {moved:+d} steps")
            if moved == 0:
                print("  It did not move. Check torque and the cable. Not recording this motor.")
                continue
            hw.move_and_watch({m: start}, enable_motion=True,
                              max_speed=IDENT_SPEED, max_accel=DEFAULT_MAX_ACCEL,
                              thresholds={m: current_threshold_for(cfg, m)})
            joint = input("  Which joint moved? (e.g. shoulder_lift, base; blank to skip): ").strip()
            if not joint:
                print("  Not recorded.")
                continue
            physical = input("  Which way did it go, in plain words? (e.g. up, left, close): ").strip() or "unspecified"
            cfg["joint_map"][str(m)] = {
                "joint": joint,
                "direction": physical,
                "note": f"+{IDENT_NUDGE} steps moved the joint {moved:+d} encoder steps",
                "recorded": dt.datetime.now().isoformat(timespec="seconds"),
            }
            save_config(cfg)
            log.info("identified motor %d -> %s (%s), moved %+d", m, joint, physical, moved)
            print(f"  Recorded. {len(cfg['joint_map'])}/8 mapped.")
        return 0
    return _with_station(go)


def cmd_jog(args, cfg, state):
    if args.motor not in MOTORS:
        print(f"Motor must be 1-8, got {args.motor}")
        return 2
    if abs(args.steps) > JOG_MAX_STEPS:
        print(f"Refusing {args.steps} steps: the jog limit is {JOG_MAX_STEPS} (about 17 degrees).")
        return 2
    speed = min(args.speed, JOG_MAX_SPEED)

    def go(hw, cfg):
        readings = hw.snapshot()
        r = readings.get(args.motor)
        if r is None:
            print(f"Motor {args.motor} is not on the bus. Run ./cli.sh hw run 3.")
            return 1
        if not _require_torque(readings, [args.motor]):
            return 1
        if not r.calibrated:
            print(f"Motor {args.motor} is not calibrated ({r.range_min}..{r.range_max}). Calibrate in the Station console.")
            return 1
        if r.faulted:
            print(f"Motor {args.motor} reports fault 0x{r.status:02x}. Not moving.")
            return 1
        target = r.present + args.steps
        try:
            goal, clamped = clamp_goal(target, r.range_min, r.range_max, DEFAULT_SAFETY_MARGIN_STEPS)
        except ValueError as exc:
            print(f"Refused: {exc}")
            return 1
        summary = (f"\nMotor {args.motor} ({_joint(cfg, args.motor)}): present {r.present} -> target {goal} "
                   f"({goal - r.present:+d} steps, speed {speed})")
        if clamped:
            summary += f"\n  NOTE: clamped from {target} to stay inside the calibrated range."
        print(summary)
        if not _confirm_motion(args.yes, ""):
            print("Cancelled. Nothing moved.")
            return 0
        status = hw.move_and_watch({args.motor: goal}, enable_motion=True, max_speed=speed,
                                   max_accel=DEFAULT_MAX_ACCEL,
                                   thresholds={args.motor: current_threshold_for(cfg, args.motor)})
        after = hw.snapshot().get(args.motor)
        print(f"Result: {status.get(args.motor)}")
        if after:
            print(f"After: present {after.present} (goal {goal}), current {after.current}, status 0x{after.status:02x}")
        return 0 if status.get(args.motor) == "reached" else 1
    return _with_station(go)


def cmd_probe_current(args, cfg, state):
    """Make a small move with overload protection off and report the peak current."""
    m = args.motor
    if m not in MOTORS:
        print(f"Motor must be 1-8, got {m}")
        return 2

    def go(hw, cfg):
        readings = hw.snapshot()
        r = readings.get(m)
        if r is None or not _require_torque(readings, [m]):
            return 1
        if not r.calibrated or r.faulted:
            print("Motor is uncalibrated or faulted. Fix that first.")
            return 1
        target = r.present + args.steps
        try:
            goal, _ = clamp_goal(target, r.range_min, r.range_max, DEFAULT_SAFETY_MARGIN_STEPS)
        except ValueError as exc:
            print(f"Refused: {exc}")
            return 1
        if not _confirm_motion(args.yes, f"\nProbe: motor {m} out {args.steps:+d} steps at speed {PROBE_SPEED}, then back."):
            print("Cancelled.")
            return 0
        hw.move_and_watch({m: goal}, enable_motion=True, max_speed=PROBE_SPEED,
                          max_accel=DEFAULT_MAX_ACCEL, thresholds={m: 0})
        out_peak = hw.last_peaks.get(m, 0)
        hw.move_and_watch({m: r.present}, enable_motion=True, max_speed=PROBE_SPEED,
                          max_accel=DEFAULT_MAX_ACCEL, thresholds={m: 0})
        back_peak = hw.last_peaks.get(m, 0)
        peak = max(out_peak, back_peak)
        suggested = max(current_threshold_for(cfg, m), 2 * peak) if peak else None
        print(f"Peak current: out {out_peak}, back {back_peak} (raw units). Current threshold: "
              f"{current_threshold_for(cfg, m)}.")
        if peak == 0:
            print("No current was reported. Keep the threshold as is and check the Station's inference data.")
            log.warning("probe-current: no current readings for motor %d", m)
            return 1
        print(f"Suggested threshold for motor {m}: {suggested} (2 x peak, at least the current threshold).")
        if sys.stdin.isatty() and input("Save it to config/elrobot.json? [y/N] ").strip().lower() == "y":
            cfg["current_threshold"][str(m)] = suggested
            save_config(cfg)
            print("Saved.")
        else:
            print("Not saved.")
        return 0
    return _with_station(go)


def cmd_teach(args, cfg, state):
    name = args.name
    if not WAYPOINT_NAME.match(name):
        print("Waypoint names: lowercase letters, digits, - or _, up to 40 characters.")
        return 2

    def go(hw, cfg):
        readings = hw.snapshot()
        missing = [m for m in MOTORS if m not in readings]
        if missing:
            print(f"Cannot teach: motors {missing} not visible.")
            return 1
        points = load_waypoints()
        if name in points and not args.yes:
            if not sys.stdin.isatty() or input(f"Waypoint '{name}' exists. Overwrite? [y/N] ").strip().lower() != "y":
                print("Kept the old waypoint.")
                return 0
        points[name] = {str(m): readings[m].present for m in MOTORS}
        save_waypoints(points)
        print(f"Saved waypoint '{name}':")
        for m in MOTORS:
            print(f"  motor {m} ({_joint(cfg, m)}): {readings[m].present}")
        return 0
    return _with_station(go)


def cmd_waypoints(args, cfg, state):
    points = load_waypoints()
    if not points:
        print("No waypoints yet. Teach one with: ./cli.sh hw teach <name>")
        return 0
    for name in sorted(points):
        vals = points[name]
        print(f"{name}: " + ", ".join(f"{k}={v}" for k, v in sorted(vals.items(), key=lambda kv: int(kv[0]))))
    return 0


def cmd_goto(args, cfg, state):
    points = load_waypoints()
    if args.name not in points:
        print(f"No waypoint '{args.name}'. Known: {', '.join(sorted(points)) or '(none)'}")
        return 2
    raw = points[args.name]
    if sorted(raw, key=int) != [str(m) for m in MOTORS]:
        print(f"Waypoint '{args.name}' must list all 8 motors. Re-teach it.")
        return 2
    target = {int(k): int(v) for k, v in raw.items()}
    max_delta = 10**9 if args.allow_large else GOTO_MAX_DELTA
    speed = min(args.speed, JOG_MAX_SPEED)

    def go(hw, cfg):
        readings = hw.snapshot()
        present = {m: readings[m].present for m in MOTORS if m in readings}
        if not _require_torque(readings, MOTORS):
            return 1
        try:
            deltas = plan_goto(present, target, max_delta)
        except ValueError as exc:
            print(f"Refused: {exc}")
            return 1
        goals = {}
        print(f"\nGoto '{args.name}' at speed {speed}:")
        print(f"  {'motor':>5} {'joint':<14} {'present':>8} {'target':>7} {'delta':>7}")
        for m in MOTORS:
            r = readings[m]
            try:
                goal, clamped = clamp_goal(target[m], r.range_min, r.range_max, DEFAULT_SAFETY_MARGIN_STEPS)
            except ValueError as exc:
                print(f"Refused: motor {m}: {exc}")
                return 1
            goals[m] = goal
            note = "  (clamped)" if clamped else ""
            print(f"  {m:>5} {_joint(cfg, m):<14} {r.present:>8} {goal:>7} {deltas[m]:>+7}{note}")
        if not _confirm_motion(args.yes, "Check the path is clear of the table and objects."):
            print("Cancelled. Nothing moved.")
            return 0
        status = hw.move_and_watch(goals, enable_motion=True, max_speed=speed, max_accel=DEFAULT_MAX_ACCEL,
                                   thresholds={m: current_threshold_for(cfg, m) for m in MOTORS})
        final = hw.snapshot()
        off = {m: goals[m] - final[m].present for m in MOTORS if m in final and abs(goals[m] - final[m].present) > 12}
        print("Status: " + ", ".join(f"{m}={s}" for m, s in sorted(status.items())))
        if off:
            print(f"Not quite at target (steps): {off}. Check for an obstacle, then ./cli.sh logs.")
            return 1
        print(f"Arrived at '{args.name}'.")
        return 0 if all(s == "reached" for s in status.values()) else 1
    return _with_station(go)


def cmd_workspace(args, cfg, state):
    ws = cfg["workspace"]
    print("Workspace (mm, relative to arm base), from config/elrobot.json:")
    for k, v in ws.items():
        if k != "measured":
            print(f"  {k:<18} {v}")
    print(f"  measured           {ws.get('measured')}")
    if not ws.get("measured"):
        print("\nThese are the old defaults, not measured. See docs/elrobot_hardware_bridge.md, 'Measure the workspace'.")
    return 0


def cmd_logs(args, cfg, state):
    latest = LOG_DIR / "hw-latest.log"
    if not latest.exists():
        print("No hardware log yet. Run any ./cli.sh hw command first.")
        return 1
    lines = latest.read_text(errors="replace").splitlines()
    print(f"--- {latest.resolve().name} (last {args.lines} lines) ---")
    print("\n".join(lines[-args.lines:]))
    return 0


def cmd_bundle(args, cfg, state):
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = LOG_DIR / "bundles"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"hw-debug-{stamp}.tar.gz"
    run_logs = sorted(p for p in LOG_DIR.glob("hw-*.log") if not p.is_symlink() and p.name != "hw-latest.log")[-5:]
    picked = []
    with tarfile.open(out, "w:gz", dereference=True) as tar:
        for p in run_logs + [LOG_DIR / "hw-latest.log"]:
            if p.exists() and p.name not in picked:
                tar.add(p, arcname=p.name)
                picked.append(p.name)
        for p in (STATE_FILE, CONFIG_FILE, WAYPOINTS_FILE, CFG_ROOT / "station.yaml"):
            if p.exists():
                tar.add(p, arcname=p.name)
                picked.append(p.name)
    print(f"Bundle written: {out}")
    print("Contents: " + ", ".join(picked))
    print("Check the bundle before sharing: it contains logs and the Station config.")
    return 0


# ---------------------------------------------------------- parser ----

def build_parser():
    p = argparse.ArgumentParser(prog="cli.sh hw", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--debug", action="store_true", help="show DEBUG output on the console too")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("status", help="checklist, joint map, waypoints (default)")
    sub.add_parser("next", help="run or show the next open step")
    r = sub.add_parser("run", help="run a specific step")
    r.add_argument("step", type=int)
    d = sub.add_parser("done", help="mark a manual step done (or --undo)")
    d.add_argument("step", type=int)
    d.add_argument("--undo", action="store_true")
    rs = sub.add_parser("reset", help="clear checklist progress only")
    rs.add_argument("--yes", action="store_true")

    sub.add_parser("motors", help="live read-only table of motors 1-8")
    t = sub.add_parser("torque", help="torque on (hold pose) or off")
    t.add_argument("state", choices=["on", "off"])
    sub.add_parser("stop", help="torque OFF on all motors (always available)")

    m = sub.add_parser("map", help="record one motor's joint by hand")
    m.add_argument("motor", type=int)
    m.add_argument("joint")
    m.add_argument("direction")
    m.add_argument("note", nargs="?", default="")

    idn = sub.add_parser("identify", help="guided: nudge each motor and record its joint")
    idn.add_argument("motors", nargs="*", type=int, help="subset of motors (default all 8)")

    j = sub.add_parser("jog", help="move one motor by N steps (type MOVE to confirm)")
    j.add_argument("motor", type=int)
    j.add_argument("steps", type=int, help=f"relative steps, max +/-{JOG_MAX_STEPS}")
    j.add_argument("--speed", type=int, default=JOG_DEFAULT_SPEED)
    j.add_argument("--yes", action="store_true", help="skip the MOVE prompt (not recommended)")

    pc = sub.add_parser("probe-current", help="small move to measure peak current for a motor")
    pc.add_argument("motor", type=int)
    pc.add_argument("--steps", type=int, default=PROBE_STEPS)
    pc.add_argument("--yes", action="store_true")

    te = sub.add_parser("teach", help="save the current pose of all 8 motors as a waypoint")
    te.add_argument("name")
    te.add_argument("--yes", action="store_true", help="overwrite without asking")
    sub.add_parser("waypoints", help="list taught waypoints")
    g = sub.add_parser("goto", help="move all motors to a waypoint (type MOVE to confirm)")
    g.add_argument("name")
    g.add_argument("--speed", type=int, default=GOTO_DEFAULT_SPEED)
    g.add_argument("--allow-large", action="store_true", help=f"allow moves above {GOTO_MAX_DELTA} steps per motor")
    g.add_argument("--yes", action="store_true")

    sub.add_parser("workspace", help="show workspace limits and whether they were measured")
    lg = sub.add_parser("logs", help="last lines of the latest hardware log")
    lg.add_argument("--lines", type=int, default=60)
    sub.add_parser("bundle", help="pack logs, config and state for sharing")
    return p


COMMANDS = {
    "status": cmd_status, "next": cmd_next, "run": cmd_run, "done": cmd_done, "reset": cmd_reset,
    "motors": cmd_motors, "torque": cmd_torque, "stop": cmd_stop, "map": cmd_map,
    "identify": cmd_identify, "jog": cmd_jog, "probe-current": cmd_probe_current,
    "teach": cmd_teach, "waypoints": cmd_waypoints, "goto": cmd_goto,
    "workspace": cmd_workspace, "logs": cmd_logs, "bundle": cmd_bundle,
}
HARDWARE_COMMANDS = {"run", "next", "jog", "stop", "motors", "torque", "identify", "probe-current",
                     "teach", "goto", "map"}


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cmd = args.cmd or "status"
    console_level = logging.DEBUG if args.debug else (
        logging.INFO if cmd in HARDWARE_COMMANDS else logging.WARNING)
    log_path = setup_logging("hw", debug=args.debug, argv=sys.argv, console_level=console_level)
    log.debug("command: %s", cmd)
    cfg = load_config()
    state = load_state()
    try:
        return COMMANDS[cmd](args, cfg, state)
    except KeyboardInterrupt:
        print("\nInterrupted. Nothing further was sent.")
        return 130
    except StationDown as exc:
        print(f"ERROR: {exc}")
        log.debug("station down: %s", exc, exc_info=True)
        return 1
    except Exception as exc:  # noqa: BLE001 - short message here, full trace in the log
        print(f"ERROR: {exc}")
        print(f"Full trace: ./cli.sh logs   (file: {log_path.name})")
        log.debug("unexpected failure in '%s': %r", cmd, exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
