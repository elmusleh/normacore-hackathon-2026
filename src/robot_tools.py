"""What Claude can do with the real ElRobot, independent of the MCP plumbing.

Joint level, through named waypoints taught on the arm (./cli.sh hw teach), small
joint nudges, the gripper, and camera snapshots. No Cartesian moves: the Station
only takes joint targets and no kinematics model is verified on this arm yet.

Safety, on top of what ElRobotHardware already enforces (calibrated-range clamp,
fault and torque checks, speed caps, overload hold):
  * Nothing moves unless ELROBOT_ALLOW_MOTION=1. Otherwise motion tools return
    the plan they would run ("dry_run"), so a session can be rehearsed safely.
  * Claude cannot turn torque off (the arm would fall). stop() holds in place.
  * Waypoint moves route through the `clear` waypoint by default, and any single
    motor moving more than agent.max_waypoint_delta_steps is refused.
  * Nudges are capped at agent.max_nudge_percent of the joint's calibrated range.
  * Nudges stay inside the action space a human recorded with the leader arm
    (config/envelope.json, ./cli.sh hw envelope record): a nudge that would end more than
    agent.envelope_margin_steps from every recorded pose is refused, unless it brings the arm
    closer to the space. With ELROBOT_REQUIRE_ENVELOPE=1 (console stepwise mode) nudges are
    refused when no space is recorded.
  * One tool call at a time (a lock), so two moves never interleave. stop() is the exception:
    it skips the lock, so it also interrupts a recorded plan (play_sequence) that is running.
  * play_sequence only plays plans a human recorded (./cli.sh hw record), with the same checks
    as ./cli.sh hw play (src/sequence_player.py).

Every method returns a plain dict for Claude to read. Errors that Claude should
react to come back as {"ok": False, "error": ...} rather than exceptions.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from action_space import SPACE_MOTORS, load_action_space
from elrobot_camera import (
    MAX_LOOKBACK,
    decode_frame,
    describe_camera,
    discover_camera_queues,
    port_of,
    usb_ports,
)
from elrobot_config import current_threshold_for, load_config, load_sequences, load_waypoints, save_waypoints
from elrobot_hardware import (
    DEFAULT_SAFETY_MARGIN_STEPS,
    ELROBOT_MOTOR_IDS,
    MotorReading,
    clamp_goal,
    plan_goto,
)
from sequence_player import SEQ_MAX_PAUSE, TRACK_TOLERANCE, plan_legs, run_legs, waypoint_target

log = logging.getLogger("elrobot.mcp")

WAYPOINT_NAME = re.compile(r"^[a-z0-9_-]{1,40}$")
ARRIVAL_TOLERANCE = 12      # steps; same as ./cli.sh hw goto
AT_WAYPOINT_TOLERANCE = 40  # steps; "already at clear" for routing purposes
HOLDING_MARGIN_PERCENT = 3.0
TELEOP_WATCH_S = 1.0        # goal registers must stay still this long before a sequence starts


def motion_allowed() -> bool:
    return os.environ.get("ELROBOT_ALLOW_MOTION", "").strip().lower() in ("1", "true", "yes", "on")


def envelope_required() -> bool:
    return os.environ.get("ELROBOT_REQUIRE_ENVELOPE", "").strip().lower() in ("1", "true", "yes", "on")


def percent_of_range(r: MotorReading) -> Optional[float]:
    if not r.calibrated:
        return None
    return round((r.present - r.range_min) * 100.0 / (r.range_max - r.range_min), 1)


def raw_from_percent(r: MotorReading, pct: float) -> int:
    return int(round(r.range_min + max(0.0, min(100.0, pct)) / 100.0 * (r.range_max - r.range_min)))


class RobotTools:
    """The tool implementations. `connect` returns an object like ElRobotHardwareSync."""

    def __init__(self, connect: Callable[[], Any], camera_queues: Optional[Callable[[], List[str]]] = None,
                 usb_ports_fn: Optional[Callable[[], dict]] = None):
        self._connect = connect
        self._camera_queues = camera_queues or discover_camera_queues
        self._usb_ports = usb_ports_fn or usb_ports
        self._camera_info: Dict[str, Dict[str, Any]] = {}  # queue -> describe_camera(); fixed per queue
        self._camera_retry_at: Dict[str, float] = {}  # queue -> when to try describing it again
        self._hw = None
        self._lock = threading.Lock()
        self._gripper_cmd_open: Optional[float] = None  # last commanded gripper opening, %
        self._abort = threading.Event()  # set by stop(); a running play_sequence halts on it

    # -- plumbing -------------------------------------------------------------

    def _cfg(self) -> Dict[str, Any]:
        return load_config()

    def hw(self):
        if self._hw is None:
            self._hw = self._connect()
        return self._hw

    def reset_connection(self) -> None:
        if self._hw is not None:
            try:
                self._hw.close()
            except Exception:  # noqa: BLE001 - best effort
                log.debug("close failed", exc_info=True)
        self._hw = None

    def call(self, fn: Callable[..., Dict[str, Any]], *args, **kwargs) -> Dict[str, Any]:
        """Run one tool under the lock, turning failures into a readable result."""
        with self._lock:
            try:
                return fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - reported to Claude, logged in full
                log.exception("tool %s failed", getattr(fn, "__name__", fn))
                if isinstance(exc, (ConnectionError, TimeoutError, OSError)) or "station" in str(exc).lower():
                    self.reset_connection()
                return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    def _joint(self, cfg, m: int) -> str:
        j = cfg["joint_map"].get(str(m))
        return j["joint"] if j else f"motor_{m}"

    def _gripper_motor(self, cfg) -> int:
        return int(cfg["gripper"]["motor"])

    def _gripper_open_percent(self, cfg, r: MotorReading) -> Optional[float]:
        pct = percent_of_range(r)
        if pct is None:
            return None
        return pct if cfg["gripper"]["open_at"] == "max" else round(100.0 - pct, 1)

    def _torque_problem(self, readings: Dict[int, MotorReading], motors) -> Optional[str]:
        off = [m for m in motors if m in readings and not readings[m].torque_on]
        missing = [m for m in motors if m not in readings]
        if missing:
            return f"motors {missing} are not visible on the bus"
        if off:
            return f"torque is off on motors {off}; call enable_torque first (it holds the current pose)"
        return None

    # -- read-only tools ------------------------------------------------------

    def get_robot_state(self) -> Dict[str, Any]:
        cfg = self._cfg()
        readings = self.hw().snapshot()
        gm = self._gripper_motor(cfg)
        joints = []
        for m in ELROBOT_MOTOR_IDS:
            r = readings.get(m)
            if r is None:
                joints.append({"motor": m, "joint": self._joint(cfg, m), "visible": False})
                continue
            joints.append({
                "motor": m,
                "joint": "gripper" if m == gm else self._joint(cfg, m),
                "percent_of_range": percent_of_range(r),
                "raw": r.present,
                "torque_on": r.torque_on,
                "current": r.current,
                "fault": r.faulted,
                "calibrated": r.calibrated,
            })
        gripper = {}
        g = readings.get(gm)
        if g is not None:
            open_pct = self._gripper_open_percent(cfg, g)
            gripper = {"open_percent": open_pct, "current": g.current,
                       "last_commanded_open_percent": self._gripper_cmd_open,
                       "direction_verified": bool(cfg["gripper"]["verified"])}
            if self._gripper_cmd_open is not None and open_pct is not None:
                gripper["likely_holding_object"] = open_pct > self._gripper_cmd_open + HOLDING_MARGIN_PERCENT
        near = self._nearest_waypoint(readings, gm)
        return {"ok": True, "motion_allowed": motion_allowed(), "joints": joints, "gripper": gripper,
                "nearest_waypoint": near}

    def _nearest_waypoint(self, readings, gripper_motor: int) -> Optional[Dict[str, Any]]:
        best = None
        for name, raw in load_waypoints().items():
            try:
                diffs = [abs(int(v) - readings[int(k)].present) for k, v in raw.items()
                         if int(k) in readings and int(k) != gripper_motor]
            except (ValueError, KeyError):
                continue
            if diffs and (best is None or max(diffs) < best[1]):
                best = (name, max(diffs))
        return None if best is None else {"name": best[0], "max_motor_difference_steps": best[1]}

    def list_waypoints(self) -> Dict[str, Any]:
        points = load_waypoints()
        cfg = self._cfg()
        return {"ok": True, "waypoints": sorted(points), "clear_waypoint": cfg["agent"]["clear_waypoint"],
                "hint": "Teach new ones with teach_waypoint or ./cli.sh hw teach <name>." if not points else ""}

    def _describe_queue(self, q: str) -> Dict[str, Any]:
        """Product and unique_id of a camera queue. The first entry (the connect event) is not
        always readable (the Station returned nothing for queues it reopened), but every entry
        carries the camera, so fall back to the newest one."""
        for read in (lambda: self.hw().read_first(q), lambda: self.hw().read_recent(q, back=1)):
            try:
                info = describe_camera(read())
            except Exception:  # noqa: BLE001 - description is optional
                log.debug("describe %s failed", q, exc_info=True)
                continue
            if info.get("unique_id"):
                return info
        return {}

    def _cameras(self, cfg) -> List[Dict[str, Any]]:
        """Every camera queue with its product, USB port (None if unplugged) and configured name.

        Config names map to "port:<usb port>" (stable across replugs) or "usbvideo/<hash>".
        """
        ports = self._usb_ports()
        names = {v: k for k, v in cfg["cameras"].items()}
        cams = []
        for q in self._camera_queues():
            info = self._camera_info.get(q)
            if not info and time.monotonic() >= self._camera_retry_at.get(q, 0.0):
                info = self._describe_queue(q)
                if info.get("unique_id"):
                    self._camera_info[q] = info
                else:  # a queue the Station has not filled yet: ask again later, not every call
                    self._camera_retry_at[q] = time.monotonic() + 10.0
            info = dict(info or {})
            port = port_of(info.get("unique_id", ""), ports)
            cams.append({"queue": q, "port": port, "live": port is not None,
                         "name": names.get(f"port:{port}") or names.get(q), "product": info.get("product")})
        return cams

    def list_cameras(self) -> Dict[str, Any]:
        cfg = self._cfg()
        cams = self._cameras(cfg)
        live = [c for c in cams if c["live"]]
        return {"ok": True, "cameras": live, "unplugged_old_queues": len(cams) - len(live),
                "hint": "" if live else "No camera is plugged in, or the Station cannot open it "
                                        "(see scripts/99-normacore-cameras.rules)."}

    def camera_queue(self, camera: str = "") -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """(queue id, None) for a configured name ('table'), 'port:3-2.4', a queue id, or empty;
        (None, error result) if that camera is not plugged in."""
        cfg = self._cfg()
        cams = self._cameras(cfg)
        live = [c for c in cams if c["live"]]
        want = camera or ("table" if "table" in cfg["cameras"] else "")
        target = cfg["cameras"].get(want, want)
        if not target:
            if not live:
                return None, {"ok": False, "error": "no camera plugged in; see list_cameras"}
            return live[0]["queue"], None
        if target.startswith("port:"):
            match = [c for c in live if f"port:{c['port']}" == target]
            if not match:
                return None, {"ok": False, "error": f"camera {camera or want!r} ({target}) is not plugged in",
                              "live_cameras": live}
            return match[0]["queue"], None
        return (target if target.startswith("usbvideo/") else f"usbvideo/{target}"), None

    def look(self, camera: str = "") -> Tuple[Dict[str, Any], Optional[bytes]]:
        """Newest JPEG from a camera: a configured name ('table'), 'port:3-2.4', a queue id, or empty."""
        queue, err = self.camera_queue(camera)
        if err:
            return err, None
        hw = self.hw()
        for back in range(1, MAX_LOOKBACK + 1):
            data = hw.read_recent(queue, back=back)
            if data is None:
                break
            frame = decode_frame(data)
            if frame is not None:
                age = frame.age_s
                meta = {"ok": True, "camera": camera or queue, "queue": queue,
                        "width": frame.width, "height": frame.height,
                        "age_seconds": None if age is None else round(age, 2)}
                if age is not None and age > 2.0:
                    meta["warning"] = "frame is old: the camera may be disconnected or stalled"
                return meta, frame.jpeg
        return {"ok": False, "error": f"no frame in {queue}; is the camera streaming?"}, None

    # -- motion ---------------------------------------------------------------

    def _move(self, goals: Dict[int, int], cfg, speed: Optional[int] = None) -> Dict[str, Any]:
        """Clamp, then move-and-watch (or describe the move in dry-run). Returns a result dict."""
        hw = self.hw()
        readings = hw.snapshot()
        problem = self._torque_problem(readings, goals)
        if problem:
            return {"ok": False, "error": problem}
        plan = {}
        final: Dict[int, int] = {}
        for m, goal in goals.items():
            r = readings[m]
            clamped, was = clamp_goal(goal, r.range_min, r.range_max, DEFAULT_SAFETY_MARGIN_STEPS)
            final[m] = clamped
            plan[m] = {"joint": self._joint(cfg, m), "from": r.present, "to": clamped, "clamped": was}
        speed = min(int(speed or cfg["agent"]["max_speed"]), int(cfg["agent"]["max_speed"]))
        if not motion_allowed():
            return {"ok": True, "dry_run": True, "plan": plan,
                    "note": "Motion is disabled (ELROBOT_ALLOW_MOTION is not 1). Nothing moved."}
        status = hw.move_and_watch(final, enable_motion=True, max_speed=speed,
                                   thresholds={m: current_threshold_for(cfg, m) for m in final})
        after = hw.snapshot()
        off = {m: final[m] - after[m].present for m in final
               if m in after and abs(final[m] - after[m].present) > ARRIVAL_TOLERANCE}
        ok = all(s == "reached" for s in status.values()) and not off
        result = {"ok": ok, "status": status, "plan": plan}
        if off:
            result["not_at_target_steps"] = off
        if not ok:
            result["hint"] = "A motor did not arrive (obstacle, overload or timeout). Look at the camera before retrying."
        return result

    def go_to_waypoint(self, name: str, via_clear: bool = True, include_gripper: bool = False,
                       speed: Optional[int] = None) -> Dict[str, Any]:
        cfg = self._cfg()
        points = load_waypoints()
        if name not in points:
            return {"ok": False, "error": f"no waypoint {name!r}", "known": sorted(points)}
        gm = self._gripper_motor(cfg)
        clear = cfg["agent"]["clear_waypoint"]
        motors = [m for m in ELROBOT_MOTOR_IDS if include_gripper or m != gm]

        def target_of(wp: str) -> Dict[int, int]:
            raw = points[wp]
            return {m: int(raw[str(m)]) for m in motors if str(m) in raw}

        readings = self.hw().snapshot()
        legs = [name]
        if via_clear and name != clear and clear in points:
            c = target_of(clear)
            if any(abs(c[m] - readings[m].present) > AT_WAYPOINT_TOLERANCE for m in c if m in readings):
                legs = [clear, name]

        results = []
        max_delta = int(cfg["agent"]["max_waypoint_delta_steps"])
        for wp in legs:
            readings = self.hw().snapshot()
            target = target_of(wp)
            if len(target) != len(motors):
                return {"ok": False, "error": f"waypoint {wp!r} does not list all motors; re-teach it"}
            present = {m: readings[m].present for m in motors if m in readings}
            # In dry-run, plan each leg from the previous leg's target rather than the unmoved arm.
            if results and results[-1].get("dry_run"):
                present = {m: results[-1]["plan"][m]["to"] for m in present}
            try:
                plan_goto(present, target, max_delta)
            except ValueError as exc:
                msg = str(exc).replace("need --allow-large", "are refused")
                return {"ok": False, "error": f"leg to {wp!r}: {msg}",
                        "hint": f"Go to {clear!r} first, or ask the operator to move the arm closer.",
                        "legs_done": results}
            res = self._move(target, cfg, speed)
            res["waypoint"] = wp
            results.append(res)
            if not res["ok"]:
                break
        ok = all(r["ok"] for r in results)
        return {"ok": ok, "route": legs, "legs": results}

    def nudge_joint(self, motor: int, delta_percent: float, speed: Optional[int] = None) -> Dict[str, Any]:
        cfg = self._cfg()
        gm = self._gripper_motor(cfg)
        if motor not in ELROBOT_MOTOR_IDS or motor == gm:
            return {"ok": False, "error": f"motor must be 1-8 and not the gripper ({gm}); use set_gripper"}
        cap = float(cfg["agent"]["max_nudge_percent"])
        if abs(delta_percent) > cap:
            return {"ok": False, "error": f"|delta_percent| must be <= {cap}; nudge in smaller steps"}
        r = self.hw().snapshot().get(motor)
        if r is None or not r.calibrated:
            return {"ok": False, "error": f"motor {motor} not visible or not calibrated"}
        delta = int(round(delta_percent / 100.0 * (r.range_max - r.range_min)))
        envelope = self._check_envelope(motor, r.present + delta, cfg)
        if envelope is not None and not envelope["ok"]:
            return envelope
        res = self._move({motor: r.present + delta}, cfg, speed)
        res["delta_steps"] = delta
        if envelope is not None:
            res["action_space_distance_steps"] = envelope["distance_after"]
        return res

    def _check_envelope(self, motor: int, goal: int, cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """None if no action space is recorded and none is required; else the check result."""
        space = load_action_space()
        if space is None or space.empty:
            if envelope_required():
                return {"ok": False, "error": "no action space recorded, so nudges are not allowed in this mode",
                        "hint": "Ask the operator to record one: teleop on, ./cli.sh hw envelope record."}
            return None
        readings = self.hw().snapshot()
        missing = [m for m in SPACE_MOTORS if m not in readings]
        if missing:
            return {"ok": False, "error": f"cannot read motors {missing}; cannot check the action space"}
        current = {m: readings[m].present for m in SPACE_MOTORS}
        r = readings[motor]
        goal, _ = clamp_goal(goal, r.range_min, r.range_max)
        check = space.check_move(current, {**current, motor: goal}, int(cfg["agent"]["envelope_margin_steps"]))
        if not check["ok"]:
            log.warning("nudge motor %d refused: %s", motor, check["reason"])
            return {"ok": False, "error": check["reason"], "refused": "action_space",
                    "distance_now_steps": check["distance_before"],
                    "hint": "Try the other direction, a smaller nudge, or another joint. get_action_space() "
                            "shows the recorded range and the anchors."}
        return check

    def get_action_space(self) -> Dict[str, Any]:
        """What the human recorded with the leader arm: joint meanings, the range each joint was
        driven through, named anchor poses, and how far the arm is from the space now."""
        cfg = self._cfg()
        space = load_action_space()
        joint_map = {m: cfg["joint_map"][m] for m in sorted(cfg["joint_map"], key=int)}
        if space is None or space.empty:
            return {"ok": True, "recorded": False, "joint_map": joint_map, "required": envelope_required(),
                    "hint": "No action space recorded. The operator records one with teleop on: "
                            "./cli.sh hw envelope record."}
        readings = self.hw().snapshot()

        def pct(m: int, raw: int) -> Optional[float]:
            r = readings.get(m)
            if r is None or not r.calibrated:
                return None
            return round((raw - r.range_min) * 100.0 / (r.range_max - r.range_min), 1)

        now = {m: readings[m].present for m in SPACE_MOTORS if m in readings}
        joints = {}
        for m, (lo, hi) in space.seen_range().items():
            joints[str(m)] = {"recorded_min_percent": pct(m, lo), "recorded_max_percent": pct(m, hi),
                              "now_percent": pct(m, now[m]) if m in now else None}
        anchors = {}
        for name, pose in space.anchors.items():
            to_go = {}
            for m in SPACE_MOTORS:
                a, n = pct(m, int(pose[str(m)])), pct(m, now[m]) if m in now else None
                if a is not None and n is not None:
                    to_go[str(m)] = round(a - n, 1)
            anchors[name] = {"distance_steps": max(abs(int(pose[str(m)]) - now[m]) for m in now) if now else None,
                             "nudge_percent_to_reach": to_go}
        distance = space.distance(now) if len(now) == len(SPACE_MOTORS) else None
        margin = int(cfg["agent"]["envelope_margin_steps"])
        return {"ok": True, "recorded": True, "updated": space.meta.get("updated"), "poses": len(space.poses),
                "joint_map": joint_map, "joints": joints, "anchors": anchors,
                "distance_now_steps": distance, "inside": distance is not None and distance <= margin,
                "margin_steps": margin,
                "note": "Nudges that would leave the recorded space are refused. nudge_percent_to_reach is "
                        "per motor, in % of range, from where the arm is now (5% max per nudge)."}

    def set_gripper(self, open_percent: float) -> Dict[str, Any]:
        cfg = self._cfg()
        gm = self._gripper_motor(cfg)
        open_percent = max(0.0, min(100.0, float(open_percent)))
        hw = self.hw()
        r = hw.snapshot().get(gm)
        if r is None or not r.calibrated:
            return {"ok": False, "error": f"gripper motor {gm} not visible or not calibrated"}
        range_pct = open_percent if cfg["gripper"]["open_at"] == "max" else 100.0 - open_percent
        closing = (self._gripper_open_percent(cfg, r) or 0.0) > open_percent
        res = self._move({gm: raw_from_percent(r, range_pct)}, cfg)
        self._gripper_cmd_open = open_percent
        if res.get("dry_run"):
            return res
        status = res.get("status", {}).get(gm)
        after = hw.snapshot()[gm]
        res["open_percent"] = self._gripper_open_percent(cfg, after)
        if closing and status in ("overload", "timeout") or (
                closing and res["open_percent"] is not None
                and res["open_percent"] > open_percent + HOLDING_MARGIN_PERCENT):
            # Stalled on something while closing: that is a grasp. Keep a light squeeze on it.
            squeeze = int(cfg["gripper"]["squeeze_steps"])
            toward_closed = -squeeze if cfg["gripper"]["open_at"] == "max" else squeeze
            goal, _ = clamp_goal(after.present + toward_closed, after.range_min, after.range_max)
            hw.move_motors({gm: goal}, enable_motion=True, max_speed=200)
            res.update(ok=True, result="holding_object",
                       note="Gripper stopped on an object before closing; holding it with a light squeeze.")
        elif closing:
            res["result"] = "closed_empty" if res["ok"] else "blocked"
        else:
            res["result"] = "opened" if res["ok"] else "blocked"
        if not cfg["gripper"]["verified"]:
            res["warning"] = "Gripper open/close direction is not verified on this arm (config gripper.verified)."
        return res

    # -- recorded plans -------------------------------------------------------

    def list_sequences(self) -> Dict[str, Any]:
        """Recorded plans, and which food each one serves (config 'foods')."""
        cfg = self._cfg()
        seqs = load_sequences()
        points = load_waypoints()
        plans = {name: {"steps": steps, "ready": all(w in points for w in steps),
                        "missing_waypoints": [w for w in steps if w not in points]}
                 for name, steps in seqs.items()}
        foods = {food: {"sequence": spec.get("sequence"), "note": spec.get("note", ""),
                        "ready": spec.get("sequence") in plans and plans[spec["sequence"]]["ready"]}
                 for food, spec in cfg.get("foods", {}).items()}
        return {"ok": True, "foods": foods, "sequences": plans,
                "hint": "" if foods else "No foods configured: add 'foods' to config/elrobot.json."}

    def play_sequence(self, name: str) -> Dict[str, Any]:
        """Run a recorded plan from start to end. Holds the arm and stops on any problem or stop()."""
        cfg = self._cfg()
        seqs = load_sequences()
        if name not in seqs:
            return {"ok": False, "error": f"no recorded plan {name!r}", "known": sorted(seqs)}
        agent = cfg["agent"]
        speed = min(int(agent.get("sequence_speed", 300)), int(agent["max_speed"]))
        pause = max(0.0, min(float(agent.get("sequence_pause_s", 1.5)), SEQ_MAX_PAUSE))
        tolerance = max(TRACK_TOLERANCE, min(int(agent.get("sequence_tolerance_steps", 60)), 100))
        points = load_waypoints()
        targets = []
        for wp in seqs[name]:
            target, err = waypoint_target(points, wp)
            if err:
                return {"ok": False, "error": f"plan {name!r}: {err}"}
            targets.append((wp, target))
        hw = self.hw()
        readings = hw.snapshot()
        problem = self._torque_problem(readings, ELROBOT_MOTOR_IDS)
        if problem:
            return {"ok": False, "error": problem}
        faulted = [m for m in ELROBOT_MOTOR_IDS if readings[m].faulted]
        if faulted:
            return {"ok": False, "error": f"motors {faulted} report a fault; not moving. Tell the operator."}
        try:
            legs = plan_legs(readings, targets, DEFAULT_SAFETY_MARGIN_STEPS)
        except ValueError as exc:
            return {"ok": False, "error": f"plan {name!r}: {exc}"}
        steps = [wp for wp, _g, _d, _c in legs]
        if not motion_allowed():
            return {"ok": True, "dry_run": True, "sequence": name, "steps": steps,
                    "note": "Motion is disabled (ELROBOT_ALLOW_MOTION is not 1). Nothing moved."}
        # Station teleop (leader -> follower) would overwrite the goals mid-plan.
        time.sleep(TELEOP_WATCH_S)
        after = hw.snapshot()
        drifting = [m for m in ELROBOT_MOTOR_IDS if m in after and after[m].torque_on
                    and abs(after[m].goal - readings[m].goal) > 5]
        if drifting:
            return {"ok": False, "error": f"goal registers of motors {drifting} change on their own: teleop "
                                          "(leader arm) is probably on. Ask the operator to turn it off."}
        self._abort.clear()
        log.info("play_sequence %s: %s", name, steps)
        result = run_legs(hw, legs, speed=speed, thresholds={m: current_threshold_for(cfg, m) for m in ELROBOT_MOTOR_IDS},
                          tolerance=tolerance, pause=pause, stop_event=self._abort, title=name)
        result.update(sequence=name, steps=steps)
        if not result["ok"]:
            result["hint"] = "The arm is holding where it stopped. Look at the camera and tell the person; do not rerun blindly."
        return result

    def stop_now(self) -> Dict[str, Any]:
        """stop() without waiting for the tool lock, so it can interrupt a running play_sequence."""
        self._abort.set()
        try:
            return self.stop()
        except Exception as exc:  # noqa: BLE001 - reported to Claude
            log.exception("stop failed")
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "hint": "Use the power switch."}

    def stop(self) -> Dict[str, Any]:
        """Hold every motor where it is. Always allowed, even with motion disabled."""
        hw = self.hw()
        readings = hw.snapshot()
        on = [m for m in ELROBOT_MOTOR_IDS if m in readings and readings[m].torque_on]
        if on:
            hw.hold(on)
        return {"ok": True, "held": on, "note": "Motors with torque on are holding position."}

    def enable_torque(self) -> Dict[str, Any]:
        if not motion_allowed():
            return {"ok": True, "dry_run": True, "note": "Motion is disabled; torque not changed."}
        hw = self.hw()
        motors = [m for m in ELROBOT_MOTOR_IDS if m in hw.snapshot()]
        hw.torque_on_hold(motors)
        return {"ok": True, "torque_on": motors, "note": "Holding the current pose."}

    def teach_waypoint(self, name: str, overwrite: bool = False) -> Dict[str, Any]:
        if not WAYPOINT_NAME.match(name):
            return {"ok": False, "error": "names: lowercase letters, digits, - or _, up to 40 characters"}
        points = load_waypoints()
        if name in points and not overwrite:
            return {"ok": False, "error": f"waypoint {name!r} exists; pass overwrite=true to replace it"}
        readings = self.hw().snapshot()
        missing = [m for m in ELROBOT_MOTOR_IDS if m not in readings]
        if missing:
            return {"ok": False, "error": f"motors {missing} not visible"}
        points[name] = {str(m): readings[m].present for m in ELROBOT_MOTOR_IDS}
        save_waypoints(points)
        return {"ok": True, "saved": name, "pose": points[name]}
