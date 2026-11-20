"""Real-hardware bridge for the ElRobot via a NormaCore Station (ST3215 bus servos).

Joint-level only. The Station exposes motor registers (goal position, speed,
acceleration, torque), not Cartesian poses, so Cartesian tools stay on the
MockStation until a kinematics model is verified against the real arm.

Safety rules enforced here:
  * Nothing moves unless `move_motors(..., enable_motion=True)` is called.
  * Goals are clamped to each motor's calibrated range, minus a margin.
  * Wrap-around calibrations (range_max < range_min) are refused, not guessed.
  * Motion is refused while any motor reports a fault other than under-voltage.
  * Speed and acceleration are capped below the teleop example's values.

Reads (`snapshot`) never change torque or position.

The NormaCore SDK lives in the downloaded source tree; its path is taken from
the NORMACORE_ROOT environment variable, defaulting to external/norma-core.
"""

from __future__ import annotations

import asyncio
import logging
import os
import struct
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 7 articulated joints + 1 parallel gripper (URDF rev_motor_01..08).
ELROBOT_MOTOR_IDS: Tuple[int, ...] = tuple(range(1, 9))

# ST3215 register addresses (same map as the NormaCore teleop example).
RAM_TORQUE_ENABLE = 0x28
RAM_ACC = 0x29
RAM_GOAL_POSITION = 0x2A
RAM_GOAL_SPEED = 0x2E
RAM_PRESENT_POSITION = 0x38
RAM_STATUS = 0x40
RAM_PRESENT_CURRENT = 0x45

MAX_STEP = 4095          # 12-bit encoder, 0..4095
SIGN_BIT_MASK = 0x8000   # high bit of the raw position word is a sign flag
STATUS_UNDERVOLTAGE = 0x01

# Conservative defaults for first moves on the real arm. Tune only after
# watching a slow test move.
DEFAULT_SAFETY_MARGIN_STEPS = 20
DEFAULT_MAX_SPEED = 800
DEFAULT_MAX_ACCEL = 30

DEFAULT_NORMACORE_ROOT = Path(__file__).resolve().parent.parent / "external" / "norma-core"


# ---------------------------------------------------------------------------
# Pure helpers (no hardware, no SDK import) -- these are what the tests cover.
# ---------------------------------------------------------------------------

def normal_position(raw: int) -> int:
    """Strip the sign flag so a position is always 0..4095."""
    if raw & SIGN_BIT_MASK:
        magnitude = raw & MAX_STEP
        return (MAX_STEP + 1 - magnitude) & MAX_STEP
    return raw & MAX_STEP


def _u16(state: bytes, addr: int) -> int:
    if len(state) < addr + 2:
        return 0
    return struct.unpack_from("<H", state, addr)[0]


def _u8(state: bytes, addr: int) -> int:
    if len(state) <= addr:
        return 0
    return state[addr]


@dataclass
class MotorReading:
    motor_id: int
    present: int
    goal: int
    torque_on: bool
    status: int
    current: int
    range_min: int
    range_max: int

    @property
    def calibrated(self) -> bool:
        return self.range_max > self.range_min

    @property
    def faulted(self) -> bool:
        return (self.status & ~STATUS_UNDERVOLTAGE) != 0


def parse_motor_state(motor_id: int, state: bytes, range_min: int, range_max: int) -> MotorReading:
    """Build a MotorReading from the raw register block of one motor."""
    present = normal_position(_u16(state, RAM_PRESENT_POSITION))
    goal = normal_position(_u16(state, RAM_GOAL_POSITION))
    torque_on = _u8(state, RAM_TORQUE_ENABLE) != 0
    return MotorReading(
        motor_id=motor_id,
        present=present,
        # With torque off the goal register holds a stale value; report present.
        goal=goal if torque_on else present,
        torque_on=torque_on,
        status=_u8(state, RAM_STATUS),
        current=_u16(state, RAM_PRESENT_CURRENT),
        range_min=range_min,
        range_max=range_max,
    )


