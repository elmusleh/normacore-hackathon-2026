"""Make camera frames easier to read for food detection, and measure how well they are exposed.

The Station stores each camera frame as a small JPEG. On the white table the table camera
is often overexposed: the table is pure white and a pale green grape barely stands out.
`enhance_jpeg` fixes what software can fix, in this order:

  0. Light denoise: removes sensor grain, which CLAHE would otherwise amplify.
  1. White balance against the table (bright, grey-ish pixels taken as white; gray-world
     if there are too few). Gains are capped, so colourful scenes are not pushed off.
  2. Auto gamma: darkens a too-bright frame (or brightens a too-dark one) so the
     mid-tones, where the food is, get more contrast.
  3. CLAHE on the lightness channel: local contrast, so grape edges and bowl rims show
     without blowing out the rest.
  4. Optional light sharpening, for frames the Station has scaled down.

Pixels that are already pure white carry no information, and no software brings them back.
`exposure_stats` reports how many there are. If it is a lot, lower the camera's exposure
(`./cli.sh cameras --tune`) instead.

Only the pictures Claude and the console see are enhanced. The ACT demo recorder stores the
raw frames on purpose (src/demo_recorder.py reads the queues directly).

Settings live in config/elrobot.json -> camera_enhance (defaults in src/elrobot_config.py).
A per-camera block under "cameras" overrides the shared values, e.g.
  "camera_enhance": {"enabled": true, "cameras": {"face": {"enabled": false}}}
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

# Luminance at or above this counts as blown out; at or below DARK as crushed black.
CLIPPED_LEVEL = 250
DARK_LEVEL = 5
# Above this share of blown-out pixels, the camera exposure itself should be lowered.
OVEREXPOSED_SHARE = 0.10
UNDEREXPOSED_SHARE = 0.25
# Target mean luminance (0-255) for auto gamma, and the band left alone around it.
TARGET_MEAN = 115.0
MEAN_DEADBAND = 20.0

DEFAULT_OPTIONS: Dict[str, Any] = {
    "enabled": True,
    "white_balance": True,
    "gamma": "auto",          # "auto", a number (>1 darkens, <1 brightens), or null for none
    "denoise": 4,             # edge-keeping smoothing strength; 0 turns it off (sensor grain)
    "clahe_clip": 1.8,        # 0 turns CLAHE off
    "clahe_grid": 8,
    "sharpen": 0.2,           # unsharp-mask amount; 0 turns it off
    "jpeg_quality": 92,
}


def options_for(cfg: Dict[str, Any], camera: str) -> Dict[str, Any]:
    """Enhancement options for one camera: defaults, then the shared block, then its own block."""
    block = dict(cfg.get("camera_enhance") or {})
    per_camera = block.pop("cameras", {}) or {}
    opts = dict(DEFAULT_OPTIONS)
    opts.update(block)
    opts.update(per_camera.get(camera, {}) or {})
    return opts


def _luma(bgr):
    import cv2  # noqa: WPS433

    return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)


def exposure_stats(bgr) -> Dict[str, Any]:
    """Mean luminance and the share of blown-out and black pixels, with a plain verdict."""
    import numpy as np  # noqa: WPS433

    y = _luma(bgr)
    total = float(y.size) or 1.0
    clipped = float(np.count_nonzero(y >= CLIPPED_LEVEL)) / total
    dark = float(np.count_nonzero(y <= DARK_LEVEL)) / total
    if clipped > OVEREXPOSED_SHARE:
        verdict = "overexposed"
    elif dark > UNDEREXPOSED_SHARE:
        verdict = "underexposed"
    else:
        verdict = "ok"
    return {"mean": round(float(y.mean()), 1), "clipped_share": round(clipped, 3),
            "dark_share": round(dark, 3), "verdict": verdict}


def auto_gamma(mean: float) -> float:
    """Gamma that moves the mean luminance toward TARGET_MEAN, kept within [0.6, 2.2]."""
    if abs(mean - TARGET_MEAN) <= MEAN_DEADBAND or mean <= 1 or mean >= 254:
        return 1.0
    g = math.log(TARGET_MEAN / 255.0) / math.log(mean / 255.0)
    return max(0.6, min(2.2, g))


def _white_balance(bgr):
    """White-patch balance on the table: bright, low-saturation, not blown-out pixels are taken
    as white. Falls back to gray-world when there are too few. Gains stay within +-20 %."""
    import cv2  # noqa: WPS433
    import numpy as np  # noqa: WPS433

    img = bgr.astype(np.float32)
    y = _luma(bgr)
    sat = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[..., 1]
    keep = (y >= 170) & (y < CLIPPED_LEVEL) & (sat < 50)
    if np.count_nonzero(keep) < 0.02 * y.size:
        keep = y < CLIPPED_LEVEL  # gray-world on everything that is not blown out
        if np.count_nonzero(keep) < 100:
            return bgr
    means = img[keep].mean(axis=0)
    gray = float(means.mean())
    gains = np.clip(gray / np.maximum(means, 1.0), 0.83, 1.2)
    return np.clip(img * gains, 0, 255).astype(np.uint8)


def _denoise(bgr, strength: float):
    import cv2  # noqa: WPS433

    # Bilateral filter: smooths grain but keeps edges (grape rims), and costs ~1 ms per frame,
    # where non-local means cost ~90 ms at 299x224.
    return cv2.bilateralFilter(bgr, 5, 8.0 * float(strength), 3.0)


def _gamma(bgr, gamma: float):
    import cv2  # noqa: WPS433
    import numpy as np  # noqa: WPS433

    if abs(gamma - 1.0) < 0.02:
        return bgr
    lut = np.clip(((np.arange(256) / 255.0) ** gamma) * 255.0, 0, 255).astype(np.uint8)
    return cv2.LUT(bgr, lut)


def _clahe(bgr, clip: float, grid: int):
    import cv2  # noqa: WPS433

    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=float(clip), tileGridSize=(int(grid), int(grid))).apply(l)
    return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)


def _sharpen(bgr, amount: float):
    import cv2  # noqa: WPS433

    blur = cv2.GaussianBlur(bgr, (0, 0), 1.2)
    return cv2.addWeighted(bgr, 1.0 + amount, blur, -amount, 0)


def enhance_bgr(bgr, opts: Optional[Dict[str, Any]] = None):
    """Return an enhanced copy of a BGR image (uint8). See the module docstring for the steps."""
    o = dict(DEFAULT_OPTIONS)
    o.update(opts or {})
    out = bgr
    if float(o.get("denoise") or 0) > 0:
        out = _denoise(out, float(o["denoise"]))
    if o.get("white_balance"):
        out = _white_balance(out)
    gamma = o.get("gamma")
    if gamma == "auto":
        gamma = auto_gamma(float(_luma(out).mean()))
    if gamma:
        out = _gamma(out, float(gamma))
    if float(o.get("clahe_clip") or 0) > 0:
        out = _clahe(out, float(o["clahe_clip"]), int(o.get("clahe_grid") or 8))
    if float(o.get("sharpen") or 0) > 0:
        out = _sharpen(out, float(o["sharpen"]))
    return out


def decode_jpeg(jpeg: bytes):
    """BGR image from JPEG bytes, or None if it cannot be decoded (or OpenCV is missing)."""
    try:
        import cv2  # noqa: WPS433
        import numpy as np  # noqa: WPS433
    except ImportError:
        return None
    img = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    return img if img is not None and img.size else None


def enhance_jpeg(jpeg: bytes, opts: Optional[Dict[str, Any]] = None
                 ) -> Tuple[bytes, Optional[Dict[str, Any]], bool]:
    """(jpeg to show, exposure stats of the raw frame, whether it was enhanced).

    Frames that cannot be decoded come back unchanged with stats None, so a camera
    problem never turns into a look() failure."""
    o = dict(DEFAULT_OPTIONS)
    o.update(opts or {})
    bgr = decode_jpeg(jpeg)
    if bgr is None:
        return jpeg, None, False
    stats = exposure_stats(bgr)
    if not o.get("enabled", True):
        return jpeg, stats, False
    import cv2  # noqa: WPS433

    ok, buf = cv2.imencode(".jpg", enhance_bgr(bgr, o),
                           [int(cv2.IMWRITE_JPEG_QUALITY), int(o.get("jpeg_quality") or 92)])
    if not ok:
        return jpeg, stats, False
    return buf.tobytes(), stats, True


def exposure_hint(camera: str, stats: Optional[Dict[str, Any]]) -> Optional[str]:
    """A short instruction for the human when the raw frame is badly exposed, else None."""
    if not stats or stats["verdict"] == "ok":
        return None
    if stats["verdict"] == "overexposed":
        return (f"camera {camera!r} is overexposed ({stats['clipped_share']:.0%} of the picture is pure white); "
                "food on the white table may be hard to see. Ask the human to lower its exposure: "
                "stop the Station, run ./cli.sh cameras --tune, then restart the Station.")
    return (f"camera {camera!r} is underexposed ({stats['dark_share']:.0%} of the picture is black). "
            "Ask the human to raise its exposure or add light (./cli.sh cameras --tune).")
