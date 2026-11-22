### Post-Implementation Suggestions

1. Enforce the hover skill's limits in a hook, not only in text — Priority 86% (High value) [Security]
   What: A Claude Code PreToolUse hook that blocks `calib goto ... --yes` unless the z is >= 66 mm and HANDOFF.md names the session's user as hardware owner.
   Why: The skill lets the agent move the arm without asking. A hook makes that rule hard to break by accident, for example a typo in z or a session run by someone else.
   How: Add a small script in `.claude/hooks/` that reads the Bash command from stdin, parses the z after `calib goto`, and exits 2 with a message if it is too low; register it in `.claude/settings.json` under `PreToolUse` for `Bash`.
   Status: ⏳ Unimplemented
   Reason Deferred: Skill just created; first wanted Jafer to see it in use.

2. Centre the object with the gripper camera before any descent — Priority 72% (High value) [Best practices]
   What: After hovering, look through the gripper camera and correct x/y by a few mm until the object is in the middle of the picture.
   Why: The table-camera calibration is ~3 cm off (the hover above the grape ended visibly to its right). The gripper camera sees the object up close, so it can remove most of that error before grasping.
   How: Note which pixel in the gripper camera is right between the fingers, then after each hover compare the grape's pixel with it and send a small `calib goto` correction (z unchanged), at most 3 times.
   Status: ⏳ Unimplemented
   Reason Deferred: Needs the hover step proven first and a gripper-camera pixel-to-mm scale.

3. Offer the hover procedure as an MCP tool for the voice agent — Priority 55% (Nice to have) [Professionalism]
   What: A `hover_above(u, v, camera)` tool in the elrobot MCP server that runs pixel -> reach -> goto with the same checks.
   Why: The console's voice agent cannot run shell commands, so today only a Claude Code session can do this move; one tool keeps both on the same safe code path.
   How: Wrap the functions behind `calib pixel` and `calib goto` from `scripts/calib.py` in `src/robot_tools.py`, keep the 66 mm floor and dry-run flag, and add an offline test with a fake Station.
   Status: ⏳ Unimplemented
   Reason Deferred: Out of the current plan step (bench calibration first).

1. Log every `calib goto` with its plan and result — Priority 80% (High value) [Security]
   What: Write each goto's target, planned legs, motor goals and final status to `logs/` (as `hw` commands already do).
   Why: If the arm hits something, the log shows exactly what was commanded and where it stopped, which is the first thing anyone needs after an incident.
   How: Call `setup_logging("calib", ...)` from `src/elrobot_log.py` in `scripts/calib.py` and log the plan before the MOVE prompt and the status after each leg.
   Status: ⏳ Unimplemented
   Reason Deferred: The first live goto had not run yet.

2. Compare the fingertip with the camera after each goto — Priority 60% (Nice to have) [Best practices]
   What: After arriving, take a table-camera frame and save it with the target drawn on it.
   Why: The joint readings only say where the arm thinks it is; the camera shows where it really is, which is the honest check of the calibration.
   How: Reuse `_grab_frame` and `TableCamera.table_to_pixel` to draw the target point into a picture in `data/calibration/`, and print its path.
   Status: ⏳ Unimplemented
   Reason Deferred: Needs the calibration below ~10 mm to be meaningful.

3. Return to `clear` with one command after a test — Priority 45% (Nice to have) [Professionalism]
   What: `calib goto ... --then clear` (or a short doc line) to lift and go back to the taught `clear` pose after the test.
   Why: Leaving the arm stretched out over the table is where people bump into it; a standard retreat keeps tests tidy.
   How: After the last leg, run the same lift leg, then call the existing waypoint goto for `clear`.
   Status: ⏳ Unimplemented
   Reason Deferred: `clear` is outside motor 2's current range; recalibrate motor 2 first.

