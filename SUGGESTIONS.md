### Post-Implementation Suggestions

1. Verify local Python dependencies and run the offline test suite — Priority 92% (Critical) [Best practices]
   What: Run `pip install -r requirements.txt` and execute `pytest tests/test_pipeline.py` on your machine.
   Why: Ensures your Python environment (especially NumPy and OpenCV/Pillow) is 100% verified and all 5 unit/integration tests pass before traveling.
   How: Run `pip install -r requirements.txt && pytest tests/test_pipeline.py -v`.
   Status: ⏳ Unimplemented
   Reason Deferred: Verification step for user's terminal environment before traveling.

3. Verify `.mcp.json` tool discovery in Claude Code or Cursor — Priority 88% (High value) [Best practices]
   What: Open this repository in Claude Code or Cursor and confirm that the `normacore-robot` MCP server is detected and tools are available.
   Why: Auto-registering tools means your AI agent can call `get_calibrated_view`, `pick_at`, and `verify_grasp` directly without manual command-line flags.
   How: Run `claude mcp list` or inspect Cursor Settings -> MCP Servers.
   Status: ⏳ Unimplemented
   Reason Deferred: Requires testing within user's specific editor/agent UI.

4. Pack essential hardware accessories: USB-A/C adapters, powered hub, and masking tape — Priority 82% (High value) [Professionalism]
   What: Put a USB-C to USB-A adapter, a 2m USB extension cable, and a small roll of masking tape into your hackathon backpack.
   Why: In live robotics hackathons, desk outlets and laptop port arrangements are unpredictable. Masking tape is invaluable for taping down AprilTags and marking bin boundaries.
   How: Pack these physical items in your travel bag tonight.
   Status: ⏳ Unimplemented
   Reason Deferred: Physical packing task before departure for Berlin.

5. Pre-download Python wheels and Protobuf packages offline — Priority 78% (High value) [Reliability]
   What: Download cached pip wheels for your environment (`pip download -r requirements.txt -d ./pip_cache`) so you can reinstall without internet.
   Why: If venue internet drops or restricts PyPI access on Saturday, you can install any missing package locally from cache.
   How: Run `pip download -r requirements.txt -d ./pip_cache`.
   Status: ⏳ Unimplemented
   Reason Deferred: Preventive measure to run before leaving home Wi-Fi.

6. Bookmark NormaCore Station Web console default URL and offline docs — Priority 70% (Nice to have) [Professionalism]
   What: Bookmark `http://localhost:8889` (the Station web console default, per `docs/NormaCore_Repositories_and_Tooling.md`) and save the Station README as an offline PDF.
   Why: Gives you instant access to manual motor calibration controls and joint sliders during the first 30 minutes of hardware bring-up.
   How: Save the Station docs locally in `docs/`.
   Status: ⏳ Unimplemented
   Reason Deferred: Optional convenience step ahead of kickoff.

7. Verify the URDF-to-motor mapping before any Cartesian move — Priority 92% (Critical) [Best practices]
   What: Confirm which ST3215 motor ID drives which URDF joint (`rev_motor_01` to `rev_motor_08`) and in which direction, using the Station web console on the real arm.
   Why: Cartesian tools (`pick_at`, `place_at`) need correct joint kinematics. A wrong mapping would move the arm in the wrong direction on the first try.
   How: With the arm on the table, jog one motor at a time at slow speed from the Station console, note the direction, and write the table into `docs/elrobot_hardware_bridge.md`.
   Status: ⏳ Unimplemented
   Reason Deferred: Needs the physical arm, USB connected and powered, on Saturday.

8. Add a current-overload guard to joint moves — Priority 85% (High value) [Security]
   What: Stop a motor from pushing on when it draws too much current, for example when it is blocked by an object or the table.
   Why: A stalled servo can strain its gears or the 3D-printed parts. The teleop example already does this, so the hackathon bridge should too.
   How: Read `RAM_PRESENT_CURRENT` before each move in `move_motors` and refuse or hold the goal above a per-motor threshold, using the teleop example's `config.py` values as a starting point.
   Status: ⏳ Unimplemented
   Reason Deferred: Thresholds must be set from measurements on the real arm; guessing now risks blocking good moves.

9. Fix the table size mismatch — Priority 60% (Nice to have) [Professionalism]
   What: The mock uses a 400 x 300 mm table, the MCP server reports a Y range of 90 to 270 mm, and the ElRobot README gives a reach of 430 mm. Pick one set of workspace numbers and use it everywhere.
   Why: Mismatched limits can make the agent plan targets the real arm cannot reach, or reject ones it can.
   How: Measure the real workspace after the arm is mounted, then update the constants in `src/mock_station.py`, `src/mcp_server.py` and `src/kinematics_safety.py`.
   Status: ⏳ Unimplemented
   Reason Deferred: Depends on the physical table layout measured on site.

10. Ignore Station runtime files in git — Priority 45% (Nice to have) [Professionalism]
    What: The Station creates `station.yaml` and `station_data/` in the project root when it runs. Add them to `.gitignore` so they never get committed by accident.
    Why: Runtime data such as camera recordings can grow large and may include private footage.
    How: Add `station_data/` and `station.yaml` to `.gitignore`, then confirm with `git status`.
    Status: ⏳ Unimplemented
    Reason Deferred: Those files exist now but were not deleted, because the delete was denied this session. Adding the ignore rule is quick once the user confirms they can be removed.

11. Run the test suite on every push with a CI workflow — Priority 50% (Nice to have) [Best practices]
    What: A small GitHub Actions job that installs `requirements.txt` and runs `pytest` on each push.
    Why: Catches broken safety helpers before they reach the lab laptop on Saturday.
    How: Add `.github/workflows/tests.yml` with checkout, Python 3.11 setup, `pip install -r requirements.txt`, and `pytest tests/`.
    Status: ⏳ Unimplemented
    Reason Deferred: Repo has no remote set up for hackathon work yet, and the job would also need the NormaCore SDK checkout.

12. Teach-and-replay joint waypoints for the demo — Priority 88% (High value) [Best practices]
    What: Record a handful of named arm poses (home, above cube, grasp, bin A, bin B) as 8 joint targets each, then replay them by name.
    Why: The Station has no Cartesian control and IK is unverified on the real arm. Named joint poses avoid that gap, are easy to debug, and are enough for a sorting demo.
    How: Add a `./cli.sh hw teach <name>` command that saves the current motor positions to `docs/waypoints.json`, and a `hw goto <name>` command that moves there through the same clamped `jog`-style path, with the MOVE confirmation.
    Status: ⏳ Unimplemented
    Reason Deferred: Needs the joint mapping (checklist step 5) and a working first move (step 6) on the real arm first.

13. Rotate and prune old run logs — Priority 40% (Optional) [Professionalism]
    What: Delete hardware logs older than a set number of days, so `logs/` does not grow forever.
    Why: Every run writes a new file, and at DEBUG level each file can be several KB. This matters only over many sessions.
    How: In `src/elrobot_log.py`, keep the newest 50 files per tool name and delete the rest when a new run starts.
    Status: ⏳ Unimplemented
    Reason Deferred: Low value for hardware day; logs are small and the bundle command only reads the most recent files.