def clamp_goal(
    goal: int,
    range_min: int,
    range_max: int,
    margin: int = DEFAULT_SAFETY_MARGIN_STEPS,
) -> Tuple[int, bool]:
    """Clamp a goal into [range_min + margin, range_max - margin].

    Returns (clamped_goal, was_clamped). Raises ValueError for an uncalibrated
    motor or a wrap-around arc, because guessing there could drive a joint
    into its hard stop.
    """
    if range_max <= range_min:
        raise ValueError(
            f"motor calibration invalid (range_min={range_min}, range_max={range_max}); "
            "recalibrate in the Station web console (wrap-around arcs are not supported)"
        )
    lo = range_min + margin
    hi = range_max - margin
    if lo > hi:
        raise ValueError(f"calibrated arc {range_min}..{range_max} is narrower than 2x margin {margin}")
    clamped = min(max(goal, lo), hi)
    return clamped, clamped != goal


def to_u16_le(value: int) -> bytes:
    return int(value).to_bytes(2, "little")


DEFAULT_CURRENT_THRESHOLD = 100


class OverloadDetector:
    """Flags a motor drawing high current while not making progress.

    Triggers after `consecutive` polls where current > threshold and the position
    moved less than `stall_steps`. threshold 0 disables the check (same convention
    as the NormaCore teleop example). Does not handle the 0/4095 wrap-around.
    """

    def __init__(self, threshold: int, consecutive: int = 3, stall_steps: int = 3):
        self.threshold = threshold
        self.consecutive = consecutive
        self.stall_steps = stall_steps
        self.peak = 0
        self._count = 0
        self._last_present: Optional[int] = None

    def update(self, current: int, present: int) -> bool:
        self.peak = max(self.peak, current)
        moved = 0 if self._last_present is None else abs(present - self._last_present)
        self._last_present = present
        if self.threshold > 0 and current > self.threshold and moved < self.stall_steps:
            self._count += 1
        else:
            self._count = 0
        return self._count >= self.consecutive


def plan_goto(
    present: Dict[int, int],
    target: Dict[int, int],
    max_delta: int,
) -> Dict[int, int]:
    """Per-motor step changes for a goto. Raises if any change is larger than max_delta."""
    missing = set(target) - set(present)
    if missing:
        raise ValueError(f"waypoint motors not visible: {sorted(missing)}")
    deltas = {m: target[m] - present[m] for m in target}
    too_big = {m: d for m, d in deltas.items() if abs(d) > max_delta}
    if too_big:
        raise ValueError(f"moves larger than {max_delta} steps need --allow-large: {too_big}")
    return deltas


# ---------------------------------------------------------------------------
# Async client over the Station TCP API.
# ---------------------------------------------------------------------------

def _ensure_sdk_on_path(root: Path) -> None:
    """Make `software.station.shared.station_py` and `target.gen_python` importable."""
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


