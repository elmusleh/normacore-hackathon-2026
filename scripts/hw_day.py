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
GOTO_WARN_DELTA = 1500       # per motor; goto always moves, but flags larger moves in the plan
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
    speed = min(args.speed, JOG_MAX_SPEED)

    def go(hw, cfg):
        readings = hw.snapshot()
        present = {m: readings[m].present for m in MOTORS if m in readings}
        if not _require_torque(readings, MOTORS):
            return 1
        try:
            deltas = plan_goto(present, target, 10**9)  # no step cap: goto always goes to the waypoint
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
            if abs(deltas[m]) > GOTO_WARN_DELTA:
                note += "  LARGE MOVE"
            print(f"  {m:>5} {_joint(cfg, m):<14} {r.present:>8} {goal:>7} {deltas[m]:>+7}{note}")
        large = [m for m in MOTORS if abs(deltas[m]) > GOTO_WARN_DELTA]
        if large:
            print(f"  Warning: motors {large} move more than {GOTO_WARN_DELTA} steps. Watch the whole path.")
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


# ------------------------------------------------- demo (follower) ----

DEMO_DEFAULT_AMPLITUDE = 200   # steps either side of the start pose (about 17 degrees)
DEMO_MAX_AMPLITUDE = 600       # above this, use --full
DEMO_DEFAULT_SPEED = 250
GRIPPER_MOTOR = 8
TELEOP_WATCH_S = 1.0           # goal registers must stay still this long before the demo starts
TRACK_TOLERANCE = 12           # same tolerance move_and_watch uses for "reached"


def plan_demo(readings, motors, amplitude, full=False, gripper_full=True,
              margin=DEFAULT_SAFETY_MARGIN_STEPS):
    """Per-motor sweep: out one way, out the other way, back to the start pose.

    Returns [(motor, [goal, goal, start]), ...]. Goals are clamped into the calibrated
    range minus the margin. With full=True a joint goes to both calibrated limits.
    The gripper (motor 8) does its full travel unless gripper_full=False.
    Raises ValueError for a missing or uncalibrated motor.
    """
    plan = []
    for m in motors:
        r = readings.get(m)
        if r is None:
            raise ValueError(f"motor {m} is not on the bus")
        lo, hi = r.range_min + margin, r.range_max - margin
        if full or (m == GRIPPER_MOTOR and gripper_full):
            targets = [hi, lo]
        else:
            targets = [r.present + amplitude, r.present - amplitude]
        goals = [clamp_goal(t, r.range_min, r.range_max, margin)[0] for t in targets]
        start = clamp_goal(r.present, r.range_min, r.range_max, margin)[0]
        plan.append((m, goals + [start]))
    return plan


def plan_combined(readings, motors, amplitude, margin=DEFAULT_SAFETY_MARGIN_STEPS):
    """All motors together: +amplitude, -amplitude, start. Returns a list of goal dicts."""
    out, back, home = {}, {}, {}
    for m in motors:
        r = readings[m]
        out[m] = clamp_goal(r.present + amplitude, r.range_min, r.range_max, margin)[0]
        back[m] = clamp_goal(r.present - amplitude, r.range_min, r.range_max, margin)[0]
        home[m] = clamp_goal(r.present, r.range_min, r.range_max, margin)[0]
    return [out, back, home]


def _goals_drifting(before, after, motors, tolerance=5):
    """Motors whose goal register changed without us sending anything (teleop or another tool)."""
    return [m for m in motors if m in before and m in after and after[m].torque_on
            and abs(after[m].goal - before[m].goal) > tolerance]


