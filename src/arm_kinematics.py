"""ElRobot forward and inverse kinematics from the follower URDF (NumPy only, no motion).

Frames
  base   URDF base_link: origin under the first motor, +z up. At all-zero joint
         angles the arm rises ~219 mm and reaches along +y (fingertips at y ~363 mm).
  tool   the closed fingertips (TCP). Offset from the Gripper_Base link, configurable
         in config/calibration.json -> joints.tcp_offset_mm (default from the jaw meshes).

Motor steps <-> URDF radians (ST3215, 4096 steps per turn):
    rad = direction * wrap(steps - zero_steps) * 2*pi / 4096
The reading wraps from 4095 to 0 within one turn, and a joint's working range can cross that
point (range min > max, e.g. 3726..1565). wrap() keeps the difference in -2048..2047 steps,
to_steps() returns 0..4095, and step_in_range()/step_delta() handle such ranges.
zero_steps and direction per motor live in config/calibration.json -> joints. Until they
are measured on the arm (./cli.sh calib zero, then calib fit), every Cartesian number is
a guess: check `joints.measured` before trusting it.

Nothing here talks to the arm. The caller decides whether to move.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
URDF_PATH = ROOT / "external" / "norma-core" / "hardware" / "elrobot" / "simulation" / "elrobot_follower.urdf"

STEPS_PER_TURN = 4096
ARM_MOTORS = (1, 2, 3, 4, 5, 6, 7)          # motor 8 is the gripper, not part of the chain
TIP_LINK = "Gripper_Base_v1_1"
# Closed fingertip in the Gripper_Base frame, from the jaw meshes (tips end at y = 363 mm at zero pose,
# the Gripper_Base origin is at y = 259.6 mm, the jaws are centred on x ~ 3.7 mm, z ~ 219 mm).
DEFAULT_TCP_OFFSET_MM = (0.8, 103.5, 0.0)


def _rot(axis: np.ndarray, angle: float) -> np.ndarray:
    a = axis / np.linalg.norm(axis)
    x, y, z = a
    c, s, C = math.cos(angle), math.sin(angle), 1 - math.cos(angle)
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])


def _rpy(r: float, p: float, y: float) -> np.ndarray:
    return _rot(np.array([0, 0, 1.0]), y) @ _rot(np.array([0, 1.0, 0]), p) @ _rot(np.array([1.0, 0, 0]), r)


def _tf(R: np.ndarray, t: Sequence[float]) -> np.ndarray:
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


@dataclass
class _Joint:
    name: str
    origin: np.ndarray            # 4x4, parent link -> joint frame
    axis: Optional[np.ndarray]    # None for fixed joints
    lower: float = -math.pi
    upper: float = math.pi
    motor: Optional[int] = None


class ArmModel:
    """Serial chain base_link -> Gripper_Base (motors 1..7) parsed from the URDF."""

    def __init__(self, urdf: Path = URDF_PATH, tcp_offset_mm: Sequence[float] = DEFAULT_TCP_OFFSET_MM):
        if not Path(urdf).exists():
            raise FileNotFoundError(f"URDF not found: {urdf}. Run ./cli.sh sync to fetch the norma-core submodule.")
        root = ET.parse(urdf).getroot()
        by_parent = {}
        for j in root.findall("joint"):
            if j.get("type") == "prismatic" or j.get("name") == "rev_motor_08":
                continue  # gripper jaws: not part of the positioning chain
            by_parent[j.find("parent").get("link")] = j
        self.chain: List[_Joint] = []
        link = "base_link"
        while link != TIP_LINK:
            if link not in by_parent:
                raise ValueError(f"URDF chain breaks at link {link!r}")
            j = by_parent[link]
            o = j.find("origin")
            xyz = [float(v) for v in (o.get("xyz", "0 0 0") if o is not None else "0 0 0").split()]
            rpy = [float(v) for v in (o.get("rpy", "0 0 0") if o is not None else "0 0 0").split()]
            joint = _Joint(j.get("name"), _tf(_rpy(*rpy), xyz), None)
            if j.get("type") == "revolute":
                joint.axis = np.array([float(v) for v in j.find("axis").get("xyz").split()])
                lim = j.find("limit")
                joint.lower, joint.upper = float(lim.get("lower")), float(lim.get("upper"))
                joint.motor = int(joint.name.rsplit("_", 1)[-1])
            self.chain.append(joint)
            link = j.find("child").get("link")
        self.revolute = [j for j in self.chain if j.axis is not None]
        if [j.motor for j in self.revolute] != list(ARM_MOTORS):
            raise ValueError(f"expected motors 1..7 in the chain, got {[j.motor for j in self.revolute]}")
        self.tcp_offset = np.asarray(tcp_offset_mm, dtype=float) / 1000.0
        self.lower = np.array([j.lower for j in self.revolute])
        self.upper = np.array([j.upper for j in self.revolute])

    # -- forward ---------------------------------------------------------------

    def fk(self, q: Sequence[float]) -> np.ndarray:
        """4x4 pose of the TCP in the base frame (metres) for joint angles q (7 radians)."""
        T = np.eye(4)
        k = 0
        for j in self.chain:
            T = T @ j.origin
            if j.axis is not None:
                T = T @ _tf(_rot(j.axis, float(q[k])), (0, 0, 0))
                k += 1
        return T @ _tf(np.eye(3), self.tcp_offset)

    def tcp(self, q: Sequence[float]) -> np.ndarray:
        """TCP position in the base frame, metres."""
        return self.fk(q)[:3, 3]

    def approach(self, q: Sequence[float]) -> np.ndarray:
        """Unit vector the fingers point along (Gripper_Base +y) in the base frame."""
        return self.fk(q)[:3, 1]

    # -- inverse ---------------------------------------------------------------

    def _error(self, q, target, down_weight):
        e = target - self.tcp(q)
        if down_weight > 0:
            # Fingers pointing straight down: approach x (0,0,-1) = 0.
            e = np.concatenate([e, down_weight * np.cross(self.approach(q), [0.0, 0.0, -1.0])])
        return e

    def _jacobian(self, q, target, down_weight, h=1e-6):
        e0 = self._error(q, target, down_weight)
        J = np.zeros((e0.size, len(q)))
        for i in range(len(q)):
            dq = np.array(q, dtype=float)
            dq[i] += h
            J[:, i] = -(self._error(dq, target, down_weight) - e0) / h
        return J, e0

    def ik(self, target_m: Sequence[float], seed: Sequence[float], *, lower=None, upper=None,
           locked: Sequence[int] = (), point_down: bool = False, down_weight: float = 0.05,
           iters: int = 200, tol_m: float = 5e-4) -> Tuple[np.ndarray, float]:
        """Damped least squares IK for the TCP position (and optionally fingers down).

        Returns (q, position error in metres). `locked` lists motor ids held at the seed
        value (e.g. 7, wrist roll: it does not move the fingertip). Joint angles stay inside
        lower/upper (defaults: URDF limits). Prefers small motion away from the seed."""
        target = np.asarray(target_m, dtype=float)
        lo = self.lower if lower is None else np.asarray(lower, dtype=float)
        hi = self.upper if upper is None else np.asarray(upper, dtype=float)
        q = np.clip(np.asarray(seed, dtype=float), lo, hi)
        free = np.array([m not in locked for m in ARM_MOTORS])
        w = down_weight if point_down else 0.0
        lam = 0.02
        for _ in range(iters):
            J, e = self._jacobian(q, target, w)
            if np.linalg.norm(e[:3]) < tol_m and (w == 0 or np.linalg.norm(e[3:]) < 0.02 * w):
                break
            Jf = J[:, free]
            dq_f = Jf.T @ np.linalg.solve(Jf @ Jf.T + lam ** 2 * np.eye(Jf.shape[0]), e)
            dq = np.zeros_like(q)
            dq[free] = np.clip(dq_f, -0.2, 0.2)
            q_new = np.clip(q + dq, lo, hi)
            if np.linalg.norm(self._error(q_new, target, w)) < np.linalg.norm(e):
                q, lam = q_new, max(lam * 0.7, 1e-3)
            else:
                lam = min(lam * 2.0, 1.0)
        return q, float(np.linalg.norm(target - self.tcp(q)))

    def solve(self, target_m: Sequence[float], seed: Sequence[float], *, tries: int = 8,
              ok_m: float = 2e-3, **kw) -> Tuple[np.ndarray, float]:
        """ik() from the seed, then from zero and random poses if it misses. Among solutions within
        ok_m, returns the one closest to the seed (least motion); otherwise the smallest error."""
        lo = self.lower if kw.get("lower") is None else np.asarray(kw["lower"])
        hi = self.upper if kw.get("upper") is None else np.asarray(kw["upper"])
        rng = np.random.default_rng(0)
        seed = np.asarray(seed, dtype=float)
        seeds = [seed, np.clip(np.zeros(7), lo, hi)] + [rng.uniform(lo * 0.7 + hi * 0.3, lo * 0.3 + hi * 0.7)
                                                        for _ in range(max(tries - 2, 0))]
        locked_idx = [i for i, m in enumerate(ARM_MOTORS) if m in kw.get("locked", ())]
        for s in seeds[1:]:
            s[locked_idx] = seed[locked_idx]  # locked joints stay where the arm is in every retry
        best = None
        for s in seeds:
            q, err = self.ik(target_m, s, **kw)
            if err <= ok_m:
                key = (0, float(np.linalg.norm(q - seed)))
            else:
                key = (1, err)
            if best is None or key < best[0]:
                best = (key, q, err)
            if s is seed and err <= ok_m:
                break  # the nearest solution: no need to search further
        return best[1], best[2]


# -- motor steps <-> radians ----------------------------------------------------

@dataclass
class JointCalibration:
    zero_steps: Dict[int, int]
    direction: Dict[int, int]

    @classmethod
    def from_config(cls, joints_cfg: dict) -> "JointCalibration":
        motors = joints_cfg.get("motors", {})
        return cls({m: int(motors.get(str(m), {}).get("zero_steps", 2048)) for m in ARM_MOTORS},
                   {m: int(motors.get(str(m), {}).get("direction", 1)) for m in ARM_MOTORS})

    def to_radians(self, steps: Dict[int, int]) -> np.ndarray:
        return np.array([self.to_radians_one(m, steps[m]) for m in ARM_MOTORS])

    def to_steps(self, q: Sequence[float]) -> Dict[int, int]:
        return {m: int(round(self.zero_steps[m] + self.direction[m] * q[i] * STEPS_PER_TURN / (2 * math.pi)))
                % STEPS_PER_TURN for i, m in enumerate(ARM_MOTORS)}

    def limits_from_ranges(self, ranges: Dict[int, Tuple[int, int]], model: ArmModel) -> Tuple[np.ndarray, np.ndarray]:
        """Joint limits (rad): the URDF limits intersected with each motor's calibrated step range."""
        lo, hi = model.lower.copy(), model.upper.copy()
        for i, m in enumerate(ARM_MOTORS):
            if m not in ranges:
                continue
            span = (ranges[m][1] - ranges[m][0]) % STEPS_PER_TURN  # steps from min up to max, across 4095->0
            if span == 0:
                continue
            start = wrap_steps(ranges[m][0] - self.zero_steps[m])
            start -= round((start + span / 2) / STEPS_PER_TURN) * STEPS_PER_TURN  # range centred nearest zero
            a = self.direction[m] * start * 2 * math.pi / STEPS_PER_TURN
            b = self.direction[m] * (start + span) * 2 * math.pi / STEPS_PER_TURN
            lo[i], hi[i] = max(lo[i], min(a, b)), min(hi[i], max(a, b))
        return lo, hi

    def to_radians_one(self, motor: int, steps: int) -> float:
        return self.direction[motor] * wrap_steps(steps - self.zero_steps[motor]) * 2 * math.pi / STEPS_PER_TURN


