### Post-Implementation Suggestions

1. Choose one primary stage deck (or combine Slides 2–4 of `CareArm_Use_Case_Pitch.pptx` with Slides 4–8 of `Assistive_Feeding_Robot_Pitch.pptx`) before uploading to Google Slides — Priority 89% (High value) [Professionalism]
   What: Decide whether to present the human-centered `docs/CareArm_Use_Case_Pitch.pptx` (9 slides) for the main-stage 5-minute pitch, the technical `docs/Assistive_Feeding_Robot_Pitch.pptx` (10 slides) for track judges, or a merged 10-slide hybrid.
   Why: Keeping a single cohesive narrative ensures you stay comfortably inside the 3-minute video / 5-minute main-stage time cap without rushing slides.
   How: Review both decks side-by-side in LibreOffice Impress and upload your chosen version to your shared Google Slides URL.
   Status: ⏳ Unimplemented
   Reason Deferred: Both decks are ready locally so the team can pick the best balance of story vs. technical depth for the final stage.

2. Add a real user/caregiver quote or Berlin care-statistics citation to Slide 2 of `CareArm_Use_Case_Pitch.pptx` — Priority 65% (Nice to have) [Professionalism]
   What: Add one concrete healthcare statistic (e.g., German long-term care staffing gap or stroke incidence) or a short quote from a teammate who tested the mouth-open standoff on the bench.
   Why: Grounding the persona slide in a real number or firsthand test quote makes the emotional hook even more memorable for non-robotics judges.
   How: Update Slide 2 in `scripts/generate_use_case_deck.py` and re-run `python3 scripts/generate_use_case_deck.py`.
   Status: ⏳ Unimplemented
   Reason Deferred: Kept this pass strictly aligned to verified project facts without introducing unverified external statistics.

3. Prepare a 30-second spoken voiceover script synced to Slides 1–4 for the 3-minute hackathon submission video — Priority 76% (High value) [Best practices]
   What: Use the embedded speaker notes in `CareArm_Use_Case_Pitch.pptx` Slides 1–4 as the opening 60 seconds of your 3-minute showcase video, followed by 90 seconds of live robot feeding and 30 seconds of safety/E-stop proof.
   Why: Judges evaluate tracks primarily on the 3-minute video; pairing a clear human story up front with live robot footage maximizes both impact and technical score.
   How: Open Presenter Notes in LibreOffice Impress while recording your webcam + bench demo video, then upload to your shared Google Drive folder.
   Status: ⏳ Unimplemented
   Reason Deferred: Ready to record once the team runs the final bench video capture.

1. Re-upload the updated `docs/Assistive_Feeding_Robot_Pitch.pptx` (now with Team 6 roster) to Google Slides — Priority 91% (Critical) [Professionalism]
   What: Import the regenerated `docs/Assistive_Feeding_Robot_Pitch.pptx` into your shared Google Slides presentation URL so the online slides match the local deck with Team 6 (`CareArm`) and all 3 member names.
   Why: Judges and stage AV staff open the Google Slides link from the Tally submission form; keeping it synced avoids showing an older draft without team names.
   How: Open your Google Slides link (`File -> Import slides` or replace file in Google Drive) and upload `docs/Assistive_Feeding_Robot_Pitch.pptx`, then confirm "Anyone with the link can view".
   Status: ⏳ Unimplemented
   Reason Deferred: Requires uploading directly in the browser to your Google Drive / Slides account.

2. Add a 60-second "Judge Q&A Cheat Sheet" section to `docs/Hackathon_submission_requirements.md` — Priority 68% (Nice to have) [Professionalism]
   What: Append 5 concise answers to likely robotics judge questions (why waypoints + bounded visual servoing over raw IK, how E-stop guarantees no arm drop, how prompt injections are blocked, BOM cost vs $10k commercial feeders, and spoon roadmap).
   Why: Helps all 3 teammates answer technical deep-dives consistently and confidently during the 2-minute stage Q&A.
   How: Add a short `## Stage Q&A Cheat Sheet` table at the bottom of `docs/Hackathon_submission_requirements.md`.
   Status: ⏳ Unimplemented
   Reason Deferred: Kept this turn focused on README, pitch deck roster, and FINDINGS updates.

