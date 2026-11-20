"""
Mock NormaCore Station Runtime & Hardware Simulator.
Allows offline testing of the complete Claude/Codex MCP tool loop before arriving in Berlin.
"""

import math
import time
from typing import Dict, Any, Optional, Tuple, List
from PIL import Image, ImageDraw, ImageFont


class MockStation:
    """
    Simulates the NormaCore Station server, ElRobot 7+1 DOF arm,
    and overhead camera stream.
    """

    def __init__(self, table_width_mm: float = 400.0, table_height_mm: float = 300.0):
        self.table_width_mm = table_width_mm
        self.table_height_mm = table_height_mm

        # Arm end-effector pose (X, Y, Z in mm, Roll, Pitch, Yaw in degrees)
        self.arm_pose = {
            "x": 0.0,
            "y": 140.0,
            "z": 120.0,  # Home height
            "roll": 0.0,
            "pitch": 90.0,  # Pointing straight down
            "yaw": 0.0,
        }
        self.gripper_state = 1.0  # 1.0 = fully open, 0.0 = fully closed
        self.gripper_load = 0.0   # 0.0 = no load, 0.8+ = gripping resistance

        # Held object ID
        self.held_object: Optional[str] = None

        # Tabletop objects: ID -> {name, x, y, z, width, height, color}
        self.objects: Dict[str, Dict[str, Any]] = {
            "blue_cube_01": {
                "name": "blue_cube",
                "x": -60.0,
                "y": 180.0,
                "z": 15.0,
                "radius": 15.0,
                "color": (40, 120, 240),
            },
            "green_tool_01": {
                "name": "green_tool",
                "x": 70.0,
                "y": 210.0,
                "z": 12.0,
                "radius": 18.0,
                "color": (40, 200, 80),
            },
            "red_cylinder_01": {
                "name": "red_cylinder",
                "x": 10.0,
                "y": 150.0,
                "z": 20.0,
                "radius": 14.0,
                "color": (230, 50, 50),
            },
        }

        # Target zones / bins
        self.target_zones: Dict[str, Dict[str, Any]] = {
            "left_bin": {"x": -130.0, "y": 210.0, "radius": 35.0, "color": (180, 210, 255)},
            "right_bin": {"x": 130.0, "y": 210.0, "radius": 35.0, "color": (210, 255, 200)},
        }

        # Corner fiducial markers (AprilTags / ArUco) in mm coordinates
        self.fiducial_markers = {
            0: (-160.0, 260.0),  # Top-Left
            1: (160.0, 260.0),   # Top-Right
            2: (160.0, 110.0),   # Bottom-Right
            3: (-160.0, 110.0),  # Bottom-Left
        }

        # Camera frame settings
        self.img_w = 640
        self.img_h = 480

    def mm_to_pixel(self, x_mm: float, y_mm: float) -> Tuple[int, int]:
        """Convert tabletop mm (origin at arm base) to camera pixel coordinates."""
        # Mapping: X in [-200, 200] -> [40, 600]
        #          Y in [80, 280]   -> [440, 40] (camera top is high Y)
        px = int(320 + (x_mm / 200.0) * 280)
        py = int(440 - ((y_mm - 80.0) / 200.0) * 400)
        return max(0, min(self.img_w - 1, px)), max(0, min(self.img_h - 1, py))

    def pixel_to_mm(self, px: int, py: int) -> Tuple[float, float]:
        """Inverse mapping from pixels to mm."""
        x_mm = ((px - 320) / 280.0) * 200.0
        y_mm = 80.0 + ((440 - py) / 400.0) * 200.0
        return round(x_mm, 1), round(y_mm, 1)

    def get_arm_telemetry(self) -> Dict[str, Any]:
        """Returns joint telemetry and end-effector pose."""
        return {
            "end_effector": dict(self.arm_pose),
            "gripper_state": self.gripper_state,
            "gripper_load": self.gripper_load,
            "held_object": self.held_object,
            "connected": True,
            "timestamp": time.time(),
        }

    def move_end_effector(
        self, x: float, y: float, z: float, roll: float = 0.0, pitch: float = 90.0, yaw: float = 0.0
    ) -> Dict[str, Any]:
        """Move arm end-effector to target cartesian coordinates."""
        # Enforce virtual floor safety clamp
        if z < 10.0:
            raise ValueError(f"Safety Violation: Z={z}mm is below table floor limit (10.0mm)")

        self.arm_pose["x"] = float(x)
        self.arm_pose["y"] = float(y)
        self.arm_pose["z"] = float(z)
        self.arm_pose["roll"] = float(roll)
        self.arm_pose["pitch"] = float(pitch)
        self.arm_pose["yaw"] = float(yaw)

        # If holding an object, update its position
        if self.held_object and self.held_object in self.objects:
            self.objects[self.held_object]["x"] = float(x)
            self.objects[self.held_object]["y"] = float(y)
            self.objects[self.held_object]["z"] = float(z)

        return {"status": "SUCCESS", "pose": dict(self.arm_pose)}

    def set_gripper(self, state: float) -> Dict[str, Any]:
        """
        Actuate gripper.
        state = 1.0 (open) to 0.0 (closed).
        """
        state = max(0.0, min(1.0, float(state)))
        self.gripper_state = state

        if state < 0.3:  # Closing gripper
            # Check if close to an object at grasp height
            grasped = None
            for obj_id, obj in self.objects.items():
                dist_xy = math.hypot(self.arm_pose["x"] - obj["x"], self.arm_pose["y"] - obj["y"])
                dist_z = abs(self.arm_pose["z"] - obj["z"])
                if dist_xy < 25.0 and dist_z < 15.0:
                    grasped = obj_id
                    break

            if grasped:
                self.held_object = grasped
                self.gripper_load = 0.85  # Motor resistance detected
                return {"status": "GRASPED", "object_id": grasped, "load": self.gripper_load}
            else:
                self.held_object = None
                self.gripper_load = 0.05  # Closed on empty air
                return {"status": "EMPTY_GRASP", "object_id": None, "load": self.gripper_load}
        else:  # Opening gripper
            released = self.held_object
            self.held_object = None
            self.gripper_load = 0.0
            if released and released in self.objects:
                # Place object on table surface
                self.objects[released]["z"] = 12.0
            return {"status": "RELEASED", "object_id": released, "load": 0.0}

    def simulate_judge_perturbation(self, obj_id: str, new_x: float, new_y: float):
        """Simulate a judge or human moving an object across the table."""
        if obj_id in self.objects:
            self.objects[obj_id]["x"] = new_x
            self.objects[obj_id]["y"] = new_y
            print(f"[PERTURBATION] Object '{obj_id}' shifted to ({new_x:.1f}, {new_y:.1f})mm")

    def capture_frame(self) -> Image.Image:
        """Render a synthetic overhead workspace camera view with objects and markers."""
        img = Image.new("RGB", (self.img_w, self.img_h), color=(240, 238, 230))
        draw = ImageDraw.Draw(img)

        # Draw Tabletop Border
        draw.rectangle([20, 20, self.img_w - 20, self.img_h - 20], outline=(180, 175, 160), width=3)

        # Draw 4 Corner AprilTags / Fiducials
        for tag_id, (tx, ty) in self.fiducial_markers.items():
            px, py = self.mm_to_pixel(tx, ty)
            r = 18
            draw.rectangle([px - r, py - r, px + r, py + r], fill=(20, 20, 20), outline=(255, 255, 255), width=2)
            draw.text((px - 5, py - 6), str(tag_id), fill=(255, 255, 255))

        # Draw Target Bins
        for bin_id, bdata in self.target_zones.items():
            bx, by = self.mm_to_pixel(bdata["x"], bdata["y"])
            br = int(bdata["radius"] * 1.4)
            draw.rounded_rectangle([bx - br, by - br, bx + br, by + br], radius=8, fill=bdata["color"], outline=(100, 100, 100))
            draw.text((bx - 24, by - 6), bin_id, fill=(40, 40, 40))

        # Draw Objects
        for obj_id, obj in self.objects.items():
            ox, oy = self.mm_to_pixel(obj["x"], obj["y"])
            rad = int(obj["radius"])
            # Shadow
            draw.ellipse([ox - rad + 3, oy - rad + 3, ox + rad + 3, oy + rad + 3], fill=(190, 185, 175))
            # Object Body
            draw.ellipse([ox - rad, oy - rad, ox + rad, oy + rad], fill=obj["color"], outline=(30, 30, 30), width=2)
            # Label
            draw.text((ox - 18, oy - 22), obj["name"], fill=(20, 20, 20))

        # Draw Arm End-Effector Position / Crosshair
        eex, eey = self.mm_to_pixel(self.arm_pose["x"], self.arm_pose["y"])
        # Gripper visual
        draw.line([eex - 12, eey, eex + 12, eey], fill=(255, 60, 60), width=3)
        draw.line([eex, eey - 12, eex, eey + 12], fill=(255, 60, 60), width=3)
        draw.ellipse([eex - 6, eey - 6, eex + 6, eey + 6], outline=(255, 60, 60), width=2)

        return img
