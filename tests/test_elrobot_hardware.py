"""Unit tests for the ElRobot hardware bridge's pure safety helpers.

These do not touch hardware or the NormaCore SDK.
"""

import asyncio
import struct

import pytest

from src.elrobot_hardware import (
    ELROBOT_MOTOR_IDS,
    RAM_GOAL_POSITION,
    RAM_PRESENT_POSITION,
    RAM_STATUS,
    RAM_TORQUE_ENABLE,
    ElRobotHardware,
    MotorReading,
    clamp_goal,
    normal_position,
    parse_motor_state,
    to_u16_le,
)


def _block(present=0, goal=0, torque=1, status=0):
    buf = bytearray(0x50)
    struct.pack_into("<H", buf, RAM_PRESENT_POSITION, present)
    struct.pack_into("<H", buf, RAM_GOAL_POSITION, goal)
    buf[RAM_TORQUE_ENABLE] = torque
    buf[RAM_STATUS] = status
    return bytes(buf)


def test_motor_ids_match_urdf_joints():
    assert ELROBOT_MOTOR_IDS == tuple(range(1, 9))


def test_normal_position_strips_sign_flag():
    assert normal_position(0x0800) == 0x0800
    # Sign bit set with magnitude 1 -> 4095 (one step below zero wraps back).
    assert normal_position(0x8001) == 4095
    assert normal_position(0x8000) == 0


def test_clamp_keeps_goal_inside_margin():
    assert clamp_goal(1000, 500, 3000, margin=20) == (1000, False)


def test_clamp_pulls_goal_back_from_both_ends():
    assert clamp_goal(0, 500, 3000, margin=20) == (520, True)
    assert clamp_goal(4095, 500, 3000, margin=20) == (2980, True)


def test_clamp_refuses_uncalibrated_motor():
    with pytest.raises(ValueError, match="calibration invalid"):
        clamp_goal(1000, 2048, 2048)


def test_clamp_refuses_wrap_around_arc():
    with pytest.raises(ValueError, match="calibration invalid"):
        clamp_goal(1000, 3500, 200)


def test_clamp_refuses_arc_narrower_than_margin():
    with pytest.raises(ValueError, match="narrower"):
        clamp_goal(100, 100, 130, margin=20)


def test_parse_reports_torque_off_goal_as_present():
    reading = parse_motor_state(3, _block(present=1200, goal=3000, torque=0), 500, 3000)
    assert reading.present == 1200
    assert reading.goal == 1200
    assert reading.torque_on is False


def test_undervoltage_alone_is_not_a_fault():
    reading = parse_motor_state(1, _block(status=0x01), 500, 3000)
    assert reading.faulted is False


def test_other_status_bits_are_faults():
    reading = parse_motor_state(1, _block(status=0x04), 500, 3000)
    assert reading.faulted is True


def test_to_u16_le_encodes_little_endian():
    assert to_u16_le(0x0102) == b"\x02\x01"


def test_move_is_refused_without_explicit_enable():
    hw = ElRobotHardware(server="localhost")
    with pytest.raises(PermissionError, match="enable_motion"):
        asyncio.run(hw.move_motors({1: 1000}))


def test_move_rejects_non_elrobot_motor_before_touching_bus():
    hw = ElRobotHardware(server="localhost")
    with pytest.raises(ValueError, match="not ElRobot motors"):
        asyncio.run(hw.move_motors({42: 1000}, enable_motion=True))


# ---- overload detection and goto planning ----------------------------------

from src.elrobot_hardware import OverloadDetector, plan_goto  # noqa: E402
from src.elrobot_config import DEFAULTS, _deep_merge  # noqa: E402


def test_overload_triggers_after_consecutive_stalled_high_current():
    d = OverloadDetector(threshold=100, consecutive=3, stall_steps=3)
    # Three stalled, high-current samples in a row trigger it (the first sample counts too).
    assert d.update(current=500, present=1000) is False
    assert d.update(current=500, present=1000) is False
    assert d.update(current=500, present=1000) is True


def test_overload_ignored_while_arm_is_moving():
    d = OverloadDetector(threshold=100, consecutive=3, stall_steps=3)
    for pos in range(1000, 1100, 20):  # high current but moving 20 steps per poll
        assert d.update(current=500, present=pos) is False


def test_overload_resets_when_current_drops():
    d = OverloadDetector(threshold=100, consecutive=3, stall_steps=3)
    d.update(current=500, present=1000)
    d.update(current=500, present=1000)
    d.update(current=10, present=1000)
    assert d.update(current=500, present=1000) is False


def test_overload_threshold_zero_disables_check():
    d = OverloadDetector(threshold=0, consecutive=1)
    for _ in range(10):
        assert d.update(current=10_000, present=500) is False


def test_overload_tracks_peak_current():
    d = OverloadDetector(threshold=0)
    for c in (10, 80, 30):
        d.update(current=c, present=100)
    assert d.peak == 80


def test_plan_goto_returns_deltas():
    assert plan_goto({1: 1000, 2: 2000}, {1: 1100, 2: 1800}, max_delta=600) == {1: 100, 2: -200}


def test_plan_goto_refuses_large_move_without_allow_flag():
    with pytest.raises(ValueError, match="allow-large"):
        plan_goto({1: 1000}, {1: 2500}, max_delta=600)


def test_plan_goto_refuses_missing_motor():
    with pytest.raises(ValueError, match="not visible"):
        plan_goto({1: 1000}, {1: 1000, 2: 1000}, max_delta=600)


def test_config_override_merges_without_losing_defaults():
    merged = _deep_merge(DEFAULTS, {"workspace": {"y_max_mm": 300.0}, "joint_map": {"2": {"joint": "x"}}})
    assert merged["workspace"]["y_max_mm"] == 300.0
    assert merged["workspace"]["x_min_mm"] == DEFAULTS["workspace"]["x_min_mm"]
    assert merged["joint_map"] == {"2": {"joint": "x"}}
    assert DEFAULTS["joint_map"] == {}  # defaults themselves are not mutated


def _watch(near_tolerance, stop_at, goal=2000, start=1500):
    """move_and_watch against a fake bus where motor 1 stops at `stop_at` with low current."""
    hw = ElRobotHardware(server="localhost")

    async def fake_move(goals, **kwargs):
        return {1: {"goal": goal, "present": start}}
    hw.move_motors = fake_move
    held = []

    async def fake_hold(ids):
        held.extend(ids)
    hw.hold = fake_hold
    hw.snapshot = lambda: {1: MotorReading(1, stop_at, goal, True, 0, 5, 500, 3500)}
    status = asyncio.run(hw.move_and_watch({1: goal}, enable_motion=True, max_speed=3000, poll_s=0.01,
                                           near_tolerance=near_tolerance, stall_s=0.05))
    return status, held


def test_move_and_watch_accepts_stopped_motor_near_goal():
    status, held = _watch(near_tolerance=40, stop_at=1975)
    assert status == {1: "near"}
    assert held == []


def test_move_and_watch_without_near_tolerance_times_out():
    status, held = _watch(near_tolerance=None, stop_at=1975)
    assert status == {1: "timeout"}
    assert held == [1]


def test_move_and_watch_does_not_accept_stop_far_from_goal():
    status, _ = _watch(near_tolerance=40, stop_at=1900)
    assert status == {1: "timeout"}
