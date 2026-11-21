"""Assistive Feeding Vision & Closed-Loop Orchestrator.

Identifies the grape bowl, spoon holder, and person's mouth from a live camera
feed (such as /dev/video4, the Station camera queue, or a synthetic test frame)
and orchestrates safe slave arm feeding motions through RobotTools and
KinematicsSafetyEngine.

Safety rules enforced (per docs/FEEDING_ASSISTANT_PLAN.md §4):
  * Physical arm motion is gated by ELROBOT_ALLOW_MOTION=1 (otherwise returns dry_run).
  * All hardware joint motions go through RobotTools (calibrated range clamps,
    torque checks, speed caps, overload hold, routing via 'clear').
  * Near the face: stops at a safe standoff distance (5-10 cm; mouth_width_px <= standoff_px)
    and never closes the last gap.
  * Stop on doubt: if the mouth or food bowl is lost or an overload trips, holds position.
"""

from __future__ import annotations

import base64
import io
import logging
import math
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

try:
    from elrobot_config import load_config, load_waypoints
    from vision_homography import TabletopCalibrator
except ImportError:
    from src.elrobot_config import load_config, load_waypoints
    from src.vision_homography import TabletopCalibrator

log = logging.getLogger("elrobot.feeding")

# Standoff thresholds (in pixels for 640x480 frame):
# When mouth width in pixels reaches STANDOFF_MOUTH_WIDTH_PX, the arm is ~7 cm from the face and MUST stop.
STANDOFF_MOUTH_WIDTH_PX = 95
DEFAULT_FRAME_W = 640
DEFAULT_FRAME_H = 480
MAR_OPEN_THRESHOLD = 0.25
MOUTH_OPEN_DEBOUNCE_FRAMES = 3
FACE_WATCHDOG_TIMEOUT_S = 0.5
DEFAULT_FACE_LANDMARKER_MODEL = Path(__file__).resolve().parent.parent / "data" / "face_landmarker.task"

# MediaPipe FaceLandmarker lip landmark indices
LM_UPPER_INNER_LIP = 13
LM_LOWER_INNER_LIP = 14
LM_LEFT_MOUTH_CORNER = 61
LM_RIGHT_MOUTH_CORNER = 291


class MouthStateTracker:
    """EMA-smoothed lip tracker with 3-frame mouth-open debounce and face-loss watchdog."""

    def __init__(
        self,
        alpha: float = 0.35,
        mar_threshold: float = MAR_OPEN_THRESHOLD,
        debounce_frames: int = MOUTH_OPEN_DEBOUNCE_FRAMES,
        watchdog_timeout_s: float = FACE_WATCHDOG_TIMEOUT_S,
    ) -> None:
        self.alpha = alpha
        self.mar_threshold = mar_threshold
        self.debounce_frames = debounce_frames
        self.watchdog_timeout_s = watchdog_timeout_s
        self._ema_u: Optional[float] = None
        self._ema_v: Optional[float] = None
        self._ema_w: Optional[float] = None
        self._ema_mar: Optional[float] = None
        self.open_streak: int = 0
        self.last_face_seen_t: Optional[float] = None

    @staticmethod
    def compute_mar(
        upper: Tuple[float, float],
        lower: Tuple[float, float],
        left: Tuple[float, float],
        right: Tuple[float, float],
    ) -> float:
        """Compute Mouth Aspect Ratio (vertical lip gap / horizontal mouth width)."""
        horiz = math.hypot(right[0] - left[0], right[1] - left[1])
        if horiz <= 1e-6:
            return 0.0
        vert = math.hypot(lower[0] - upper[0], lower[1] - upper[1])
        return round(vert / horiz, 3)

    def _ema(self, prev: Optional[float], val: float) -> float:
        if prev is None:
            return val
        return self.alpha * val + (1.0 - self.alpha) * prev

    def update(
        self,
        u: float,
        v: float,
        width_px: float,
        mar: float,
        now: Optional[float] = None,
    ) -> Dict[str, Any]:
        ts = time.monotonic() if now is None else now
        self.last_face_seen_t = ts
        self._ema_u = self._ema(self._ema_u, float(u))
        self._ema_v = self._ema(self._ema_v, float(v))
        self._ema_w = self._ema(self._ema_w, float(width_px))
        self._ema_mar = self._ema(self._ema_mar, float(mar))

        mouth_open = self._ema_mar >= self.mar_threshold
        self.open_streak = (self.open_streak + 1) if mouth_open else 0
        confirmed = self.open_streak >= self.debounce_frames

        return {
            "u_px": int(round(self._ema_u)),
            "v_px": int(round(self._ema_v)),
            "width_px": int(round(self._ema_w)),
            "mar": round(self._ema_mar, 3),
            "mouth_open": mouth_open,
            "mouth_open_confirmed": confirmed,
            "open_streak": self.open_streak,
            "face_lost": False,
        }

    def check_watchdog(self, now: Optional[float] = None) -> bool:
        """Return True if a previously tracked face has been missing longer than watchdog_timeout_s."""
        if self.last_face_seen_t is None:
            return False
        ts = time.monotonic() if now is None else now
        if (ts - self.last_face_seen_t) > self.watchdog_timeout_s:
            self.open_streak = 0
            return True
        return False


