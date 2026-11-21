"""Offline tests for camera frame enhancement and exposure tuning helpers (no camera needed)."""

import importlib.util
import sys
from pathlib import Path

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import frame_enhance as fe  # noqa: E402


def _camera_settings():
    spec = importlib.util.spec_from_file_location("camera_settings", ROOT / "scripts" / "camera_settings.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def overexposed_table():
    """A washed-out white table (mostly clipped) with a pale green 'grape' in the middle."""
    img = np.full((224, 298, 3), 252, np.uint8)
    img[:60] = (200, 205, 210)                      # wall, bright but not clipped
    cv2.circle(img, (150, 140), 12, (190, 235, 215), -1)  # pale green grape (BGR)
    return img


def contrast(img, center, r):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(float)
    x, y = center
    inside = gray[y - r // 2:y + r // 2, x - r // 2:x + r // 2].mean()
    ring = gray[y - 2 * r:y + 2 * r, x + r + 4:x + 2 * r].mean()
    return abs(ring - inside)


def test_exposure_stats_flags_white_table():
    stats = fe.exposure_stats(overexposed_table())
    assert stats["verdict"] == "overexposed" and stats["clipped_share"] > 0.5
    hint = fe.exposure_hint("table", stats)
    assert "overexposed" in hint and "--tune" in hint


def test_normal_frame_is_ok():
    img = np.full((100, 100, 3), 120, np.uint8)
    stats = fe.exposure_stats(img)
    assert stats["verdict"] == "ok" and fe.exposure_hint("table", stats) is None


def test_auto_gamma_direction():
    assert fe.auto_gamma(200) > 1.0      # too bright -> darken
    assert fe.auto_gamma(50) < 1.0       # too dark -> brighten
    assert fe.auto_gamma(fe.TARGET_MEAN) == 1.0
    assert 0.6 <= fe.auto_gamma(250) <= 2.2


def test_enhance_raises_grape_contrast_and_darkens_bright_frame():
    img = cv2.GaussianBlur(overexposed_table(), (3, 3), 0)
    img[60:] = np.clip(img[60:].astype(int) - 25, 0, 255).astype(np.uint8)  # bright, not all clipped
    out = fe.enhance_bgr(img)
    assert out.shape == img.shape and out.dtype == np.uint8
    assert contrast(out, (150, 140), 12) > contrast(img, (150, 140), 12)
    assert cv2.cvtColor(out, cv2.COLOR_BGR2GRAY).mean() < cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).mean()


def test_enhance_jpeg_round_trip_and_disable():
    ok, buf = cv2.imencode(".jpg", overexposed_table())
    jpeg = buf.tobytes()
    out, stats, enhanced = fe.enhance_jpeg(jpeg)
    assert enhanced and out != jpeg and out[:2] == b"\xff\xd8" and stats["verdict"] == "overexposed"
    same, stats, enhanced = fe.enhance_jpeg(jpeg, {"enabled": False})
    assert same == jpeg and not enhanced and stats is not None


def test_undecodable_frame_passes_through():
    bad = b"\xff\xd8not-a-jpeg\xff\xd9"
    assert fe.enhance_jpeg(bad) == (bad, None, False)


def test_options_per_camera_override():
    cfg = {"camera_enhance": {"clahe_clip": 3.0, "cameras": {"face": {"enabled": False}}}}
    assert fe.options_for(cfg, "table")["clahe_clip"] == 3.0 and fe.options_for(cfg, "table")["enabled"]
    assert fe.options_for(cfg, "face")["enabled"] is False
    assert fe.options_for({}, "table") == fe.DEFAULT_OPTIONS


def test_ordered_controls_puts_auto_switches_first():
    cs = _camera_settings()
    ctrls = cs.ordered_controls({"exposure": 70, "controls": {"white_balance_temperature": 4600,
                                                              "white_balance_automatic": 0, "gain": 0}})
    assert ctrls[:3] == ["auto_exposure=1", "exposure_dynamic_framerate=0", "exposure_time_absolute=70"]
    assert ctrls.index("white_balance_automatic=0") < ctrls.index("white_balance_temperature=4600")
    assert "gain=0" in ctrls


def test_supported_controls_parses_v4l2_listing(monkeypatch):
    cs = _camera_settings()
    listing = ("\nUser Controls\n\n"
               "                     brightness 0x00980900 (int)    : min=-64 max=64 step=1 default=0 value=0\n"
               "        white_balance_automatic 0x0098090c (bool)   : default=1 value=1\n"
               "\nCamera Controls\n\n"
               "                  auto_exposure 0x009a0901 (menu)   : min=0 max=3 default=3 value=1\n"
               "\t\t\t\t1: Manual Mode\n")

    class R:
        stdout = listing
    monkeypatch.setattr(cs.subprocess, "run", lambda *a, **k: R())
    assert cs.supported_controls("/dev/video0") == {"brightness", "white_balance_automatic", "auto_exposure"}


def test_pick_exposure_avoids_blown_out_and_dark():
    cs = _camera_settings()
    results = {
        10: {"mean": 40.0, "clipped_share": 0.0, "dark_share": 0.30},
        70: {"mean": 125.0, "clipped_share": 0.01, "dark_share": 0.0},
        160: {"mean": 230.0, "clipped_share": 0.60, "dark_share": 0.0},
    }
    assert cs.pick_exposure(results) == 70
