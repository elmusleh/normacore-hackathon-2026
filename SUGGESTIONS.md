### Post-Implementation Suggestions

1. Apply camera exposure automatically before the Station starts — Priority 75% (High value) [Best practices]
   What: Have `./cli.sh station` and `./cli.sh start` run the `./cli.sh cameras` exposure step right before launching the Station.
   Why: Exposure only works while the Station is stopped, so teammates keep getting nearly white table/gripper frames and have to stop, fix and restart by hand.
   How: In `cli.sh`, before `./bin/station` in both commands, call `"$PY" scripts/camera_settings.py || true`; keep a flag such as `ELROBOT_SKIP_EXPOSURE=1` to skip it.
   Status: ⏳ Unimplemented
   Reason Deferred: Needs a check that it never fights a camera the Station already holds on other laptops.

2. Verify the downloaded MediaPipe models by checksum — Priority 60% (Nice to have) [Security]
   What: Pin the SHA-256 of `face_landmarker.task` and `efficientdet_lite0.tflite` and check them in `./cli.sh setup-vision` and `scripts/vision_check.py`.
   Why: The models decide whether the robot thinks a mouth is open; a corrupted or swapped file should be refused, not loaded.
   How: Record `sha256sum data/*.task data/*.tflite` from a known-good laptop, store the values in `scripts/vision_check.py`, compare after download and fail with a clear message on mismatch.
   Status: ⏳ Unimplemented
   Reason Deferred: Needs the hashes from a known-good download agreed by the team.

3. Add a test that `cli.sh` never calls bare `python3` — Priority 45% (Nice to have) [Professionalism]
   What: A small offline test that fails if a new `cli.sh` command uses `python3 ...` instead of `"$PY" ...`.
   Why: Stops the venv problem coming back the next time someone adds a command in a hurry.
   How: In `tests/`, read `cli.sh`, ignore comment and echo lines and the `PY=` default, and assert no line starts with `python3 `.
   Status: ⏳ Unimplemented
   Reason Deferred: Low risk now that all commands are converted; do it with the next `cli.sh` change.

1. Splice a 30–60 second real ElRobot bench demo clip right after Scene 5 of `data/carearm_story_film_1080p.mp4` before uploading to Google Drive — Priority 92% (Critical) [Professionalism]
   What: Insert a short real-hardware clip showing the physical ElRobot picking a grape and pausing for the OBSBOT Mouth-Open gate between Scene 5 (architecture) and Scene 6 (family dinner) in CapCut or ffmpeg.
   Why: Keeps the emotional, studio-narrated Marta story while also satisfying the Robotics Track rule to show the real physical robot in action.
   How: Drop `data/carearm_story_film_1080p.mp4` and your bench phone/OBS clip into CapCut, cut right after Scene 5, export 1080p MP4, and upload to your shared Google Drive folder before `16:30`.
   Status: ⏳ Unimplemented
   Reason Deferred: Ready as soon as you capture one clean 30–60 s clip on the physical bench.

2. Generate a German-narrated version of the story film (`--voice nova` with German script) for local Berlin care-home partners — Priority 55% (Nice to have) [Professionalism]
   What: Add a `--lang de` option to `scripts/build_story_film.py` with translated German narration and captions so you can share the video directly with Berlin occupational therapists and care facilities.
   Why: CareArm already supports bilingual EN/DE voice; having a German story film makes post-hackathon pilot outreach in Berlin effortless.
   How: Add a `STORY_SCENES_DE` list in `scripts/build_story_film.py` and run `.venv/bin/python scripts/build_story_film.py --output data/carearm_story_film_de_1080p.mp4`.
   Status: ⏳ Unimplemented
   Reason Deferred: English version is the primary submission for the international Berlin hackathon jury.

3. Export an `.srt` subtitle file alongside `data/carearm_story_film_1080p.mp4` for accessibility — Priority 50% (Nice to have) [Best practices]
   What: Have `scripts/build_story_film.py` write a matching `data/carearm_story_film_1080p.srt` timed to each scene's narration start/end so viewers watching on mute or with hearing impairments get full word-for-word captions.
   Why: Reinforces CareArm's accessibility-first mission and helps judges watching quickly in Google Drive or YouTube.
   How: Record each scene's cumulative start/end timestamps in `build_story_film.py` and write standard SRT blocks next to the `.mp4`.
   Status: ⏳ Unimplemented
   Reason Deferred: Every scene already has baked-in lower-third headline & summary captions.