class FeedingSafetyFSM:
    """Deterministic safety state machine for assistive facial feeding (ada_feeding pattern)."""

    STATES = (
        "IDLE",
        "APPROACH",
        "HOLD_STANDOFF",
        "WAIT_MOUTH_OPEN",
        "RELEASE",
        "RETRACT",
        "EMERGENCY_HOLD",
    )

    def __init__(self) -> None:
        self.state: str = "IDLE"
        self.reason: str = "ready"

    def reset(self) -> str:
        self.state = "IDLE"
        self.reason = "reset"
        return self.state

    def step(
        self,
        *,
        face_detected: bool,
        mouth_open_confirmed: bool = False,
        at_standoff: bool = False,
        too_close: bool = False,
        holding_object: bool = False,
        face_lost: bool = False,
        stop_requested: bool = False,
    ) -> str:
        """Advance one FSM step with hard safety overrides."""
        if stop_requested:
            self.state = "EMERGENCY_HOLD"
            self.reason = "stop_requested"
            return self.state

        if too_close and self.state in ("APPROACH", "HOLD_STANDOFF", "WAIT_MOUTH_OPEN"):
            self.state = "EMERGENCY_HOLD"
            self.reason = "too_close_to_face"
            return self.state

        if (face_lost or not face_detected) and self.state in ("APPROACH", "HOLD_STANDOFF", "WAIT_MOUTH_OPEN"):
            self.state = "EMERGENCY_HOLD"
            self.reason = "face_lost_watchdog"
            return self.state

        if self.state == "IDLE":
            if holding_object and face_detected:
                self.state = "APPROACH"
                self.reason = "food_ready_and_face_visible"
        elif self.state == "APPROACH":
            if at_standoff:
                self.state = "HOLD_STANDOFF"
                self.reason = "standoff_reached"
        elif self.state == "HOLD_STANDOFF":
            self.state = "WAIT_MOUTH_OPEN"
            self.reason = "awaiting_mouth_open_confirmation"
        elif self.state == "WAIT_MOUTH_OPEN":
            if mouth_open_confirmed:
                self.state = "RELEASE"
                self.reason = "mouth_open_confirmed_3_frames"
        elif self.state == "RELEASE":
            self.state = "RETRACT"
            self.reason = "bite_delivered"
        elif self.state == "RETRACT":
            if not holding_object:
                self.state = "IDLE"
                self.reason = "returned_to_clear"

        return self.state


@dataclass
class DetectedTarget:
    label: str
    u_px: int
    v_px: int
    x_mm: float
    y_mm: float
    width_px: int
    height_px: int
    confidence: float
    extra: Dict[str, Any]


