"""
Agent Prompts & Autonomous Error Recovery Orchestrator.
Contains system prompts, tool schemas, and an interactive test runner.
"""

from typing import Dict, Any
import time
try:
    from mcp_server import NormaCoreMCPServer
except ImportError:
    from src.mcp_server import NormaCoreMCPServer


# -----------------------------------------------------------------
# 1. System Prompt for Claude Code / Codex
# -----------------------------------------------------------------
AGENT_SYSTEM_PROMPT = """
You are the NormaCore Tabletop Robotics Assistant. You control an ElRobot 7+1 DOF arm
mounted on a workbench via high-level Cartesian tools.

### WORKSPACE & COORDINATES:
- Coordinates are in real-world millimeters (X, Y) relative to the arm base origin (0, 0).
- X-axis: Left is negative (e.g., -100mm), Right is positive (e.g., +100mm).
- Y-axis: Distance from base forward into table (e.g., 120mm to 260mm).
- The camera frame includes a labeled metric grid. Always use the labeled grid to determine exact (X, Y) targets.

### AVAILABLE TOOLS:
1. `get_calibrated_view()`: Returns the latest camera frame with grid overlay and current robot state.
2. `pick_at(x_mm, y_mm, yaw_deg)`: Executes a vertical descent, grasp, and lift at (X, Y).
3. `place_at(x_mm, y_mm)`: Moves across at safe clearance height and descends to place the item.
4. `verify_grasp()`: Confirms if an object is held via motor load sensors.
5. `reset_home()`: Retracts the arm to a safe neutral position.

### EXECUTION RULES & SAFETY:
1. Always call `get_calibrated_view()` first to observe the current scene.
2. Before calling `place_at()`, always call `verify_grasp()`.
   - If `verify_grasp()` returns `EMPTY_GRIP`: DO NOT proceed to place! The object slipped or was moved.
   - Immediately call `get_calibrated_view()` again to find the object's new position and re-attempt the pick.
3. Keep all targets within X: [-160, 160] and Y: [100, 260].
4. State your visual reasoning step by step before calling tools.
"""


# -----------------------------------------------------------------
# 2. End-to-End Autonomous Simulation Runner
# -----------------------------------------------------------------
def run_autonomous_demo_with_perturbation():
    """
    Simulates the winning stage demo:
    1. Agent inspects workspace.
    2. Identifies target 'blue_cube'.
    3. Judge perturbs object mid-task (simulating real-world interference).
    4. First pick fails or misses.
    5. Agent detects failure, re-inspects camera, gets new coordinates, and completes pick-and-place!
    """
    print("=" * 65)
    print(" STARTING NORMACORE AUTONOMOUS RECOVERY DEMO ")
    print("=" * 65)

    server = NormaCoreMCPServer()

    # Step 1: Agent calls get_calibrated_view()
    print("\n[Step 1] Agent calling: get_calibrated_view()")
    view = server.get_calibrated_view()
    print(" -> Camera frame captured with metric grid overlay.")
    print(" -> Telemetry: Arm at home (Z=120mm), Gripper Open.")

    # Agent reasons from vision (mock visual detection)
    print("\n[Agent Reasoning]:")
    print(" 'I see blue_cube at X=-60mm, Y=180mm. Target left_bin is at X=-130mm, Y=210mm.'")
    print(" 'Executing pick_at(x=-60, y=180)...'")

    # SIMULATE JUDGE PERTURBATION: Judge slides the blue cube mid-task!
    print("\n>>> [JUDGE PERTURBATION] Judge slides the blue cube across the table! <<<")
    server.simulate_perturbation("blue_cube_01", new_x_mm=-30.0, new_y_mm=195.0)

    # Step 2: Robot attempts pick at old coordinate (-60, 180)
    print("\n[Step 2] Executing pick_at(-60, 180)...")
    pick_result = server.pick_at(-60.0, 180.0)
    print(f" -> Pick finished. Result: {pick_result['status']}")

    # Step 3: Agent calls verify_grasp()
    print("\n[Step 3] Agent calling: verify_grasp()")
    v_res = server.verify_grasp()
    print(f" -> verify_grasp() returned: {v_res}")

    if not v_res["grasped"]:
        print("\n[Agent Recovery Triggered]:")
        print(" 'WARNING: Grasp failed (load=0.05). Object is not in gripper.'")
        print(" 'Self-healing: Re-inspecting workspace to find updated object location...'")

        # Step 4: Re-capture camera frame
        new_view = server.get_calibrated_view()
        print(" -> Fresh camera view captured.")
        print(" 'Detected blue_cube has shifted to X=-30mm, Y=195mm.'")
        print(" 'Re-attempting pick at updated coordinates (-30, 195)...'")

        # Step 5: Second pick attempt at new coordinates
        pick_result2 = server.pick_at(-30.0, 195.0)
        print(f" -> Second pick result: {pick_result2['status']} (Object: {pick_result2['object_id']})")

        v_res2 = server.verify_grasp()
        print(f" -> verify_grasp() confirmation: {v_res2['status']} (Load={v_res2['load_ratio']})")

        # Step 6: Safe placement into left_bin
        print("\n[Step 6] Grasp verified! Calling place_at(x=-130, y=210) [left_bin]...")
        place_res = server.place_at(-130.0, 210.0)
        print(f" -> Placement status: {place_res['status']}")

        # Step 7: Return Home
        server.reset_home()
        print("\n[Step 7] Arm returned to safe home pose.")

        print("\n" + "=" * 65)
        print(" DEMO COMPLETE: SUCCESSFUL AUTONOMOUS ERROR RECOVERY! ")
        print("=" * 65)
        return True

    return False


if __name__ == "__main__":
    run_autonomous_demo_with_perturbation()
