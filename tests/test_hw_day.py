"""Flow tests for scripts/hw_day.py using a fake bridge and in-memory config.

No hardware and no Station. These catch logic errors in the hardware-day
commands (identify, jog, probe, teach, goto) before they run on the arm.
"""

import copy
import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from elrobot_hardware import MotorReading  # noqa: E402
from elrobot_config import DEFAULTS  # noqa: E402

_spec = importlib.util.spec_from_file_location("hw_day", ROOT / "scripts" / "hw_day.py")
hw_day = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hw_day)


class FakeTTY:
    def isatty(self):
        return True


class FakeBus:
    """Behaves like ElRobotHardwareSync: positions follow goals instantly, torque is tracked."""

    readings = {}
    moves = []
    peak = 50
    stall = False  # if True, the moved motor does not move (simulates a block)

    def __init__(self, server, bus):
        self.server = server

    def connect(self, timeout_s=10.0):
        pass

    def close(self):
        pass

    def snapshot(self):
        return dict(FakeBus.readings)

    def move_and_watch(self, goals, **kwargs):
        FakeBus.moves.append((dict(goals), kwargs))
        status = {}
        for m, g in goals.items():
            r = FakeBus.readings[m]
            if not r.torque_on:
                raise RuntimeError(f"motor {m} has torque OFF")
            if not FakeBus.stall:
                FakeBus.readings[m] = replace(r, present=g, goal=g)
            status[m] = "reached"
        return status

    def move_motors(self, goals, **kwargs):  # not used by the tool directly
        raise AssertionError("tool should call move_and_watch")

    def set_torque(self, ids, enable):
        for m in ids:
            FakeBus.readings[m] = replace(FakeBus.readings[m], torque_on=enable)

    def torque_on_hold(self, ids):
        for m in ids:
            FakeBus.readings[m] = replace(FakeBus.readings[m], torque_on=True)

    def hold(self, ids):
        pass

    @property
    def last_peaks(self):
        return {m: FakeBus.peak for m in FakeBus.readings}


def _fresh_reading(m, present=2000):
    return MotorReading(motor_id=m, present=present, goal=present, torque_on=True,
                        status=0, current=10, range_min=500, range_max=3500)


@pytest.fixture
def env(monkeypatch):
    """Wire hw_day to an in-memory config, waypoints and state, and a fake bridge."""
    store = {"cfg": copy.deepcopy(DEFAULTS), "waypoints": {}, "state": {"done": {}}}

    monkeypatch.setattr(hw_day, "load_config", lambda: copy.deepcopy(store["cfg"]))
    monkeypatch.setattr(hw_day, "save_config", lambda c: store.update(cfg=copy.deepcopy(c)))
    monkeypatch.setattr(hw_day, "load_waypoints", lambda: copy.deepcopy(store["waypoints"]))
    monkeypatch.setattr(hw_day, "save_waypoints", lambda w: store.update(waypoints=copy.deepcopy(w)))
    monkeypatch.setattr(hw_day, "load_state", lambda: copy.deepcopy(store["state"]))
    monkeypatch.setattr(hw_day, "save_state", lambda s: store.update(state=copy.deepcopy(s)))
    monkeypatch.setattr(hw_day, "ElRobotHardwareSync", FakeBus)
    monkeypatch.setattr(sys, "stdin", FakeTTY())

    FakeBus.readings = {m: _fresh_reading(m) for m in hw_day.MOTORS}
    FakeBus.moves = []
    FakeBus.peak = 50
    FakeBus.stall = False
    return store


def _answers(monkeypatch, *answers):
    it = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(it))


def _run(*argv):
    return hw_day.main(list(argv))


def test_identify_records_joint_and_returns_arm_to_start(env, monkeypatch, capsys):
    _answers(monkeypatch, "MOVE", "shoulder lift", "up")
    rc = _run("identify", "2")
    assert rc == 0
    assert env["cfg"]["joint_map"]["2"]["joint"] == "shoulder lift"
    assert env["cfg"]["joint_map"]["2"]["direction"] == "up"
    assert "+30 steps moved the joint +30" in env["cfg"]["joint_map"]["2"]["note"]
    # Nudged out by +30, then returned to the starting position.
    assert [g for g, _ in FakeBus.moves] == [{2: 2030}, {2: 2000}]
    assert FakeBus.readings[2].present == 2000


def test_identify_skips_motor_that_does_not_move(env, monkeypatch, capsys):
    FakeBus.stall = True
    _answers(monkeypatch, "MOVE")
    assert _run("identify", "3") == 0
    assert "3" not in env["cfg"]["joint_map"]
    assert "did not move" in capsys.readouterr().out


