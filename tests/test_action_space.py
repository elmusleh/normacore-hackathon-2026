"""Tests for the recorded action space (src/action_space.py) and its use in nudge_joint."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import action_space  # noqa: E402
from action_space import ActionSpace, Recorder, load_action_space, save_action_space  # noqa: E402
from test_robot_mcp import env  # noqa: E402,F401 - fixture: fake arm, config in tmp


def pose7(value, **over):
    p = {m: value for m in range(1, 8)}
    p.update({int(k[1:]): v for k, v in over.items()})
    return p


def test_distance_and_check_move():
    space = ActionSpace([tuple([2000] * 7), tuple([2100] * 7)])
    assert space.distance(pose7(2000)) == 0
    assert space.distance(pose7(2050, m2=2300)) == 200  # nearest is 2100 (m2 off by 200)
    assert space.check_move(pose7(2000), pose7(2000, m2=2070), margin=80)["ok"]
    out = space.check_move(pose7(2000), pose7(2000, m2=1800), margin=80)
    assert not out["ok"] and "leave the recorded action space" in out["reason"]
    # outside the space, a move back toward it is allowed even if still outside
    assert space.check_move(pose7(2000, m2=1700), pose7(2000, m2=1800), margin=80)["ok"]
    assert not space.check_move(pose7(2000, m2=1700), pose7(2000, m2=1650), margin=80)["ok"]


def test_recorder_thins_poses_and_keeps_anchors():
    rec = Recorder(spacing=15)
    assert rec.add(pose7(2000))
    assert not rec.add(pose7(2010))
    assert rec.add(pose7(2016))
    full = {**pose7(2200), 8: 1500}
    rec.anchor("lifted", full)
    assert rec.added == 2 and len(rec.space.poses) == 3
    assert rec.space.anchors["lifted"]["8"] == 1500


def test_save_and_load_roundtrip(env):  # noqa: F811
    _, _, tmp = env
    assert load_action_space() is None
    save_action_space(ActionSpace([tuple([2000] * 7)], {"lifted": {str(m): 2000 for m in range(1, 9)}}))
    data = json.loads((tmp / "envelope.json").read_text())
    assert data["motors"] == list(range(1, 8)) and data["poses"] == [[2000] * 7]
    space = load_action_space()
    assert space.poses == [tuple([2000] * 7)] and "lifted" in space.anchors
    (tmp / "envelope.json").write_text("{broken")
    assert load_action_space() is None


def test_nudge_refused_outside_space(env):  # noqa: F811
    tools, arm, tmp = env  # fake arm: every motor at 2000, range 1000..3000 (5% = 100 steps)
    save_action_space(ActionSpace([tuple([2000] * 7), tuple([2000, 2100, 2000, 2000, 2000, 2000, 2000])]))
    res = tools.nudge_joint(2, 5)  # to 2100: recorded
    assert res["ok"] and res["action_space_distance_steps"] == 0
    res = tools.nudge_joint(2, 5)  # to 2200: 100 from nearest > 80
    assert not res["ok"] and res["refused"] == "action_space"
    assert arm.readings[2].present == 2100
    assert tools.nudge_joint(2, -5)["ok"]  # back is fine


def test_no_space_allowed_unless_required(env, monkeypatch):  # noqa: F811
    tools, arm, _ = env
    assert tools.nudge_joint(1, 2)["ok"]
    monkeypatch.setenv("ELROBOT_REQUIRE_ENVELOPE", "1")
    res = tools.nudge_joint(1, 2)
    assert not res["ok"] and "no action space" in res["error"]


def test_get_action_space_reports_anchor_nudges(env):  # noqa: F811
    tools, arm, tmp = env
    assert tools.get_action_space()["recorded"] is False
    anchor = {str(m): 2000 for m in range(1, 9)}
    anchor["3"] = 2400
    save_action_space(ActionSpace([tuple([2000] * 7)], {"above_grape": anchor}))
    out = tools.get_action_space()
    assert out["recorded"] and out["inside"] and out["distance_now_steps"] == 0
    assert out["anchors"]["above_grape"]["nudge_percent_to_reach"]["3"] == 20.0
    assert out["anchors"]["above_grape"]["distance_steps"] == 400
    assert out["joints"]["3"]["recorded_min_percent"] == 50.0