3. Close the LibreOffice lockfile `docs/.~lock.Assistive_Feeding_Robot_Pitch.pptx#` and add `.~lock.*#` to `.gitignore` — Priority 52% (Nice to have) [Best practices]
   What: Add `*.~lock.*#` (or `.~lock.*`) to `.gitignore` so LibreOffice Impress temporary lockfiles never clutter `git status` while editing the deck.
   Why: Prevents accidental staging of temporary editor lockfiles during frantic pre-deadline hackathon commits.
   How: Append `**/.~lock.*#` to `.gitignore` and close LibreOffice Impress when finished viewing the deck.
   Status: ⏳ Unimplemented
   Reason Deferred: Non-blocking cleanup; lockfile was left untracked and excluded from commits.

1. Verify all 3 submission links in an incognito browser window 15 minutes before the 16:30 deadline — Priority 94% (Critical) [Security]
   What: Open the Google Drive video folder, Google Slides link, and GitHub repository URL in a logged-out incognito browser tab to confirm judges can access every asset without login prompts.
   Why: A private repo or restricted Google Drive permission can automatically disqualify a team or prevent judges from watching your demo video.
   How: Open a new Private/Incognito window, paste all three links from `docs/Hackathon_submission_requirements.md`, and verify each loads cleanly without signing in.
   Status: ⏳ Unimplemented
   Reason Deferred: Pending final video upload, Google Slides import, and GitHub push.

1. Embed real bench photos and a 3-camera console screenshot into the pitch deck — Priority 86% (High value) [Professionalism]
   What: Add live screenshots of `http://localhost:8890` (showing the annotated `Table`, `Gripper`, and `OBSBOT` feeds with `Mouth: OPEN ✓`) and a photo of the ElRobot arm to Slides 5 and 7 of `docs/Assistive_Feeding_Robot_Pitch.pptx`.
   Why: Real hardware visuals give judges immediate proof that the physical arm, 3-camera vision overlays, and multi-tab console are running live rather than mocked.
   How: Capture a browser screenshot and bench photo into `docs/assets/`, then add `slide.shapes.add_picture(...)` calls in `scripts/generate_pitch_deck.py` and re-run `python3 scripts/generate_pitch_deck.py`.
   Status: ⏳ Unimplemented
   Reason Deferred: No bench photos or live console screenshots were stored in the repository yet during this offline deck generation pass.

2. Record a 45-second backup demo video of a full grape + mouth-open feeding cycle — Priority 84% (High value) [Best practices]
   What: Capture a screen + bench video showing voice request -> grape pick -> standoff pause -> mouth open -> delivery -> voice `"Stop!"` and link/embed it as a fallback slide.
   Why: Live robotics demos on hackathon stages can face Wi-Fi drops or lighting changes; a recorded backup ensures your 3-minute pitch finishes strongly no matter what happens on stage.
   How: Record one clean run on the bench with OBS or a phone, save it locally (outside git), and keep it open in a media player behind the slide deck during the pitch.
   Status: ⏳ Unimplemented
   Reason Deferred: Requires a live bench session with the powered arm and hardware owner present.

3. Export a presenter-ready PDF copy alongside the PPTX before walking on stage — Priority 58% (Nice to have) [Best practices]
   What: Export `docs/Assistive_Feeding_Robot_Pitch.pdf` using LibreOffice (`soffice --headless --convert-to pdf`) so the deck renders identically on any stage laptop even if fonts or PowerPoint differ.
   Why: Eliminates last-minute font substitution or slide-layout shifts when plugging into an unfamiliar hackathon presentation machine.
   How: Run `soffice --headless --convert-to pdf docs/Assistive_Feeding_Robot_Pitch.pptx --outdir docs/` right after any final team-name or photo edits.
   Status: ⏳ Unimplemented
   Reason Deferred: Kept the repository focused on the editable `.pptx` and its Python generator until any final team customizations are added.

1. Complete Stage 1B + 2B bench calibration on the real arm (`gripper.verified`, `grape_open`, `grasp_alignment`) — Priority 92% (Critical) [Best practices]
   What: Run `./cli.sh hw identify 8` and `./cli.sh hw identify 1`, re-teach an open-jaw `grape_open` waypoint, and record `grasp_alignment.camera_sign` in `config/elrobot.json`.
   Why: Activates Stage 1–2 closed-loop alignment and empty-grasp rejection on the physical follower arm without guessing motor IDs or directions.
   How: Follow Steps 1B and 2B in `docs/GRIPPER_CAMERA_ROADMAP.md` with the hardware owner present and hand on the 12 V switch.
   Status: ⏳ Unimplemented
   Reason Deferred: Requires the physical arm powered on at the bench with the hardware owner confirming each step.