1. Refuse a Cartesian move when the fit error is above 10 mm — Priority 92% (Critical) [Security]
   What: The future move command reads `base_in_table.rms_mm` from `config/calibration.json` and refuses to move when it is above 10 mm.
   Why: A fit of 19-21 mm (what we have now) means the fingertip can land 2 cm off, for example on the table or near a person's face. A hard check stops that before the arm moves.
   How: In the command that will drive the arm to `calib reach` targets, load the calibration, compare `rms_mm` with a limit in `config/elrobot.json`, and exit with a clear message when it is too high. Add an offline test for both cases.
   Status: ⏳ Unimplemented
   Reason Deferred: The move command does not exist yet; it needs the hardware owner's review.

2. Warn when a `calib reach` goal is close to a motor's range end — Priority 70% (High value) [Best practices]
   What: Mark any motor whose goal lies within about 50 steps of its range end (today motor 6 goes to 1199 with a limit of 1202).
   Why: Driving a servo into its end stop strains the gear and can stall the motor; a warning lets the operator pick another target or approach angle.
   How: In `cmd_reach` in `scripts/calib.py`, compute the distance to each range end with `step_delta` and print `NEAR LIMIT`. Add a test for a wrapping range.
   Status: ⏳ Unimplemented
   Reason Deferred: Out of scope for the wraparound fix.

3. Show the touch points and their errors on the camera overlay — Priority 50% (Nice to have) [Professionalism]
   What: `calib show` draws where each touch landed according to the fit next to the tag it should have hit.
   Why: Seeing which touches are off, and in which direction, makes a bad fit (wrong width, bad zero) much faster to diagnose than a list of numbers.
   How: Map each touch's fitted fingertip to a pixel with `TableCamera.table_to_pixel` and draw a line from it to its tag centre in `draw_overlay`.
   Status: ⏳ Unimplemented
   Reason Deferred: Diagnosis aid only; the fit is still being measured.

1. Test that `look()` never changes the picture — Priority 75% (High value) [Best practices]
   What: Add a small offline test that feeds a known JPEG through `RobotTools.look()` and checks that the same bytes come back.
   Why: The picture clean-up was added and then removed. A test makes sure no future change quietly starts altering what Claude sees, which would also change what the AprilTag calibration measures.
   How: In `tests/test_robot_mcp.py`, reuse the `env` fixture and `_envelopes()` helper: put a JPEG made with OpenCV into the fake camera queue, call `tools.look()`, and assert the returned bytes equal the input.
   Status: ⏳ Unimplemented
   Reason Deferred: Small; do it in the next vision change.

2. Save one raw reference frame per camera after each exposure change — Priority 55% (Nice to have) [Professionalism]
   What: After `./cli.sh cameras --write`, save one frame per camera into `data/camera_reference/` with the date and exposure in its name.
   Why: With no software clean-up, picture quality depends only on the camera settings. A reference frame lets the team see later whether the light or the settings changed. `data/` is gitignored, so people in the frame stay out of git.
   How: In `scripts/camera_settings.py`, after a `--tune --write`, keep the frame captured at the chosen exposure and write it with `cv2.imwrite`. Print the path.
   Status: ⏳ Unimplemented
   Reason Deferred: Needs a live tuning session with the Station stopped.

3. Show the camera exposure in the console page — Priority 35% (Optional) [Professionalism]
   What: Show the configured exposure value for each camera under its tile on the console page.
   Why: `look()` no longer reports exposure. A visible value helps someone at the bench notice when a camera is still on old or automatic settings.
   How: In `src/web_console.py`, return `camera_settings` from the `/cameras` endpoint, and in `src/web/console.html` print `exposure` under each tile's name.
   Status: ⏳ Unimplemented
   Reason Deferred: Cosmetic; wait until the exposure values are final.

1. Add a hard table-height floor to every IK target — Priority 92% (Critical) [Security]
   What: Before any Cartesian move, check that every point on the planned path stays a few millimetres above the table and inside the tag rectangle, and refuse the move otherwise.
   Why: A wrong joint zero or a typo in a target can send the fingertips into the table or the bowl. The arm already hit the table once (motor 2, 2026-11-21). A check in code catches this before a motor moves, whatever Claude or a person asks for.
   How: In `src/arm_kinematics.py`, add a function that samples FK along the straight line in joint space from the current pose to the IK goal (e.g. 20 steps) and returns the lowest fingertip z in the table frame. In the future Cartesian move command, refuse when it is below `workspace.z_table_floor_mm` or outside the tag rectangle plus a margin. Add a unit test with a target below the table.
   Status: ⏳ Unimplemented
   Reason Deferred: There is no Cartesian move command yet; add the check in the same change that adds it.

