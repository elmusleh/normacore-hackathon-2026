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
