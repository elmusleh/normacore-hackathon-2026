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
        self.log = logger or logging.getLogger("elrobot")
        self.client = None
        self.bus_serial: Optional[str] = None
        self._queue: Optional[asyncio.Queue] = None
        self._latest = None  # latest decoded st3215.InferenceStateReader

    # -- connection ---------------------------------------------------------

    async def connect(self, timeout_s: float = 10.0) -> None:
        _ensure_sdk_on_path(self.root)
        from software.station.shared.station_py import new_station_client  # noqa: WPS433
        from target.gen_python.protobuf.drivers.st3215 import st3215  # noqa: WPS433

        self._st3215 = st3215
        self.client = await new_station_client(self.server, self.log)
        self._queue = asyncio.Queue()
        self._err_queue = self.client.follow("st3215/inference", self._queue)
        await self._wait_for_frame(timeout_s)
        self.bus_serial = self._resolve_bus(self.bus_request)

    async def _wait_for_frame(self, timeout_s: float) -> None:
        deadline = asyncio.get_running_loop().time() + timeout_s
        while self._latest is None:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise RuntimeError(f"no st3215/inference frames from station {self.server} within {timeout_s}s")
            try:
                entry = await asyncio.wait_for(self._queue.get(), timeout=remaining)
            except asyncio.TimeoutError:
                continue
            if entry is None:
                raise RuntimeError("st3215/inference stream closed by station")
            self._latest = self._st3215.InferenceStateReader(entry.Data)

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
        if not serials:
            raise RuntimeError("no ST3215 bus visible on the station")
        if requested == "auto":
            if len(serials) != 1:
                raise RuntimeError(f"--bus auto needs exactly one bus, found {serials}")
            return serials[0]
        if requested not in serials:
            raise RuntimeError(f"bus {requested!r} not on station; visible: {serials}")
        return requested

    async def close(self) -> None:
        if self.client is not None:
            try:
                self.client.close_connection()
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
        for m in bus.get_motors() or []:
            if m is None:
                continue
            mid = m.get_id()
            if mid not in ELROBOT_MOTOR_IDS:
                continue
            readings[mid] = parse_motor_state(
                mid, bytes(m.get_state()), m.get_range_min(), m.get_range_max(),
            )
        return readings

    # -- writes -------------------------------------------------------------

    async def set_torque(self, motor_ids: List[int], enable: bool) -> None:
        """Enable or disable torque. Disabling makes the arm go limp."""
        value = b"\x01" if enable else b"\x00"
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
        if not enable_motion:
            raise PermissionError("motion disabled: pass enable_motion=True to move the real arm")
        unknown = set(goals) - set(ELROBOT_MOTOR_IDS)
        if unknown:
            raise ValueError(f"not ElRobot motors: {sorted(unknown)}")

        readings = self.snapshot()
        missing = set(goals) - set(readings)
        if missing:
            raise RuntimeError(f"motors not visible on the bus: {sorted(missing)}")

        results: Dict[int, dict] = {}
        final_goals: Dict[int, int] = {}
        for mid, goal in goals.items():
            r = readings[mid]
            if r.faulted:
                raise RuntimeError(f"motor {mid} reports fault status 0x{r.status:02x}; not moving")
            clamped, was_clamped = clamp_goal(int(goal), r.range_min, r.range_max, margin)
            final_goals[mid] = clamped
            results[mid] = {
                "requested": int(goal),
                "goal": clamped,
                "clamped": was_clamped,
                "present": r.present,
            }

        # Speed and acceleration go out before the goal, as in the teleop example.
        speed = max(1, min(max_speed, 3300))
        accel = max(1, min(max_accel, 254))
        await self._sync_write(RAM_GOAL_SPEED, [(mid, to_u16_le(speed)) for mid in final_goals])
        await self._sync_write(RAM_ACC, [(mid, bytes([accel])) for mid in final_goals])
        await self._sync_write(RAM_GOAL_POSITION, [(mid, to_u16_le(g)) for mid, g in final_goals.items()])
        return results

    async def _sync_write(self, address: int, motors: List[Tuple[int, bytes]]) -> None:
        if not motors:
            return
        from target.gen_python.protobuf.station import commands as station_commands, drivers  # noqa: WPS433
        from software.station.shared.station_py import send_commands  # noqa: WPS433

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
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout)

    def connect(self, timeout_s: float = 10.0) -> None:
        self._run(self._hw.connect(timeout_s), timeout=timeout_s + 5)

    def snapshot(self) -> Dict[int, MotorReading]:
        return self._run(self._hw.read())

    def set_torque(self, motor_ids: List[int], enable: bool) -> None:
        self._run(self._hw.set_torque(motor_ids, enable))

    def move_motors(self, goals: Dict[int, int], **kwargs) -> Dict[int, dict]:
        return self._run(self._hw.move_motors(goals, **kwargs))

    def close(self) -> None:
        self._run(self._hw.close())
        self._loop.call_soon_threadsafe(self._loop.stop)
