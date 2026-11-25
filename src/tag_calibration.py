"""Table coordinate frame from 4 corner AprilTags (36h11, IDs 0-3) seen by the table camera.

Table frame (mm, on the table surface, z up):
    origin = centre of tag 0 (front-left, seen from the person), +x toward tag 1 (front-right),
    +y toward tag 3 (back-left, away from the person), z up. Right-handed. Each tag's centre position is measured with a tape measure and stored in
    config/calibration.json -> table.tags_mm.

What this module does (no arm motion, no Station access):
  * detect_tags(image)            -> tag centres and corners in pixels
  * fit_camera(detections, ...)   -> pixel -> table homography + a size check in mm
  * TableCamera.pixel_to_table()  -> where a pixel lies on the table (z = 0 plane only:
                                     an object 30 mm tall appears shifted, see docs/FINDINGS.md)
  * draw_overlay()                -> picture with tags, a 50 mm grid and the arm base
The arm base pose in this frame comes from touching tags with the fingertips (arm_kinematics).
"""

from __future__ import annotations

import datetime as _dt
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CALIBRATION_FILE = Path(os.environ.get("ELROBOT_CONFIG_DIR", ROOT / "config")) / "calibration.json"
TAG_IDS = (0, 1, 2, 3)

DEFAULT_CALIBRATION = {
    "table": {
        "tag_family": "36h11",
        "tag_size_mm": 80.0,
        # Tag centres in the table frame. Placeholder rectangle until measured.
        "tags_mm": {"0": [0.0, 0.0], "1": [500.0, 0.0], "2": [500.0, 350.0], "3": [0.0, 350.0]},
        "measured": False,
    },
    "camera": {},
    "joints": {
        # Per motor: zero_steps = reading when the joint is at the URDF zero angle; direction +1/-1.
        "motors": {str(m): {"zero_steps": 2048, "direction": 1} for m in range(1, 8)},
        "tcp_offset_mm": [0.8, 103.5, 0.0],
        "measured": False,
    },
    "base_in_table": {"x_mm": 0.0, "y_mm": 0.0, "yaw_deg": 0.0, "z_mm": 0.0, "rms_mm": None,
                      "points": [], "measured": False},
}


def load_calibration(path: Path = CALIBRATION_FILE) -> dict:
    cal = json.loads(json.dumps(DEFAULT_CALIBRATION))
    if Path(path).exists():
        for key, val in json.loads(Path(path).read_text()).items():
            if isinstance(val, dict) and isinstance(cal.get(key), dict):
                cal[key].update(val)
            else:
                cal[key] = val
    return cal


def save_calibration(cal: dict, path: Path = CALIBRATION_FILE) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(cal, indent=2) + "\n")


def now_iso() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


# -- detection --------------------------------------------------------------------------------

@dataclass
class TagDetection:
    tag_id: int
    center: Tuple[float, float]
    corners: np.ndarray          # 4x2 pixels, the tag's own order (its top-left first, clockwise)
    family: str = "36h11"

    @property
    def side_px(self) -> float:
        c = self.corners
        return float(np.mean([np.linalg.norm(c[i] - c[(i + 1) % 4]) for i in range(4)]))


# The 45 mm sheet printed on 2026-11-21 ("printed-v1", docs/NormaCore Hackathon - 4-Corner AprilTags.pdf)
# is NOT real AprilTag 36h11: a hand-typed 8x8 grid inside the black border. OpenCV reads it fine as a
# custom dictionary. Rows of the 8x8 grid inside the black border, 1 = white. Patterns differ by >= 8
# bits between IDs (any rotation). Tag 1 is close to symmetric under rotation; only centres are used.
PRINTED_V1_BITS = {
    0: ("11111111", "10010101", "10110011", "11001001", "10100111", "11101001", "10011101", "11111111"),
    1: ("11111111", "11001101", "10100111", "10010011", "11011001", "11100101", "10110011", "11111111"),
    2: ("11111111", "10110011", "11001001", "10011101", "11100011", "10101101", "11010111", "11111111"),
    3: ("11111111", "11100101", "10010011", "11011001", "10110111", "10001011", "11010001", "11111111"),
}
FAMILIES = ("36h11", "printed-v1")


def _dictionary(family: str) -> "cv2.aruco.Dictionary":
    if family == "36h11":
        return cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
    if family == "printed-v1":
        rows = [np.array([[int(ch) for ch in r] for r in PRINTED_V1_BITS[i]], np.uint8) for i in TAG_IDS]
        return cv2.aruco.Dictionary(np.vstack([cv2.aruco.Dictionary.getByteListFromBits(b) for b in rows]), 8, 3)
    raise ValueError(f"unknown tag family {family!r}; use one of {FAMILIES}")