2. Embed `docs/assets/scene_01_need.png` through `scene_06_carehome.png` into `docs/CareArm_Use_Case_Pitch.pptx` — Priority 78% (High value) [Professionalism]
   What: Place the 6 bespoke illustrations directly onto the slides of `docs/CareArm_Use_Case_Pitch.pptx` so your live stage slides share the exact same visual world as your video.
   Why: Visual continuity between your submission video and stage presentation makes Team 6 look like a polished med-tech startup.
   How: Add `slide.shapes.add_picture("docs/assets/scene_0X_*.png", ...)` calls in `scripts/generate_use_case_deck.py` and re-run it.
   Status: ⏳ Unimplemented
   Reason Deferred: Kept the text-focused slides crisp until you decide which illustrations you want featured on stage.

3. Embed `docs/diagrams/carearm_overview.png` directly in `README.md` — Priority 70% (High value) [Best practices]
   What: Add `![CareArm System Overview](docs/diagrams/carearm_overview.png)` under the Architecture section of `README.md` so judges immediately see the color-coded 4-layer diagram on GitHub.
   Why: A visual diagram renders natively on GitHub and communicates the entire decoupled architecture in 3 seconds.
   How: Insert the markdown image link right above or below the ASCII diagram in `README.md`.
   Status: ⏳ Unimplemented
   Reason Deferred: Kept this turn focused on generating the PNG/PDF diagrams and the 6-scene illustrated video.

1. Splice live ElRobot bench footage into `data/carearm_pitch_1080p.mp4` using CapCut or DaVinci Resolve for the 3-minute submission video — Priority 93% (Critical) [Professionalism]
   What: Combine the first 45 seconds of `data/carearm_pitch_1080p.mp4` (the human story slides) with 90–120 seconds of real bench video (a teammate speaking to camera + live grape pick + OBSBOT Mouth-Open delivery + voice `"Stop!"`) and auto-captions.
   Why: The Robotics Track rules explicitly require showing the physical robot in action and recommend a team member speaking to camera — slides alone will score lower than a real hardware + story cut.
   How: Import `data/carearm_pitch_1080p.mp4` and your bench phone/OBS clip into CapCut (web/desktop), add auto-captions, export 1080p MP4, and upload to your shared Google Drive folder before `16:30`.
   Status: ⏳ Unimplemented
   Reason Deferred: Requires capturing the live physical robot feeding clip on the bench.

2. Export SVG/PNG renders of both PlantUML diagrams and embed `carearm_overview.svg` in `README.md` and Slide 4 of the technical deck — Priority 74% (High value) [Professionalism]
   What: Render `docs/diagrams/carearm_overview.puml` and `docs/diagrams/carearm_feeding_sequence.puml` to high-DPI SVG/PNG via `plantuml.com` or the VS Code PlantUML extension and reference them in `README.md`.
   Why: GitHub does not natively render raw `.puml` files inline, so embedding an exported `.svg` lets judges see the full 4-layer architecture immediately on your GitHub page.
   How: Paste each `.puml` file into `https://www.plantuml.com/plantuml/uml` (or VS Code PlantUML -> Export Current Diagram), save as `docs/diagrams/carearm_overview.svg`, and embed with `![System Overview](docs/diagrams/carearm_overview.svg)`.
   Status: ⏳ Unimplemented
   Reason Deferred: `plantuml` CLI is not installed in the local sandbox environment.

3. Generate an optional narrated MP3 voiceover for `scripts/build_pitch_video.py --audio` using OpenAI TTS or a live mic recording — Priority 60% (Nice to have) [Best practices]
   What: Record a crisp 3-minute human voiceover (or generate a clean narration track) and pass `--audio narration.mp3` to `scripts/build_pitch_video.py` to mux studio-clean audio automatically.
   Why: Clear audio makes a bigger impression on hackathon judges than any visual effect, especially in a noisy Berlin venue.
   How: Record voiceover in a quiet corner (or via Audacity/OBS), then run `python3 scripts/build_pitch_video.py --audio data/narration.mp3`.
   Status: ⏳ Unimplemented
   Reason Deferred: Human narration synced to the live robot clip is best recorded once the bench clip is captured.

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
1. Show "REAL MOTION ON" on the console page — Priority 85% (High value) [Security]
   What: A red banner at the top of the console page whenever `.mcp.json` has `ELROBOT_ALLOW_MOTION` set to "1".
   Why: The switch is committed as "1" on the handover branch, so a teammate opening the console may not know that a chat message moves the real arm near a person.
   How: In `src/web_console.py`, read the switch with `load_mcp_server_config()` from `src/console_agent.py` and add it to the `/api/messages` reply; in `src/web/console.html`, show a red bar when it is on. Add one test in `tests/test_web_console.py`.
   Status: ⏳ Unimplemented
   Reason Deferred: Found during the 2026-11-22 handover check; documenting came first.

