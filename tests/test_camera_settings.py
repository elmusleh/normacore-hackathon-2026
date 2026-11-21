"""Offline tests for the camera exposure tuning helpers (no camera needed)."""

import importlib.util
import sys
from pathlib import Path

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


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


def test_exposure_stats_flags_white_table():
    stats = _camera_settings().exposure_stats(overexposed_table())
    assert stats["verdict"] == "overexposed" and stats["clipped_share"] > 0.5


def test_normal_frame_is_ok():
    img = np.full((100, 100, 3), 120, np.uint8)
    assert _camera_settings().exposure_stats(img)["verdict"] == "ok"


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
