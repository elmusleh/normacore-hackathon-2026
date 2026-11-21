"""The arm's trusted action space, recorded by a human driving the follower with the leader arm.

`./cli.sh hw envelope record` samples the follower's joint positions while a person moves the
leader arm (teleop on) through every place the arm may be: above the table, over the food,
lifted, toward the person up to a safe distance. Every sampled pose is kept (thinned so poses
are at least `spacing` steps apart). Named anchors are poses the person marked on the way
("above_grape", "lifted", "face_standoff").

`check_move` is what makes it safe: a nudge may only end at a pose close to one the human
actually drove through (Chebyshev distance over motors 1-7 <= margin), or one that gets closer
to the recorded space than where the arm is now (so the arm can always come back). The check is
on whole poses, not per joint min/max, because "does it touch the table" depends on several
joints together. The gripper (motor 8) is not part of the space.

File: config/envelope.json (committed, like waypoints; valid only while arm, table and base stay put).
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple

import elrobot_config

log = logging.getLogger("elrobot.envelope")

SPACE_MOTORS = (1, 2, 3, 4, 5, 6, 7)
DEFAULT_SPACING_STEPS = 15
DEFAULT_MARGIN_STEPS = 80


def envelope_file():
    return elrobot_config.CONFIG_DIR / "envelope.json"


def pose_vector(pose: Dict[Any, int]) -> Tuple[int, ...]:
    """Motors 1-7 of a pose given as {motor: raw} (int or str keys)."""
    return tuple(int(pose[m] if m in pose else pose[str(m)]) for m in SPACE_MOTORS)


def chebyshev(a: Iterable[int], b: Iterable[int]) -> int:
    return max(abs(x - y) for x, y in zip(a, b))


class ActionSpace:
    def __init__(self, poses: List[Tuple[int, ...]], anchors: Optional[Dict[str, Dict[str, int]]] = None,
                 meta: Optional[Dict[str, Any]] = None):
        self.poses = [tuple(p) for p in poses]
        self.anchors = dict(anchors or {})
        self.meta = dict(meta or {})

    @property
    def empty(self) -> bool:
        return not self.poses

    def distance(self, pose: Dict[Any, int]) -> Optional[int]:
        """Steps from `pose` to the nearest recorded pose (largest single-motor difference)."""
        if self.empty:
            return None
        v = pose_vector(pose)
        return min(chebyshev(v, p) for p in self.poses)

    def check_move(self, current: Dict[Any, int], target: Dict[Any, int], margin: int) -> Dict[str, Any]:
        """ok if the target is within `margin` of the recorded space, or closer to it than now."""
        before, after = self.distance(current), self.distance(target)
        if after is None:
            return {"ok": False, "reason": "no action space recorded", "distance_before": None, "distance_after": None}
        ok = after <= margin or after < before
        return {"ok": ok, "distance_before": before, "distance_after": after, "margin": margin,
                "reason": "" if ok else (f"the move would leave the recorded action space "
                                         f"({after} steps from the nearest recorded pose, limit {margin})")}

    def seen_range(self) -> Dict[int, Tuple[int, int]]:
        return {m: (min(p[i] for p in self.poses), max(p[i] for p in self.poses))
                for i, m in enumerate(SPACE_MOTORS)} if self.poses else {}

    def to_dict(self) -> Dict[str, Any]:
        return {**self.meta, "motors": list(SPACE_MOTORS), "poses": [list(p) for p in self.poses],
                "anchors": self.anchors}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionSpace":
        if list(data.get("motors", SPACE_MOTORS)) != list(SPACE_MOTORS):
            raise ValueError(f"envelope motors {data.get('motors')} != {list(SPACE_MOTORS)}")
        meta = {k: v for k, v in data.items() if k not in ("motors", "poses", "anchors")}
        return cls([tuple(p) for p in data.get("poses", [])], data.get("anchors", {}), meta)


class Recorder:
    """Collects poses while the human drives the arm; keeps one every `spacing` steps of change."""

    def __init__(self, space: Optional[ActionSpace] = None, spacing: int = DEFAULT_SPACING_STEPS):
        self.space = space or ActionSpace([])
        self.spacing = spacing
        self.added = 0
        self._last: Optional[Tuple[int, ...]] = None

    def add(self, pose: Dict[Any, int]) -> bool:
        v = pose_vector(pose)
        if self._last is not None and chebyshev(v, self._last) < self.spacing:
            return False
        self.space.poses.append(v)
        self._last = v
        self.added += 1
        return True

    def anchor(self, name: str, pose: Dict[Any, int]) -> None:
        """A named pose (all motors given, gripper included). Also part of the space."""
        self.space.anchors[name] = {str(m): int(v) for m, v in pose.items()}
        self.space.poses.append(pose_vector(pose))
        self._last = pose_vector(pose)


def load_action_space() -> Optional[ActionSpace]:
    path = envelope_file()
    if not path.exists():
        return None
    try:
        return ActionSpace.from_dict(json.loads(path.read_text()))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        log.error("config/envelope.json is unreadable (%s); treating it as missing.", exc)
        return None


def save_action_space(space: ActionSpace) -> None:
    path = envelope_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    space.meta["updated"] = dt.datetime.now().isoformat(timespec="seconds")
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(space.to_dict(), separators=(",", ":")) + "\n")
    tmp.replace(path)