def _demo_move(hw, cfg, goals, speed, label, report):
    t0 = time.monotonic()
    status = hw.move_and_watch(goals, enable_motion=True, max_speed=speed, max_accel=DEFAULT_MAX_ACCEL,
                               thresholds={m: current_threshold_for(cfg, m) for m in goals})
    took = time.monotonic() - t0
    time.sleep(0.2)
    final = hw.snapshot()
    peaks = dict(hw.last_peaks)
    for m, g in goals.items():
        r = final.get(m)
        err = (r.present - g) if r else None
        row = {"label": label, "motor": m, "goal": g, "status": status.get(m, "?"),
               "error": err, "peak_current": peaks.get(m, 0), "seconds": round(took, 1)}
        report.append(row)
        log.info("demo %s motor %d goal %d -> %s err=%s peak=%s %.1fs", label, m, g, row["status"],
                 err, row["peak_current"], took)
        flag = "" if row["status"] == "reached" and err is not None and abs(err) <= 2 * TRACK_TOLERANCE \
            else "   <-- CHECK"
        err_s = f"{err:+d}" if err is not None else "?"
        print(f"    {label:<14} m{m} goal {g:>5}  {row['status']:<8} err {err_s:>5}  "
              f"peak I {row['peak_current']:>4}  {took:4.1f}s{flag}")
    return status


def _print_demo_report(cfg, report):
    print("\n=== Follower demo summary ===")
    print(f"  {'motor':>5} {'joint':<14} {'moves':>5} {'ok':>3} {'worst err':>9} {'peak I':>7} {'thresh':>7}  verdict")
    bad = 0
    for m in sorted({row["motor"] for row in report}):
        rows = [row for row in report if row["motor"] == m]
        ok = sum(row["status"] == "reached" and row["error"] is not None
                 and abs(row["error"]) <= 2 * TRACK_TOLERANCE for row in rows)
        errs = [abs(row["error"]) for row in rows if row["error"] is not None]
        worst = max(errs) if errs else None
        peak = max(row["peak_current"] for row in rows)
        thr = current_threshold_for(cfg, m)
        if ok == len(rows):
            verdict = "OK"
            if peak > 0.8 * thr:
                verdict = "OK, but current near threshold (stiff joint or load?)"
        else:
            bad += 1
            kinds = sorted({row["status"] for row in rows if row["status"] != "reached"})
            if worst is not None and worst > 2 * TRACK_TOLERANCE:
                kinds.append(f"ended {worst} steps off target")
            verdict = "PROBLEM: " + ", ".join(kinds)
        print(f"  {m:>5} {_joint(cfg, m):<14} {len(rows):>5} {ok:>3} "
              f"{worst if worst is not None else '?':>9} {peak:>7} {thr:>7}  {verdict}")
    print()
    if bad:
        print("Hints: timeout = joint did not arrive (blocked, weak power, speed too low, or teleop fighting);\n"
              "       overload = current above threshold while stalled (obstacle or hard stop);\n"
              "       fault = servo status error (check `./cli.sh hw motors`, power supply, cable).")
    return bad