2. Add a `check_gripper_roi()` MCP tool so Claude gets exact `offset_x_pct` numbers alongside `look("gripper")` — Priority 76% (High value) [Professionalism]
   What: Expose `FeedingVisionDetector.analyze_gripper_roi()` as a read-only MCP tool returning `{in_jaws, offset_x_pct, coverage}` from the latest gripper frame.
   Why: Gives Claude deterministic numerical alignment feedback (e.g. `offset_x_pct: +0.32`) and logs exact before/after offsets in the `Developer Trace` tab.
   How: Add `check_gripper_roi()` to `src/robot_tools.py` reusing `look("gripper")` + `FeedingVisionDetector.analyze_gripper_roi()`, register it in `src/robot_mcp_server.py`, and add a unit test.
   Status: ⏳ Unimplemented
   Reason Deferred: Stage 0–2A already draws the live jaw-zone overlay on the gripper stream and gives Claude multimodal `look("gripper")` inspection.

3. Add a `FakeClaude` end-to-end empty-grasp abort test in `tests/test_console_agent.py` — Priority 62% (Nice to have) [Best practices]
   What: Add a test simulating `play_sequence(stop_after="grape")` -> `align_base` -> `set_gripper` returning `closed_empty` and verifying Claude does not call `play_sequence(start_at="feed_1")`.
   Why: Regression-tests the full Stage 1–2 agent loop offline so prompt edits never weaken the "never bring an empty gripper to the mouth" rule.
   How: Add a `FakeClaude` test in `tests/test_console_agent.py` asserting the `tool_use` sequence stops cleanly on `closed_empty`.
   Status: ⏳ Unimplemented
   Reason Deferred: Core `RobotTools` slicing, `align_base` bounds, and `analyze_gripper_roi` unit tests are already passing in `tests/test_robot_mcp.py`.

3. Add a hardware-bench calibration script (`./cli.sh hw calibrate-grasp`) for Stage 1B/2B — Priority 64% (Nice to have) [Security]
   What: Add a guided read-only/single-step CLI wizard that walks the hardware owner through identifying motor 8 (gripper), motor 1 (base), and verifying camera-to-motor sign safely.
   Why: Prevents manual JSON typos in `config/elrobot.json` and ensures `gripper.verified` and `grasp_alignment.camera_sign` are recorded consistently.
   How: Add a helper in `scripts/hw_day.py` that wraps `identify` and prints the exact JSON snippet to review before saving.
   Status: ⏳ Unimplemented
   Reason Deferred: Manual `./cli.sh hw identify` commands already exist for the hackathon bench session.

1. Add a 1-click `Dry-Run Command Preview` mode toggle in the `Developer Trace` tab — Priority 79% (High value) [Security]
   What: Add a toggle in the `Developer Trace` tab showing whether `ELROBOT_ALLOW_MOTION` is `1` (live) or `0` (dry-run) and warning loudly in red when live arm motion is armed.
   Why: Lets developers verify at a glance whether a traced command will physically move the arm before speaking a feeding command during rehearsal.
   How: Include `"motion_enabled": bool(motion_allowed())` in `GET /api/trace` in `src/web_console.py` and render a live `MOTION: LIVE` / `MOTION: DRY-RUN` badge in the `Developer Trace` toolbar in `src/web/console.html`.
   Status: ⏳ Unimplemented
   Reason Deferred: Kept this turn focused on scope guardrails, live action tracing, and multi-tab UI separation.

2. Persist Developer Trace entries to a timestamped JSONL file in `logs/console_trace_*.jsonl` — Priority 68% (Nice to have) [Best practices]
   What: Append each trace entry (`guardrail`, `thinking`, `tool_call`, `tool_result`) to a gitignored `logs/console_trace_YYYYMMDD.jsonl` file in addition to the in-memory ring buffer.
   Why: Preserves the full post-mortem log of every arm command and guardrail decision even if the console server is restarted during a demo.
   How: In `ConsoleAgent._trace()` (`src/console_agent.py`), append `json.dumps(entry) + "\n"` to `ROOT / "logs" / f"console_trace_{date}.jsonl"` inside a best-effort `try/except`.
   Status: ⏳ Unimplemented
   Reason Deferred: In-memory trace + `Copy JSON` button covers live debugging; file persistence is a quick follow-up.