2. Re-check the camera calibration automatically on every look — Priority 72% (High value) [Best practices]
   What: Each time the table camera is used for coordinates, detect the four tags again and compare their pixel positions with the ones saved at calibration time.
   Why: If someone bumps the camera or a tag, every coordinate silently shifts by centimetres. A quick check turns that into a clear warning ("camera moved 14 px, run calib camera") instead of a missed grape.
   How: `config/calibration.json` already stores `camera.centers_px`. Write a small function in `src/tag_calibration.py` that runs `detect_tags`, scales to the saved image size, and returns the largest shift in pixels; call it before `pixel_to_table` in the vision code and warn above ~5 px.
   Status: ⏳ Unimplemented
   Reason Deferred: Needs the first real camera calibration to pick a sensible threshold.

3. Save each bench calibration run as a small report — Priority 45% (Nice to have) [Professionalism]
   What: When `calib fit --write` runs, also write a dated text report (points, per-point errors, joint zeros, overlay path) into `docs/calibration_runs/`.
   Why: Judges and teammates can see how accurate the arm really is, and if accuracy gets worse later you can compare against the earlier run instead of guessing.
   How: In `scripts/calib.py` `cmd_fit`, after saving, format the printed numbers into a Markdown file named by date. No camera images in it (people can appear in frames); link to `data/calibration/` only by file name.
   Status: ⏳ Unimplemented
   Reason Deferred: Only useful once real touch points exist.

1. Put a matte, darker cloth on the table — Priority 88% (High value) [Best practices]
   What: Replace the bright white table cover with a matte mid-grey or dark-blue cloth or card.
   Why: On white, 47-62% of the table and gripper pictures are pure white (measured 2026-11-21), and a pale green grape almost disappears. No software can recover pure-white pixels; a darker, non-shiny surface gives the grape and bowls clear edges for Claude and for the ACT policy.
   How: Lay the cloth over the work area, tape the corners so it cannot move, run `./cli.sh cameras --tune` again (Station stopped), then check that the chosen exposure's verdict is `ok` in the `--tune` table.
   Status: ⏳ Unimplemented
   Reason Deferred: Needs a physical material at the bench and the team's agreement before ACT demos are recorded.

2. Freeze the camera setup before recording ACT demos, and store it with each episode — Priority 80% (High value) [Best practices]
   What: Save the camera exposure, controls and `resize_target` into each demo episode's metadata, and warn when they differ from the first episode.
   Why: A policy trained on one exposure or frame size can fail when the picture changes. Without the settings stored, nobody can tell later why a model stopped working.
   How: In `src/demo_recorder.py`, add `camera_settings` (from `config/elrobot.json`) and `resize_target` (from `station.yaml`) to the episode's meta file; in `scripts/record_demos.py`, compare with episode 0 and print a warning if they differ.
   Status: ⏳ Unimplemented
   Reason Deferred: Camera settings are still being tuned; do it once they are final.

3. Crop the table camera to the table — Priority 55% (Nice to have) [Security]
   What: Add an optional crop box per camera in `config/elrobot.json`, so `look()` only shows the table area.
   Why: The table and gripper cameras also catch people and screens in the background. Cropping keeps them out of what is sent to Claude and of the logs, and gives the food more pixels.
   How: Add `"crop": [x, y, w, h]` (fractions of the frame) under `camera_settings.table`, apply it in `RobotTools.look()` in `src/robot_tools.py`, and add a test with a synthetic frame. Note that this is image processing again; the software picture enhancement was removed on request on 2026-11-22.
   Status: ⏳ Unimplemented
   Reason Deferred: The crop box needs to be chosen on the real camera view once the camera position is final.