def _detector(family: str = "36h11") -> "cv2.aruco.ArucoDetector":
    params = cv2.aruco.DetectorParameters()
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    return cv2.aruco.ArucoDetector(_dictionary(family), params)


def _detect_family(gray: np.ndarray, scale: float, family: str) -> Dict[int, TagDetection]:
    corners, ids, _ = _detector(family).detectMarkers(gray)
    found: Dict[int, TagDetection] = {}
    if ids is None:
        return found
    for c, i in zip(corners, ids.ravel()):
        i = int(i)
        if i not in TAG_IDS or i in found:
            continue
        pts = c.reshape(4, 2).astype(float) / scale
        found[i] = TagDetection(i, (float(pts[:, 0].mean()), float(pts[:, 1].mean())), pts, family)
    return found


def detect_tags(image: np.ndarray, upscale_below_px: int = 640, families: Sequence[str] = FAMILIES
                ) -> Dict[int, TagDetection]:
    """Find tags 0-3. Tries each family (real 36h11, then the printed-v1 sheet) and keeps the one that
    finds the most tags; mixing families on one table is not supported. Small frames are upscaled
    first (the Station sends 299x224)."""
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    scale = 1.0
    if max(gray.shape) < upscale_below_px:
        scale = upscale_below_px / max(gray.shape)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    best: Dict[int, TagDetection] = {}
    for family in families:
        found = _detect_family(gray, scale, family)
        if len(found) > len(best):
            best = found
        if len(best) == len(TAG_IDS):
            break
    return best


# -- camera fit -------------------------------------------------------------------------------

@dataclass
class TableCamera:
    """pixel -> table-mm homography for one camera at one image size."""
    H: np.ndarray
    image_size: Tuple[int, int]      # (width, height) the homography was fitted at

    @classmethod
    def from_config(cls, cam: dict) -> "TableCamera":
        if not cam.get("pixel_to_table"):
            raise RuntimeError("camera not calibrated: run ./cli.sh calib camera")
        return cls(np.array(cam["pixel_to_table"], dtype=float), tuple(cam["image_size"]))

    def _scaled_H(self, size: Optional[Tuple[int, int]]) -> np.ndarray:
        if size is None or tuple(size) == tuple(self.image_size):
            return self.H
        sx, sy = self.image_size[0] / size[0], self.image_size[1] / size[1]
        return self.H @ np.diag([sx, sy, 1.0])

    def pixel_to_table(self, u: float, v: float, size: Optional[Tuple[int, int]] = None) -> Tuple[float, float]:
        """Table (x, y) mm of pixel (u, v); size = (w, h) of the frame the pixel came from."""
        p = self._scaled_H(size) @ np.array([u, v, 1.0])
        return float(p[0] / p[2]), float(p[1] / p[2])

    def table_to_pixel(self, x: float, y: float, size: Optional[Tuple[int, int]] = None) -> Tuple[float, float]:
        p = np.linalg.inv(self._scaled_H(size)) @ np.array([x, y, 1.0])
        return float(p[0] / p[2]), float(p[1] / p[2])


def fit_camera(dets: Dict[int, TagDetection], tags_mm: Dict[str, Sequence[float]], tag_size_mm: float,
               image_size: Tuple[int, int]) -> Tuple[TableCamera, dict]:
    """Homography from the 4 tag centres, then a check that needs no extra measurement:
    each tag's corners projected onto the table should form a square of tag_size_mm.
    Returns (camera, report)."""
    missing = [i for i in TAG_IDS if i not in dets]
    if missing:
        raise ValueError(f"tags not found: {missing} (found {sorted(dets)}). Check lighting, glare, "
                         "that the tags are the real 36h11 print, and that all 4 are in view.")
    src = np.array([dets[i].center for i in TAG_IDS], dtype=np.float64)
    dst = np.array([tags_mm[str(i)] for i in TAG_IDS], dtype=np.float64)
    H, _ = cv2.findHomography(src, dst, 0)
    if H is None:
        raise ValueError("homography failed: are three tags in a line?")
    cam = TableCamera(H, (int(image_size[0]), int(image_size[1])))
    sides, warnings = [], []
    for i in TAG_IDS:
        pts = [cam.pixel_to_table(*c) for c in dets[i].corners]
        sides += [math.dist(pts[k], pts[(k + 1) % 4]) for k in range(4)]
    side_err = [s - tag_size_mm for s in sides]
    rms = float(math.sqrt(np.mean(np.square(side_err))))
    # Orientation: a camera looking down sees a right-handed table frame mirrored in pixel
    # coordinates (v points down), so tag 0 -> 1 -> 2 must turn the OPPOSITE way in the image.
    def turn(p):
        a, b = p[1] - p[0], p[2] - p[0]
        return np.sign(a[0] * b[1] - a[1] * b[0])
    if turn(src) == turn(dst):
        warnings.append("tag layout is mirrored: tags 1 and 3 swapped, or the camera image is flipped")
    if rms > 0.1 * tag_size_mm:
        warnings.append(f"tag squares come out {rms:.1f} mm off their {tag_size_mm:g} mm size: re-measure the "
                        "tag centres and the printed tag size, or a tag is not flat")
    min_side_px = min(d.side_px for d in dets.values())
    if min_side_px < 24:
        warnings.append(f"smallest tag is only {min_side_px:.0f} px wide: use bigger tags or a larger frame")
    families = sorted({d.family for d in dets.values()})
    report = {"tag_family": families[0] if len(families) == 1 else families,
              "tag_square_rms_mm": round(rms, 2), "tag_side_px_min": round(min_side_px, 1),
              "centers_px": {str(i): [round(v, 2) for v in dets[i].center] for i in TAG_IDS},
              "warnings": warnings}
    return cam, report


