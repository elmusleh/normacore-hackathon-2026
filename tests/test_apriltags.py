"""The printable corner tags must be real AprilTag 36h11 codes (offline, no camera)."""

import importlib.util
from pathlib import Path

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

ROOT = Path(__file__).resolve().parent.parent


def _gen():
    spec = importlib.util.spec_from_file_location("generate_apriltags", ROOT / "scripts" / "generate_apriltags.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_generated_tags_are_detected_as_36h11_after_perspective_and_downscale():
    gen = _gen()
    canvas = np.full((600, 800), 255, np.uint8)
    for tag_id, (x, y) in zip(range(4), [(50, 50), (600, 50), (600, 400), (50, 400)]):
        bits = np.array(gen.tag_bits(tag_id), np.uint8) * 255
        canvas[y + 15:y + 135, x + 15:x + 135] = cv2.resize(bits, (120, 120), interpolation=cv2.INTER_NEAREST)
    warp = np.array([[0.8, 0.1, 20], [0.05, 0.7, 30], [0.0002, 0.0003, 1]])
    img = cv2.warpPerspective(canvas, warp, (800, 600), borderValue=255)
    img = cv2.resize(img, (299, 224), interpolation=cv2.INTER_AREA)  # the Station's frame size
    det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11),
                                  cv2.aruco.DetectorParameters())
    _, ids, _ = det.detectMarkers(img)
    assert ids is not None and sorted(ids.ravel().tolist()) == [0, 1, 2, 3]


def test_sheet_svg_has_requested_physical_size(tmp_path):
    gen = _gen()
    out = gen.generate_printable_sheet(str(tmp_path / "tags.html"), size_mm=80)
    html = Path(out).read_text()
    # 8 modules = 80 mm black square, plus one 10 mm white module each side.
    assert html.count('width="100.00mm"') == 4
    assert "36h11" in html