1. Warn on start when a named camera is missing — Priority 60% (Nice to have) [Professionalism]
   What: When the console starts, print which configured cameras (`table`, `gripper`, `face`) the Station is actually streaming, and name any that are missing.
   Why: Today a missing camera only shows as an error tile on the page. The USB hub on bus 3 has dropped cameras several times, and a clear message at start saves time at the bench.
   How: In `src/web_console.py` `main()`, call `tools.list_cameras()` once, compare the live names with `config/elrobot.json` → `cameras`, and log a warning that names each missing camera and its USB port.
   Status: ⏳ Unimplemented
   Reason Deferred: Small; do it after the face camera is confirmed live.

1. Check the start pose before each demo episode — Priority 75% (High value) [Best practices]
   What: Before Enter starts an episode, show how far the follower is from the start anchor (for example `arm_rest`) and warn if it is far off.
   Why: ACT learns much faster from 60-100 demos when every episode starts from the same pose; mixed starts waste demonstrations.
   How: In `scripts/record_demos.py`, add `--start-anchor arm_rest`, read it from `config/envelope.json` anchors, print the largest motor difference before each episode, and warn above about 60 steps.
   Status: ⏳ Unimplemented
   Reason Deferred: First confirm the recorder works live and which start pose the team wants.

2. Keep demo frames private and deletable — Priority 65% (Nice to have) [Security]
   What: Write down who may copy `data/demos/`, and add `./cli.sh demos delete <episode>` for removing an episode where a person is visible.
   Why: The table camera can show people sitting at the table. Training data tends to get copied to other laptops or uploaded, and frames of people should not leave the team.
   How: Add a short "Privacy" paragraph to `docs/act_pick_skill.md` and a delete subcommand that removes one episode folder after a confirmation.
   Status: ⏳ Unimplemented
   Reason Deferred: No episodes are recorded yet.

3. Preview an episode as a short video — Priority 50% (Nice to have) [Professionalism]
   What: `./cli.sh demos preview <episode>` writes an MP4 of the camera frames with the joint values printed on them.
   Why: Bad demos (shaky, a missed grasp, a camera frozen) are easy to spot in a 10-second clip and hard to spot in numbers; removing them improves the trained model.
   How: Use PyAV (already in `.venv` for the console) to encode `frames/<camera>/*.jpg` at the recorded rate into `logs/preview-<episode>.mp4`.
   Status: ⏳ Unimplemented
   Reason Deferred: Useful once the first real episodes exist.

1. Slow down and shrink nudges near the face anchor in code — Priority 85% (High value) [Security]
   What: When the arm is close to the recorded `face_standoff` anchor, let `nudge_joint` allow only 1-2% nudges at low speed, whatever Claude asks for.
   Why: The action space stops the arm going where the operator never went, but near the face the speed and step size are still Claude's choice. The plan requires code limits near a person (safety rule 4).
   How: In `RobotTools.nudge_joint`, if the distance to the `face_standoff` anchor is under about 150 steps, cap `delta_percent` at 2 and `speed` at 150; add a fake-arm test.
   Status: ⏳ Unimplemented
   Reason Deferred: Needs a recorded `face_standoff` anchor to tune the distance.

2. Warn when the recorded action space no longer matches the table — Priority 60% (Nice to have) [Best practices]
   What: At console start, warn if the table camera view differs a lot from the view at recording time.
   Why: The space is only valid while the arm base and table stay put. If someone moves the table, the "safe" space may now go through it.
   How: Keep a small table-camera thumbnail locally when recording (logs/, not git), compare it with a fresh frame when the console starts, and post a warning in the chat if they differ a lot.
   Status: ⏳ Unimplemented
   Reason Deferred: First see how stable the setup is during a session.

3. Show the recorded space as a picture — Priority 45% (Nice to have) [Professionalism]
   What: A small plot of the recorded poses per pair of joints (for example motor 2 vs motor 3), with anchors marked.
   Why: It shows at a glance whether the operator covered the area over the food and toward the person, or left gaps that will make Claude's nudges get refused.
   How: Add `./cli.sh hw envelope plot` that writes a PNG into `logs/` from `config/envelope.json`.
   Status: ⏳ Unimplemented
   Reason Deferred: Only useful once a real recording exists.

