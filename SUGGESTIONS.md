### Post-Implementation Suggestions

1. Verify local Python dependencies and run the offline test suite — Priority 92% (Critical) [Best practices]
   What: Run `pip install -r requirements.txt` and execute `pytest tests/test_pipeline.py` on your machine.
   Why: Ensures your Python environment (especially NumPy and OpenCV/Pillow) is 100% verified and all 5 unit/integration tests pass before traveling.
   How: Run `pip install -r requirements.txt && pytest tests/test_pipeline.py -v`.
   Status: ⏳ Unimplemented
   Reason Deferred: Verification step for user's terminal environment before traveling.

2. Verify `.mcp.json` tool discovery in Claude Code or Cursor — Priority 88% (High value) [Best practices]
   What: Open this repository in Claude Code or Cursor and confirm that the `normacore-robot` MCP server is detected and tools are available.
   Why: Auto-registering tools means your AI agent can call `get_calibrated_view`, `pick_at`, and `verify_grasp` directly without manual command-line flags.
   How: Run `claude mcp list` or inspect Cursor Settings -> MCP Servers.
   Status: ⏳ Unimplemented
   Reason Deferred: Requires testing within user's specific editor/agent UI.

3. Pack essential hardware accessories: USB-A/C adapters, powered hub, and masking tape — Priority 82% (High value) [Professionalism]
   What: Put a USB-C to USB-A adapter, a 2m USB extension cable, and a small roll of masking tape into your hackathon backpack.
   Why: In live robotics hackathons, desk outlets and laptop port arrangements are unpredictable. Masking tape is invaluable for taping down AprilTags and marking bin boundaries.
   How: Pack these physical items in your travel bag tonight.
   Status: ⏳ Unimplemented
   Reason Deferred: Physical packing task before departure for Berlin.

4. Pre-download Python wheels and Protobuf packages offline — Priority 78% (High value) [Reliability]
   What: Download cached pip wheels for your environment (`pip download -r requirements.txt -d ./pip_cache`) so you can reinstall without internet.
   Why: If venue internet drops or restricts PyPI access on Saturday, you can install any missing package locally from cache.
   How: Run `pip download -r requirements.txt -d ./pip_cache`.
   Status: ⏳ Unimplemented
   Reason Deferred: Preventive measure to run before leaving home Wi-Fi.

5. Bookmark NormaCore Station Web console default URL and offline docs — Priority 70% (Nice to have) [Professionalism]
   What: Bookmark `http://localhost:8889` (the Station web console default, per `docs/NormaCore_Repositories_and_Tooling.md`) and save the Station README as an offline PDF.
   Why: Gives you instant access to manual motor calibration controls and joint sliders during the first 30 minutes of hardware bring-up.
   How: Save the Station docs locally in `docs/`.
   Status: ⏳ Unimplemented
   Reason Deferred: Optional convenience step ahead of kickoff.

6. Verify the URDF-to-motor mapping before any Cartesian move — Priority 92% (Critical) [Best practices]
   What: Confirm which ST3215 motor ID drives which URDF joint (`rev_motor_01` to `rev_motor_08`) and in which direction, using the Station web console on the real arm.
   Why: Cartesian tools (`pick_at`, `place_at`) need correct joint kinematics. A wrong mapping would move the arm in the wrong direction on the first try.
   How: With the arm on the table, jog one motor at a time at slow speed from the Station console, note the direction, and write the table into `docs/elrobot_hardware_bridge.md`.
   Status: ⏳ Partly done (tool exists, arm check pending)
   Reason Deferred: `./cli.sh hw identify` now records the mapping, but the result still needs checking on the physical arm.

7. Measure the table and set workspace limits — Priority 60% (Nice to have) [Professionalism]
   What: Measure the real table, then set the limits in `config/elrobot.json`. The limits are now read from one file (the old hardcoded values are gone).
   Why: Mismatched limits can make the agent plan targets the real arm cannot reach, or reject ones it can.
   How: Follow "Step 11" in `docs/elrobot_hardware_bridge.md`, then run `./cli.sh hw workspace`.
   Status: ⏳ Unimplemented
   Reason Deferred: Needs a tape measure on site. Config and tooling are in place.

8. Run the test suite on every push with a CI workflow — Priority 50% (Nice to have) [Best practices]
    What: A small GitHub Actions job that installs `requirements.txt` and runs `pytest` on each push.
    Why: Catches broken safety helpers before they reach the lab laptop on Saturday.
    How: Add `.github/workflows/tests.yml` with checkout, Python 3.11 setup, `pip install -r requirements.txt`, and `pytest tests/`.
    Status: ⏳ Unimplemented
    Reason Deferred: Repo has no remote set up for hackathon work yet, and the job would also need the NormaCore SDK checkout.

9. Rotate and prune old run logs — Priority 40% (Optional) [Professionalism]
    What: Delete hardware logs older than a set number of days, so `logs/` does not grow forever.
    Why: Every run writes a new file, and at DEBUG level each file can be several KB. This matters only over many sessions.
    How: In `src/elrobot_log.py`, keep the newest 50 files per tool name and delete the rest when a new run starts.
    Status: ⏳ Unimplemented
    Reason Deferred: Low value for hardware day; logs are small and the bundle command only reads the most recent files.

10. Measure the workspace using the arm's own taught poses — Priority 75% (High value) [Best practices]
    What: Teach the arm to each table corner and read the joint positions, instead of relying only on a tape measure.
    Why: Joint readings at the corners show the arm's reach directly, so the workspace limits match what the arm can actually do.
    How: With torque off, move the gripper to each corner and run `./cli.sh hw teach corner_1` through `corner_4`. Then compare the taught poses with the measured limits in `config/elrobot.json`.
    Status: ⏳ Unimplemented
    Reason Deferred: Needs the physical arm, and the tape measure check (item 9) is the simpler first step.

11. Record and replay named sequences — Priority 55% (Nice to have) [Best practices]
    What: Chain several waypoints into one named routine, such as "pick then place", and run it with one command.
    Why: The sorting demo will repeat the same route many times. One command is less error-prone than typing each goto.
    How: Store a list of waypoint names under `config/sequences.json`, and add `./cli.sh hw run-seq <name>` that calls goto for each step and stops on the first failure.
    Status: ⏳ Unimplemented
    Reason Deferred: Build it after single gotos work on the arm.

12. Handle encoder wrap-around in the overload detector — Priority 45% (Optional) [Best practices]
    What: The overload check compares motor positions, so it can misread movement when a joint crosses the encoder's zero point (0 and 4095).
    Why: Crossing zero is rare in the current workspace, but a missed stall there could strain a motor.
    How: In `OverloadDetector.update`, measure movement as the shorter distance around the 0–4095 circle.
    Status: ⏳ Unimplemented
    Reason Deferred: No joint crosses zero in the planned workspace. Fix it if a range changes.
