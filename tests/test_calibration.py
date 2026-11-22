"""Offline tests: AprilTag table frame, URDF kinematics, base fit and the calib CLI (no arm, no camera)."""

import importlib.util
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import arm_kinematics as ak  # noqa: E402
import tag_calibration as tc  # noqa: E402

needs_urdf = pytest.mark.skipif(not ak.URDF_PATH.exists(), reason="norma-core submodule not checked out")

TAGS_MM = tc.rectangle_layout(520.0, 360.0)
TAG_MM = 80.0
PX_PER_MM = 2.0
MARGIN_MM = 80.0


def _gen():
    spec = importlib.util.spec_from_file_location("generate_apriltags", ROOT / "scripts" / "generate_apriltags.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _table_canvas():
    """Top view of the table at PX_PER_MM, white, tags centred on TAGS_MM (y up = away from person)."""
    gen = _gen()
    w = int((520 + 2 * MARGIN_MM) * PX_PER_MM)
    h = int((360 + 2 * MARGIN_MM) * PX_PER_MM)
    canvas = np.full((h, w), 255, np.uint8)
    side = int(TAG_MM * PX_PER_MM)
    for tid, (x, y) in TAGS_MM.items():
        bits = np.array(gen.tag_bits(int(tid)), np.uint8) * 255
        # Canvas rows grow with +y, i.e. it is the table seen from below: store tags flipped so a
        # camera looking down (which flips v back) sees them the right way round.
        tag = np.flipud(cv2.resize(bits, (side, side), interpolation=cv2.INTER_NEAREST))
        cx, cy = (x + MARGIN_MM) * PX_PER_MM, (y + MARGIN_MM) * PX_PER_MM
        canvas[int(cy - side / 2):int(cy - side / 2) + side, int(cx - side / 2):int(cx - side / 2) + side] = tag
    # canvas pixel (c, r) = table mm ((c / s) - m, (r / s) - m): rows grow with +y, as seen from below.
    return canvas


def _render(size=(480, 360)):
    """Camera picture of the table (camera above it, on the person's side) and the true
    table-mm -> pixel homography."""
    canvas = _table_canvas()
    S = np.array([[PX_PER_MM, 0, MARGIN_MM * PX_PER_MM], [0, PX_PER_MM, MARGIN_MM * PX_PER_MM], [0, 0, 1]])
    # A camera looking down from the person's side sees +y (away) going UP the image: v = -y.
    flip = np.diag([1.0, -1.0, 1.0])
    persp = np.array([[0.62, 0.05, 60], [0.02, 0.55, 300], [0.0001, -0.0003, 1]])
    H_table_to_px = persp @ flip
    img = cv2.warpPerspective(canvas, H_table_to_px @ np.linalg.inv(S), size, borderValue=255)
    return img, H_table_to_px


def test_camera_fit_recovers_table_mm_from_pixels():
    img, H = _render()
    dets = tc.detect_tags(img)
    assert sorted(dets) == [0, 1, 2, 3]
    cam, report = tc.fit_camera(dets, TAGS_MM, TAG_MM, (img.shape[1], img.shape[0]))
    assert report["warnings"] == []
    assert report["tag_square_rms_mm"] < 3.0
    for x, y in [(100, 50), (260, 180), (480, 330), (10, 300)]:
        p = H @ [x, y, 1]
        u, v = p[0] / p[2], p[1] / p[2]
        gx, gy = cam.pixel_to_table(u, v)
        assert math.hypot(gx - x, gy - y) < 3.0
        # A half-size frame maps the same table point.
        hx, hy = cam.pixel_to_table(u / 2, v / 2, (img.shape[1] // 2, img.shape[0] // 2))
        assert math.hypot(hx - x, hy - y) < 3.0


def test_station_sized_frame_still_detects_tags():
    img, _ = _render()
    small = cv2.resize(img, (299, 224), interpolation=cv2.INTER_AREA)
    assert sorted(tc.detect_tags(small)) == [0, 1, 2, 3]


def test_mirrored_layout_and_missing_tag_are_reported():
    img, _ = _render()
    dets = tc.detect_tags(img)
    swapped = {**TAGS_MM, "1": TAGS_MM["3"], "3": TAGS_MM["1"]}  # tags 1 and 3 taped on the wrong corners
    _, report = tc.fit_camera(dets, swapped, TAG_MM, (img.shape[1], img.shape[0]))
    assert any("mirrored" in w for w in report["warnings"])
    dets.pop(2)
    with pytest.raises(ValueError, match=r"not found: \[2\]"):
        tc.fit_camera(dets, TAGS_MM, TAG_MM, (480, 360))


@needs_urdf
def test_fk_zero_pose_matches_urdf_and_jaw_meshes():
    m = ak.ArmModel()
    assert np.allclose(m.tcp(np.zeros(7)) * 1000, [3.7, 363.1, 218.9], atol=0.5)
    assert np.allclose(m.approach(np.zeros(7)), [0, 1, 0], atol=0.02)


@needs_urdf
def test_ik_round_trip_and_fingers_down():
    m = ak.ArmModel()
    rng = np.random.default_rng(3)
    for _ in range(10):
        q = rng.uniform(m.lower * 0.6, m.upper * 0.6)
        q2, err = m.solve(m.tcp(q), np.zeros(7))
        assert err < 2e-3
        assert np.all(q2 >= m.lower - 1e-9) and np.all(q2 <= m.upper + 1e-9)
    q, err = m.solve([0.05, 0.22, 0.03], np.zeros(7), point_down=True, locked=(7,))
    assert err < 2e-3
    assert m.approach(q)[2] < -0.98


def test_steps_radians_round_trip_and_range_limits():
    jc = ak.JointCalibration({m: 2000 + m for m in ak.ARM_MOTORS}, {m: (-1) ** m for m in ak.ARM_MOTORS})
    steps = {m: 1500 + 100 * m for m in ak.ARM_MOTORS}
    assert jc.to_steps(jc.to_radians(steps)) == steps
    if ak.URDF_PATH.exists():
        lo, hi = jc.limits_from_ranges({2: (1900, 2300)}, ak.ArmModel())
        assert math.isclose(min(abs(lo[1]), abs(hi[1])), (2002 - 1900) * 2 * math.pi / 4096, rel_tol=1e-6)


def test_base_fit_recovers_pose():
    true = ak.BaseInTable(260.0, -90.0, 92.0, -12.0)
    table = [[0, 0, 0], [520, 0, 0], [520, 360, 0], [0, 360, 0], [250, 120, 0]]
    base_pts = [true.table_to_base(p) for p in table]
    fit, rms, _ = ak.fit_base_in_table(base_pts, table)
    assert rms < 1e-6
    assert math.isclose(fit.x_mm, 260.0, abs_tol=1e-6) and math.isclose(fit.yaw_deg, 92.0, abs_tol=1e-6)
    assert math.isclose(fit.z_mm, -12.0, abs_tol=1e-6)


@needs_urdf
def test_refine_finds_wrong_direction_and_zero_offsets():
    m = ak.ArmModel()
    true = ak.JointCalibration({1: 2048, 2: 2110, 3: 1985, 4: 2070, 5: 2048, 6: 2048, 7: 2048},
                               {1: 1, 2: -1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1})
    base = ak.BaseInTable(260.0, -90.0, 90.0, -15.0)
    rng = np.random.default_rng(7)
    samples = []
    for x, y in [(0, 0), (520, 0), (520, 360), (0, 360), (260, 100), (150, 220)] * 2:
        q, err = m.solve(base.table_to_base((x, y, 0)), rng.uniform(-0.6, 0.6, 7))
        if err < 1e-3:
            samples.append((true.to_steps(q), (x, y, 0)))
    assert len(samples) >= 8
    guess = ak.JointCalibration({**true.zero_steps, 2: 2060, 3: 2030, 4: 2048}, {m: 1 for m in ak.ARM_MOTORS})
    cal, fit, rms, _ = ak.refine_joint_zeros(m, guess, samples)
    assert rms < 2.0
    assert cal.direction[2] == -1 and cal.direction[4] == 1
    assert all(abs(cal.zero_steps[k] - true.zero_steps[k]) <= 8 for k in (2, 3, 4))


@needs_urdf
def test_calib_cli_offline_flow(tmp_path):
    img, H = _render()
    pic = tmp_path / "table.jpg"
    cv2.imwrite(str(pic), img)
    env = {**os.environ, "ELROBOT_CONFIG_DIR": str(tmp_path), "ELROBOT_DATA_DIR": str(tmp_path)}

    def run(*args):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "calib.py"), *args], env=env,
                           capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr + r.stdout
        return r.stdout

    run("layout", "--width-mm", "520", "--depth-mm", "360", "--tag-size-mm", "80")
    out = run("camera", "--image", str(pic), "--write")
    assert "tags found: [0, 1, 2, 3]" in out and "Saved camera homography" in out
    cal = json.loads((tmp_path / "calibration.json").read_text())
    assert cal["table"]["measured"] is True and cal["camera"]["image_size"] == [480, 360]
    p = H @ [260, 180, 1]
    out = run("pixel", f"{p[0] / p[2]:.2f}", f"{p[1] / p[2]:.2f}")
    x, y = [float(v) for v in out.split("table (")[1].split(")")[0].split(",")]
    assert math.hypot(x - 260, y - 180) < 3.0
    out = run("reach", "0", "0", "200", "--offline")
    assert "IK error" in out and "Nothing moved" in out
    assert "camera:" in run("show")


def _printed_v1_view(size):
    """The 45 mm 2026-11-21 printed sheet (not real AprilTags) at the corners of a 520x360 mm table."""
    s, m = 2.0, 80
    canvas = np.full((int((360 + 2 * m) * s), int((520 + 2 * m) * s)), 255, np.uint8)
    side = int(45 * s)
    for tid, (x, y) in TAGS_MM.items():
        full = np.zeros((10, 10), np.uint8)
        full[1:9, 1:9] = [[int(ch) for ch in row] for row in tc.PRINTED_V1_BITS[int(tid)]]
        tag = np.flipud(cv2.resize(full * 255, (side, side), interpolation=cv2.INTER_NEAREST))
        cx, cy = int((x + m) * s), int((y + m) * s)
        canvas[cy - side // 2:cy - side // 2 + side, cx - side // 2:cx - side // 2 + side] = tag
    S = np.array([[s, 0, m * s], [0, s, m * s], [0, 0, 1]])
    H = np.array([[0.62, 0.05, 60], [0.02, 0.55, 300], [0.0001, -0.0003, 1]]) @ np.diag([1.0, -1.0, 1.0])
    img = cv2.warpPerspective(canvas, H @ np.linalg.inv(S), (480, 360), borderValue=255)
    return cv2.resize(img, size, interpolation=cv2.INTER_AREA)


def test_printed_v1_sheet_is_detected_and_fits():
    img = _printed_v1_view((480, 360))
    dets = tc.detect_tags(img)
    assert sorted(dets) == [0, 1, 2, 3]
    assert {d.family for d in dets.values()} == {"printed-v1"}
    _, report = tc.fit_camera(dets, TAGS_MM, 45.0, (480, 360))
    assert report["tag_family"] == "printed-v1"
    assert report["tag_square_rms_mm"] < 3.0


def test_real_36h11_is_not_read_as_printed_v1():
    img, _ = _render()
    assert {d.family for d in tc.detect_tags(img).values()} == {"36h11"}


def test_steps_wrap_across_4095_to_0():
    """Motor readings wrap from 4095 to 0; ranges like 3726..1565 cross that point (seen on the arm 2026-11-22)."""
    jc = ak.JointCalibration({m: 555 for m in ak.ARM_MOTORS}, {m: 1 for m in ak.ARM_MOTORS})
    steps = {m: 3892 for m in ak.ARM_MOTORS}
    q = jc.to_radians(steps)
    assert math.isclose(q[0], (3892 - 555 - 4096) * 2 * math.pi / 4096)  # -759 steps, not +3337
    assert jc.to_steps(q) == steps
    assert all(0 <= s < 4096 for s in jc.to_steps(np.full(7, -1.0)).values())
    assert ak.step_delta(3885, 537) == 748
    assert ak.step_delta(537, 3885) == -748
    assert ak.step_in_range(3892, 3726, 1565) and ak.step_in_range(163, 3726, 1565)
    assert not ak.step_in_range(2500, 3726, 1565)
    assert ak.step_in_range(2000, 1900, 2300) and not ak.step_in_range(2400, 1900, 2300)
    if ak.URDF_PATH.exists():
        lo, hi = jc.limits_from_ranges({1: (3726, 1565)}, ak.ArmModel())
        assert lo[0] >= (3726 - 555 - 4096) * 2 * math.pi / 4096 - 1e-9
        assert lo[0] < 0 < hi[0]
        assert hi[0] <= (1565 - 555) * 2 * math.pi / 4096 + 1e-9
        # a nearly full-turn range (motor 7: 2439..2198, zero 411) must overlap the URDF limits
        lo, hi = ak.JointCalibration({m: 411 for m in ak.ARM_MOTORS}, {m: 1 for m in ak.ARM_MOTORS}
                                     ).limits_from_ranges({7: (2439, 2198)}, ak.ArmModel())
        assert lo[6] < 0 < hi[6]


def _goto_setup():
    model = ak.ArmModel()
    jc = ak.JointCalibration({m: 2048 for m in ak.ARM_MOTORS}, {m: 1 for m in ak.ARM_MOTORS})
    base = ak.BaseInTable(228.0, 380.0, 180.0, 0.0)  # arm behind the tags, facing the person
    q0 = np.zeros(7)
    q0[1], q0[3] = 0.6, 0.9  # a folded, raised start pose
    present = jc.to_steps(q0)
    ranges = {m: (100, 4000) for m in ak.ARM_MOTORS}
    return model, jc, base, present, ranges


@pytest.mark.skipif(not ak.URDF_PATH.exists(), reason="needs the norma-core submodule URDF")
def test_cartesian_goto_lifts_moves_across_and_descends_in_small_steps():
    model, jc, base, present, ranges = _goto_setup()
    plan = ak.plan_cartesian_goto(model, jc, base, present, ranges, [228, 150, 80], point_down=True, fit_rms_mm=16)
    names = [label.split(" ")[0] for label, _, _, mode in plan if mode == "stream"]
    assert names[0] == "lift" and names[-1] == "descend" and "across" in names
    assert [label for label, *_ , mode in plan if mode == "watch"] == ["turn wrist down"]
    prev = None
    for label, p, goals, mode in plan:
        tip = base.base_to_table(model.tcp(jc.to_radians(goals)))
        assert np.linalg.norm(tip - np.asarray(p)) < 5           # every point is where it should be
        assert goals[7] == present[7]
        if prev is not None and mode == "stream":
            assert np.linalg.norm(np.asarray(p) - prev) <= ak.PATH_STEP_MM + 1e-6
            if not label.startswith("lift"):
                assert p[2] >= 80 - 1e-6
        prev = np.asarray(p)
    assert model.approach(jc.to_radians(plan[-1][2]))[2] < -0.95


@pytest.mark.skipif(not ak.URDF_PATH.exists(), reason="needs the norma-core submodule URDF")
def test_cartesian_goto_travel_height_is_settable_but_never_below_the_floor():
    model, jc, base, present, ranges = _goto_setup()

    def across_z(plan):
        return {round(p[2], 3) for label, p, _, mode in plan if label.startswith("across")}

    assert across_z(ak.plan_cartesian_goto(model, jc, base, present, ranges, [228, 150, 80],
                                           fit_rms_mm=16, travel_z_mm=110)) == {110.0}
    # Asked below the floor (50 + 16 mm) and below the target: travels at the target height.
    assert across_z(ak.plan_cartesian_goto(model, jc, base, present, ranges, [228, 150, 80],
                                           fit_rms_mm=16, travel_z_mm=40)) == {80.0}


@pytest.mark.skipif(not ak.URDF_PATH.exists(), reason="needs the norma-core submodule URDF")
def test_cartesian_goto_lowered_floor_allows_a_grasp_height_but_keeps_fit_error():
    model, jc, base, present, ranges = _goto_setup()
    plan = ak.plan_cartesian_goto(model, jc, base, present, ranges, [228, 150, 20], fit_rms_mm=16, min_z_mm=0)
    assert abs(plan[-1][1][2] - 20) < 1e-6
    with pytest.raises(ValueError, match="below the allowed"):
        ak.plan_cartesian_goto(model, jc, base, present, ranges, [228, 150, 10], fit_rms_mm=16, min_z_mm=0)


@pytest.mark.skipif(not ak.URDF_PATH.exists(), reason="needs the norma-core submodule URDF")
def test_cartesian_goto_refuses_unsafe_targets():
    model, jc, base, present, ranges = _goto_setup()
    with pytest.raises(ValueError, match="below the allowed"):
        ak.plan_cartesian_goto(model, jc, base, present, ranges, [228, 150, 60], fit_rms_mm=16)
    with pytest.raises(ValueError, match="out of reach|would jump"):
        ak.plan_cartesian_goto(model, jc, base, present, ranges, [228, -900, 100])
    with pytest.raises(ValueError, match="not a valid calibrated range"):
        ak.plan_cartesian_goto(model, jc, base, present, {**ranges, 2: (3726, 1565)}, [228, 150, 100])
    narrow = {**ranges, 2: (present[2] - 30, present[2] + 30)}
    with pytest.raises(ValueError, match="outside its range|out of reach"):
        ak.plan_cartesian_goto(model, jc, base, present, narrow, [228, 150, 80], point_down=True)


@pytest.mark.skipif(not ak.URDF_PATH.exists(), reason="needs the norma-core submodule URDF")
def test_cartesian_line_follows_the_line_without_pose_jumps():
    model, jc, base, present, ranges = _goto_setup()
    plan = ak.plan_cartesian_line(model, jc, base, present, ranges, [150, 150, 100], [300, 150, 100])
    line = [step for step in plan if step[0].startswith("line ")]
    assert len(line) == 30
    prev = plan[len(plan) - len(line) - 1][2]
    for _, p, goals, mode in line:
        assert mode == "stream"
        tip = base.base_to_table(model.tcp(jc.to_radians(goals)))
        assert np.linalg.norm(tip - np.asarray(p)) < 5
        assert abs(p[1] - 150) < 1e-6 and abs(p[2] - 100) < 1e-6
        assert max(abs(goals[m] - prev[m]) for m in ak.ARM_MOTORS) <= ak.PATH_MAX_JUMP_STEPS
        prev = goals


@pytest.mark.skipif(not ak.URDF_PATH.exists(), reason="needs the norma-core submodule URDF")
def test_cartesian_line_refuses_low_lines():
    model, jc, base, present, ranges = _goto_setup()
    with pytest.raises(ValueError, match="below the allowed"):
        ak.plan_cartesian_line(model, jc, base, present, ranges, [150, 150, 100], [300, 150, 40])


def _load_calib_script():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("calib_script", ROOT / "scripts" / "calib.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _FakeGripperHw:
    """Motor 8 that moves toward its goal and stalls at `stall` (an object between the jaws)."""

    def __init__(self, present, stall=None):
        self.present, self.stall, self.goal, self.goals = present, stall, present, []

    def snapshot(self):
        step = max(-60, min(60, self.goal - self.present))
        nxt = self.present + step
        if self.stall is not None and self.goal < self.present and nxt <= self.stall:
            nxt = max(self.stall, nxt) if self.present > self.stall else self.present
        self.present = nxt
        r = type("R", (), {})()
        r.present, r.range_min, r.range_max = self.present, 1245, 2851
        return {8: r}

    def move_motors(self, goals, **kw):
        self.goal = goals[8]
        self.goals.append(goals[8])


def test_gripper_after_close_holds_with_squeeze_on_a_fresh_reading(monkeypatch):
    calib = _load_calib_script()
    monkeypatch.setattr(calib.time, "sleep", lambda s: None)
    hw = _FakeGripperHw(2800, stall=1490)
    assert calib._gripper_after(hw, {"gripper": {"open_at": "max", "squeeze_steps": 57}}, "close") == 0
    assert hw.goals[0] == 1265 and hw.goals[-1] == 1490 - 57


def test_gripper_after_close_empty_and_open(monkeypatch):
    calib = _load_calib_script()
    monkeypatch.setattr(calib.time, "sleep", lambda s: None)
    hw = _FakeGripperHw(2800)
    calib._gripper_after(hw, {"gripper": {"open_at": "max", "squeeze_steps": 57}}, "close")
    assert hw.goals == [1265]                       # reached the closed end: no squeeze added
    hw = _FakeGripperHw(1300)
    calib._gripper_after(hw, {"gripper": {"open_at": "max"}}, "open")
    assert hw.goals == [2831]