3. Add a `Test Guardrail` input box inside the `Commands & Guardrails` tab — Priority 54% (Nice to have) [Professionalism]
   What: Add a small read-only test input in the `Commands & Guardrails` tab that runs `classify_intent()` via `POST /api/guardrail_test` without sending anything to Claude or the arm.
   Why: Lets judges test prompt-injection attempts and off-topic questions live to see the `<1 ms` gatekeeper block them cleanly.
   How: Expose `POST /api/guardrail_test` calling `classify_intent(text)` in `src/web_console.py` and wire a tiny form in the `Commands & Guardrails` tab of `src/web/console.html`.
   Status: ⏳ Unimplemented
   Reason Deferred: Users can already test off-topic messages directly in the chat and inspect the `BLOCKED` event in `Developer Trace`.

1. Add a one-click `Test Mouth Gate (Dry-Run)` button next to the OBSBOT badge in `http://localhost:8890` — Priority 80% (High value) [Professionalism]
   What: Add a small button beside the live mouth badge that lets the user or a judge test the full mouth-open confirmation flow (waiting banner -> open mouth -> chime + "Mouth confirmed!") without moving any robot motors.
   Why: Lets you demonstrate the MediaPipe mouth-open trigger safely to judges or calibrate a new user in 5 seconds before turning on arm motion.
   How: Add a client-side rehearsal toggle in `src/web/console.html` that watches `/api/mouth_status` until `mouth_open_confirmed` turns true and then plays the confirm chime and shows a green success banner.
   Status: ⏳ Unimplemented
   Reason Deferred: Kept this turn focused on live status badge, real sequence waiting cue, and configurable timeout.

2. Add a `GET /api/mouth_status` unit test in `tests/test_web_console.py` — Priority 74% (High value) [Best practices]
   What: Add an offline test in `tests/test_web_console.py` verifying that `GET /api/mouth_status` returns fresh `data/mouth_gate_state.json` without opening a physical V4L2 camera when a sequence is waiting.
   Why: Locks in the zero-contention V4L2 handoff contract so future edits to `web_console.py` cannot accidentally cause camera busy errors during feeding.
   How: Monkeypatch `robot_tools.MOUTH_GATE_STATE_FILE` to a temp file with `waiting: true` and assert `TestClient(app).get("/api/mouth_status").json()["waiting_for_mouth"] is True`.
   Status: ⏳ Unimplemented
   Reason Deferred: Unit tests for `mouth_gate_timeout_s` and state-file roundtrip were added in `tests/test_robot_mcp.py`; HTTP route test is a quick follow-up.

3. Add a configurable `Mouth Timeout (s)` number input in `http://localhost:8890` — Priority 52% (Nice to have) [Professionalism]
   What: Expose `feeding_vision.mouth_gate_timeout_s` as a small `3–30 s` numeric input next to the `Wait for Mouth-Open (OBSBOT)` checkbox via `POST /api/mouth_gate`.
   Why: Allows caregivers to adjust how long the arm waits for a diner's mouth to open directly from the browser instead of editing `config/elrobot.json`.
   How: Accept optional `timeout_s` in `POST /api/mouth_gate` (clamped with `mouth_gate_timeout_s`), save it to `config/elrobot.json`, and bind an `<input type="number" min="3" max="30">` in `src/web/console.html`.
   Status: ⏳ Unimplemented
   Reason Deferred: Default 12 s (with config override) is sufficient for the demo; UI slider is optional polish.

1. Raise `resize_target` in `station.yaml` (224 -> 480) and apply manual exposure via `v4l-utils` — Priority 93% (Critical) [Best practices]
   What: Increase `usb-video.resize_target` from `224` to `480` in `station.yaml`, install `v4l-utils`, and run `./cli.sh cameras` before starting the Station.
   Why: Fixes both causes of poor Station camera image quality permanently — removes the 224px blurriness and eliminates the washed-out libuvc auto-exposure bug so AI vision sees food clearly.
   How: Update `resize_target: 480` in `station.yaml`, install `sudo apt-get install -y v4l-utils`, stop the Station, run `./cli.sh cameras`, and restart `./cli.sh station`.
   Status: ⏳ Unimplemented
   Reason Deferred: Requires a brief Station restart while `v4l2-ctl` applies manual exposure to the KD-USB cameras.

