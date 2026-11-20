"""
Vision Homography & Coordinate Calibration Engine.
Maps 2D camera pixels to 3D tabletop millimeters (X, Y) and draws a labeled metric grid.
"""

from typing import Tuple, List, Dict, Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFont


class TabletopCalibrator:
    """
    Computes perspective homography from 4 corner fiducial markers (AprilTags / ArUco)
    and projects a calibrated millimeter coordinate grid onto camera frames.
    """

    def __init__(self, marker_coords_mm: Optional[Dict[int, Tuple[float, float]]] = None):
        # Default physical positions of markers in mm (relative to arm base origin)
        self.marker_coords_mm = marker_coords_mm or {
            0: (-160.0, 260.0),  # Top-Left (Tag 0)
            1: (160.0, 260.0),   # Top-Right (Tag 1)
            2: (160.0, 110.0),   # Bottom-Right (Tag 2)
            3: (-160.0, 110.0),  # Bottom-Left (Tag 3)
        }
        self.homography_matrix: Optional[np.ndarray] = None
        self.inv_homography_matrix: Optional[np.ndarray] = None

    def compute_homography(self, detected_pixels: Dict[int, Tuple[float, float]]) -> np.ndarray:
        """
        Compute 3x3 homography matrix mapping image pixels [u, v, 1]^T -> tabletop [X, Y, 1]^T.
        detected_pixels: {0: (u0, v0), 1: (u1, v1), 2: (u2, v2), 3: (u3, v3)}
        """
        src_pts = []
        dst_pts = []
        for tag_id in [0, 1, 2, 3]:
            if tag_id not in detected_pixels:
                raise ValueError(f"Marker {tag_id} missing from detected points")
            src_pts.append(detected_pixels[tag_id])
            dst_pts.append(self.marker_coords_mm[tag_id])

        src = np.array(src_pts, dtype=np.float32)
        dst = np.array(dst_pts, dtype=np.float32)

        # Standard 4-point homography (Direct Linear Transformation)
        H = self._calculate_homography_dlt(src, dst)
        self.homography_matrix = H
        self.inv_homography_matrix = np.linalg.inv(H)
        return H

    def _calculate_homography_dlt(self, src: np.ndarray, dst: np.ndarray) -> np.ndarray:
        """Pure-NumPy DLT implementation (zero external OpenCV dependency required)."""
        A = []
        for i in range(4):
            x, y = src[i][0], src[i][1]
            u, v = dst[i][0], dst[i][1]
            A.append([-x, -y, -1, 0, 0, 0, x * u, y * u, u])
            A.append([0, 0, 0, -x, -y, -1, x * v, y * v, v])
        A = np.asarray(A)
        _, _, Vh = np.linalg.svd(A)
        L = Vh[-1, :]
        H = L.reshape(3, 3)
        return H / H[2, 2]

    def pixel_to_mm(self, u: float, v: float) -> Tuple[float, float]:
        """Transform image pixel (u, v) to physical tabletop coordinate (X_mm, Y_mm)."""
        if self.homography_matrix is None:
            raise RuntimeError("Homography matrix has not been calibrated yet.")
        p = np.array([u, v, 1.0], dtype=np.float32)
        p_mapped = np.dot(self.homography_matrix, p)
        x_mm = p_mapped[0] / p_mapped[2]
        y_mm = p_mapped[1] / p_mapped[2]
        return round(float(x_mm), 1), round(float(y_mm), 1)

    def mm_to_pixel(self, x_mm: float, y_mm: float) -> Tuple[int, int]:
        """Transform physical tabletop coordinate (X_mm, Y_mm) back to pixel (u, v)."""
        if self.inv_homography_matrix is None:
            raise RuntimeError("Homography matrix has not been calibrated yet.")
        p = np.array([x_mm, y_mm, 1.0], dtype=np.float32)
        p_pixel = np.dot(self.inv_homography_matrix, p)
        u = p_pixel[0] / p_pixel[2]
        v = p_pixel[1] / p_pixel[2]
        return int(round(float(u))), int(round(float(v)))

    def overlay_calibrated_grid(self, image: Image.Image) -> Image.Image:
        """
        Draws a high-contrast metric coordinate grid with mm labels directly onto the image.
        This allows Claude / Codex to visually verify coordinates with zero hallucination.
        """
        if self.inv_homography_matrix is None:
            return image

        annotated = image.copy()
        draw = ImageDraw.Draw(annotated)

        # X grid lines every 50 mm from -150 to +150
        # Y grid lines every 50 mm from 100 to 250
        x_ticks = range(-150, 151, 50)
        y_ticks = range(100, 251, 50)

        # Draw vertical lines (constant X)
        for x in x_ticks:
            p_top = self.mm_to_pixel(x, 260.0)
            p_bot = self.mm_to_pixel(x, 100.0)
            draw.line([p_top, p_bot], fill=(100, 140, 220, 160), width=1)
            draw.text((p_bot[0] - 12, p_bot[1] + 4), f"{x}", fill=(60, 90, 180))

        # Draw horizontal lines (constant Y)
        for y in y_ticks:
            p_left = self.mm_to_pixel(-160.0, y)
            p_right = self.mm_to_pixel(160.0, y)
            draw.line([p_left, p_right], fill=(100, 140, 220, 160), width=1)
            draw.text((p_left[0] - 32, p_left[1] - 6), f"{y}", fill=(60, 90, 180))

        # Draw coordinate legend in corner
        draw.rectangle([10, 10, 175, 45], fill=(255, 255, 255, 220), outline=(50, 50, 50))
        draw.text((16, 14), "METRIC GRID (mm)", fill=(0, 0, 0))
        draw.text((16, 28), "Origin (0,0) = Arm Base", fill=(100, 100, 100))

        return annotated