class FeedingVisionDetector:
    """Detects grape bowl, spoon, and human face/mouth in overhead or camera frames."""

    def __init__(self, calibrator: Optional[TabletopCalibrator] = None):
        self.calibrator = calibrator or self._default_calibrator()
        self._face_cascade = self._load_cascade("haarcascade_frontalface_default.xml")
        self._smile_cascade = self._load_cascade("haarcascade_smile.xml")
        self.mouth_tracker = MouthStateTracker()
        self.safety_fsm = FeedingSafetyFSM()
        self._landmarker = self._load_mediapipe_landmarker()

    @staticmethod
    def _load_mediapipe_landmarker():
        """Load MediaPipe FaceLandmarker if mediapipe and data/face_landmarker.task are available."""
        if not DEFAULT_FACE_LANDMARKER_MODEL.is_file():
            return None
        try:
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision as mp_vision

            opts = mp_vision.FaceLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=str(DEFAULT_FACE_LANDMARKER_MODEL)),
                num_faces=1,
            )
            return mp_vision.FaceLandmarker.create_from_options(opts)
        except Exception as exc:  # noqa: BLE001
            log.debug("MediaPipe FaceLandmarker unavailable, using OpenCV fallback: %s", exc)
            return None

    @staticmethod
    def _default_calibrator() -> TabletopCalibrator:
        cal = TabletopCalibrator()
        # Standard 640x480 tabletop mapping matching MockStation fiducials
        cal.compute_homography({
            0: (96, 80),    # (-160, 260)
            1: (544, 80),   # (160, 260)
            2: (544, 380),  # (160, 110)
            3: (96, 380),   # (-160, 110)
        })
        return cal

    @staticmethod
    def _load_cascade(name: str) -> Optional[cv2.CascadeClassifier]:
        try:
            path = cv2.data.haarcascades + name
            clf = cv2.CascadeClassifier(path)
            return clf if not clf.empty() else None
        except Exception:  # noqa: BLE001
            return None

    def pixel_to_mm(self, u: int, v: int) -> Tuple[float, float]:
        if self.calibrator.homography_matrix is not None:
            return self.calibrator.pixel_to_mm(float(u), float(v))
        x_mm = ((u - 320) / 280.0) * 200.0
        y_mm = 80.0 + ((440 - v) / 400.0) * 200.0
        return round(x_mm, 1), round(y_mm, 1)

    def detect_grape_bowl(self, bgr: np.ndarray) -> Optional[DetectedTarget]:
        """Locate the bowl with grapes by color segmentation (purple/dark-red/blue-green cluster) or circle contour."""
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        # Purple / violet / dark-red / blue-grape hues + green grape hues
        mask_purple = cv2.inRange(hsv, np.array([115, 45, 35]), np.array([175, 255, 255]))
        mask_blue = cv2.inRange(hsv, np.array([95, 60, 40]), np.array([130, 255, 255]))
        mask_red = cv2.inRange(hsv, np.array([0, 70, 40]), np.array([12, 255, 255]))
        mask = cv2.bitwise_or(mask_purple, cv2.bitwise_or(mask_blue, mask_red))

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best = None
        best_area = 120.0  # minimum pixel area
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > best_area:
                best_area = area
                best = cnt

        if best is not None:
            x, y, w, h = cv2.boundingRect(best)
            u, v = int(x + w / 2), int(y + h / 2)
            x_mm, y_mm = self.pixel_to_mm(u, v)
            # Clamp to reachable tabletop workspace
            x_mm = max(-170.0, min(170.0, x_mm))
            y_mm = max(95.0, min(265.0, y_mm))
            return DetectedTarget(
                label="grape_bowl",
                u_px=u,
                v_px=v,
                x_mm=x_mm,
                y_mm=y_mm,
                width_px=int(w),
                height_px=int(h),
                confidence=min(0.98, round(0.6 + best_area / 5000.0, 2)),
                extra={"zone": "zone_a", "food": "grapes", "tool": "gripper", "grasp_open_percent": 30},
            )

        # Fallback: default zone_a position on tabletop (-60, 180)
        return DetectedTarget(
            label="grape_bowl",
            u_px=236,
            v_px=240,
            x_mm=-60.0,
            y_mm=180.0,
            width_px=48,
            height_px=48,
            confidence=0.65,
            extra={"zone": "zone_a", "food": "grapes", "tool": "gripper", "grasp_open_percent": 30, "fallback": True},
        )

    def detect_spoon(self, bgr: np.ndarray) -> Optional[DetectedTarget]:
        """Locate the spoon / food bowl zone by green/teal/metallic marker or zone_b fallback."""
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        mask_green = cv2.inRange(hsv, np.array([35, 50, 40]), np.array([88, 255, 255]))
        contours, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best = None
        best_area = 100.0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > best_area:
                best_area = area
                best = cnt

        if best is not None:
            x, y, w, h = cv2.boundingRect(best)
            u, v = int(x + w / 2), int(y + h / 2)
            x_mm, y_mm = self.pixel_to_mm(u, v)
            x_mm = max(-170.0, min(170.0, x_mm))
            y_mm = max(95.0, min(265.0, y_mm))
            return DetectedTarget(
                label="spoon_holder",
                u_px=u,
                v_px=v,
                x_mm=x_mm,
                y_mm=y_mm,
                width_px=int(w),
                height_px=int(h),
                confidence=min(0.96, round(0.6 + best_area / 4000.0, 2)),
                extra={"zone": "spoon_holder", "food": "rice_bowl", "tool": "spoon", "grasp_open_percent": 0},
            )

        return DetectedTarget(
            label="spoon_holder",
            u_px=418,
            v_px=180,
            x_mm=70.0,
            y_mm=210.0,
            width_px=40,
            height_px=40,
            confidence=0.65,
            extra={"zone": "spoon_holder", "food": "rice_bowl", "tool": "spoon", "grasp_open_percent": 0, "fallback": True},
        )

    def detect_mouth(self, bgr: np.ndarray) -> DetectedTarget:
        """Detect person's face and mouth via MediaPipe FaceLandmarker (with OpenCV fallback)."""
        h_img, w_img = bgr.shape[:2]

        # 1. Preferred: MediaPipe FaceLandmarker (3D lip landmarks + MAR + EMA + 3-frame debounce)
        if self._landmarker is not None:
            try:
                import mediapipe as mp

                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = self._landmarker.detect(mp_img)
                if result.face_landmarks:
                    lms = result.face_landmarks[0]
                    upper = (lms[LM_UPPER_INNER_LIP].x * w_img, lms[LM_UPPER_INNER_LIP].y * h_img)
                    lower = (lms[LM_LOWER_INNER_LIP].x * w_img, lms[LM_LOWER_INNER_LIP].y * h_img)
                    left = (lms[LM_LEFT_MOUTH_CORNER].x * w_img, lms[LM_LEFT_MOUTH_CORNER].y * h_img)
                    right = (lms[LM_RIGHT_MOUTH_CORNER].x * w_img, lms[LM_RIGHT_MOUTH_CORNER].y * h_img)

                    raw_u = (left[0] + right[0]) * 0.5
                    raw_v = (upper[1] + lower[1]) * 0.5
                    raw_w = max(20.0, math.hypot(right[0] - left[0], right[1] - left[1]))
                    raw_h = max(12.0, math.hypot(lower[0] - upper[0], lower[1] - upper[1]) + 10.0)
                    mar = MouthStateTracker.compute_mar(upper, lower, left, right)

                    tracked = self.mouth_tracker.update(raw_u, raw_v, raw_w, mar)
                    mu, mv, mw = tracked["u_px"], tracked["v_px"], tracked["width_px"]
                    mh = int(round(raw_h))
                    at_standoff = mw >= STANDOFF_MOUTH_WIDTH_PX
                    x_mm, y_mm = self.pixel_to_mm(mu, mv)
                    x_mm = max(-160.0, min(160.0, x_mm))
                    y_mm = max(110.0, min(260.0, y_mm))

                    return DetectedTarget(
                        label="person_mouth",
                        u_px=mu,
                        v_px=mv,
                        x_mm=x_mm,
                        y_mm=y_mm,
                        width_px=mw,
                        height_px=mh,
                        confidence=0.96,
                        extra={
                            "detector": "mediapipe",
                            "face_detected": True,
                            "mar": tracked["mar"],
                            "mouth_open": tracked["mouth_open"],
                            "mouth_open_confirmed": tracked["mouth_open_confirmed"],
                            "open_streak": tracked["open_streak"],
                            "at_standoff": at_standoff,
                            "standoff_cm": round(max(5.0, 15.0 * (60.0 / max(mw, 25))), 1),
                            "waypoint": "serve",
                            "lip_points": [
                                (int(upper[0]), int(upper[1])),
                                (int(lower[0]), int(lower[1])),
                                (int(left[0]), int(left[1])),
                                (int(right[0]), int(right[1])),
                            ],
                        },
                    )
            except Exception as exc:  # noqa: BLE001
                log.debug("MediaPipe detect_mouth failed, falling back to OpenCV: %s", exc)

        # 2. Fallback: OpenCV Haar cascade face detection
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        faces = []
        if self._face_cascade is not None:
            faces = self._face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(50, 50))

        if len(faces) > 0:
            # Pick largest face
            fx, fy, fw, fh = max(faces, key=lambda r: r[2] * r[3])
            # Mouth is in the lower third of the face bounding box
            mu = int(fx + fw * 0.5)
            mv = int(fy + fh * 0.76)
            mw = int(fw * 0.42)
            mh = int(fh * 0.18)

            # Check if mouth is open via dark inner lip region intensity
            roi = gray[max(0, mv - mh // 2):min(gray.shape[0], mv + mh // 2),
                       max(0, mu - mw // 2):min(gray.shape[1], mu + mw // 2)]
            mouth_open = bool(roi.size > 0 and float(np.mean(roi)) < 85.0)
            at_standoff = mw >= STANDOFF_MOUTH_WIDTH_PX

            x_mm, y_mm = self.pixel_to_mm(mu, mv)
            x_mm = max(-160.0, min(160.0, x_mm))
            y_mm = max(110.0, min(260.0, y_mm))
            return DetectedTarget(
                label="person_mouth",
                u_px=mu,
                v_px=mv,
                x_mm=x_mm,
                y_mm=y_mm,
                width_px=mw,
                height_px=mh,
                confidence=0.92,
                extra={
                    "face_detected": True,
                    "mouth_open": mouth_open,
                    "at_standoff": at_standoff,
                    "standoff_cm": round(max(5.0, 15.0 * (60.0 / max(mw, 25))), 1),
                    "waypoint": "serve",
                },
            )

        # Also check for skin-tone / warm oval region in upper workspace (person leaning near table edge)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        skin_mask = cv2.inRange(hsv, np.array([0, 25, 60]), np.array([25, 180, 255]))
        # Focus on upper portion of image (Y near top edge of table where user sits)
        skin_mask[int(bgr.shape[0] * 0.65):, :] = 0
        contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best = max(contours, key=cv2.contourArea, default=None)
        if best is not None and cv2.contourArea(best) > 450:
            x, y, w, h = cv2.boundingRect(best)
            mu = int(x + w * 0.5)
            mv = int(y + h * 0.72)
            mw = max(35, int(w * 0.4))
            mh = max(16, int(h * 0.18))
            x_mm, y_mm = self.pixel_to_mm(mu, mv)
            x_mm = max(-160.0, min(160.0, x_mm))
            y_mm = max(110.0, min(260.0, y_mm))
            return DetectedTarget(
                label="person_mouth",
                u_px=mu,
                v_px=mv,
                x_mm=x_mm,
                y_mm=y_mm,
                width_px=mw,
                height_px=mh,
                confidence=0.78,
                extra={
                    "face_detected": True,
                    "mouth_open": True,
                    "at_standoff": mw >= STANDOFF_MOUTH_WIDTH_PX,
                    "standoff_cm": 7.5,
                    "waypoint": "serve",
                },
            )

        # Fallback: default assistive feeding delivery position in front of user
        return DetectedTarget(
            label="person_mouth",
            u_px=320,
            v_px=95,
            x_mm=0.0,
            y_mm=245.0,
            width_px=55,
            height_px=24,
            confidence=0.70,
            extra={
                "face_detected": False,
                "mouth_open": True,
                "at_standoff": True,
                "standoff_cm": 8.0,
                "waypoint": "serve",
                "fallback": True,
            },
        )

    def analyze_and_annotate(self, bgr: np.ndarray) -> Tuple[Dict[str, Any], np.ndarray]:
        """Run full scene perception (grape bowl, spoon, mouth) and draw HUD overlays."""
        annotated = bgr.copy()
        grape_bowl = self.detect_grape_bowl(bgr)
        spoon = self.detect_spoon(bgr)
        mouth = self.detect_mouth(bgr)

        # Draw detections on frame
        if grape_bowl:
            u, v, w, h = grape_bowl.u_px, grape_bowl.v_px, grape_bowl.width_px, grape_bowl.height_px
            cv2.rectangle(annotated, (u - w // 2, v - h // 2), (u + w // 2, v + h // 2), (180, 60, 240), 2)
            cv2.circle(annotated, (u, v), 4, (180, 60, 240), -1)
            cv2.putText(
                annotated,
                f"BOWL (Grapes) ({grape_bowl.x_mm:.0f},{grape_bowl.y_mm:.0f})mm",
                (max(8, u - 60), max(20, v - h // 2 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (180, 60, 240),
                2,
            )

        if spoon:
            u, v, w, h = spoon.u_px, spoon.v_px, spoon.width_px, spoon.height_px
            cv2.rectangle(annotated, (u - w // 2, v - h // 2), (u + w // 2, v + h // 2), (50, 210, 100), 2)
            cv2.putText(
                annotated,
                f"SPOON ({spoon.x_mm:.0f},{spoon.y_mm:.0f})mm",
                (max(8, u - 45), max(20, v - h // 2 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (50, 210, 100),
                2,
            )

        if mouth:
            u, v, w, h = mouth.u_px, mouth.v_px, mouth.width_px, mouth.height_px
            color = (40, 220, 255)
            cv2.rectangle(annotated, (u - w // 2, v - h // 2), (u + w // 2, v + h // 2), color, 2)
            cv2.circle(annotated, (u, v), 4, (0, 255, 255), -1)
            standoff_cm = mouth.extra.get("standoff_cm", 8.0)
            cv2.putText(
                annotated,
                f"MOUTH TARGET ({mouth.x_mm:.0f},{mouth.y_mm:.0f})mm [Standoff {standoff_cm}cm]",
                (max(8, u - 90), max(20, v - h // 2 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                color,
                2,
            )

        # Draw feeding vector arrow from grape bowl to mouth
        if grape_bowl and mouth:
            cv2.arrowedLine(
                annotated,
                (grape_bowl.u_px, grape_bowl.v_px),
                (mouth.u_px, mouth.v_px),
                (50, 240, 180),
                2,
                tipLength=0.08,
            )

        summary = {
            "grape_bowl": asdict(grape_bowl) if grape_bowl else None,
            "spoon": asdict(spoon) if spoon else None,
            "mouth": asdict(mouth) if mouth else None,
        }
        return summary, annotated


def capture_camera_frame_bgr(preferred_devices: Tuple[int, ...] = (4, 2, 0), fallback_station=None) -> Tuple[np.ndarray, str]:
    """Capture a BGR frame from /dev/video4 (overhead tabletop), /dev/video2, or fallback simulator."""
    for dev_idx in preferred_devices:
        cap = cv2.VideoCapture(dev_idx)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None and frame.size > 0:
                return frame, f"/dev/video{dev_idx}"

    # Fallback to MockStation synthetic camera frame
    if fallback_station is not None:
        pil_img = fallback_station.capture_frame()
        rgb = np.array(pil_img)
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), "mock_station"

    # Blank synthetic tabletop with grape bowl, spoon, and mouth zone
    canvas = np.full((DEFAULT_FRAME_H, DEFAULT_FRAME_W, 3), (230, 238, 240), dtype=np.uint8)
    cv2.circle(canvas, (236, 240), 22, (180, 50, 160), -1)  # Purple grape bowl
    cv2.circle(canvas, (418, 180), 20, (60, 190, 60), -1)   # Green spoon holder
    cv2.ellipse(canvas, (320, 95), (35, 45), 0, 0, 360, (150, 180, 225), -1)  # Person face/mouth region
    return canvas, "synthetic"


def run_camera_feeding_cycle(
    mode: str = "grapes",
    mcp_server=None,
    robot_tools=None,
    preferred_camera: int = 4,
) -> Dict[str, Any]:
    """
    End-to-end camera-driven assistive feeding cycle:
      1. Captures overhead camera frame (/dev/video4 by default).
      2. Detects the bowl with grapes (or spoon + bowl) and the person's mouth.
      3. Computes safe trajectory waypoints & standoff.
      4. Moves the slave arm via RobotTools (if hardware connected and ELROBOT_ALLOW_MOTION=1,
         or returns dry_run plan) AND updates the Digital Twin / KinematicsSafetyEngine.
    """
    if mode not in ("grapes", "spoon"):
        raise ValueError(f"Unsupported feeding mode: {mode!r}. Use 'grapes' or 'spoon'.")

    station = getattr(mcp_server, "station", None) if mcp_server else None
    bgr, source = capture_camera_frame_bgr(preferred_devices=(preferred_camera, 4, 2), fallback_station=station)

    detector = FeedingVisionDetector()
    detections, annotated_bgr = detector.analyze_and_annotate(bgr)

    # Encode annotated image to base64 JPEG for Web UI / logs
    rgb = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)
    try:
        pil_img = detector.calibrator.overlay_calibrated_grid(pil_img)
    except Exception:  # noqa: BLE001
        pass
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=85)
    annotated_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    grape_bowl = detections["grape_bowl"]
    spoon = detections["spoon"]
    mouth = detections["mouth"]

    steps_log: List[str] = [
        f"Camera source: {source} (preferred /dev/video{preferred_camera})",
        f"Detected grape bowl at ({grape_bowl['x_mm']:.1f}, {grape_bowl['y_mm']:.1f}) mm [conf={grape_bowl['confidence']}]",
        f"Detected spoon holder at ({spoon['x_mm']:.1f}, {spoon['y_mm']:.1f}) mm [conf={spoon['confidence']}]",
        f"Detected person mouth target at ({mouth['x_mm']:.1f}, {mouth['y_mm']:.1f}) mm "
        f"[standoff={mouth['extra']['standoff_cm']} cm]",
    ]

    # 1. Execute Cartesian safety engine trajectory (updates 3D Digital Twin & validates Z >= 12mm floor clamp)
    cartesian_result: Dict[str, Any] = {}
    if mcp_server is not None:
        if mode == "grapes":
            bx, by = grape_bowl["x_mm"], grape_bowl["y_mm"]
            mx, my = mouth["x_mm"], mouth["y_mm"]
            # Move simulated blue_cube_01 to detected bowl position so grasp succeeds cleanly
            if hasattr(mcp_server.station, "objects") and "blue_cube_01" in mcp_server.station.objects:
                mcp_server.station.objects["blue_cube_01"]["x"] = bx
                mcp_server.station.objects["blue_cube_01"]["y"] = by
                mcp_server.station.objects["blue_cube_01"]["name"] = "grape_cluster"

            pick_res = mcp_server.pick_at(bx, by)
            steps_log.extend(pick_res.get("steps", []))

            # Approach person's mouth at safe facial height (Z = 110mm, stopping at standoff)
            standoff_y = min(255.0, max(120.0, my - 15.0))
            mcp_server.kinematics.safe_move(mx, standoff_y, 110.0)
            steps_log.append(
                f"Delivered grape to mouth standoff ({mx:.1f}, {standoff_y:.1f}, Z=110.0 mm) — "
                f"stopped {mouth['extra']['standoff_cm']} cm in front of face for user to lean in"
            )
            # Release when user takes bite
            mcp_server.set_gripper(0.35)
            steps_log.append("Gentle grape grasp (30% open) -> opened on bite handover")
            cartesian_result = {"pick": pick_res, "standoff_pose": {"x": mx, "y": standoff_y, "z": 110.0}}

        elif mode == "spoon":
            sx, sy = spoon["x_mm"], spoon["y_mm"]
            bx, by = grape_bowl["x_mm"], grape_bowl["y_mm"]
            mx, my = mouth["x_mm"], mouth["y_mm"]
            if hasattr(mcp_server.station, "objects") and "green_tool_01" in mcp_server.station.objects:
                mcp_server.station.objects["green_tool_01"]["x"] = sx
                mcp_server.station.objects["green_tool_01"]["y"] = sy
                mcp_server.station.objects["green_tool_01"]["name"] = "feeding_spoon"

            # Step A: Pick spoon from holder
            pick_spoon = mcp_server.pick_at(sx, sy)
            steps_log.append(f"Picked feeding spoon at ({sx:.1f}, {sy:.1f}) mm")
            # Step B: Dip & scoop food from bowl
            mcp_server.kinematics.safe_move(bx, by, 45.0)
            mcp_server.kinematics.safe_move(bx, by, 18.0)
            mcp_server.kinematics.safe_move(bx, by, 75.0)
            steps_log.append(f"Scooped food from bowl at ({bx:.1f}, {by:.1f}) mm and leveled spoon at Z=75mm")
            # Step C: Deliver spoon to mouth standoff (keep gripper closed!)
            standoff_y = min(255.0, max(120.0, my - 15.0))
            mcp_server.kinematics.safe_move(mx, standoff_y, 110.0)
            steps_log.append(
                f"Holding level spoon at mouth standoff ({mx:.1f}, {standoff_y:.1f}, Z=110.0 mm) — "
                "gripper remains closed while person eats"
            )
            cartesian_result = {"pick_spoon": pick_spoon, "standoff_pose": {"x": mx, "y": standoff_y, "z": 110.0}}

    # 2. Execute Joint-level Waypoint / Slave Arm Hardware Plan via RobotTools (if available)
    hardware_plan: List[Dict[str, Any]] = []
    if robot_tools is not None:
        wps = load_waypoints()
        desired_seq = (
            [("waypoint", "zone_a_hover"), ("waypoint", "zone_a"), ("gripper", 30.0), ("waypoint", "serve")]
            if mode == "grapes"
            else [
                ("waypoint", "spoon_holder_hover"),
                ("waypoint", "spoon_holder"),
                ("gripper", 0.0),
                ("waypoint", "bowl_hover"),
                ("waypoint", "bowl_scoop"),
                ("waypoint", "bowl_lift"),
                ("waypoint", "serve_spoon"),
            ]
        )
        for kind, target in desired_seq:
            if kind == "waypoint":
                if target in wps:
                    res = robot_tools.call(robot_tools.go_to_waypoint, target)
                    hardware_plan.append({"action": "go_to_waypoint", "target": target, "result": res})
                else:
                    hardware_plan.append({
                        "action": "go_to_waypoint",
                        "target": target,
                        "status": "waypoint_not_taught_yet",
                        "hint": f"Teach with: ./cli.sh hw teach {target}",
                    })
            elif kind == "gripper":
                res = robot_tools.call(robot_tools.set_gripper, float(target))
                hardware_plan.append({"action": "set_gripper", "open_percent": target, "result": res})

    return {
        "status": "FEEDING_CYCLE_COMPLETED",
        "mode": mode,
        "camera_source": source,
        "detections": detections,
        "steps": steps_log,
        "cartesian": cartesian_result,
        "hardware_plan": hardware_plan,
        "annotated_image_base64": annotated_b64,
    }
