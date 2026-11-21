"""Play a recorded sequence of waypoints (config/sequences.json) on the arm.

Shared by `./cli.sh hw play` (scripts/hw_day.py) and Claude's `play_sequence` MCP tool
(src/robot_tools.py), so both use the same safety checks:
  * every leg is planned up front with goals clamped to the calibrated range;
  * per leg: move_and_watch (overload guard), then wait until the arm has really stopped,
    then check every motor is within `tolerance` steps of its goal;
  * loaded joints settle 20-35 (up to ~45) steps short under gravity: a motor that has stopped
    within `tolerance` without overload counts as arrived ("near");
  * any failure, or `stop_event` being set (stop button / stop tool), holds the arm and ends the run.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from elrobot_hardware import DEFAULT_MAX_ACCEL, DEFAULT_SAFETY_MARGIN_STEPS, ELROBOT_MOTOR_IDS, clamp_goal

log = logging.getLogger("elrobot.sequence")

MOTORS = list(ELROBOT_MOTOR_IDS)
SEQ_DEFAULT_PAUSE = 1.5      # seconds to wait at each waypoint after the arm has stopped
SEQ_MAX_PAUSE = 10.0
SEQ_NEAR_TOLERANCE = 60      # steps: loaded joints stop 20-45 short under gravity; accept if stopped this close
TRACK_TOLERANCE = 12         # same tolerance move_and_watch uses for "reached"
SETTLE_TOLERANCE = 2         # steps: a motor counts as still if it moved at most this much ...
SETTLE_HOLD_S = 0.5          # ... between polls, for this long
SETTLE_POLL_S = 0.1
SETTLE_TIMEOUT_S = 5.0       # give up waiting (and stop the sequence) after this long

Leg = Tuple[str, Dict[int, int], Dict[int, int], List[int]]  # name, goals, deltas, clamped motors


def waypoint_target(points: Dict[str, Dict[str, int]], name: str):
    """Joint goals of a stored waypoint, or (None, error message)."""
    if name not in points:
        return None, f"No waypoint '{name}'. Known: {', '.join(sorted(points)) or '(none)'}"
    raw = points[name]
    if sorted(raw, key=int) != [str(m) for m in MOTORS]:
        return None, f"Waypoint '{name}' must list all 8 motors. Re-teach it."
    return {int(k): int(v) for k, v in raw.items()}, None


def plan_legs(readings, named_targets: List[Tuple[str, Dict[int, int]]],
              margin: int = DEFAULT_SAFETY_MARGIN_STEPS) -> List[Leg]:
    """Clamp every leg's goals and compute per-motor deltas from the previous leg. Raises ValueError."""
    legs: List[Leg] = []
    prev = {m: readings[m].present for m in MOTORS}
    for name, target in named_targets:
        goals, clamped = {}, []
        for m in MOTORS:
            r = readings[m]
            try:
                goal, was_clamped = clamp_goal(target[m], r.range_min, r.range_max, margin)
            except ValueError as exc:
                raise ValueError(f"waypoint '{name}' motor {m}: {exc}") from exc
            goals[m] = goal
            if was_clamped:
                clamped.append(m)
        legs.append((name, goals, {m: goals[m] - prev[m] for m in MOTORS}, clamped))
        prev = goals
    return legs


def wait_settled(hw, motors, tolerance=None, hold_s=None, timeout_s=None, poll_s=None):
    """Poll until no motor has moved more than `tolerance` steps for `hold_s` seconds.

    move_and_watch returns as soon as each motor is near its goal, which can be while the arm
    is still coasting. This waits until it has really stopped. Returns (settled, readings).
    """
    tolerance = SETTLE_TOLERANCE if tolerance is None else tolerance
    hold_s = SETTLE_HOLD_S if hold_s is None else hold_s
    timeout_s = SETTLE_TIMEOUT_S if timeout_s is None else timeout_s
    poll_s = SETTLE_POLL_S if poll_s is None else poll_s
    start = time.monotonic()
    last = hw.snapshot()
    still_since = time.monotonic()
    while True:
        time.sleep(poll_s)
        now_readings = hw.snapshot()
        moved = max((abs(now_readings[m].present - last[m].present)
                     for m in motors if m in now_readings and m in last), default=0)
        now = time.monotonic()
        if moved > tolerance:
            still_since = now
        elif now - still_since >= hold_s:
            return True, now_readings
        if now - start > timeout_s:
            return False, now_readings
        last = now_readings


def run_legs(hw, legs: List[Leg], *, speed: int, thresholds: Dict[int, int],
             tolerance: int = SEQ_NEAR_TOLERANCE, pause: float = SEQ_DEFAULT_PAUSE,
             stop_event: Optional[threading.Event] = None,
             report: Callable[[str], Any] = lambda _msg: None, title: str = "") -> Dict[str, Any]:
    """Run planned legs in order. Returns {"ok", "done": [names], ...}; on failure the arm is held."""
    done: List[str] = []
    short_by_leg: Dict[str, Dict[int, int]] = {}

    def fail(i, name, error):
        hw.hold(MOTORS)
        log.warning("sequence %s stopped at step %d '%s': %s", title, i, name, error)
        return {"ok": False, "done": done, "stopped_at": name, "step": i, "error": error,
                "stopped_short": short_by_leg}

    for i, (name, goals, _deltas, _clamped) in enumerate(legs, 1):
        if stop_event is not None and stop_event.is_set():
            return fail(i, name, "stopped by request before this step")
        report(f"[{i}/{len(legs)}] -> '{name}' ...")
        t0 = time.monotonic()
        status = hw.move_and_watch(goals, enable_motion=True, max_speed=speed, max_accel=DEFAULT_MAX_ACCEL,
                                   thresholds=thresholds, near_tolerance=tolerance)
        if stop_event is not None and stop_event.is_set():
            return fail(i, name, "stopped by request during this step")
        bad = {m: s for m, s in status.items() if s not in ("reached", "near")}
        if bad:
            return fail(i, name, f"motor status {bad} (overload, fault or timeout); check for an obstacle")
        settled, final = wait_settled(hw, MOTORS)
        if not settled:
            return fail(i, name, f"the arm did not come to rest within {SETTLE_TIMEOUT_S:g} s "
                                 "(teleop on, or oscillating?)")
        off = {m: goals[m] - final[m].present for m in MOTORS
               if m in final and abs(goals[m] - final[m].present) > tolerance}
        if off:
            return fail(i, name, f"not at target (steps off: {off})")
        short = {m: final[m].present - goals[m] for m in MOTORS
                 if m in final and abs(goals[m] - final[m].present) > TRACK_TOLERANCE}
        if short:
            short_by_leg[name] = short
        done.append(name)
        log.info("sequence %s step %d '%s' reached and settled in %.1fs", title, i, name, time.monotonic() - t0)
        note = f"; stopped short (steps): {short}" if short else ""
        report(f"  at '{name}', stopped ({time.monotonic() - t0:.1f} s){note}")
        if i < len(legs) and pause > 0:
            if stop_event is not None:
                if stop_event.wait(pause):
                    return fail(i + 1, legs[i][0], "stopped by request before this step")
            else:
                time.sleep(pause)
    return {"ok": True, "done": done, "stopped_short": short_by_leg}