def test_identify_refuses_when_torque_is_off(env, monkeypatch, capsys):
    FakeBus.readings[4] = replace(FakeBus.readings[4], torque_on=False)
    _answers(monkeypatch, "MOVE")
    assert _run("identify", "4") == 1
    assert FakeBus.moves == []
    assert "torque" in capsys.readouterr().out.lower()


def test_jog_needs_move_typed(env, monkeypatch, capsys):
    _answers(monkeypatch, "no")
    assert _run("jog", "2", "100") == 0
    assert FakeBus.moves == []
    assert "Cancelled" in capsys.readouterr().out


def test_jog_moves_when_move_typed(env, monkeypatch):
    _answers(monkeypatch, "MOVE")
    assert _run("jog", "2", "100", "--speed", "300") == 0
    goals, kwargs = FakeBus.moves[-1]
    assert goals == {2: 2100}
    assert kwargs["max_speed"] == 300


def test_jog_refuses_over_limit(env, capsys):
    assert _run("jog", "2", "500") == 2
    assert FakeBus.moves == []


def test_jog_clamps_to_calibrated_range(env, monkeypatch, capsys):
    FakeBus.readings[2] = _fresh_reading(2, present=3400)
    _answers(monkeypatch, "MOVE")
    assert _run("jog", "2", "+200") == 0
    goals, _ = FakeBus.moves[-1]
    assert goals[2] == 3500 - 20  # clamped to range_max minus margin
    assert "clamped" in capsys.readouterr().out


def test_probe_current_reports_peak_and_offers_threshold(env, monkeypatch, capsys):
    FakeBus.peak = 240
    _answers(monkeypatch, "MOVE", "n")
    assert _run("probe-current", "2") == 0
    out = capsys.readouterr().out
    assert "Peak current" in out
    assert "Suggested threshold for motor 2: 480" in out
    assert env["cfg"]["current_threshold"] == {}  # answered n: nothing saved


def test_teach_then_goto_round_trip(env, monkeypatch, capsys):
    # Teach the current pose as home, then move away and go back.
    assert _run("teach", "home") == 0
    assert env["waypoints"]["home"] == {str(m): 2000 for m in hw_day.MOTORS}
    for m in hw_day.MOTORS:
        FakeBus.readings[m] = _fresh_reading(m, present=2300)
    _answers(monkeypatch, "MOVE")
    assert _run("goto", "home") == 0
    goals, _ = FakeBus.moves[-1]
    assert goals == {m: 2000 for m in hw_day.MOTORS}


def test_goto_refuses_large_move_without_flag(env, monkeypatch, capsys):
    env["waypoints"]["far"] = {str(m): 3000 for m in hw_day.MOTORS}
    FakeBus.readings = {m: _fresh_reading(m, present=500) for m in hw_day.MOTORS}
    _answers(monkeypatch, "MOVE")
    assert _run("goto", "far") == 1
    assert FakeBus.moves == []
    assert "allow-large" in capsys.readouterr().out


def test_goto_allow_large_moves(env, monkeypatch):
    env["waypoints"]["far"] = {str(m): 3000 for m in hw_day.MOTORS}
    FakeBus.readings = {m: _fresh_reading(m, present=500) for m in hw_day.MOTORS}
    _answers(monkeypatch, "MOVE")
    assert _run("goto", "far", "--allow-large") == 0
    assert FakeBus.moves[-1][0] == {m: 3000 for m in hw_day.MOTORS}


def test_goto_rejects_waypoint_missing_motors(env, capsys):
    env["waypoints"]["partial"] = {"1": 2000}
    assert _run("goto", "partial") == 2
    assert "must list all 8 motors" in capsys.readouterr().out


def test_teach_rejects_bad_name(env, capsys):
    assert _run("teach", "Bad Name") == 2
    assert env["waypoints"] == {}


def test_checklist_step5_passes_when_all_motors_mapped(env):
    assert hw_day._step_done(hw_day.STEPS[4], env["cfg"], env["state"]) is False
    for m in hw_day.MOTORS:
        env["cfg"]["joint_map"][str(m)] = {"joint": f"j{m}", "direction": "up"}
    assert hw_day._step_done(hw_day.STEPS[4], env["cfg"], env["state"]) is True


def test_stop_turns_torque_off(env, capsys):
    assert _run("stop") == 0
    assert all(not FakeBus.readings[m].torque_on for m in hw_day.MOTORS)


def test_torque_on_sets_torque_back(env, capsys):
    FakeBus.readings = {m: replace(_fresh_reading(m), torque_on=False) for m in hw_day.MOTORS}
    assert _run("torque", "on") == 0
    assert all(FakeBus.readings[m].torque_on for m in hw_day.MOTORS)
