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


def test_digital_twin_html_exists():
    import os
    html_path = os.path.join(os.path.dirname(__file__), "..", "src", "digital_twin.html")
    assert os.path.exists(html_path)
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "select-cam-table" in content
    assert "select-cam-person" in content
    assert "NormaCore AI Control Dashboard" in content
    assert "feed_grapes" in content
    assert "feed_spoon" in content


def test_camera_feeding_vision_and_orchestration():
    import cv2
    from src.feeding_vision import FeedingVisionDetector, run_camera_feeding_cycle

    # Build a synthetic camera frame with a purple grape bowl, green spoon, and skin-toned face/mouth region
    frame = np.full((480, 640, 3), (230, 235, 240), dtype=np.uint8)
    cv2.circle(frame, (220, 260), 25, (180, 50, 160), -1)   # Purple grape cluster in bowl
    cv2.circle(frame, (420, 190), 20, (50, 200, 60), -1)    # Green spoon holder
    cv2.ellipse(frame, (320, 100), (40, 50), 0, 0, 360, (140, 175, 225), -1)  # Person face/mouth region

    detector = FeedingVisionDetector()
    summary, annotated = detector.analyze_and_annotate(frame)
    assert annotated.shape == frame.shape
    assert summary["grape_bowl"] is not None
    assert summary["spoon"] is not None
    assert summary["mouth"] is not None
    assert summary["mouth"]["extra"]["standoff_cm"] >= 5.0

    # Run full feeding cycles (grapes and spoon) with NormaCoreMCPServer
    server = NormaCoreMCPServer()
    res_grapes = run_camera_feeding_cycle(mode="grapes", mcp_server=server, preferred_camera=99)
    assert res_grapes["status"] == "FEEDING_CYCLE_COMPLETED"
    assert res_grapes["mode"] == "grapes"
    assert res_grapes["cartesian"]["standoff_pose"]["z"] == 110.0

    res_spoon = run_camera_feeding_cycle(mode="spoon", mcp_server=server, preferred_camera=99)
    assert res_spoon["status"] == "FEEDING_CYCLE_COMPLETED"
    assert res_spoon["mode"] == "spoon"
    assert res_spoon["cartesian"]["standoff_pose"]["z"] == 110.0


def test_mouth_state_tracker_and_feeding_safety_fsm():
    from src.feeding_vision import FeedingSafetyFSM, MouthStateTracker

    # 1. MAR calculation
    mar_closed = MouthStateTracker.compute_mar((100, 100), (100, 104), (80, 102), (120, 102))
    mar_open = MouthStateTracker.compute_mar((100, 92), (100, 112), (80, 102), (120, 102))
    assert mar_closed < 0.2
    assert mar_open >= 0.45

    # 2. EMA smoothing + 3-frame mouth-open debounce + watchdog
    tracker = MouthStateTracker(alpha=0.5, mar_threshold=0.25, debounce_frames=3, watchdog_timeout_s=0.5)
    r1 = tracker.update(320, 200, 60, mar_open, now=10.0)
    assert r1["mouth_open"] is True and r1["mouth_open_confirmed"] is False
    r2 = tracker.update(322, 200, 60, mar_open, now=10.1)
    assert r2["mouth_open_confirmed"] is False
    r3 = tracker.update(320, 200, 60, mar_open, now=10.2)
    assert r3["mouth_open_confirmed"] is True and r3["open_streak"] == 3
    assert tracker.check_watchdog(now=10.4) is False
    assert tracker.check_watchdog(now=10.8) is True
    assert tracker.open_streak == 0

    # 3. FeedingSafetyFSM happy path & emergency hold overrides
    fsm = FeedingSafetyFSM()
    assert fsm.state == "IDLE"
    assert fsm.step(face_detected=True, holding_object=True) == "APPROACH"
    assert fsm.step(face_detected=True, at_standoff=True, holding_object=True) == "HOLD_STANDOFF"
    assert fsm.step(face_detected=True, at_standoff=True, holding_object=True) == "WAIT_MOUTH_OPEN"
    assert fsm.step(face_detected=True, mouth_open_confirmed=False, holding_object=True) == "WAIT_MOUTH_OPEN"
    assert fsm.step(face_detected=True, mouth_open_confirmed=True, holding_object=True) == "RELEASE"
    assert fsm.step(face_detected=True, holding_object=True) == "RETRACT"
    assert fsm.step(face_detected=True, holding_object=False) == "IDLE"

    # Face lost during approach -> EMERGENCY_HOLD
    fsm.step(face_detected=True, holding_object=True)
    assert fsm.step(face_detected=False, face_lost=True, holding_object=True) == "EMERGENCY_HOLD"
    assert fsm.reason == "face_lost_watchdog"

    # Explicit stop -> EMERGENCY_HOLD
    fsm.reset()
    assert fsm.step(face_detected=True, stop_requested=True) == "EMERGENCY_HOLD"
    assert fsm.reason == "stop_requested"

    # 4. User calibration updates live thresholds cleanly
    from src.feeding_vision import FeedingVisionDetector
    det = FeedingVisionDetector()
    cal = det.set_calibration(mar_open_threshold=0.22, standoff_mouth_width_px=80)
    assert cal["mar_open_threshold"] == 0.22
    assert cal["standoff_mouth_width_px"] == 80
    assert det.mouth_tracker.mar_threshold == 0.22
    assert det.standoff_mouth_width_px == 80


if __name__ == "__main__":
    pytest.main(["-v", "tests/test_pipeline.py"])