2. Load the Claude API key from a local `.env` file — Priority 60% (Nice to have) [Security]
   What: `./cli.sh console` reads `ANTHROPIC_API_KEY` from a gitignored `.env` file, with a committed `.env.example` that shows the name but no value.
   Why: Today the key must be typed with `export` in each terminal, which tempts people to paste it into scripts or docs that end up in git.
   How: `.gitignore` already ignores `.env` and allows `.env.example`. Add `.env.example` with `ANTHROPIC_API_KEY=`, and in the `console)` branch of `cli.sh` run `set -a; [ -f .env ] && . ./.env; set +a` before starting Python. Mention it in `docs/team_setup.md` step 8.
   Status: ⏳ Unimplemented
   Reason Deferred: Found during the 2026-11-22 handover check; no key is on this laptop yet to test with.

3. Save each console chat with its tool calls to `logs/` — Priority 45% (Nice to have) [Professionalism]
   What: Write every console conversation (what the person said, Claude's replies and each tool call with its result) to `logs/chat-<timestamp>.jsonl`.
   Why: When a run goes wrong in front of the judges or a teammate asks "what did Claude do?", there is no record after the page is closed; a log makes failures reproducible.
   How: In `ChatLog.add` in `src/web_console.py`, also append the message as one JSON line to a file opened at startup via the existing `src/elrobot_log.py` folder. `logs/` is already gitignored; note that logs can contain names (AGENTS.md privacy).
   Status: ⏳ Unimplemented
   Reason Deferred: Found during the 2026-11-22 handover check.

1. Add a test that catches docs naming the wrong arm or camera port — Priority 72% (High value) [Best practices]
   What: A small offline test that reads `config/elrobot.json` and fails if a doc names a different follower bus serial or camera USB port as the current one.
   Why: The team plan still named the arm that is out for repair and old camera ports a day after they changed, and agents read that plan first; a wrong serial means commands go to the wrong arm or no arm.
   How: In `tests/`, load the config, take `station.bus` and the `port:` values, grep `docs/FEEDING_ASSISTANT_PLAN.md` and `docs/mcp_server.md` for lines marked as current state, and assert they match. Keep history sections out of the check.
   Status: ⏳ Unimplemented
   Reason Deferred: Found during the 2026-11-22 handover; fixing the stale text came first.

2. Protect `main` on GitHub: review and passing tests before merge — Priority 66% (Nice to have) [Security]
   What: Turn on GitHub branch protection so nobody can push straight to `main` or merge a PR without one review.
   Why: Four people and their agents push to the same repo; one accidental push to `main` (or a force-push) can wipe teammates' work right before the demo.
   How: GitHub → repository Settings → Branches → Add rule for `main`: require a pull request with 1 approval, block force pushes. If CI exists later, also require its check.
   Status: ⏳ Unimplemented
   Reason Deferred: Needs the repository owner's account; not something an agent should change.

3. A short handover checklist at the top of HANDOFF.md — Priority 50% (Nice to have) [Professionalism]
   What: Five tick boxes every person fills in before leaving: commits pushed, PR link, hardware owner updated, arm left in a safe pose, open blockers listed.
   Why: At this handover HANDOFF said "pushed to origin" while the last two commits were still only on the laptop; a checklist makes such gaps visible before the person walks away.
   How: Add the checklist block under the front matter of `.ai-sync/HANDOFF.md`, and one line in AGENTS.md "On Stop" asking to tick it; `git status -sb` shows "ahead N" when commits are unpushed.
   Status: ⏳ Unimplemented
   Reason Deferred: Process change for the whole team; propose it at the next checkpoint.

1. Confirm a grasp by lifting a little and watching the jaws — Priority 82% (High value) [Security]
   What: After closing, lift 1 cm and re-read the gripper; if the jaws kept closing, call it a miss instead of "holding".
   Why: A stall on the bowl or the table looks exactly like a grasp today, so the robot can carry "nothing" to a person and believe it is feeding them.
   How: In `scripts/calib.py` `_gripper_after`, after the squeeze, move the arm up 10 mm, read motor 8 again, and print "closed empty" if it moved more than ~30 steps past the stall value. Add an offline test with the fake gripper.
   Status: ⏳ Unimplemented
   Reason Deferred: Found at the end of the 2026-11-22 session (bowl grips); handover came first.

2. Refuse gripper commands when the MCP server's reading is old — Priority 74% (High value) [Security]
   What: Have `set_gripper` and `get_robot_state` check how old the motor reading is and refuse (with a "reconnect /mcp" hint) when it is frozen.
   Why: A frozen reading made the gripper squeeze 11x harder than set and split a grape; the same could hurt a fingertip during a handover.
   How: In `src/robot_tools.py`, compare the reading's timestamp (or two reads a moment apart while a motor is moving) and return ok=false with a clear message when it is stale. Test it with a fake reader that never changes.
   Status: ⏳ Unimplemented
   Reason Deferred: Workaround exists (`calib goto --close-after` reads fresh); needs a look at how the Station frames carry time.

3. Store the bowl (and other fixed places) as named table points — Priority 48% (Nice to have) [Best practices]
   What: Keep `places: {"bowl": [365, 28, 130]}` in `config/elrobot.json` and let `calib goto bowl` use it.
   Why: The drop then needs no camera step and no pixel guessing, which makes it faster and the same every time; the camera is only needed when the bowl was moved.
   How: Add the `places` block, accept a place name instead of X Y Z in `calib goto`, and update `drop-in-bowl` to try the stored place first and re-measure with `calib pixel` only if the look shows the bowl elsewhere.
   Status: ⏳ Unimplemented
   Reason Deferred: The bowl was moved during the session; wait until its position on the table is fixed.

1. Hardware-owner check inside the motion commands — Priority 80% (High value) [Security]
   What: `calib goto`, `calib line` and `hw jog/goto` read `hardware_owner` from `.ai-sync/HANDOFF.md` and refuse to move unless `git config user.name` (or an `ELROBOT_OPERATOR` variable) matches it.
   Why: With several teammates and their agents on the same repo, the single-writer rule is only written down; a second agent could move the arm while the owner is working on it.
   How: Add a small `check_owner()` helper in `src/elrobot_config.py`, call it before the MOVE prompt, add an `--i-am-owner` override that is logged, and add an offline test for match/mismatch.
   Status: ⏳ Unimplemented
   Reason Deferred: Raised at the 2026-11-22 team handover; motion code needs the hardware owner's review.

2. One-command status report for a new teammate — Priority 62% (Nice to have) [Professionalism]
   What: `./cli.sh status` prints the branch and PR, hardware owner, follower bus in use, calibration date and fit error, and whether the Station and console are running.
   Why: A teammate's agent can see in five seconds which arm and calibration are live, instead of reading a long HANDOFF.md.
   How: Add a `status` case to `cli.sh` that calls a short Python script reading `config/elrobot.json`, `config/calibration.json` and the HANDOFF front matter, plus `gh pr list --head <branch>`; test the parsing offline.
   Status: ⏳ Unimplemented
   Reason Deferred: Raised at the 2026-11-22 team handover; docs-only session.

3. Short demo-day runbook — Priority 55% (Nice to have) [Professionalism]
   What: One page, `docs/demo_runbook.md`, with the exact commands in order from power-on to "grape in the bowl", and what to do when each step fails.
   Why: During the demo, whoever stands at the arm needs a checklist, not the history of every session.
   How: Copy the working commands from the three skills, add the start-up steps (Station, cameras, MCP reconnect) and the stop rule (12 V switch); rehearse it once and fix what was missing.
   Status: ⏳ Unimplemented
   Reason Deferred: Waits until the fingers-down grip works, so the runbook describes the final procedure.

1. Dry-run flag for `calib goto` — Priority 78% (High value) [Security]
   What: A `--check` flag that runs every path check and prints the plan, then exits without asking or moving.
   Why: Today the only way to test a path is to answer "no" at the MOVE prompt; one wrong keystroke or a `--yes` left in a command moves the arm.
   How: In `scripts/calib.py`, add `--check`; after planning, print the segments and `return 0` before the torque check and the prompt. Add a test that it never calls the motion code.
   Status: ⏳ Unimplemented
   Reason Deferred: Found during the 2026-11-22 grape hover; this session only added `--travel-z`.

2. Tag waypoints with the arm they were taught on — Priority 72% (High value) [Security]
   What: Store the follower bus serial with each waypoint and sequence, and refuse to play them on a different arm.
   Why: With the temporary arm, `clear` and the feeding waypoints would send raw step values from another arm to unchecked poses.
   How: In `config/waypoints.json` add a `"bus"` field per waypoint; in the waypoint and sequence code compare it with `station.bus` from `config/elrobot.json` and refuse on mismatch with a clear message.
   Status: ⏳ Unimplemented
   Reason Deferred: Needs the waypoint format change agreed with the team.

3. Per-motor overload thresholds measured per arm — Priority 55% (Nice to have) [Best practices]
   What: Record the normal current of each motor while moving, and set overload thresholds from it for the arm in use.
   Why: Motor 4 stopped a free move at 167 against a limit of 100; a limit that is too low stops good moves, one too high misses real collisions.
   How: Run a slow `calib goto` in free air, log the peak current per motor (`./cli.sh logs`), and set each threshold to about 1.5x that peak in a calibration commit.
   Status: ⏳ Unimplemented
   Reason Deferred: Needs a bench session with the hardware owner.

1. Show the grasp target on the camera picture before going down — Priority 74% (High value) [Security]
   What: Before `grab` descends, save the gripper-camera frame with the planned grasp point drawn on it and let the agent check it.
   Why: The descent is the riskiest table move; a wrong target (wrong grape, edge of the bowl) is caught before the fingers hit anything.
   How: In the grab procedure, after centring, call `look("gripper")`, draw a cross at the finger-centre pixel, and stop if the object is not under it.
   Status: ⏳ Unimplemented
   Reason Deferred: The finger-centre pixel is not measured yet.

2. Time each step of `grab` and `feed` — Priority 62% (Nice to have) [Best practices]
   What: Log how long each step takes (find, hover, centre, grasp, carry, approach, handover).
   Why: "Smooth" means no long pauses; the timings show which step to speed up instead of guessing.
   How: Print a timestamp at the start and end of each step in the skill run and add a one-line summary to the handoff after rehearsals.
   Status: ⏳ Unimplemented
   Reason Deferred: Skills not written yet.

3. Wait in a "ready" pose above the table middle between requests — Priority 45% (Nice to have) [Best practices]
   What: After `feed` returns, park the fingertip above the middle of the table instead of at `clear`.
   Why: Every next move starts closer to the food, so requests feel faster and paths are shorter.
   How: Pick a table point (e.g. x 250, y 120, z 150), check it with `calib reach`, and use it as the end of `feed` once the owner agrees.
   Status: ⏳ Unimplemented
   Reason Deferred: Needs the owner's OK on a new resting pose.

1. Give each skill a written "done when" test and run it before trusting the skill — Priority 84% (High value) [Best practices]
   What: For `grab` and `feed` in docs/feeding_skills.md, a short pass rule (e.g. "grab grape: 5 in a row, none crushed") recorded in FINDINGS.md with the run date.
   Why: A skill that worked once at 4 a.m. is not a demo skill. A clear pass rule tells the team which skills `feed-me` may rely on and which must fall back to the recorded plan.
   How: Copy the "Done when" column from the plan's task tables into each skill file; after each bench run, add one FINDINGS.md line with the result and the log path.
   Status: ⏳ Unimplemented
   Reason Deferred: Skills other than hover are not written yet.

2. Keep a one-page "autonomy register" of what the agent may do without asking — Priority 78% (High value) [Security]
   What: One table (for example in GUIDELINES.md) listing each skill, whether it may run without confirmation, who allowed it and when.
   Why: Standing permissions are spread over skill files and chat. One register makes it obvious when a skill near the person's face is running without a human OK, and makes it easy to revoke.
   How: Add a table with columns skill / auto or ask / given by / date / limits; link it from every SKILL.md; change it only in its own commit by the hardware owner.
   Status: ⏳ Unimplemented
   Reason Deferred: Only one skill has a standing OK today.

3. Record a short video of every skill's first good bench run — Priority 45% (Nice to have) [Professionalism]
   What: A phone or screen recording of each skill working on the arm, kept outside git, listed by date in HANDOFF.md.
   Why: If something breaks on Sunday, the team still has proof each piece worked for the pitch, and the video shows exactly how the arm moved if a skill later behaves differently.
   How: Start a recording before each first live run, save it to the shared drive (not the repo; faces must be cropped or consented), and note the file name in the handoff entry.
   Status: ⏳ Unimplemented
   Reason Deferred: Demo recording is owned by role D and starts once skills run end to end.

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