def camera_config(cam: TableCamera, report: dict, camera_name: str) -> dict:
    return {"name": camera_name, "tag_family": report.get("tag_family"), "image_size": list(cam.image_size),
            "pixel_to_table": [[round(float(v), 9) for v in row] for row in cam.H],
            "tag_square_rms_mm": report["tag_square_rms_mm"], "centers_px": report["centers_px"],
            "calibrated_at": now_iso()}


# -- overlay ----------------------------------------------------------------------------------

def draw_overlay(image: np.ndarray, cam: Optional[TableCamera], dets: Dict[int, TagDetection],
                 tags_mm: Dict[str, Sequence[float]], base: Optional[Tuple[float, float, float]] = None,
                 grid_mm: float = 50.0, extra_points: Sequence[Tuple[str, float, float]] = ()) -> np.ndarray:
    """Tags (green), a table grid every grid_mm (blue), arm base + axes (red) and labelled points."""
    out = image.copy() if image.ndim == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    size = (out.shape[1], out.shape[0])
    thick = max(1, round(size[0] / 400))
    for d in dets.values():
        cv2.polylines(out, [d.corners.astype(np.int32)], True, (0, 200, 0), thick)
        top = d.corners[np.argmin(d.corners[:, 1])]
        cv2.putText(out, f"tag {d.tag_id}", (int(top[0]) - 12, max(int(top[1]) - 5, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4 * thick, (0, 0, 255), thick)
    if cam is None:
        return out
    xs = [p[0] for p in tags_mm.values()]
    ys = [p[1] for p in tags_mm.values()]

    def px(x, y):
        u, v = cam.table_to_pixel(x, y, size)
        return int(round(u)), int(round(v))

    x0, x1 = math.floor(min(xs) / grid_mm) * grid_mm, math.ceil(max(xs) / grid_mm) * grid_mm
    y0, y1 = math.floor(min(ys) / grid_mm) * grid_mm, math.ceil(max(ys) / grid_mm) * grid_mm
    for x in np.arange(x0, x1 + 1e-6, grid_mm):
        cv2.line(out, px(x, y0), px(x, y1), (200, 120, 40), 1)
    for y in np.arange(y0, y1 + 1e-6, grid_mm):
        cv2.line(out, px(x0, y), px(x1, y), (200, 120, 40), 1)
    cv2.putText(out, f"grid {grid_mm:g} mm", (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 120, 40), 1)
    if base is not None:
        bx, by, yaw = base
        a = math.radians(yaw)
        o = px(bx, by)
        cv2.circle(out, o, 4 * thick, (0, 0, 255), -1)
        cv2.arrowedLine(out, o, px(bx + 60 * math.cos(a), by + 60 * math.sin(a)), (0, 0, 255), thick)   # base +x
        cv2.arrowedLine(out, o, px(bx - 60 * math.sin(a), by + 60 * math.cos(a)), (0, 160, 255), thick)  # base +y
        cv2.putText(out, "base", (o[0] + 5, o[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    for label, x, y in extra_points:
        p = px(x, y)
        cv2.drawMarker(out, p, (255, 0, 255), cv2.MARKER_CROSS, 10, thick)
        cv2.putText(out, label, (p[0] + 4, p[1] - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 0, 255), 1)
    return out


def rectangle_layout(width_mm: float, depth_mm: float) -> Dict[str, List[float]]:
    """Tag centres for a rectangle: 0 (0,0), 1 (W,0), 2 (W,D), 3 (0,D)."""
    return {"0": [0.0, 0.0], "1": [width_mm, 0.0], "2": [width_mm, depth_mm], "3": [0.0, depth_mm]}