class ElRobotHardware:
    """Talks to one ElRobot bus through a running NormaCore Station."""

    def __init__(
        self,
        server: str = "localhost",
        bus: str = "auto",
        normacore_root: Optional[Path] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.server = server
        self.bus_request = bus
        self.root = Path(os.environ.get("NORMACORE_ROOT", normacore_root or DEFAULT_NORMACORE_ROOT))
        self.log = logger or logging.getLogger("elrobot.hw")
        self.client = None
        self.bus_serial: Optional[str] = None
        self._queue: Optional[asyncio.Queue] = None
        self._latest = None  # latest decoded st3215.InferenceStateReader
        # Highest current seen per motor during the last move_and_watch call (for probing).
        self.last_peaks: Dict[int, int] = {}

    # -- connection ---------------------------------------------------------

    async def connect(self, timeout_s: float = 10.0) -> None:
        self.log.info("connecting to station %s (bus=%s, sdk=%s)", self.server, self.bus_request, self.root)
        _ensure_sdk_on_path(self.root)
        try:
            from software.station.shared.station_py import new_station_client  # noqa: WPS433
            from target.gen_python.protobuf.drivers.st3215 import st3215  # noqa: WPS433
        except ImportError:
            self.log.exception("SDK import failed; check NORMACORE_ROOT=%s and that target/gen_python exists", self.root)
            raise

        self._st3215 = st3215
        self.client = await new_station_client(self.server, self.log)
        self.log.debug("station client created, subscribing to st3215/inference")
        self._queue = asyncio.Queue()
        self._err_queue = self.client.follow("st3215/inference", self._queue)
        await self._wait_for_frame(timeout_s)
        self.bus_serial = self._resolve_bus(self.bus_request)
        self.log.info("connected: bus serial %s", self.bus_serial)

    async def _wait_for_frame(self, timeout_s: float) -> None:
        deadline = asyncio.get_running_loop().time() + timeout_s
        frames = 0
        while self._latest is None:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                self.log.error(
                    "no st3215/inference frame from %s after %.1fs. Usually the Station is not running, "
                    "no bus is connected, or the USB cable is unplugged.", self.server, timeout_s)
                raise RuntimeError(f"no st3215/inference frames from station {self.server} within {timeout_s}s")
            try:
                entry = await asyncio.wait_for(self._queue.get(), timeout=remaining)
            except asyncio.TimeoutError:
                continue
            if entry is None:
                self.log.error("st3215/inference stream closed by the station")
                raise RuntimeError("st3215/inference stream closed by station")
            frames += 1
            self._latest = self._st3215.InferenceStateReader(entry.Data)
            if frames == 1:
                self.log.debug("first st3215/inference frame received (%d bytes)", len(entry.Data))

    def _drain(self) -> None:
        """Keep only the newest frame so reads never work from a backlog."""
        if self._queue is None:
            return
        while not self._queue.empty():
            entry = self._queue.get_nowait()
            if entry is None:
                raise RuntimeError("st3215/inference stream closed by station")
            self._latest = self._st3215.InferenceStateReader(entry.Data)

    def _resolve_bus(self, requested: str) -> str:
        buses = self._latest.get_buses() or []
        serials = [b.get_bus().get_serial_number() for b in buses if b.get_bus()]
        self.log.debug("buses on station: %s (requested=%s)", serials, requested)
        if not serials:
            self.log.error("station reports no ST3215 bus. Check the USB cable and the driver board power.")
            raise RuntimeError("no ST3215 bus visible on the station")
        if requested == "auto":
            if len(serials) != 1:
                self.log.error("--bus auto needs exactly one bus, found %d: %s. Pass the serial explicitly.",
                               len(serials), serials)
                raise RuntimeError(f"--bus auto needs exactly one bus, found {serials}")
            return serials[0]
        if requested not in serials:
            self.log.error("bus %r not on station; visible: %s", requested, serials)
            raise RuntimeError(f"bus {requested!r} not on station; visible: {serials}")
        return requested

    async def close(self) -> None:
        if self.client is not None:
            try:
                self.client.close_connection()
                self.log.info("station connection closed")
            except Exception:  # noqa: BLE001 - best effort on shutdown
                self.log.exception("error while closing station connection")
            self.client = None

    # -- reads (never move anything) ---------------------------------------

    async def read(self) -> Dict[int, MotorReading]:
        """Async wrapper so reads run on the same loop as the frame consumer."""
        return self.snapshot()

    def _bus_reader(self):
        self._drain()
        for bus in self._latest.get_buses() or []:
            info = bus.get_bus()
            if info and info.get_serial_number() == self.bus_serial:
                return bus
        raise RuntimeError(f"bus {self.bus_serial} missing from the latest frame")

    def snapshot(self) -> Dict[int, MotorReading]:
        """Read every ElRobot motor on the bus. Read-only."""
        bus = self._bus_reader()
        readings: Dict[int, MotorReading] = {}
        seen = []
        for m in bus.get_motors() or []:
            if m is None:
                continue
            mid = m.get_id()
            seen.append(mid)
            if mid not in ELROBOT_MOTOR_IDS:
                continue
            raw = bytes(m.get_state())
            readings[mid] = parse_motor_state(mid, raw, m.get_range_min(), m.get_range_max())
            self.log.debug(
                "motor %d: present=%d goal=%d torque=%s status=0x%02x current=%d range=%d..%d state_len=%d",
                mid, readings[mid].present, readings[mid].goal, readings[mid].torque_on,
                readings[mid].status, readings[mid].current, readings[mid].range_min,
                readings[mid].range_max, len(raw),
            )
        self.log.debug("snapshot: motors on bus %s; ElRobot motors read %s", seen, sorted(readings))
        return readings

    # -- writes -------------------------------------------------------------

    async def set_torque(self, motor_ids: List[int], enable: bool) -> None:
        """Enable or disable torque. Disabling makes the arm go limp."""
        value = b"\x01" if enable else b"\x00"
        self.log.info("torque %s on motors %s", "ON" if enable else "OFF", list(motor_ids))
        await self._sync_write(RAM_TORQUE_ENABLE, [(mid, value) for mid in motor_ids])

    async def move_motors(
        self,
        goals: Dict[int, int],
        *,
        enable_motion: bool = False,
        margin: int = DEFAULT_SAFETY_MARGIN_STEPS,
        max_speed: int = DEFAULT_MAX_SPEED,
        max_accel: int = DEFAULT_MAX_ACCEL,
    ) -> Dict[int, dict]:
        """Move motors to encoder goals. Refuses unless enable_motion=True.

        Returns one result per motor, including whether the goal was clamped.
        """
        self.log.info("move request: goals=%s enable_motion=%s margin=%d max_speed=%d max_accel=%d",
                      goals, enable_motion, margin, max_speed, max_accel)
        if not enable_motion:
            self.log.error("move refused: enable_motion is False")
            raise PermissionError("motion disabled: pass enable_motion=True to move the real arm")
        unknown = set(goals) - set(ELROBOT_MOTOR_IDS)
        if unknown:
            self.log.error("move refused: not ElRobot motors %s", sorted(unknown))
            raise ValueError(f"not ElRobot motors: {sorted(unknown)}")

        readings = self.snapshot()
        missing = set(goals) - set(readings)
        if missing:
            self.log.error("move refused: motors %s not visible on bus %s", sorted(missing), self.bus_serial)
            raise RuntimeError(f"motors not visible on the bus: {sorted(missing)}")

        results: Dict[int, dict] = {}
        final_goals: Dict[int, int] = {}
        for mid, goal in goals.items():
            r = readings[mid]
            if r.faulted:
                self.log.error("move refused: motor %d status 0x%02x (only under-voltage 0x01 is tolerated)",
                               mid, r.status)
                raise RuntimeError(f"motor {mid} reports fault status 0x{r.status:02x}; not moving")
            if not r.torque_on:
                # With torque off a goal write does nothing, so refuse rather than appear to work.
                self.log.error("move refused: motor %d has torque OFF. Run ./cli.sh hw torque on first.", mid)
                raise RuntimeError(f"motor {mid} has torque OFF; enable it with ./cli.sh hw torque on")
            try:
                clamped, was_clamped = clamp_goal(int(goal), r.range_min, r.range_max, margin)
            except ValueError as exc:
                self.log.error("move refused: motor %d: %s", mid, exc)
                raise
            if was_clamped:
                self.log.warning("motor %d: goal %d clamped to %d (calibrated %d..%d, margin %d)",
                                 mid, int(goal), clamped, r.range_min, r.range_max, margin)
            final_goals[mid] = clamped
            results[mid] = {
                "requested": int(goal),
                "goal": clamped,
                "clamped": was_clamped,
                "present": r.present,
            }
            self.log.debug("motor %d: present=%d -> goal=%d (delta %+d steps)",
                           mid, r.present, clamped, clamped - r.present)

        # Speed and acceleration go out before the goal, as in the teleop example.
        speed = max(1, min(max_speed, 3300))
        accel = max(1, min(max_accel, 254))
        self.log.info("sending: speed=%d accel=%d goals=%s", speed, accel, final_goals)
        await self._sync_write(RAM_GOAL_SPEED, [(mid, to_u16_le(speed)) for mid in final_goals])
        await self._sync_write(RAM_ACC, [(mid, bytes([accel])) for mid in final_goals])
        await self._sync_write(RAM_GOAL_POSITION, [(mid, to_u16_le(g)) for mid, g in final_goals.items()])
        self.log.info("move command sent for motors %s; check present positions with `./cli.sh hw status`",
                      sorted(final_goals))
        return results

    async def hold(self, motor_ids: List[int]) -> None:
        """Freeze motors at their present positions (goal = present). Used on overload or timeout."""
        readings = self.snapshot()
        writes = [(mid, to_u16_le(readings[mid].present)) for mid in motor_ids if mid in readings]
        if writes:
            self.log.warning("HOLD: freezing motors %s at their present positions", [m for m, _ in writes])
            await self._sync_write(RAM_GOAL_POSITION, writes)

    async def torque_on_hold(self, motor_ids: List[int]) -> None:
        """Enable torque without a jump: set goal = present first, then enable torque."""
        readings = self.snapshot()
        missing = [m for m in motor_ids if m not in readings]
        if missing:
            raise RuntimeError(f"motors not visible on the bus: {missing}")
        self.log.info("torque ON (holding current pose) for motors %s", list(motor_ids))
        await self._sync_write(RAM_GOAL_POSITION, [(m, to_u16_le(readings[m].present)) for m in motor_ids])
        await self._sync_write(RAM_TORQUE_ENABLE, [(m, b"\x01") for m in motor_ids])

    async def move_and_watch(
        self,
        goals: Dict[int, int],
        *,
        enable_motion: bool = False,
        margin: int = DEFAULT_SAFETY_MARGIN_STEPS,
        max_speed: int = DEFAULT_MAX_SPEED,
        max_accel: int = DEFAULT_MAX_ACCEL,
        thresholds: Optional[Dict[int, int]] = None,
        tolerance: int = 12,
        poll_s: float = 0.1,
    ) -> Dict[int, str]:
        """Move, then watch each motor until it arrives, overloads, faults, or times out.

        On overload, fault, or timeout, every motor still moving is held in place.
        Returns a status per motor: reached, overload, fault, missing or timeout.
        """
        results = await self.move_motors(
            goals, enable_motion=enable_motion, margin=margin, max_speed=max_speed, max_accel=max_accel)
        targets = {mid: r["goal"] for mid, r in results.items()}
        distance = max(abs(targets[m] - results[m]["present"]) for m in targets)
        timeout = max(3.0, 3.0 * distance / max(max_speed, 50) + 2.0)
        thresholds = thresholds or {}
        detectors = {m: OverloadDetector(thresholds.get(m, DEFAULT_CURRENT_THRESHOLD)) for m in targets}
        status: Dict[int, str] = {}
        self.last_peaks = {m: 0 for m in targets}
        started = asyncio.get_running_loop().time()

        while len(status) < len(targets):
            await asyncio.sleep(poll_s)
            readings = self.snapshot()
            for mid, goal in targets.items():
                if mid in status:
                    continue
                r = readings.get(mid)
                if r is not None:
                    self.last_peaks[mid] = max(self.last_peaks[mid], r.current)
                if r is None:
                    status[mid] = "missing"
                elif r.faulted:
                    status[mid] = "fault"
                    self.log.error("motor %d fault 0x%02x during move", mid, r.status)
                elif abs(r.present - goal) <= tolerance:
                    status[mid] = "reached"
                    self.log.info("motor %d reached %d (present %d)", mid, goal, r.present)
                elif detectors[mid].update(r.current, r.present):
                    status[mid] = "overload"
                    self.log.error("motor %d OVERLOAD: current %d above %d while stalled at %d",
                                   mid, r.current, detectors[mid].threshold, r.present)
                else:
                    self.log.debug("motor %d moving: present=%d goal=%d current=%d",
                                   mid, r.present, goal, r.current)
            stopping = any(s in ("overload", "fault", "missing") for s in status.values())
            elapsed = asyncio.get_running_loop().time() - started
            if stopping or elapsed > timeout:
                pending = [m for m in targets if m not in status]
                for m in pending:
                    status[m] = "timeout" if not stopping else "held"
                if pending:
                    await self.hold(pending)
                break
        self.log.info("move finished: %s", status)
        return status

    async def _sync_write(self, address: int, motors: List[Tuple[int, bytes]]) -> None:
        if not motors:
            return
        from target.gen_python.protobuf.station import commands as station_commands, drivers  # noqa: WPS433
        from software.station.shared.station_py import send_commands  # noqa: WPS433

        self.log.debug("sync_write addr=0x%02x bus=%s motors=%s", address, self.bus_serial,
                       [(mid, val.hex()) for mid, val in motors])
        st = self._st3215
        cmd = st.Command(
            target_bus_serial=self.bus_serial,
            sync_write=st.ST3215SyncWriteCommand(
                address=address,
                motors=[st.ST3215SyncWriteCommand_MotorWrite(motor_id=mid, value=val) for mid, val in motors],
            ),
        )
        driver_cmd = station_commands.DriverCommand(
            type=drivers.StationCommandType.STC_ST3215_COMMAND,
            body=cmd.encode(),
        )
        await send_commands(self.client, [driver_cmd])


# ---------------------------------------------------------------------------
# Synchronous facade for the MCP server (which is not asyncio-based).
# ---------------------------------------------------------------------------

class ElRobotHardwareSync:
    """Runs ElRobotHardware on a private event loop thread."""

    def __init__(self, **kwargs):
        self._hw = ElRobotHardware(**kwargs)
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, name="elrobot-loop", daemon=True)
        self._thread.start()

    def _run(self, coro, timeout: float = 30.0):
        try:
            return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout)
        except Exception as exc:
            # Full traceback goes to the log file only; the console gets the short message.
            logging.getLogger("elrobot.hw").debug("hardware call failed: %r", exc, exc_info=True)
            raise

    def connect(self, timeout_s: float = 10.0) -> None:
        self._run(self._hw.connect(timeout_s), timeout=timeout_s + 5)

    def snapshot(self) -> Dict[int, MotorReading]:
        return self._run(self._hw.read())

    def set_torque(self, motor_ids: List[int], enable: bool) -> None:
        self._run(self._hw.set_torque(motor_ids, enable))

    def move_motors(self, goals: Dict[int, int], **kwargs) -> Dict[int, dict]:
        return self._run(self._hw.move_motors(goals, **kwargs))

    def move_and_watch(self, goals: Dict[int, int], **kwargs) -> Dict[int, str]:
        # Watching takes longer than the default call timeout, so allow the move's own timeout.
        return self._run(self._hw.move_and_watch(goals, **kwargs), timeout=120)

    @property
    def last_peaks(self) -> Dict[int, int]:
        return dict(self._hw.last_peaks)

    def torque_on_hold(self, motor_ids: List[int]) -> None:
        self._run(self._hw.torque_on_hold(motor_ids))

    def hold(self, motor_ids: List[int]) -> None:
        self._run(self._hw.hold(motor_ids))

    def close(self) -> None:
        try:
            self._run(self._hw.close(), timeout=5)
        finally:
            # Cancel and await anything left pending (e.g. the SDK's reconnect loop after a
            # failed connect), so the interpreter does not warn about destroyed tasks.
            async def _drain():
                me = asyncio.current_task()
                pending = [t for t in asyncio.all_tasks() if t is not me]
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)

            try:
                asyncio.run_coroutine_threadsafe(_drain(), self._loop).result(timeout=5)
            except Exception:  # noqa: BLE001 - shutdown is best effort
                logging.getLogger("elrobot.hw").debug("task drain on close failed", exc_info=True)
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=5)
