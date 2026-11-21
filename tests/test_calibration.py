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