1. Reconnect the arm command channel after a Station restart — Priority 95% (Critical) [Best practices]
   What: Make the MCP server notice that the Station restarted and open a fresh connection for motor commands, not only for readings.
   Why: On 2026-11-21 the Station was restarted while the MCP server kept running. Readings still worked, but every move and even the "hold" from stop() silently went nowhere (the motors' goal register kept its old value). A stop that does nothing is the worst failure near a person.
   How: In `src/elrobot_hardware.py`, after each `_sync_write` read back the goal register; if it did not change, close `self.client`, call `connect()` again and retry once, then report an error. Add a fake-Station test for it.
   Status: ⏳ Unimplemented
   Reason Deferred: It changes motion code, which needs the owner's OK first (AGENTS.md).

2. Enforce the face standoff in code for stepwise mode — Priority 88% (High value) [Security]
   What: Have local code, not Claude's judgement, refuse nudges that bring the gripper closer once the face in the gripper camera is big enough.
   Why: In stepwise mode the 5-10 cm standoff is only a prompt rule. A wrong guess by the model about which joint moves toward the face could push food into someone's face.
   How: Add a `face_size` check (for example MediaPipe face detection on the gripper frame) inside `RobotTools.nudge_joint`; when the face is wider than half the frame, allow only nudges that make it smaller, and return a clear refusal otherwise.
   Status: ⏳ Unimplemented
   Reason Deferred: Needs the mouth tracker (plan task 2.1) and a teammate in front of the camera to tune the size.

3. Save each stepwise run as a replayable log — Priority 55% (Nice to have) [Best practices]
   What: Record every tick of a stepwise run (camera frame, Claude's reason, the nudge, the joint positions) to `logs/`.
   Why: Runs take minutes and fail in ways that are hard to remember. A log lets the team see where Claude got confused, and a good run can be turned into a recorded plan for the demo.
   How: In `ConsoleAgent._run_turn`, append each tool call, its result and the latest robot state as one JSON line to `logs/stepwise-<time>.jsonl`, with frames saved next to it (logs are gitignored and stay local because frames show people).
   Status: ⏳ Unimplemented
   Reason Deferred: First see whether stepwise steering works at all on the arm.

1. Teach and lock the 6 assistive feeding waypoints on the follower arm (`zone_a_hover`, `zone_a`, `serve`, `spoon_holder`, `bowl_scoop`, `serve_spoon`) — Priority 94% (Critical) [Best practices]
   What: Pose the physical follower arm by hand (with torque off) at the grape bowl, spoon holder, and a 7 cm standoff in front of the diner's mouth, and save each pose with `./cli.sh hw teach <name>`.
   Why: The camera-guided feeding controller (`./cli.sh feed`) maps detected food and mouth targets directly to these verified joint waypoints so the arm moves smoothly without inverse-kinematics guesswork near a person's face.
   How: With the Station running and torque off, guide the gripper to each position and run `./cli.sh hw teach clear`, `./cli.sh hw teach zone_a_hover`, `./cli.sh hw teach zone_a`, and `./cli.sh hw teach serve`, then commit `config/waypoints.json`.
   Status: ⏳ Unimplemented
   Reason Deferred: Requires the physical USB hub to be re-seated and the hardware owner to position the arm at the bench.

2. Add a live mouth-open trigger confirmation before releasing a grape at the facial standoff — Priority 86% (High value) [Security]
   What: Require the camera detector to see the diner's mouth stay open for 3 consecutive frames at the `serve` standoff pose before opening the gripper to release the grape.
   Why: Prevents dropping a grape prematurely while the diner is still leaning in or speaking, making the feeding handover safe and comfortable.
   How: In `src/feeding_vision.py`, poll `detect_mouth()` 3 times at 0.2 s intervals after reaching the `serve` waypoint and only call `set_gripper(60)` once `mouth_open` is true in all 3 frames.
   Status: ⏳ Unimplemented
   Reason Deferred: Best tuned with a teammate sitting in front of the live camera during the Stage 2 bench rehearsal.

3. Add an automatic USB hub health banner to `./cli.sh feed` and Mission Control — Priority 76% (High value) [Professionalism]
   What: Check whether `/dev/video4` and `/dev/ttyACM0`–`1` are present before starting a feeding cycle, and print a clear warning if the USB hub has dropped them.
   Why: We observed the bus-3 port-4 USB hub drop both cameras and serial adapters mid-session; an immediate visual alert saves debugging time during live demos.
   How: Check `Path("/dev/video4").exists()` and `list(Path("/dev").glob("ttyACM*"))` in `scripts/camera_feed_arm.py` and include a `"usb_hub_healthy"` flag in `/api/state` in `src/digital_twin_server.py`.
   Status: ⏳ Unimplemented
   Reason Deferred: Keep the current change focused on the camera-to-slave-arm feeding pipeline.

4. Calibrate tabletop homography with printed AprilTags — Priority 95% (Critical) [Best practices]
   What: Place the printed 4-corner AprilTags on the workspace table under `/dev/video2` or `/dev/video4` and run `python3 scripts/calibrate_camera.py`.
   Why: Transforms 2D image coordinates into exact millimeter $(X, Y)$ coordinates relative to the arm base, allowing autonomous agents to see objects on the table without coordinate hallucinations.
   How: Print `docs/apriltags_printable.html` or display on a smartphone, place at table corners, and execute `python3 scripts/calibrate_camera.py`.
   Status: ⏳ Unimplemented
   Reason Deferred: Requires physical placement of tags on the hackathon desk.

2. Teach initial core waypoints (`home`, `hover`, `bin`) — Priority 85% (High value) [Best practices]
   What: Use the leader arm or `./cli.sh hw teach <name>` to record default reference positions into `config/waypoints.json`.
   Why: Provides deterministic, collision-safe poses that the autonomous agent can return to between pick and place operations.
   How: Move the arm to desired rest and clearance positions and run `./cli.sh hw teach home` and `./cli.sh hw teach clear`.
   Status: ⏳ Unimplemented
   Reason Deferred: To be performed on the physical table alongside the team.

3. Add dynamic role indicators to web console / CLI HUD — Priority 72% (Nice to have) [Professionalism]
   What: Display a visual banner or terminal HUD clearly indicating Master (`5B61034962`) and Slave (`5B61037051`) with live joint angle comparison.
   Why: Prevents confusion between identical-looking leader and follower buses during rapid demo presentations and judging rounds.
   How: Add a small status banner in `scripts/teleop_sync.py` and the digital twin dashboard.
   Status: ⏳ Unimplemented
   Reason Deferred: Core sync functionality is verified; UI embellishment can be added before Sunday pitch.
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

13. Enforce the commit checklist with a git pre-commit hook — Priority 74% (High value) [Best practices]
    What: A script that runs automatically before each commit, checks that the tests pass and that `CHANGELOG.md` is staged, and blocks the commit if not.
    Why: Right now the commit rules only live in `AGENTS.md`. A hook catches a forgotten test run or changelog entry before it reaches the shared history.
    How: Create `.githooks/pre-commit` with a few lines that run `python3 -m pytest tests/ -q` and check `git diff --cached --name-only` for `CHANGELOG.md`, then run `git config core.hooksPath .githooks` once on each machine.
    Status: ⏳ Unimplemented
    Reason Deferred: Adds a gate to every commit for the whole team. Needs agreement on which checks are mandatory before it is turned on.

14. Add a hardware-safety checklist to pull requests that touch motion code — Priority 86% (High value) [Security]
    What: A short checklist that every pull request changing motion code must complete before it is merged, covering torque state, workspace clearance, and a test run on the bench.
    Why: The arm can hit people or the table. A code change that looks correct on paper can still move the arm the wrong way, and a reviewer who is not at the bench cannot see that.
    How: Add `.github/pull_request_template.md` with checkboxes: "tests pass", "no `hw jog`/`hw goto` run without the hardware owner", "workspace clear", "E-stop (`./cli.sh hw stop`) tested".
    Status: ⏳ Unimplemented
    Reason Deferred: Needs the team to agree who the hardware owner is and what counts as a bench test before the checklist can be written.

15. Use a lock file so only one terminal can send motion commands — Priority 78% (High value) [Security]
    What: A small lock file that the motion commands check before moving the arm, so a second terminal cannot start a move while the first one is running.
    Why: Two people or two agents sending commands at the same time can fight each other on the same motors. A lock stops that before any motor moves.
    How: In `scripts/hw_day.py`, create `data/hw_motion.lock` with the process ID when a move starts, refuse new moves while the lock exists and the process is alive, and remove the lock when the move ends.
    Status: ⏳ Unimplemented
    Reason Deferred: Changes the motion code, which needs the real arm to test properly. Should wait until the first bench session confirms the current flow.

16. Save each camera's stable port path in the config — Priority 72% (High value) [Best practices]
    What: Record which USB port each camera is plugged into (for example, "overhead" and "wrist") in `config/`, so the software finds the right camera without guessing.
    Why: Camera numbers like `/dev/video2` change after a replug. Two of our cameras share the same name, so a wrong guess could send the wrong image to the robot's logic.
    How: Use `ls -l /dev/v4l/by-path/` to find each camera's path, confirm it with a test frame, and add the paths to `config/elrobot.json` in a calibration commit.
    Status: ⏳ Unimplemented
    Reason Deferred: Needs the cameras plugged into their final ports and a confirmed overhead/wrist assignment from the hardware owner first.

17. Add a one-command bench readiness check — Priority 65% (Nice to have) [Best practices]
    What: A single command that checks serial permissions, the Station, the bus serial numbers and the cameras, and prints pass or fail for each.
    Why: Right now setup problems are found one at a time during a bench session. One check before powering the arm saves time and avoids the permission and bus-selection mistakes we have already hit.
    How: Add a `./cli.sh bench-check` subcommand that reuses the existing preflight checks and adds a serial permission check and a camera frame check. It should only read, never move the arm.
    Status: ⏳ Unimplemented
    Reason Deferred: Mostly a convenience. The manual steps in `docs/team_setup.md` cover it until the team has used them on a bench session.

18. Check that every link in the docs points to a real file — Priority 45% (Nice to have) [Professionalism]
    What: An automatic check that flags any broken link or missing file path in the Markdown docs.
    Why: The team docs now link to each other. A renamed file would leave a broken link that a new team member finds only when they are stuck.
    How: Add a small test in `tests/` that reads each `docs/*.md` and `AGENTS.md`, extracts relative links, and fails if a target file does not exist.
    Status: ⏳ Unimplemented
    Reason Deferred: Useful but not urgent. The docs are new and few, so a manual check is enough for now.

19. Add automated tests for the sync script's four outcomes — Priority 76% (High value) [Best practices]
    What: Automatic tests that prove `scripts/agent_sync.sh` behaves correctly when it is behind, dirty, diverged or offline.
    Why: The sync script decides whether a teammate's work gets pulled over an agent's edits. Its fast-forward, dirty-tree and diverged paths were not run in a real test yet, so a bug there could cause the very conflicts it is meant to prevent.
    How: Add `tests/test_agent_sync.py` that builds a throwaway bare remote and two clones in a temporary folder, makes a commit in one clone, and runs the script in the other for each case. Check the exit code in each case.
    Status: ⏳ Unimplemented
    Reason Deferred: Writing the test is not hard, but the first run was blocked. Scratch-repo tests need a go-ahead, so this stays on the list until it is approved.

20. Run the sync check automatically when an agent session starts — Priority 68% (High value) [Best practices]
    What: A session-start hook that runs `./cli.sh sync` as soon as an AI agent session opens, so the agent does not depend on remembering to do it.
    Why: The rule in `AGENTS.md` only works if every agent follows it. A hook makes the sync happen every time and shows the result before any edit.
    How: Add a `SessionStart` hook in the project's `.claude/settings.json` that runs `./cli.sh sync` and prints the output. Test it once on a clean branch.
    Status: ⏳ Unimplemented
    Reason Deferred: Changes the agent tool configuration for everyone on the team. Needs a team decision first.

21. Flag stale feature branches in continuous integration — Priority 50% (Nice to have) [Best practices]
    What: An automatic check on each pull request that warns when the branch is far behind `main`.
    Why: A long-stale branch is the main source of painful merge conflicts. An early warning gives the author time to rebase while the changes are still small.
    How: Add a GitHub Actions workflow that runs `git rev-list --count HEAD..origin/main` on each pull request and posts a warning comment when the count is above a set limit, such as 20.
    Status: ⏳ Unimplemented
    Reason Deferred: Needs the repository to use GitHub Actions and pull requests. Nice to have once the team is using pull requests regularly.

23. Record the Station binary's checksum next to the SDK's — Priority 55% (Nice to have) [Security]
    What: Store the SHA-256 of `bin/station` in the check script, so `sdk-check` also proves the binary is the one the team agreed on.
    Why: The check currently confirms the version string the binary prints. A replaced binary that prints the same version would pass. A checksum closes that gap.
    How: Run `sha256sum bin/station` on a known-good machine, add the value as a constant in `scripts/sdk_check.py`, and add a check that compares it.
    Status: ⏳ Unimplemented
    Reason Deferred: Only useful once the team's Station binary is fixed and shared. Doing it now would lock in a binary that may still change.

24. Require an approval note when the SDK pin changes — Priority 50% (Nice to have) [Professionalism]
    What: A pull request check that flags any change to `.gitmodules` or the submodule's commit, and asks for the owner's approval in the description.
    Why: The SDK pin decides which NormaCore code every teammate runs. A pin changed by accident would spread to the whole team without anyone noticing in review.
    How: Add a GitHub Actions workflow that runs `git diff --name-only origin/main...HEAD` and fails the check if `.gitmodules` or `external/norma-core` appears without the words "SDK pin approved" in the pull request body.
    Status: ⏳ Unimplemented
    Reason Deferred: Needs GitHub Actions and pull requests in regular use. The team has not used pull requests yet.

25. Keep an offline mirror of the pinned SDK — Priority 58% (Nice to have) [Best practices]
    What: A copy of the SDK at commit `5f4f805` on a team drive or in a backup, so a bench session can go ahead even if GitHub is unreachable.
    Why: The Station venue may have poor internet. Without a mirror, a new machine cannot fetch the submodule on the day.
    How: Run `git bundle create norma-core-5f4f805.bundle 5f4f805` in the submodule folder, store the bundle with its SHA-256 on the team drive, and add the restore steps to `docs/team_setup.md`.
    Status: ⏳ Unimplemented
    Reason Deferred: Only needed if the team will work offline. The owner should decide whether a mirror is needed for the venue.

26. Remove the old SDK backup once every machine uses the submodule — Priority 35% (Optional) [Professionalism]
    What: Delete the leftover copies `external/norma-core-snapshot/` and `external/norma-core-main.tar.gz`, which the submodule has replaced.
    Why: Two unused copies of the SDK take up space and can be mistaken for the real one. Removing them stops a teammate from using the wrong copy.
    How: After every machine has run `./cli.sh sdk-check` and passed, delete both paths. They are gitignored, so nothing is committed.
    Status: ⏳ Unimplemented
    Reason Deferred: Deleting files needs the owner's go-ahead, and the backups are the fallback if the submodule has a problem on the bench.

27. Guard the generated protobuf code against accidental regeneration — Priority 40% (Optional) [Professionalism]
    What: A check that fails if `external/norma-core/target/gen_python` differs from the team's known copy.
    Why: Regenerating the protobuf code with a different `protoc` version can break the message format quietly. A check catches that before a bench session. (Restored: this was wrongly removed as obsolete. Git now tracks the folder and `sdk-check` already fails on local edits, but it does not compare the generated code itself.)
    How: Store a checksum of the generated folder's file list in `scripts/sdk_check.py` and compare it on each run.
    Status: ⏳ Unimplemented
    Reason Deferred: Low risk while nobody regenerates the code. Worth doing now that the SDK is pinned.
