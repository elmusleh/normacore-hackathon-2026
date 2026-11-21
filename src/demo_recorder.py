"""Record teleop demonstrations for imitation learning (ACT): follower state, follower goal, cameras.

A person drives the follower with the leader arm (teleop in the Station viewer). Each tick
(default 30 per second) stores:
  state   follower present position, motors 1-8 (raw steps)       -> observation.state
  action  follower goal register, motors 1-8 (raw steps)          -> action
          This is what teleop commanded, already in the follower's own calibration, so a policy
          that outputs it can be sent to the follower as goals unchanged.
  leader  leader present position, motors 1-8 (raw steps), for reference only
  cameras newest JPEG from each named camera (stored once per new frame, then referenced)

Only reads. Nothing here sends a command to either arm.

Episode folder (data/demos/<skill>/<time>_<food>/, gitignored: frames can show people):
  meta.json     skill, food, task text, fps, cameras, buses, follower calibration ranges, timing
  steps.npz     t, state, action, leader, cam_<name> (index into frames/<name>/, -1 = none yet)
  frames/<name>/<k>.jpg
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from elrobot_hardware import ELROBOT_MOTOR_IDS, MotorReading

log = logging.getLogger("elrobot.demos")

MOTORS = list(ELROBOT_MOTOR_IDS)
NAME = re.compile(r"^[a-z0-9_-]{1,40}$")
FORMAT_VERSION = 1


class Frame:
    """A camera frame: JPEG bytes and the camera's own timestamp (to spot repeated frames)."""

    def __init__(self, jpeg: bytes, stamp: int, width: int = 0, height: int = 0):
        self.jpeg, self.stamp, self.width, self.height = jpeg, stamp, width, height


class EpisodeWriter:
    """Collects ticks in memory, then writes one episode folder."""

    def __init__(self, cameras: List[str]):
        self.cameras = list(cameras)
        self.t: List[float] = []
        self.state: List[List[int]] = []
        self.action: List[List[int]] = []
        self.leader: List[List[int]] = []
        self.cam_index: Dict[str, List[int]] = {c: [] for c in self.cameras}
        self.frames: Dict[str, List[Frame]] = {c: [] for c in self.cameras}
        self.frame_size: Dict[str, List[int]] = {}

    def __len__(self) -> int:
        return len(self.t)

    def add(self, t: float, follower: Dict[int, MotorReading], leader: Dict[int, MotorReading],
            frames: Dict[str, Optional[Frame]]) -> None:
        self.t.append(t)
        self.state.append([follower[m].present for m in MOTORS])
        self.action.append([follower[m].goal for m in MOTORS])
        self.leader.append([leader[m].present if m in leader else -1 for m in MOTORS])
        for cam in self.cameras:
            frame = frames.get(cam)
            stored = self.frames[cam]
            if frame is None:
                self.cam_index[cam].append(len(stored) - 1)  # last frame, or -1 if none yet
                continue
            if not stored or stored[-1].stamp != frame.stamp:
                stored.append(frame)
                self.frame_size.setdefault(cam, [frame.width, frame.height])
            self.cam_index[cam].append(len(stored) - 1)

    def action_changed(self) -> bool:
        """False if the follower's goal never changed: teleop was probably off."""
        a = np.asarray(self.action)
        return bool(len(a) > 1 and (a.max(axis=0) - a.min(axis=0)).max() > 5)

    def camera_fps(self) -> Dict[str, float]:
        dur = (self.t[-1] - self.t[0]) if len(self.t) > 1 else 0.0
        return {c: round((len(self.frames[c]) - 1) / dur, 1) if dur > 0 and self.frames[c] else 0.0
                for c in self.cameras}

    def save(self, folder: Path, meta: Dict[str, Any]) -> Path:
        folder.mkdir(parents=True, exist_ok=False)
        arrays = {"t": np.asarray(self.t, dtype=np.float64),
                  "state": np.asarray(self.state, dtype=np.int32),
                  "action": np.asarray(self.action, dtype=np.int32),
                  "leader": np.asarray(self.leader, dtype=np.int32)}
        for cam in self.cameras:
            arrays[f"cam_{cam}"] = np.asarray(self.cam_index[cam], dtype=np.int32)
            cam_dir = folder / "frames" / cam
            cam_dir.mkdir(parents=True)
            for k, frame in enumerate(self.frames[cam]):
                (cam_dir / f"{k}.jpg").write_bytes(frame.jpeg)
        np.savez_compressed(folder / "steps.npz", **arrays)
        duration = float(self.t[-1] - self.t[0]) if len(self.t) > 1 else 0.0
        meta = {**meta, "format_version": FORMAT_VERSION, "motors": MOTORS, "n_steps": len(self.t),
                "duration_s": round(duration, 2), "camera_frames": {c: len(self.frames[c]) for c in self.cameras},
                "camera_fps": self.camera_fps(), "frame_size": self.frame_size}
        (folder / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
        return folder


def record_episode(read_follower: Callable[[], Dict[int, MotorReading]],
                   read_leader: Callable[[], Dict[int, MotorReading]],
                   read_frames: Callable[[], Dict[str, Optional[Frame]]],
                   cameras: List[str], fps: float, should_stop: Callable[[], bool],
                   max_seconds: float = 120.0, clock: Callable[[], float] = time.monotonic,
                   sleep: Callable[[float], None] = time.sleep) -> Dict[str, Any]:
    """Tick at `fps` until should_stop() or max_seconds. Returns the writer and timing stats."""
    writer = EpisodeWriter(cameras)
    period = 1.0 / fps
    start = clock()
    next_tick = start
    late = skipped = 0
    while not should_stop() and clock() - start < max_seconds:
        follower = read_follower()
        leader = read_leader()
        if any(m not in follower for m in MOTORS):
            skipped += 1  # a motor missing from this frame; do not store a partial row
        else:
            writer.add(clock() - start, follower, leader, read_frames())
        next_tick += period
        delay = next_tick - clock()
        if delay > 0:
            sleep(delay)
        else:
            late += 1
            next_tick = clock()  # fell behind: do not try to catch up with a burst
    ticks = len(writer)
    return {"writer": writer, "ticks": ticks, "late_ticks": late, "skipped_ticks": skipped,
            "achieved_fps": round(ticks / (clock() - start), 1) if clock() > start else 0.0}


def episode_folder(root: Path, skill: str, food: str, now: Optional[dt.datetime] = None) -> Path:
    stamp = (now or dt.datetime.now()).strftime("%Y%m%d-%H%M%S")
    return root / skill / f"{stamp}_{food or 'any'}"


def task_text(skill: str, food: str) -> str:
    """The task string stored with each episode (LeRobot 'task'), e.g. 'pick grape', 'deliver'."""
    return f"{skill} {food}".strip() if food else skill


def list_episodes(root: Path) -> List[Dict[str, Any]]:
    out = []
    for meta_file in sorted(root.glob("*/*/meta.json")):
        try:
            meta = json.loads(meta_file.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        out.append({"path": str(meta_file.parent), **{k: meta.get(k) for k in
                    ("skill", "food", "n_steps", "duration_s", "achieved_fps", "camera_fps", "note")}})
    return out
