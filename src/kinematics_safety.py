"""
Deterministic Kinematics & Safety Guardrails Engine.
Enforces hard physical boundary limits, table floor collision protection,
and executes smooth pick-and-place primitive trajectories.
"""

from typing import Dict, Any, Tuple
import time


class SafetyLimits:
    """Hard physical boundaries for the 7+1 DOF ElRobot workspace."""
    X_MIN = -180.0
    X_MAX = 180.0
    Y_MIN = 90.0
    Y_MAX = 270.0
    Z_TABLE_FLOOR = 12.0     # Never descend below 12mm above tabletop surface
    Z_TRANSIT_HEIGHT = 70.0  # Horizontal moves occur safely at this clearance
    Z_HOVER_HEIGHT = 45.0    # Pre-grasp approach height
    Z_GRASP_HEIGHT = 14.0    # Grasping height


class KinematicsSafetyEngine:
    """
    Wraps the Station hardware driver with deterministic safety checks
    and multi-stage approach trajectories.
    """

    def __init__(self, station_driver):
        self.station = station_driver

    def validate_cartesian_target(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        """Clamps and validates coordinates against workspace boundaries."""
        if z < SafetyLimits.Z_TABLE_FLOOR:
            raise ValueError(
                f"[SAFETY ABORT] Target Z={z:.1f}mm violates table floor limit ({SafetyLimits.Z_TABLE_FLOOR}mm)"
            )
        if not (SafetyLimits.X_MIN <= x <= SafetyLimits.X_MAX):
            raise ValueError(
                f"[SAFETY ABORT] Target X={x:.1f}mm out of workspace bounds [{SafetyLimits.X_MIN}, {SafetyLimits.X_MAX}]"
            )
        if not (SafetyLimits.Y_MIN <= y <= SafetyLimits.Y_MAX):
            raise ValueError(
                f"[SAFETY ABORT] Target Y={y:.1f}mm out of workspace bounds [{SafetyLimits.Y_MIN}, {SafetyLimits.Y_MAX}]"
            )
        return float(x), float(y), float(z)

    def safe_move(self, x: float, y: float, z: float, yaw: float = 0.0) -> Dict[str, Any]:
        """Validates coordinates and commands end-effector move."""
        cx, cy, cz = self.validate_cartesian_target(x, y, z)
        return self.station.move_end_effector(cx, cy, cz, roll=0.0, pitch=90.0, yaw=yaw)

    def execute_safe_pick(self, x_mm: float, y_mm: float, yaw_deg: float = 0.0) -> Dict[str, Any]:
        """
        Executes a deterministic multi-stage vertical pick trajectory:
        1. Transit to hover height above target.
        2. Open gripper fully.
        3. Descend vertically to grasp height.
        4. Close gripper.
        5. Verify gripper motor load (detect if item actually gripped).
        6. Ascend vertically to transit height.
        """
        self.validate_cartesian_target(x_mm, y_mm, SafetyLimits.Z_GRASP_HEIGHT)

        log = []
        # Step 1: Move to Hover Clearance
        res1 = self.safe_move(x_mm, y_mm, SafetyLimits.Z_HOVER_HEIGHT, yaw_deg)
        log.append(f"Hovered at ({x_mm:.1f}, {y_mm:.1f}, {SafetyLimits.Z_HOVER_HEIGHT})")

        # Step 2: Open Gripper
        self.station.set_gripper(1.0)
        log.append("Gripper opened")

        # Step 3: Vertical Descent to Grasp
        self.safe_move(x_mm, y_mm, SafetyLimits.Z_GRASP_HEIGHT, yaw_deg)
        log.append(f"Descended to grasp height {SafetyLimits.Z_GRASP_HEIGHT}mm")

        # Step 4: Close Gripper
        grip_res = self.station.set_gripper(0.0)
        log.append(f"Grip status: {grip_res.get('status')} (load: {grip_res.get('load', 0.0):.2f})")

        # Step 5: Vertical Ascent to Transit Height
        self.safe_move(x_mm, y_mm, SafetyLimits.Z_TRANSIT_HEIGHT, yaw_deg)
        log.append(f"Ascended to transit clearance {SafetyLimits.Z_TRANSIT_HEIGHT}mm")

        is_grasped = grip_res.get("status") == "GRASPED"
        return {
            "success": is_grasped,
            "status": grip_res.get("status"),
            "object_id": grip_res.get("object_id"),
            "load": grip_res.get("load"),
            "steps": log,
        }

    def execute_safe_place(self, x_mm: float, y_mm: float) -> Dict[str, Any]:
        """
        Executes a deterministic vertical place trajectory:
        1. Transit horizontally at clearance height.
        2. Descend vertically to release height.
        3. Open gripper to release.
        4. Ascend vertically back to clearance height.
        """
        self.validate_cartesian_target(x_mm, y_mm, SafetyLimits.Z_GRASP_HEIGHT + 5.0)

        log = []
        # Step 1: Horizontal transit at clearance height
        self.safe_move(x_mm, y_mm, SafetyLimits.Z_TRANSIT_HEIGHT)
        log.append(f"Transited to target ({x_mm:.1f}, {y_mm:.1f}) at clearance height")

        # Step 2: Vertical descent to release height
        release_z = SafetyLimits.Z_GRASP_HEIGHT + 6.0
        self.safe_move(x_mm, y_mm, release_z)
        log.append(f"Descended to release height {release_z}mm")

        # Step 3: Open gripper
        rel_res = self.station.set_gripper(1.0)
        log.append("Gripper opened (object placed)")

        # Step 4: Ascend back to clearance height
        self.safe_move(x_mm, y_mm, SafetyLimits.Z_TRANSIT_HEIGHT)
        log.append(f"Ascended to clearance height {SafetyLimits.Z_TRANSIT_HEIGHT}mm")

        return {
            "success": True,
            "status": "PLACED",
            "released_object": rel_res.get("object_id"),
            "steps": log,
        }

    def execute_home(self) -> Dict[str, Any]:
        """Returns arm safely to neutral home pose."""
        return self.safe_move(0.0, 140.0, SafetyLimits.Z_TRANSIT_HEIGHT + 30.0)