def wrap_steps(d: float) -> float:
    """A step difference folded into -2048..2047 (the reading wraps from 4095 to 0)."""
    return (d + STEPS_PER_TURN // 2) % STEPS_PER_TURN - STEPS_PER_TURN // 2


def step_delta(frm: int, to: int) -> int:
    """Shortest signed step change from one reading to another."""
    return int(wrap_steps(to - frm))


def step_in_range(steps: int, rng_min: int, rng_max: int) -> bool:
    """True if a reading lies in a motor range; min > max means the range crosses 4095 -> 0."""
    if rng_min <= rng_max:
        return rng_min <= steps <= rng_max
    return steps >= rng_min or steps <= rng_max


# -- base frame <-> table frame -------------------------------------------------

@dataclass
class BaseInTable:
    """Where the arm base sits on the table: table = Rz(yaw) * base_xy + (x, y); z_table = z_base + z."""
    x_mm: float = 0.0
    y_mm: float = 0.0
    yaw_deg: float = 0.0
    z_mm: float = 0.0

    @classmethod
    def from_config(cls, cfg: dict) -> "BaseInTable":
        return cls(*(float(cfg.get(k, 0.0)) for k in ("x_mm", "y_mm", "yaw_deg", "z_mm")))

    def _R(self) -> np.ndarray:
        a = math.radians(self.yaw_deg)
        return np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])

    def base_to_table(self, p_base_m: Sequence[float]) -> np.ndarray:
        p = np.asarray(p_base_m, dtype=float) * 1000.0
        xy = self._R() @ p[:2] + [self.x_mm, self.y_mm]
        return np.array([xy[0], xy[1], p[2] + self.z_mm])

    def table_to_base(self, p_table_mm: Sequence[float]) -> np.ndarray:
        p = np.asarray(p_table_mm, dtype=float)
        xy = self._R().T @ (p[:2] - [self.x_mm, self.y_mm])
        return np.array([xy[0], xy[1], p[2] - self.z_mm]) / 1000.0