2. Add OBSBOT Meet SE (`3564:fefe`) to `scripts/99-normacore-cameras.rules` and install `v4l-utils` — Priority 84% (High value) [Security]
   What: Add the OBSBOT Meet SE USB vendor/product ID (`3564:fefe`) to the camera udev rule and install `v4l-utils` so both the Station and manual exposure controls work cleanly without root privileges.
   Why: Stops the Station from logging repeated USB permission errors (`-3`) for the OBSBOT camera and allows consistent exposure tuning under bright hackathon lighting.
   How: Append a udev rule line for `idVendor=="3564", idProduct=="fefe"` in `scripts/99-normacore-cameras.rules`, copy to `/etc/udev/rules.d/`, reload udevadm, and run `sudo apt-get install -y v4l-utils`.
   Status: ⏳ Unimplemented
   Reason Deferred: Waiting for confirmation on whether the user wants the OBSBOT camera managed by the Station or kept as a direct V4L2 stream.

3. Add role-specific vision overlays (food-only on Table Cam, face/standoff-only on Person Cam) — Priority 78% (High value) [Professionalism]
   What: Run table object detection (`grape_bowl`, `spoon`) exclusively on the Table camera and facial/mouth standoff detection exclusively on the Person camera in `CameraHub.get_annotated_frame()`.
   Why: Eliminates false-positive detections (such as detecting a "bowl" on the person camera or a "mouth" on the table) and doubles frame rate by cutting unnecessary detector work in half.
   How: Pass `role` into `FeedingVisionDetector.analyze_and_annotate(frame, role=role)` in `src/feeding_vision.py` so each camera only runs and draws the detectors relevant to its viewpoint.
   Status: ⏳ Unimplemented
   Reason Deferred: Kept the initial dual-camera dashboard change focused on `src/digital_twin_server.py` and `src/digital_twin.html`.

1. Add a pre-push verification command or `./cli.sh push` helper — Priority 90% (Critical) [Best practices]
   What: Introduce `./cli.sh push` that automatically validates the local branch against tests (`pytest`, `bash -n`) and sync status before prompting and running `git push -u origin <branch>`.
   Why: Reduces friction for developers pushing branches while guaranteeing that broken or unverified builds never reach the remote repository.
   How: Add a `push` subcommand in `cli.sh` that checks `git status`, executes verification, and triggers `git push` with clear user feedback.
   Status: ⏳ Unimplemented
   Reason Deferred: Initial rule update establishes the agent policy first.

2. Integrate a GitHub PR check / creation prompt into agent completion — Priority 82% (High value) [Professionalism]
   What: Have agents ask whether to open a PR (`gh pr create`) automatically after user confirms a branch push.
   Why: Streamlines peer review and branch integration into `main` so changes do not stall on remote feature branches.
   How: Include an automated GitHub CLI prompt (`gh pr create --fill`) whenever a branch is newly pushed to `origin`.
   Status: ⏳ Unimplemented
   Reason Deferred: Depends on developer push workflow adoption first.

3. Add git commit reminder linting to `./cli.sh sync` — Priority 75% (High value) [Security]
   What: Warn developers during `./cli.sh sync` if their local feature branch has unpushed commits that are more than 2 hours old.
   Why: Avoids silent local drift or accidental work loss during active multi-agent / multi-developer hackathon sessions.
   How: Add an `ahead` count check and timestamp warning in `cli.sh` under `sync` command output.
   Status: ⏳ Unimplemented
   Reason Deferred: Non-blocking polish item for hackathon workflow tooling.

1. Teach and lock the 6 assistive feeding waypoints on the follower arm (`zone_a_hover`, `zone_a`, `serve`, `spoon_holder`, `bowl_scoop`, `serve_spoon`) — Priority 94% (Critical) [Best practices]
   What: Pose the physical follower arm by hand (with torque off) at the grape bowl, spoon holder, and a 7 cm standoff in front of the diner's mouth, and save each pose with `./cli.sh hw teach <name>`.
   Why: The camera-guided feeding controller (`./cli.sh feed`) maps detected food and mouth targets directly to these verified joint waypoints so the arm moves smoothly without inverse-kinematics guesswork near a person's face.
   How: With the Station running and torque off, guide the gripper to each position and run `./cli.sh hw teach clear`, `./cli.sh hw teach zone_a_hover`, `./cli.sh hw teach zone_a`, and `./cli.sh hw teach serve`, then commit `config/waypoints.json`.
   Status: ⏳ Unimplemented
   Reason Deferred: Requires the physical USB hub to be re-seated and the hardware owner to position the arm at the bench.

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
