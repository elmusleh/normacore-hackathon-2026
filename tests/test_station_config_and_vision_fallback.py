"""Offline tests: HD camera config for station.yaml, and no OpenCV mouth guesses."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

yaml = pytest.importorskip("yaml")

import station_config  # noqa: E402
from feeding_vision import FeedingVisionDetector, mediapipe_status  # noqa: E402


def test_empty_formats_get_hd_list(tmp_path, monkeypatch):
    monkeypatch.delenv("ELROBOT_KEEP_STATION_YAML", raising=False)
    p = tmp_path / "station.yaml"
    p.write_text(
        "drivers:\n  st3215:\n    enabled: true\n    current-threshold: 150\n"
        "  usb-video:\n    enabled: true\n    resize_target: 480\n    formats: []\n    frame-skip: 0\n"
    )
    assert station_config.main(p) == 0
    cfg = yaml.safe_load(p.read_text())
    usb = cfg["drivers"]["usb-video"]
    assert usb["formats"][0] == {"format": "1920x1080@30fps,mjpeg"}
    assert usb["resize_target"] == 1080
    # Unrelated settings survive, and the old file is kept.
    assert cfg["drivers"]["st3215"]["current-threshold"] == 150
    assert "formats: []" in (tmp_path / "station.yaml.bak").read_text()


def test_own_formats_are_left_alone(tmp_path, monkeypatch):
    monkeypatch.delenv("ELROBOT_KEEP_STATION_YAML", raising=False)
    p = tmp_path / "station.yaml"
    text = ("drivers:\n  usb-video:\n    enabled: true\n    resize_target: 224\n"
            "    formats:\n    - format: 640x480@30fps,mjpeg\n")
    p.write_text(text)
    assert station_config.main(p) == 0
    assert p.read_text() == text
    assert not (tmp_path / "station.yaml.bak").exists()


def test_missing_file_is_written_with_hd(tmp_path, monkeypatch):
    monkeypatch.delenv("ELROBOT_KEEP_STATION_YAML", raising=False)
    p = tmp_path / "station.yaml"
    assert station_config.main(p) == 0
    cfg = yaml.safe_load(p.read_text())
    assert cfg["drivers"]["usb-video"]["formats"][0]["format"].startswith("1920x1080")
    assert cfg["drivers"]["st3215"]["enabled"] is True


def test_opt_out_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ELROBOT_KEEP_STATION_YAML", "1")
    p = tmp_path / "station.yaml"
    assert station_config.main(p) == 0
    assert not p.exists()


def test_opencv_mouth_guesses_are_marked_fallback(monkeypatch):
    """Without MediaPipe, no OpenCV result may look like a real mouth to the consumers."""
    det = FeedingVisionDetector()
    det._landmarker = None
    rng = np.random.default_rng(0)
    frames = [
        np.full((720, 1280, 3), (90, 110, 170), dtype=np.uint8),  # brick/skin-toned wall
        rng.integers(0, 255, (720, 1280, 3), dtype=np.uint8),
        np.zeros((720, 1280, 3), dtype=np.uint8),
    ]
    for frame in frames:
        m = det.detect_mouth(frame)
        extra = m.extra or {}
        assert extra.get("fallback") is True, extra
        assert extra.get("detector") != "mediapipe"


def test_mediapipe_status_shape():
    status = mediapipe_status()
    assert set(status) >= {"python", "mediapipe", "face_model", "ok", "problem"}
    assert status["ok"] == (status["problem"] == "")
