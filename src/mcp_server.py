"""
Model Context Protocol (MCP) Server for NormaCore Station.
Exposes high-level cartesian and visual tools to Claude Code / Codex.
"""

import io
import base64
from typing import Dict, Any, Optional

try:
    from mock_station import MockStation
    from vision_homography import TabletopCalibrator
    from kinematics_safety import KinematicsSafetyEngine
except ImportError:
    from src.mock_station import MockStation
    from src.vision_homography import TabletopCalibrator
    from src.kinematics_safety import KinematicsSafetyEngine


class NormaCoreMCPServer:
    """
    Standard MCP Tool Server interface for Claude / Codex.
    Connects to NormaCore Station runtime (or MockStation in testing mode).
    """

    def __init__(self, station_instance=None):
        self.station = station_instance or MockStation()
        self.calibrator = TabletopCalibrator()

        # Initialize calibration with mock tag pixel locations
        mock_tag_pixels = {
            0: self.station.mm_to_pixel(-160.0, 260.0),
            1: self.station.mm_to_pixel(160.0, 260.0),
            2: self.station.mm_to_pixel(160.0, 110.0),
            3: self.station.mm_to_pixel(-160.0, 110.0),
        }
        self.calibrator.compute_homography(mock_tag_pixels)
        self.kinematics = KinematicsSafetyEngine(self.station)

    # -------------------------------------------------------------
    # Tool 1: get_calibrated_view
    # -------------------------------------------------------------
    def get_calibrated_view(self) -> Dict[str, Any]:
        """
        Captures an overhead workspace image, overlays the calibrated metric
        millimeter coordinate grid, and returns the image as a base64 string
        alongside current robot telemetry.
        """
        raw_frame = self.station.capture_frame()
        grid_frame = self.calibrator.overlay_calibrated_grid(raw_frame)

        # Convert to Base64 PNG
        buffer = io.BytesIO()
        grid_frame.save(buffer, format="PNG")
        b64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

        telemetry = self.station.get_arm_telemetry()
        return {
            "image_base64": b64_image,
            "telemetry": telemetry,
            "table_limits": {
                "x_range_mm": [-180, 180],
                "y_range_mm": [90, 270],
                "z_floor_mm": 12.0,
            },
            "instructions": "Inspect the image using the metric grid labels. Coordinates are in millimeters relative to arm base (0,0).",
        }

    # -------------------------------------------------------------
    # Tool 2: pick_at
    # -------------------------------------------------------------
    def pick_at(self, x_mm: float, y_mm: float, yaw_deg: float = 0.0) -> Dict[str, Any]:
        """
        Executes a safe vertical pick at the specified tabletop (X, Y) coordinate in millimeters.
        Automatically handles approach, descent, grip, load checking, and ascent.
        """
        return self.kinematics.execute_safe_pick(x_mm, y_mm, yaw_deg)

    # -------------------------------------------------------------
    # Tool 3: place_at
    # -------------------------------------------------------------
    def place_at(self, x_mm: float, y_mm: float) -> Dict[str, Any]:
        """
        Executes a safe horizontal transit and vertical placement at the specified tabletop (X, Y) coordinate in millimeters.
        """
        return self.kinematics.execute_safe_place(x_mm, y_mm)

    # -------------------------------------------------------------
    # Tool 4: set_gripper
    # -------------------------------------------------------------
    def set_gripper(self, state: float) -> Dict[str, Any]:
        """
        Commands gripper position: 1.0 (fully open) to 0.0 (fully closed).
        """
        return self.station.set_gripper(state)

    # -------------------------------------------------------------
    # Tool 5: verify_grasp
    # -------------------------------------------------------------
    def verify_grasp(self) -> Dict[str, Any]:
        """
        Verifies if an object is currently gripped using motor current/load telemetry.
        Returns 'CONFIRMED' if load > 0.3, otherwise 'EMPTY_GRIP'.
        """
        telem = self.station.get_arm_telemetry()
        load = telem.get("gripper_load", 0.0)
        held = telem.get("held_object")
        return {
            "grasped": load > 0.3,
            "held_object": held,
            "load_ratio": round(load, 2),
            "status": "CONFIRMED" if load > 0.3 else "EMPTY_GRIP",
        }

    # -------------------------------------------------------------
    # Tool 6: reset_home
    # -------------------------------------------------------------
    def reset_home(self) -> Dict[str, Any]:
        """
        Returns arm to safe home position.
        """
        return self.kinematics.execute_home()

    # -------------------------------------------------------------
    # Testing Utility: simulate_perturbation
    # -------------------------------------------------------------
    def simulate_perturbation(self, object_id: str, new_x_mm: float, new_y_mm: float) -> Dict[str, Any]:
        """
        Simulates a judge sliding an object across the table during testing.
        """
        if hasattr(self.station, "simulate_judge_perturbation"):
            self.station.simulate_judge_perturbation(object_id, new_x_mm, new_y_mm)
            return {"status": "PERTURBED", "object_id": object_id, "new_pos": (new_x_mm, new_y_mm)}
        return {"status": "UNSUPPORTED_ON_PHYSICAL_HARDWARE"}
