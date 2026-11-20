"""
Unit and Integration Tests for NormaCore Tabletop Manipulation Pipeline.
"""

import pytest
import numpy as np
from src.mock_station import MockStation
from src.vision_homography import TabletopCalibrator
from src.kinematics_safety import KinematicsSafetyEngine, SafetyLimits
from src.mcp_server import NormaCoreMCPServer


def test_mock_station_initialization():
    station = MockStation()
    telem = station.get_arm_telemetry()
    assert telem["connected"] is True
    assert telem["end_effector"]["z"] == 120.0
    assert len(station.objects) == 3


def test_homography_calibration_accuracy():
    station = MockStation()
    calibrator = TabletopCalibrator()

    mock_tag_pixels = {
        0: station.mm_to_pixel(-160.0, 260.0),
        1: station.mm_to_pixel(160.0, 260.0),
        2: station.mm_to_pixel(160.0, 110.0),
        3: station.mm_to_pixel(-160.0, 110.0),
    }
    calibrator.compute_homography(mock_tag_pixels)

    # Test mapping back and forth for multiple tabletop positions
    for test_x, test_y in [(-100.0, 200.0), (0.0, 150.0), (80.0, 220.0)]:
        px, py = calibrator.mm_to_pixel(test_x, test_y)
        calc_x, calc_y = calibrator.pixel_to_mm(px, py)
        assert abs(calc_x - test_x) <= 1.5, f"X mismatch: {calc_x} vs {test_x}"
        assert abs(calc_y - test_y) <= 1.5, f"Y mismatch: {calc_y} vs {test_y}"


def test_kinematics_safety_clamps():
    station = MockStation()
    engine = KinematicsSafetyEngine(station)

    # Valid coordinate should succeed
    cx, cy, cz = engine.validate_cartesian_target(50.0, 150.0, 40.0)
    assert cz == 40.0

    # Table floor violation (Z < 12mm) must raise ValueError
    with pytest.raises(ValueError, match="violates table floor limit"):
        engine.validate_cartesian_target(0.0, 150.0, 5.0)

    # X bounds violation must raise ValueError
    with pytest.raises(ValueError, match="out of workspace bounds"):
        engine.validate_cartesian_target(250.0, 150.0, 40.0)


def test_mcp_server_pick_and_place():
    server = NormaCoreMCPServer()

    # Initial state
    view = server.get_calibrated_view()
    assert "image_base64" in view
    assert view["telemetry"]["held_object"] is None

    # Pick blue cube at (-60, 180)
    pick_res = server.pick_at(-60.0, 180.0)
    assert pick_res["status"] == "GRASPED"
    assert pick_res["object_id"] == "blue_cube_01"

    # Verify grasp confirms item held
    v_res = server.verify_grasp()
    assert v_res["grasped"] is True
    assert v_res["held_object"] == "blue_cube_01"

    # Place in left bin at (-130, 210)
    place_res = server.place_at(-130.0, 210.0)
    assert place_res["status"] == "PLACED"

    # Verify grasp confirms empty gripper
    v_res2 = server.verify_grasp()
    assert v_res2["grasped"] is False


def test_closed_loop_recovery_on_perturbation():
    server = NormaCoreMCPServer()

    # Simulate judge sliding the cube from (-60, 180) to (20, 200)
    server.simulate_perturbation("blue_cube_01", new_x_mm=20.0, new_y_mm=200.0)

    # Robot attempts pick at old location (-60, 180)
    pick_res = server.pick_at(-60.0, 180.0)
    assert pick_res["status"] == "EMPTY_GRASP"

    v_res = server.verify_grasp()
    assert v_res["grasped"] is False  # Correctly detected that grasp failed!

    # Robot attempts pick at new location (20, 200)
    pick_res2 = server.pick_at(20.0, 200.0)
    assert pick_res2["status"] == "GRASPED"
    assert pick_res2["object_id"] == "blue_cube_01"


if __name__ == "__main__":
    pytest.main(["-v", "tests/test_pipeline.py"])