def fit_base_in_table(base_pts_m: Sequence[Sequence[float]], table_pts_mm: Sequence[Sequence[float]]
                      ) -> Tuple[BaseInTable, float, List[float]]:
    """Least-squares 2D rigid fit (Kabsch) + z offset from touched points.

    base_pts_m: TCP positions from FK (base frame, metres); table_pts_mm: the same points in the
    table frame (z = 0 on the table). Needs >= 2 points; use >= 4 for a residual that means something.
    Returns (transform, rms error mm, per-point error mm)."""
    B = np.asarray(base_pts_m, dtype=float) * 1000.0
    T = np.asarray(table_pts_mm, dtype=float)
    if len(B) < 2 or len(B) != len(T):
        raise ValueError("need at least 2 matching points")
    if T.shape[1] == 2:
        T = np.hstack([T, np.zeros((len(T), 1))])
    bc, tc = B[:, :2].mean(0), T[:, :2].mean(0)
    H = (B[:, :2] - bc).T @ (T[:, :2] - tc)
    U, _, Vt = np.linalg.svd(H)
    D = np.diag([1.0, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T
    t = tc - R @ bc
    fit = BaseInTable(float(t[0]), float(t[1]), math.degrees(math.atan2(R[1, 0], R[0, 0])),
                      float(np.mean(T[:, 2] - B[:, 2])))
    errs = [float(np.linalg.norm(fit.base_to_table(b / 1000.0) - tp)) for b, tp in zip(B, T)]
    return fit, float(math.sqrt(np.mean(np.square(errs)))), errs


def refine_joint_zeros(model: ArmModel, calib: JointCalibration, samples: Sequence[Tuple[Dict[int, int], Sequence[float]]],
                       motors: Sequence[int] = (2, 3, 4), sign_motors: Sequence[int] = (1, 2, 3, 4),
                       try_directions: bool = True, iters: int = 40
                       ) -> Tuple[JointCalibration, BaseInTable, float, List[float]]:
    """Fit motor zero offsets (and optionally directions) plus the base pose from touched points.

    samples: [(motor steps {1..7: steps}, table point (x, y, z) mm), ...]. Every sample is a
    fingertip touch at a known table point. Unknowns: 4 base parameters + one zero per motor
    in `motors`, so use clearly more points than that (>= 8, touching each tag from two
    different arm poses is the cheapest way). Motor 1's zero is not fitted: it turns the
    whole arm about the vertical axis, exactly like the base yaw, so the yaw absorbs it.
    Directions: all 2^len(sign_motors) sign combinations are tried and the best fit is kept.
    Returns (calibration, base, rms mm, per-point error mm)."""
    steps = [s for s, _ in samples]
    table = [list(t) + [0.0] * (3 - len(t)) for _, t in samples]
    if len(samples) < len(motors) + 4:
        raise ValueError(f"{len(samples)} points cannot fix {len(motors)} zeros + 4 base parameters; "
                         f"touch at least {len(motors) + 5}")

    def residual(cal: JointCalibration) -> Tuple[np.ndarray, BaseInTable, float, List[float]]:
        pts = [model.tcp(cal.to_radians(s)) for s in steps]
        base, rms, errs = fit_base_in_table(pts, table)
        r = np.concatenate([base.base_to_table(p) - np.asarray(t) for p, t in zip(pts, table)])
        return r, base, rms, errs

    def solve_zeros(start: JointCalibration):
        cal = JointCalibration(dict(start.zero_steps), dict(start.direction))
        lam = 1.0
        r, base, rms, errs = residual(cal)
        for _ in range(iters):
            J = np.zeros((r.size, len(motors)))
            for k, m in enumerate(motors):
                probe = JointCalibration(dict(cal.zero_steps), cal.direction)
                probe.zero_steps[m] += 4
                J[:, k] = (residual(probe)[0] - r) / 4
            step = -np.linalg.solve(J.T @ J + lam * np.eye(len(motors)), J.T @ r)
            trial = JointCalibration(dict(cal.zero_steps), cal.direction)
            for k, m in enumerate(motors):
                trial.zero_steps[m] = int(round(cal.zero_steps[m] + np.clip(step[k], -400, 400)))
            r2, b2, rms2, e2 = residual(trial)
            if rms2 < rms - 1e-3:
                cal, r, base, rms, errs, lam = trial, r2, b2, rms2, e2, max(lam * 0.5, 1e-3)
            else:
                lam *= 4
                if lam > 1e6:
                    break
        return cal, base, rms, errs

    combos = [calib.direction]
    if try_directions:
        combos = []
        for bits in range(2 ** len(sign_motors)):
            d = dict(calib.direction)
            for k, m in enumerate(sign_motors):
                d[m] = -1 if bits >> k & 1 else 1
            combos.append(d)
    best = None
    for d in combos:
        result = solve_zeros(JointCalibration(dict(calib.zero_steps), d))
        if best is None or result[2] < best[2]:
            best = result
    return best


# -- Cartesian paths (pure: the caller sends the goals) --------------------------
#
# A move is a list of steps (label, table point mm, {motor: goal steps 1..7}, mode):
#   mode "stream": a point on a straight segment, sent in a steady stream without waiting
#   mode "watch":  a joint move that is sent and then watched until it arrives (wrist turn)

GOTO_TRAVEL_Z_MM = 150.0     # lift to this height before moving sideways, then descend
GOTO_MIN_Z_MM = 50.0         # never aim lower than this (plus the fit error) above the table
GOTO_RANGE_MARGIN = 20       # steps kept away from each motor's range ends (same as clamp_goal)
GOTO_MAX_IK_ERR_MM = 5.0
PATH_STEP_MM = 5.0           # distance between streamed points
PATH_MAX_JUMP_STEPS = 120    # a bigger change of one motor between neighbouring points = IK flipped pose
LINE_STEP_MM = PATH_STEP_MM  # kept for callers of the first version


def _check_goals(label: str, goals: Dict[int, int], ranges: Dict[int, Tuple[int, int]]) -> None:
    for m in ARM_MOTORS:
        lo_s, hi_s = ranges[m]
        if not lo_s + GOTO_RANGE_MARGIN <= goals[m] <= hi_s - GOTO_RANGE_MARGIN:
            raise ValueError(f"{label}: motor {m} goal {goals[m]} is outside its range "
                             f"{lo_s}..{hi_s} (minus {GOTO_RANGE_MARGIN})")


def plan_cartesian_path(model: ArmModel, calib: JointCalibration, base: BaseInTable,
                        present: Dict[int, int], ranges: Dict[int, Tuple[int, int]],
                        corners: Sequence[Tuple[str, Sequence[float]]], *, point_down: bool = False,
                        fit_rms_mm: float = 0.0, step_mm: float = PATH_STEP_MM,
                        travel_z_mm: float = GOTO_TRAVEL_Z_MM, min_z_mm: float = GOTO_MIN_Z_MM
                        ) -> List[Tuple[str, List[float], Dict[int, int], str]]:
    """Plan: lift straight up to travel_z at the current spot, then straight segments through
    `corners` [(name, table point mm), ...], every point step_mm apart. Every point is checked
    before anything moves: height (min_z + fit error, except the lift which only goes up), reach
    (IK error <= 5 mm), motor ranges (never clamped) and no motor jumping more than
    PATH_MAX_JUMP_STEPS between neighbours. With point_down the wrist turns down once, above the
    first corner at travel height ("watch" step). Motor 7 stays where it is. Raises ValueError instead of guessing."""
    if not 2.0 <= step_mm <= 20.0:
        raise ValueError("step must be 2-20 mm")
    floor = min_z_mm + max(fit_rms_mm, 0.0)
    for name, c in corners:
        if c[2] < floor:
            raise ValueError(f"{name} z {c[2]:.0f} mm is below the allowed {floor:.0f} mm "
                             f"({min_z_mm:.0f} mm + fit error {fit_rms_mm:.0f} mm)")
    for m in ARM_MOTORS:
        lo_s, hi_s = ranges.get(m, (0, 0))
        if hi_s - lo_s <= 2 * GOTO_RANGE_MARGIN:
            raise ValueError(f"motor {m} range {lo_s}..{hi_s} is not a valid calibrated range; "
                             "recalibrate in the Station console")
    lo, hi = calib.limits_from_ranges(ranges, model)
    q = calib.to_radians(present)
    prev = dict(present)
    here = base.base_to_table(model.tcp(q))
    steps: List[Tuple[str, List[float], Dict[int, int], str]] = []

    def solve(label: str, p: np.ndarray, down: bool) -> Dict[int, int]:
        nonlocal q
        q, err = model.solve(base.table_to_base(p), q, lower=lo, upper=hi, point_down=down, locked=(7,))
        if err * 1000 > GOTO_MAX_IK_ERR_MM:
            raise ValueError(f"{label} ({p[0]:.0f}, {p[1]:.0f}, {p[2]:.0f}) mm is out of reach "
                             f"(IK error {err * 1000:.0f} mm)")
        goals = calib.to_steps(q)
        goals[7] = present[7]
        _check_goals(label, goals, ranges)
        return goals

    def segment(name: str, a: np.ndarray, b: np.ndarray, down: bool) -> None:
        nonlocal prev
        n = int(math.ceil(float(np.linalg.norm(b - a)) / step_mm))
        for i in range(1, n + 1):
            p = a + (b - a) * i / n
            label = f"{name} {i}/{n}"
            goals = solve(label, p, down)
            jump = max(ARM_MOTORS, key=lambda m: abs(goals[m] - prev[m]))
            if abs(goals[jump] - prev[jump]) > PATH_MAX_JUMP_STEPS:
                raise ValueError(f"{label}: motor {jump} would jump {goals[jump] - prev[jump]:+d} steps between "
                                 "neighbouring points (the arm would change pose); try another path")
            steps.append((label, [float(v) for v in p], goals, "stream"))
            prev = goals

    # Never travel sideways below the safety floor, whatever travel_z_mm was asked for.
    travel = max(travel_z_mm, floor, max(c[2] for _, c in corners))
    top = np.array([here[0], here[1], travel])
    segment("lift", here, top, False)
    first = np.asarray(corners[0][1], dtype=float)
    above = np.array([first[0], first[1], travel])
    segment("across", top, above, False)
    if point_down:
        goals = solve("turn wrist down", above, True)
        steps.append(("turn wrist down", [float(v) for v in above], goals, "watch"))
        prev = goals
    pos = above
    for name, c in corners:
        c = np.asarray(c, dtype=float)
        segment(name, pos, c, point_down)
        pos = c
    if not steps:
        raise ValueError("already there")
    return steps


def plan_cartesian_goto(model: ArmModel, calib: JointCalibration, base: BaseInTable,
                        present: Dict[int, int], ranges: Dict[int, Tuple[int, int]],
                        target_table_mm: Sequence[float], **kw) -> List[Tuple[str, List[float], Dict[int, int], str]]:
    """Lift, across at travel height, then straight down to the target. See plan_cartesian_path."""
    return plan_cartesian_path(model, calib, base, present, ranges, [("descend", target_table_mm)], **kw)


def plan_cartesian_line(model: ArmModel, calib: JointCalibration, base: BaseInTable,
                        present: Dict[int, int], ranges: Dict[int, Tuple[int, int]],
                        start_mm: Sequence[float], end_mm: Sequence[float], **kw
                        ) -> List[Tuple[str, List[float], Dict[int, int], str]]:
    """Like plan_cartesian_goto to start_mm, then along the straight line to end_mm."""
    return plan_cartesian_path(model, calib, base, present, ranges,
                               [("descend", start_mm), ("line", end_mm)], **kw)