def cmd_demo(args, cfg, state):
    """Move every follower motor in turn, then all together, and report how each one did."""
    motors = args.motors or MOTORS
    if any(m not in MOTORS for m in motors):
        print(f"Motors must be 1-8, got {motors}")
        return 2
    if args.amplitude <= 0 or (args.amplitude > DEMO_MAX_AMPLITUDE and not args.full):
        print(f"Amplitude must be 1..{DEMO_MAX_AMPLITUDE} steps (use --full for the whole calibrated range).")
        return 2
    speed = min(args.speed, JOG_MAX_SPEED)

    def go(hw, cfg):
        readings = hw.snapshot()
        missing = [m for m in motors if m not in readings]
        if missing:
            print(f"Motors {missing} are not on the follower bus. Run ./cli.sh preflight.")
            return 1
        if not _require_torque(readings, motors):
            return 1
        faulted = {m: f"0x{readings[m].status:02x}" for m in motors if readings[m].faulted}
        if faulted:
            print(f"Motors report faults {faulted}. Not moving. Check power and ./cli.sh hw motors.")
            return 1
        try:
            plan = plan_demo(readings, motors, args.amplitude, full=args.full,
                             gripper_full=not args.no_gripper_full)
        except ValueError as exc:
            print(f"Refused: {exc}")
            return 1

        # Something else (Station teleop from the leader arm) may be writing goals.
        time.sleep(TELEOP_WATCH_S)
        drifting = _goals_drifting(readings, hw.snapshot(), motors)
        if drifting:
            print(f"Goal registers of motors {drifting} changed while nothing was sent from here.\n"
                  "Teleop (leader -> follower) is probably on. Turn it off in the Station viewer\n"
                  "(http://localhost:8889, follower bus card) and run the demo again.")
            return 1

        arm_motors = [m for m in motors if m != GRIPPER_MOTOR]
        print(f"\nFollower demo, speed {speed}, "
              f"{'FULL calibrated range' if args.full else f'+/-{args.amplitude} steps around the current pose'}:")
        print(f"  {'motor':>5} {'joint':<14} {'present':>7} {'range':>11}  sweep goals")
        for m, goals in plan:
            r = readings[m]
            print(f"  {m:>5} {_joint(cfg, m):<14} {r.present:>7} {r.range_min:>5}..{r.range_max:<5}  "
                  + " -> ".join(str(g) for g in goals))
        if not args.no_combined and len(arm_motors) > 1:
            print(f"  then motors {arm_motors} together +/-{args.amplitude // 2} steps and back.")
        warn = ("\nThe arm starts from where it is now: put it in a high, open pose first (e.g. "
                "./cli.sh hw goto clear).\nClear the table near the arm and empty the gripper. "
                "Ctrl-C holds the arm where it is.")
        if args.full:
            warn += "\n--full drives every joint to its calibrated limits: the arm WILL reach the table if it can."
        if not _confirm_motion(args.yes, warn):
            print("Cancelled. Nothing moved.")
            return 0

        report = []
        aborted = False
        try:
            for m, goals in plan:
                print(f"\n  Motor {m} ({_joint(cfg, m)})")
                full_sweep = args.full or (m == GRIPPER_MOTOR and not args.no_gripper_full)
                labels = ["to max", "to min", "back to start"] if full_sweep else \
                    ["sweep +", "sweep -", "back to start"]
                for goal, label in zip(goals, labels):
                    status = _demo_move(hw, cfg, {m: goal}, speed, label, report)
                    if status.get(m) == "fault":
                        print("  Servo fault: stopping the demo.")
                        aborted = True
                        break
                    if status.get(m) != "reached":
                        # Do not push further into an obstacle; go back to the start and move on.
                        print("  Did not arrive. Returning this motor to its start pose and moving on.")
                        _demo_move(hw, cfg, {m: goals[-1]}, speed, "recover", report)
                        break
                    if args.pause:
                        time.sleep(args.pause)
                if aborted:
                    break
                if args.step and sys.stdin.isatty() and \
                        input("  Enter for next motor, q to stop: ").strip().lower() == "q":
                    aborted = True
                    break

            if not aborted and not args.no_combined and len(arm_motors) > 1:
                print("\n  All arm motors together")
                fresh = hw.snapshot()
                for i, goals in enumerate(plan_combined(fresh, arm_motors, args.amplitude // 2)):
                    status = _demo_move(hw, cfg, goals, speed,
                                        ["together +", "together -", "together back"][i], report)
                    if any(s != "reached" for s in status.values()):
                        print("  Not every motor arrived: stopping the combined move.")
                        break
        except KeyboardInterrupt:
            hw.hold(motors)
            print("\nInterrupted: arm held where it is (torque stays ON). ./cli.sh hw stop makes it limp.")
            _print_demo_report(cfg, report)
            return 130

        bad = _print_demo_report(cfg, report)
        print("Full per-move log: ./cli.sh logs")
        return 1 if (bad or aborted) else 0
    return _with_station(go)


# --------------------------------------------- leader (master) monitor ----

def range_percent(present, range_min, range_max):
    """Position as a percentage of the calibrated range (0 = range_min, 100 = range_max)."""
    if range_max <= range_min:
        return None
    return 100.0 * (present - range_min) / (range_max - range_min)


class CoverageTracker:
    """Remembers, per motor, the lowest and highest position seen and the biggest frame-to-frame jump."""

    JUMP_WARN = 300  # steps between two frames ~0.1 s apart: a hand cannot do that, a glitch can

    def __init__(self):
        self.lo, self.hi, self.last, self.max_jump, self.frames = {}, {}, {}, {}, {}

    def update(self, readings):
        for m, r in readings.items():
            p = r.present
            if m in self.last:
                self.max_jump[m] = max(self.max_jump.get(m, 0), abs(p - self.last[m]))
            self.last[m] = p
            self.lo[m] = min(self.lo.get(m, p), p)
            self.hi[m] = max(self.hi.get(m, p), p)
            self.frames[m] = self.frames.get(m, 0) + 1

    def coverage(self, m, range_min, range_max):
        if m not in self.lo or range_max <= range_min:
            return 0.0
        return 100.0 * (self.hi[m] - self.lo[m]) / (range_max - range_min)


def leader_issues(m, r, tracker):
    """Short problem notes for one leader motor reading."""
    if r is None:
        return ["MISSING from bus"]
    issues = []
    if not r.calibrated:
        issues.append("uncalibrated")
    elif r.present < r.range_min - 50 or r.present > r.range_max + 50:
        issues.append("outside calibrated range")
    if r.faulted:
        issues.append(f"fault 0x{r.status:02x}")
    if r.torque_on:
        issues.append("torque ON (leader should be limp)")
    if tracker.max_jump.get(m, 0) > CoverageTracker.JUMP_WARN:
        issues.append(f"jumped {tracker.max_jump[m]} steps")
    return issues


def _fmt_pct(v):
    return "   -" if v is None else f"{v:5.0f}%"


def cmd_leader(args, cfg, state):
    """Live read-only view of the leader (master) arm next to the follower. Moves nothing."""
    cfg_station = cfg["station"]
    leader_bus = args.bus or os.environ.get("ELROBOT_LEADER_BUS") or cfg_station.get("leader_bus")
    if not leader_bus:
        print("No leader bus serial. Pass --bus <serial> or set station.leader_bus in config/elrobot.json.")
        return 2
    server = os.environ.get("ELROBOT_STATION", cfg_station["server"])
    leader = ElRobotHardwareSync(server=server, bus=leader_bus)
    follower = None
    try:
        try:
            leader.connect(timeout_s=10)
        except Exception as exc:  # noqa: BLE001
            raise StationDown(f"cannot read the leader bus {leader_bus} at {server} ({exc}). "
                              "Is the Station running and the leader's USB plugged in?") from exc
        if not args.no_follower:
            follower = ElRobotHardwareSync(server=server, bus=os.environ.get("ELROBOT_BUS", cfg_station["bus"]))
            try:
                follower.connect(timeout_s=10)
            except Exception as exc:  # noqa: BLE001 - leader view still useful on its own
                print(f"(follower not readable: {exc}; showing the leader only)")
                follower.close()
                follower = None

        tracker = CoverageTracker()
        deadline = time.monotonic() + args.seconds if args.seconds else None
        live = sys.stdout.isatty()
        print("Move each LEADER joint slowly through its whole travel. Ctrl-C to finish and see the summary.")
        time.sleep(1.0)
        lead, foll = {}, {}
        try:
            while deadline is None or time.monotonic() < deadline:
                lead = leader.snapshot()
                foll = follower.snapshot() if follower else {}
                tracker.update(lead)
                if live:
                    lines = ["\033[H\033[J" + f"Leader {leader_bus}"
                             + (f"  vs follower {follower._hw.bus_serial}" if follower else "")
                             + "   (Ctrl-C to stop)",
                             f"{'m':>2} {'leader':>6} {'pos':>6} {'seen':>11} {'cover':>6} "
                             f"{'follower':>8} {'pos':>6} {'diff':>6}  notes"]
                    for m in MOTORS:
                        r = lead.get(m)
                        f = foll.get(m)
                        lp = range_percent(r.present, r.range_min, r.range_max) if r else None
                        fp = range_percent(f.present, f.range_min, f.range_max) if f else None
                        diff = (fp - lp) if (lp is not None and fp is not None) else None
                        seen = f"{tracker.lo.get(m, 0)}..{tracker.hi.get(m, 0)}" if r else "-"
                        cov = tracker.coverage(m, r.range_min, r.range_max) if r else 0.0
                        notes = leader_issues(m, r, tracker)
                        lines.append(f"{m:>2} {r.present if r else '-':>6} {_fmt_pct(lp):>6} {seen:>11} "
                                     f"{cov:5.0f}% {f.present if f else '-':>8} {_fmt_pct(fp):>6} "
                                     f"{'   -' if diff is None else f'{diff:+5.0f}%':>6}  {'; '.join(notes)}")
                    print("\n".join(lines), flush=True)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            pass

        print("\n=== Leader summary ===")
        print(f"  {'m':>2} {'cover':>6} {'max jump':>8}  verdict")
        problems = 0
        for m in MOTORS:
            r = lead.get(m)
            cov = tracker.coverage(m, r.range_min, r.range_max) if r else 0.0
            issues = leader_issues(m, r, tracker)
            if cov < args.min_coverage:
                issues.append(f"only {cov:.0f}% of the range was seen (move it end to end)")
            problems += bool(issues)
            log.info("leader motor %d coverage %.0f%% jump %s issues %s", m, cov, tracker.max_jump.get(m), issues)
            print(f"  {m:>2} {cov:5.0f}% {tracker.max_jump.get(m, 0):>8}  {'OK' if not issues else '; '.join(issues)}")
        if foll:
            print("\nLeader vs follower now (% of each arm's calibrated range; teleop should keep these close):")
            for m in MOTORS:
                r, f = lead.get(m), foll.get(m)
                if r and f:
                    lp = range_percent(r.present, r.range_min, r.range_max)
                    fp = range_percent(f.present, f.range_min, f.range_max)
                    if lp is not None and fp is not None:
                        print(f"  m{m}: leader {lp:5.0f}%  follower {fp:5.0f}%  diff {fp - lp:+5.0f}%")
        return 1 if problems else 0
    finally:
        leader.close()
        if follower:
            follower.close()


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
    g.add_argument("--allow-large", action="store_true", help="accepted for old scripts; goto no longer has a step cap")
    g.add_argument("--yes", action="store_true")

    dm = sub.add_parser("demo", help="move each follower motor out, back and together; report per motor")
    dm.add_argument("motors", nargs="*", type=int, help="subset of motors (default all 8)")
    dm.add_argument("--amplitude", type=int, default=DEMO_DEFAULT_AMPLITUDE,
                    help=f"steps either side of the start pose (default {DEMO_DEFAULT_AMPLITUDE}, max {DEMO_MAX_AMPLITUDE})")
    dm.add_argument("--full", action="store_true", help="go to both calibrated limits of every joint (can hit the table)")
    dm.add_argument("--speed", type=int, default=DEMO_DEFAULT_SPEED)
    dm.add_argument("--pause", type=float, default=0.3, help="seconds between moves")
    dm.add_argument("--step", action="store_true", help="wait for Enter between motors")
    dm.add_argument("--no-combined", action="store_true", help="skip the all-motors-together move")
    dm.add_argument("--no-gripper-full", action="store_true", help="gripper uses --amplitude instead of full travel")
    dm.add_argument("--yes", action="store_true")
    ld = sub.add_parser("leader", help="live read-only view of the leader (master) arm vs the follower")
    ld.add_argument("--bus", help="leader bus serial (default station.leader_bus in config)")
    ld.add_argument("--seconds", type=float, default=0, help="stop after N seconds (default: until Ctrl-C)")
    ld.add_argument("--interval", type=float, default=0.1)
    ld.add_argument("--min-coverage", type=float, default=80.0,
                    help="flag joints moved through less than this %% of their range")
    ld.add_argument("--no-follower", action="store_true", help="show the leader only")

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
    "demo": cmd_demo, "leader": cmd_leader,
}
HARDWARE_COMMANDS = {"run", "next", "jog", "stop", "motors", "torque", "identify", "probe-current",
                     "teach", "goto", "map", "demo", "leader"}


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
