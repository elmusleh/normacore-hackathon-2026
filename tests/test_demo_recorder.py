"""Tests for the teleop demonstration recorder (src/demo_recorder.py). No hardware."""

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from demo_recorder import Frame, episode_folder, list_episodes, record_episode, task_text  # noqa: E402
from elrobot_hardware import ELROBOT_MOTOR_IDS, MotorReading  # noqa: E402


def readings(present, goal):
    return {m: MotorReading(motor_id=m, present=present + m, goal=goal + m, torque_on=True, status=0,
                            current=0, range_min=1000, range_max=3000) for m in ELROBOT_MOTOR_IDS}


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, s):
        self.now += s


def run(n_ticks=10, frames_every=2, follower_missing_at=None):
    clock = Clock()
    tick = {"i": 0}

    def follower():
        i = tick["i"]
        r = readings(2000 + i, 2010 + i)
        if i == follower_missing_at:
            r.pop(3)
            tick["i"] += 1  # frames() is not called for a skipped tick
        return r

    def leader():
        return readings(1500 + tick["i"], 0)

    def frames():
        i = tick["i"]
        stamp = i // frames_every
        tick["i"] += 1
        return {"table": Frame(b"jpg%d" % stamp, stamp, 299, 224), "gripper": None}

    def stop():
        return tick["i"] >= n_ticks

    return record_episode(follower, leader, frames, ["table", "gripper"], fps=10, should_stop=stop,
                          clock=clock, sleep=clock.sleep)


def test_records_state_action_and_dedupes_frames(tmp_path):
    res = run(n_ticks=10, frames_every=2)
    w = res["writer"]
    assert res["ticks"] == 10 and res["late_ticks"] == 0
    assert w.state[0][0] == 2001 and w.action[0][0] == 2011  # present -> state, goal -> action
    assert w.leader[0][0] == 1501
    assert len(w.frames["table"]) == 5 and w.cam_index["table"][:4] == [0, 0, 1, 1]
    assert w.cam_index["gripper"] == [-1] * 10
    assert w.action_changed()

    meta = {"skill": "pick", "food": "grape", "task": task_text("pick", "grape")}
    folder = w.save(episode_folder(tmp_path, "pick", "grape"), meta)
    data = np.load(folder / "steps.npz")
    assert data["state"].shape == (10, 8) and data["action"].dtype == np.int32
    assert (folder / "frames" / "table" / "4.jpg").read_bytes() == b"jpg4"
    saved = json.loads((folder / "meta.json").read_text())
    assert saved["task"] == "pick grape" and saved["n_steps"] == 10 and saved["camera_frames"]["table"] == 5
    assert list_episodes(tmp_path)[0]["food"] == "grape"


def test_partial_reading_is_skipped_not_stored():
    res = run(n_ticks=6, follower_missing_at=2)
    assert res["skipped_ticks"] == 1 and res["ticks"] == 5


def test_teleop_off_is_detected():
    clock = Clock()
    n = {"i": 0}

    def stop():
        n["i"] += 1
        return n["i"] > 5

    res = record_episode(lambda: readings(2000, 2000), lambda: {}, lambda: {}, [], fps=10,
                         should_stop=stop, clock=clock, sleep=clock.sleep)
    assert not res["writer"].action_changed()
    assert res["writer"].leader[0] == [-1] * 8


def test_task_text():
    assert task_text("pick", "chocolate") == "pick chocolate" and task_text("deliver", "") == "deliver"
