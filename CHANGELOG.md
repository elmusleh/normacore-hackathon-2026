# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- README and `docs/README.md`: replaced the submission-asset table with a Demo & Presentation section (YouTube demo video, final PDF deck), added a demo-status note and labelled the use-case images as illustrations.
- Moved the draft decks, story script and submission checklist from `docs/pitch/` to `docs/archive/pitch-drafts/`; generator scripts now write there.
- Added `docs/pitch/CareArm_Presentation.pdf`: final 9-slide hackathon presentation.
- Repository renamed from `normacore-hackathon-2026` to `carearm-feeding-robot` (2026-11-25); updated clone URLs, repo links and video footers in docs, prompts and scripts. Old GitHub URLs redirect.
- `FINDINGS.md`/`HANDOFF.md`: first hover on `5B61034962` (within 3 mm by joint readings, grape centred in the gripper camera) and the person-camera numbering problem.
- `config/elrobot.json`: camera exposure table 250 -> 20, gripper 250 -> 50 (`./cli.sh cameras --tune`, daylight 2026-11-22). At 250 the table camera was 71% pure white and the grape was invisible.
- `FINDINGS.md`/`HANDOFF.md`: gripper direction (`open_at: "max"`) verified on follower `5B61034962`; calibration position check on tag 1 within 1.5 cm.
- `config/calibration.json`: joint zeros and arm base re-measured on follower `5B61034962` (upright L zero pose + 8 AprilTag touches; fit 16.4 mm RMS, base yaw 177.7°). Replaces the values taken on the temporary arm.
- `config/elrobot.json`: follower bus back to `5B61034962` (the usual arm is back from repair; the temporary arm `5B61034679` from `049a4fe` is no longer on the bench). Confirmed by the hardware owner 2026-11-22.

### Added
- `./cli.sh setup-vision`: installs MediaPipe into `.venv`, downloads `data/face_landmarker.task` and `data/efficientdet_lite0.tflite`, then runs `scripts/vision_check.py`.
- `scripts/station_config.py`: `./cli.sh station` and `./cli.sh start` add the HD camera `formats` list and `resize_target: 1080` to a local `station.yaml` that has none (backup `station.yaml.bak`; opt out with `ELROBOT_KEEP_STATION_YAML=1`).
- `scripts/vision_check.py` and `feeding_vision.mediapipe_status()`; a one-time warning when MediaPipe face detection is unavailable.

### Fixed
- `./cli.sh cameras --tune <name>` now tunes the port that is plugged in when the config lists several ports for one camera (one per laptop); before, it only tried the last listed port and failed with "not configured or not plugged in".
- Every `./cli.sh` Python command (including `hw`, `calib`, `cameras`, `feed`) now runs with `.venv/bin/python` when it exists.
- OpenCV Haar and skin-tone mouth guesses are marked `fallback`, so the dashboard, web console and MCP mouth check never show or trust a mouth MediaPipe did not find.
- `requirements.txt` now lists `mediapipe` and `pyyaml`; setup docs cover the venv, models, HD frames, and camera/bus troubleshooting.
- `./cli.sh start` and `./cli.sh digital-twin` now run the dashboard with `.venv/bin/python` (falling back to `python3`), like `console` and `mcp`. Under plain `python3` MediaPipe is missing, so the person camera fell back to the OpenCV Haar detector and drew a false "MOUTH closed" box on an empty scene.

### Changed
- Polished repository structure for hackathon submission: organized `docs/` into `docs/pitch/`, `docs/diagrams/`, `docs/assets/`, active engineering guides, and `docs/archive/` with a `docs/README.md` index; upgraded `README.md` with embedded architecture/flow PNGs, use-case illustrations, badges, and AprilTag IK coverage; added `.env.example` and MIT `LICENSE`; untracked personal `archive/` exports and root `sample_calibrated_view.png` in `.gitignore`.
- Updated `README.md` to reflect Team 6 (**CareArm — Assistive Feeding Robot**), its 4-layer architecture, 3-camera MediaPipe vision, 15 MCP tools, 3-layer guardrails, verified benchmarks (123/123 tests), `./cli.sh` reference, and Team 6 roster.
- Added Team 6 (`CareArm`) and all 3 team member names (Jan Schulz, Jafer Sharfeddin, Mohammad El-Musleh) to Slides 1 and 10 of `scripts/generate_pitch_deck.py` and regenerated `docs/Assistive_Feeding_Robot_Pitch.pptx`.
- Recorded 6 verified 2026-11-22 hardware, camera, MediaPipe MAR, gravity-settle, torque-readback, and test-suite findings at the top of `FINDINGS.md`.
- `config/elrobot.json`: `table` and `gripper` camera names swapped (table = port 3-5.2.2, gripper = port 3-5.2.4). The old mapping showed the gripper view as `table`; confirmed by the user 2026-11-21.
- `.mcp.json`: `ELROBOT_ALLOW_MOTION` set to `"1"`, so Claude's MCP tools move the real arm (was dry-run).

### Fixed
- Tightened Hands-Free voice `STOP_RE` in `src/web/console.html` to anchor explicit stop commands (`stop|stopp|halt|freeze` only, removing `wait`) and tag voice stops in `POST /api/stop` so normal sentences containing `"wait"` never falsely trigger `Stop (button)`.
- Served local `v4l2:*` cameras (such as OBSBOT `person: "v4l2:2"`) directly in `src/web_console.py` (`GET /api/frame/{camera}`) without requiring Station to be running, sharing the V4L2 handle with `GET /api/mouth_status` and releasing cleanly whenever the agent is busy.
- `.ai-sync/HANDOFF.md`: handover check entry with a warning that real motion is on in `.mcp.json` on this branch; `SUGGESTIONS.md`: 3 new suggestions.
- `docs/team_setup.md`: new step 8 for the web console (API key, speech model download, motion switch, stop); test count updated to 144.
- `docs/FEEDING_ASSISTANT_PLAN.md`: current-state section and movement design updated to the 2026-11-22 handover (temporary arm, new camera ports, calib goto IK, what works and what is blocked); HANDOFF.md named as the live source of truth.
- Docs: `docs/tcp_calibration.md` lists the new `calib goto/line` options, defaults and the sag note; `docs/feeding_skills.md` status and autonomy updated for `grip-object` / `drop-in-bowl`; `calib` usage text updated.
- FINDINGS: bowl grip failure, `--down` refusals (wrist zeros), stale MCP readings, reach-dependent sag. PREFERENCES: Jafer's fast arm pace. SUGGESTIONS: 3 new (2026-11-22 handover).
- Team handover docs: HANDOFF "START HERE" summary (branch, temporary arm, calibration, what works/fails, ordered next steps), PROGRESS brought up to date, GUIDELINES §6 grasp rules and per-owner standing permissions, plan status line (2026-11-22).
- `config/calibration.json`: joint zeros re-captured and the base-in-table fit redone from 8 AprilTag touches (rms 16.0 -> 15.55 mm, base z -36.9 -> -20.2 mm), measured 2026-11-22.
- `config/elrobot.json`: gripper motor 8 current threshold set to 100 and the `agent` motion limits written out explicitly (same values as the code defaults); keys reordered by the config writer, 2026-11-22.
- `grip-object`: grasps only with the fingers vertical down (`--down`), no angled fallback (Jafer, 2026-11-22).
- HANDOFF and `grip-object`: grip from the bowl failed 3 times (jaw tips stall on the curved bowl; false "holding"), 2026-11-22.
- `calib goto` gets `--open-after` / `--close-after` (gripper on the same Station connection; close stops at the stall and keeps `squeeze_steps` from a fresh reading) and a faster default speed (25 -> 60 mm/s). New skill `drop-in-bowl`; `grip-object` rewritten to fewer, faster calls. Grape dropped into the bowl at 70 mm/s (2026-11-22). Tests added.
- Gripper hold squeeze `squeeze_steps` 10 -> 57: Jafer asked for half the grip actually applied (~115 steps, caused by a stale MCP reading). `grip-object` skill notes how to spot the stale reading (2026-11-22).
- `grip-object` skill: notes on the along-finger offset and on commanding ~25 mm when the arm sags (left grape gripped first try, 2026-11-22).
- New skill `.claude/skills/grip-object/SKILL.md` ("grip <object>"): hover, open, two-stage descent with `--min-z 0`, close, check with the gripper camera, lift; retries allowed (up to 3). From the first grape grasp, 2026-11-22.
- `calib goto` / `calib line` take `--min-z MM` (0-50, default 50) to lower the safety floor for a grasp; the fit error is still added and a warning is printed. First grape grasp on the temporary arm used it (2026-11-22). Test added.
- Gripper direction verified on the temporary arm (`config/elrobot.json` gripper `verified: true`); FINDINGS entry added (2026-11-22).
- `calib goto` / `calib line` speed cap raised from 60 to 70 mm/s (Jafer asked for 70 mm/s, 2026-11-22). Grape hovers ran at 45 and 70 mm/s on the temporary arm with no overload; overload stop unchanged.
- HANDOFF: right grape hover reached on the temporary arm with `--travel-z 90 --mm-per-s 15` (2026-11-22).
- `calib goto` / `calib line` take `--travel-z MM` (default 150, 50-250) to travel sideways lower. The planner never travels below the safety floor (50 mm + fit error) or the target height. Added because the 150 mm lift pushed motor 2 past its range on the temporary arm. Test added.
- Follower bus switched to the temporary arm `5B61034679` in `config/elrobot.json` and `.mcp.json` (2026-11-22, Jafer): the usual follower `5B61034962` is out for a motor repair. Switch both back when it returns. `config/calibration.json` must be redone for each arm (joint zeros and touches are per arm).

### Added
- `docs/feeding_skills.md`: two skills to feed a person, `grab <object>` and `feed <object>` (feed grabs first if needed), with their steps, the missing pieces per step and the autonomy rule. Replaces the 17-skill list written earlier the same day. Docs only.
- Project skill `.claude/skills/hover-above-object/SKILL.md`: the fixed procedure for "move above <object>" (table camera look -> `calib pixel` -> `calib reach` -> `calib goto X Y 70 --yes` -> look again). Jafer (hardware owner) authorised it to run without asking each time on 2026-11-22, for hover moves only; grasping, lower moves and gripper commands still need typed confirmation.

### Changed
- `calib goto` and `calib line` move smoothly: the whole move (lift, across, descend, line) is planned as straight segments with a point every 3 mm (`plan_cartesian_path`) and streamed at a steady fingertip speed (`--mm-per-s`, default 25, max 60) with `move_motors`, instead of stopping at each point (Jafer saw the line stutter). Watched on every point: overload, fault, motor > 200 steps behind -> hold. `--speed` replaced by `--mm-per-s`. With `--down` the wrist turns once above the target.

### Added
- `./cli.sh calib line X1 Y1 Z1 X2 Y2 Z2 [--step-mm 10] [--down] [--speed N] [--yes]`: goes to the start like `calib goto`, then follows a straight line point by point (`plan_cartesian_line` in `src/arm_kinematics.py`). All points are planned and checked before the MOVE prompt (height, reach, ranges, no motor jump > 200 steps between neighbours). Not yet run on the arm. Dry plan on live readings: (128,114,120)->(328,114,120) plans; lines toward the arm hit motor 2's range.
- `./cli.sh calib goto X Y Z [--down] [--speed N] [--yes]`: moves the fingertip to a table point. Plans lift -> across at 150 mm -> descend (`plan_cartesian_goto` in `src/arm_kinematics.py`), shows the plan, asks for MOVE, then drives each leg with the `hw goto` machinery (torque check, speed cap 800, overload watch). Refuses without a measured calibration, below 50 mm + fit error, when out of reach (> 5 mm) or when any goal leaves a motor's range (no clamping). Not yet run on the arm.

### Fixed
- `calib goto` stopped with `timeout` on its first live run: motors 2-4 settled 18-48 steps short of the lift pose under gravity. It now accepts a joint that stopped within 60 steps without overload (`near`, same rule as the sequence player) and prints how far short each joint settled.
- `calib fit --refine` with too few touches prints a short error instead of a Python traceback.
- `calib reach` with real motor ranges: motor readings wrap from 4095 to 0 and the ranges cross that point (e.g. 3726..1565). Step <-> radian conversion now wraps (`wrap_steps`), `to_steps` returns 0..4095, the range check and step change handle wrapping ranges (`step_in_range`, `step_delta`), and the IK limits use the real ranges (they were skipped before because min > max). Before the fix every motor showed OUT OF RANGE with wrong step changes.

### Added
- Tag layout recorded in `config/calibration.json` (2026-11-22, Jafer): tag centres 456 x 228 mm (6 x 3 sticky notes, assumed 76 mm each; no tape measure), tag size 45 mm (printed size, not measured). Diagonals should both be ~510 mm. Corrected the same day to each tag's real place (tag 2 front-left origin, 1 front-right, 3 back-right, 0 back-left; the person sits on the table-camera side, the arm at the back) and saved the table-camera fit (2.4 mm RMS on the tag squares).
- AprilTag table frame and TCP kinematics, reads only (`./cli.sh calib`, `scripts/calib.py`, runbook `docs/tcp_calibration.md`). `src/tag_calibration.py` detects 36h11 tags 0-3 (OpenCV aruco, upscales the Station's small frames), fits the pixel -> table-mm homography from tape-measured tag centres, checks it against the printed tag size, warns on a mirrored layout and draws a grid overlay into `data/calibration/`. `src/arm_kinematics.py` parses the follower URDF (motors 1-7) for forward kinematics, damped least squares IK with retries and an optional fingers-down constraint, steps <-> radians per motor, the arm base pose in the table frame from fingertip touches (2D Kabsch + z offset), and a fit of motor 2-4 zeros and motor 1-4 directions. Calibration lives in `config/calibration.json`. `calib reach` prints the joint steps for a table point; nothing moves the arm yet. The tag sheet now places tag 0 front-left, 1 front-right, 2 back-right, 3 back-left (seen from the person), so the table frame is right-handed with z up. Tests: `tests/test_calibration.py`.
- Camera picture enhancement for food detection (`src/frame_enhance.py`): `look()` (MCP tool and console tiles) now denoises, white-balances against the table, applies auto gamma, CLAHE local contrast and light sharpening (~9 ms per 299x224 frame). Settings in `config/elrobot.json` → `camera_enhance` (defaults in `src/elrobot_config.py`, per-camera overrides). `look(raw=True)` / `/frame/<cam>?raw=1` return the untouched frame. Each look reports `exposure` (mean, pure-white and black share) and an `exposure_warning` when the camera is over- or underexposed. ACT demo recordings stay raw.
- `./cli.sh cameras --tune [name] [--write]`: sweeps exposure on a camera (Station stopped), measures each picture and recommends (or saves) the best exposure. `camera_settings.<name>.controls` applies any other V4L2 control (gain, white balance, backlight compensation); controls a camera lacks are skipped.
- Camera ports in `config/elrobot.json` moved to `3-1.x` after the USB hub was replugged into another laptop port (table 3-1.2.2, gripper 3-1.2.4, face 3-1.3).
- Third camera in the console: `face` (OBSBOT Meet SE on USB port 3-5.3, points at the person being fed) in `config/elrobot.json` → `cameras`. The console page shows table across the top with gripper and face below. The console prompts tell Claude `look("face")` shows the person. `scripts/99-normacore-cameras.rules` now also covers the OBSBOT (3564:fefe) so the Station can capture it; it needs reinstalling with sudo.
- Teleop demonstration recorder for ACT: `./cli.sh demos record --skill pick --food grape` / `demos list` (`scripts/record_demos.py`, `src/demo_recorder.py`). Stores follower position (state), follower goal register (action), leader position and table/gripper camera frames at 30 per second in `data/demos/`; reads only. Runbook `docs/act_pick_skill.md`. `RobotTools.camera_queue()` split out of `look()`. `.venv-*/` gitignored (LeRobot goes in `.venv-lerobot`).
- `hw envelope record` skips samples where a motor reads outside its calibrated range (a read glitch put motor 2 = 0 into the first recording).
- `config/envelope.json`: first action space, 1027 follower poses and 8 anchors, recorded with the leader arm 2026-11-21.
- Action space recorded with the leader arm: `./cli.sh hw envelope record` samples the follower while a person drives it with teleop and marks named anchors (`config/envelope.json`, `src/action_space.py`). `nudge_joint` refuses nudges that would leave the recorded space (margin `agent.envelope_margin_steps`, 80 steps) unless they move back toward it; stepwise console mode requires a recording. New MCP tool `get_action_space` gives Claude the recorded ranges, anchors and the nudges that reach them.
- Console stepwise mode (`./cli.sh console [port] --mode stepwise`, env `WEB_CONSOLE_MODE`): the person names a food and Claude steers the arm tick by tick (look, small `nudge_joint`, look) with no waypoints or recorded plans. Only six tools are exposed in this mode, up to 150 rounds per request. `./cli.sh console` now passes extra arguments to `src/web_console.py`.

### Changed
- `config/elrobot.json`: `table` and `gripper` camera names swapped (table = port 3-5.2.2, gripper = port 3-5.2.4). The old mapping showed the gripper view as `table`; confirmed by the user 2026-11-21.
- `.mcp.json`: `ELROBOT_ALLOW_MOTION` set to `"1"`, so Claude's MCP tools move the real arm (was dry-run).

### Changed
- Camera exposure in `config/elrobot.json` → `camera_settings`: table 160 → 250, gripper 14 → 250 (set by Jafer 2026-11-22 after the live view was too bright on auto and nearly black at 14). Apply with `./cli.sh cameras` while the Station is stopped.
- Camera ports in `config/elrobot.json` back on the `3-5` hub port: table `3-5.1`, gripper `3-5.2.4`, face `3-5.3` (checked from frames 2026-11-22; the gripper camera was stuck at manual exposure 14, which made its view nearly black).

### Removed
- Software picture enhancement in `look()` (`src/frame_enhance.py`: denoise, white balance, auto gamma, CLAHE, sharpen). `look()` (MCP tool, console tiles, `calib camera`) again returns the camera's own JPEG, unchanged. Gone with it: the `camera_enhance` config defaults, `look(raw=...)`, the console's `/frame/<cam>?raw=1`, and the `exposure` / `exposure_warning` fields of `look()`. `./cli.sh cameras --tune` still measures exposure; `exposure_stats` moved into `scripts/camera_settings.py`. Tests: `tests/test_frame_enhance.py` -> `tests/test_camera_settings.py` (tuning helpers only).

### Fixed
- Console and MCP `look()` treated a live camera as unplugged when the Station returned nothing for the first entry of its queue (seen for the gripper and face cameras after a Station restart), and cached that answer for good. `RobotTools` now falls back to the newest entry, which also names the camera, and retries an undescribed queue every 10 s instead of never. Test: `test_camera_found_when_first_entry_is_unreadable`.
- `./cli.sh cameras --tune --write` said nothing when a camera failed and the save was skipped, so it looked saved. It now prints `NOT saved` and how to tune only the working camera.
- `scripts/generate_apriltags.py` (`./cli.sh apriltags`) printed hand-typed patterns that are not AprilTags (8x8 inner grid; real 36h11 is 6x6), so no detector could read them. This includes `docs/NormaCore Hackathon - 4-Corner AprilTags.pdf`. The generator now takes the bits from OpenCV's 36h11 dictionary, defaults to an 80 mm black square (`--size-mm`) so tags stay readable in the Station's 299x224 frames, and keeps a white margin. The old printed sheet still works: `detect_tags` also reads its patterns as the custom family `printed-v1` (needs 480 px Station frames at 45 mm). One tag per row, two per A4 page (80 mm tags do not fit two across). Test: `tests/test_apriltags.py`.
- Leader/follower serial roles were swapped in `scripts/teleop_sync.py` (it drove the leader arm by default), `src/digital_twin_server.py`, `src/digital_twin.html`, `scripts/camera_feed_arm.py` and `docs/team_setup.md`. Confirmed on the arm 2026-11-21: follower `5B61034962`, leader `5B61037051`.

### Added
- Wrote the CareArm 9-scene production story script ("Marta's Dinner") in `docs/CAREARM_STORY_SCRIPT.md` and built a narrated 1080p story film generator (`scripts/build_story_film.py`) using OpenAI `tts-1-hd` (`nova`) voiceover, Ken Burns motion, architecture diagram reveal, subtle ambient pad, and smooth crossfades (`data/carearm_story_film_1080p.mp4`, gitignored).
- Rendered high-DPI PNG & PDF architecture diagrams (`docs/diagrams/carearm_overview.png/.pdf`, `docs/diagrams/carearm_feeding_sequence.png/.pdf` via `scripts/render_architecture_diagrams.py`), generated 6 bespoke editorial use-case illustrations (`docs/assets/scene_01_need.png`..`scene_06_carehome.png`), and built a cinematic 1080p Ken Burns + crossfade illustrated story video generator (`scripts/build_illustrated_video.py` -> `data/carearm_use_case_story_1080p.mp4`).
- Added PlantUML system overview (`docs/diagrams/carearm_overview.puml`) and end-to-end feeding & E-stop sequence (`docs/diagrams/carearm_feeding_sequence.puml`) diagrams, plus a local 1080p MP4 slide-video builder (`scripts/build_pitch_video.py`).
- Created a 9-slide use-case & human-impact presentation deck (`docs/CareArm_Use_Case_Pitch.pptx`) with embedded speaker notes and its generator (`scripts/generate_use_case_deck.py`), focusing on target personas, daily mealtime transformation, 4-scene diner storyboard, patient trust & face-proximity comfort, home/rehab/elder-care settings, and 10× cost/accessibility advantage.
- Completed ready-to-submit Tally form inputs (Team 6 details, members, project summary, Drive video folder, Google Slides link, GitHub repo, Normacore track, and pre-submission checklist) in `docs/Hackathon_submission_requirements.md`.
- Generated a 10-slide widescreen final pitch deck (`docs/Assistive_Feeding_Robot_Pitch.pptx`) with embedded presenter notes and its reproducible Python generator (`scripts/generate_pitch_deck.py`), covering the problem, 5-step user flow, decoupled 4-layer architecture, 3-camera vision + MediaPipe mouth-open gate, 3-layer AI guardrails + hardware safety, multi-tab Web Console, verified benchmarks, and roadmap.
- Implemented Gripper Camera Stages 0, 1A, and 2A (offline-ready): added `FeedingVisionDetector.analyze_gripper_roi()` + live `gripper` crosshair/jaw-zone overlay in `src/web_console.py`, partial `play_sequence(name, start_at, stop_after)` + `grasp` config validation in `src/robot_tools.py`, bounded `align_base(delta_percent)` MCP tool in `src/robot_mcp_server.py`, Stage 1–2 grasp instructions in `src/console_agent.py`, and unit tests in `tests/test_robot_mcp.py`.
- Documented the 5-stage gripper (eye-in-hand) camera roadmap (Stage 0 demo baseline through Stage 4 clinical robotics) and concrete Stage 0–2 execution plan in `docs/GRIPPER_CAMERA_ROADMAP.md`.
- Added 2-layer chatbot scope guardrails (`classify_intent()` pre-LLM gatekeeper + `<user_voice_transcript>` XML delimiter isolation + `# Scope & Guardrails` prompt rules) and a live Developer Action Trace (`GET /api/trace`, `POST /api/trace/clear`) with a 3-tab UI (`Demo Console`, `Developer Trace`, `Commands & Guardrails`) and `Dev Log in Chat: OFF/ON` toggle in `src/console_agent.py`, `src/web_console.py`, `src/web/console.html`, and `docs/GUARDRAILS_AND_TRACE.md`.
- Applied live MediaPipe vision detection overlays (`FeedingVisionDetector`: lip landmarks + MAR + `MOUTH OPEN!/closed` on `person`; bowl + food-piece boxes on `table`) directly to `GET /api/frame/{camera}` in `src/web_console.py` (`http://localhost:8890`), matching Mission Control (`./cli.sh start`).
- Added live OBSBOT mouth-status badge (`Mouth: Open / Closed / No Face`), amber waiting-for-mouth banner + spoken TTS cue (`GET /api/mouth_status` + `data/mouth_gate_state.json` zero-contention handoff), and clamped `feeding_vision.mouth_gate_timeout_s` (`[3.0, 30.0]s`) in `src/robot_tools.py`, `src/web_console.py`, and `src/web/console.html`.
- Connected live OBSBOT MediaPipe `mouth_open_confirmed` safety gate into `src/sequence_player.py`, `src/robot_tools.py`, and `src/robot_mcp_server.py` (`check_person_mouth` + `set_mouth_gate` MCP tools), with an enable/disable toggle (`Wait for Mouth-Open (OBSBOT)`) in `src/web/console.html` (`GET/POST /api/mouth_gate`).
- Added gentle Web Audio chimes (start listening, command sent, stop) to Hands-Free Mode in `src/web/console.html` for eyes-free accessibility feedback.
- Updated `AGENTS.md` to remove mandatory post-commit remote push prompting (push only when explicitly requested).
- Hardware-muted the hands-free microphone track (`track.enabled = false`) and aborted any active VAD recording whenever TTS starts playing in `src/web/console.html`, re-enabling STT only 700 ms after TTS playback finishes.
- Hardened Hands-Free Voice Loop UX in `src/web/console.html`: added color-coded state badge (`STANDBY` / `RECORDING` / `THINKING` / `SPEAKING`) + live mic volume meter, raised VAD noise floor (`0.045`) + min speech filter (`400ms`), paused mic while Claude is busy or speaking, and enforced strict `"Robo"` wake-word gating to prevent runaway messages from background noise.
- Added Hands-Free Voice Loop (`Hands-Free (Auto-Listen)` + `Wake word ("Robo")`) in `src/web/console.html`: continuous Web Audio VAD detects speech start and auto-sends after 1.1 s silence, triggers immediate `POST /api/stop` on `"stop"/"halt"/"wait"` without wake word, pauses mic automatically during TTS playback to prevent echo loops, and keeps a 12 s follow-up window after each robot reply.
- Added server-side `POST /api/tts` endpoint in `src/web_console.py` (OpenAI `tts-1` voice `nova` MP3 with offline `espeak-ng` WAV fallback) so TTS works reliably on Linux browsers without system browser voices, plus `localStorage` persistence for `autosend` and `tts` checkboxes in `src/web/console.html`.
- Fixed `src/console_agent.py` compatibility with standard `anthropic` SDK versions (falls back from `beta.messages.create(..., fallbacks=...)` to `messages.create(...)` on `TypeError`).
- Fixed `src/speech.py` compatibility with OpenAI Python SDK 2.x (automatically falls back from `languages`/`keywords` to `gpt-4o-mini-transcribe` with `prompt` when `TypeError` is raised).
- Added browser Text-to-Speech (`Speak replies (TTS)` toggle + `Test Voice` button) in `src/web/console.html` and refined `CONSOLE_PROMPT` in `src/console_agent.py` for natural spoken feeding guidance (including `grapes` and `chocolate`).
- Improved tabletop bowl & food-piece stability (`src/feeding_vision.py`): added specular-glare rejection, thin-sliver circularity/aspect filtering, distance-transform peak splitting for touching grapes, and EMA temporal smoothing on the bowl bounding box.
- Upgraded Table Cam detection (`src/feeding_vision.py`, `src/digital_twin_server.py`) with a tabletop colored-bowl + LAB chroma-contrast food-piece detector combined with MediaPipe `ObjectDetector`: locks reliably onto overhead colored bowls and highlights every grape/chocolate piece inside while ignoring ceramic glare.
- Fixed V4L2 camera opening in `src/digital_twin_server.py` to use explicit `/dev/video{idx}` device paths with `cv2.CAP_V4L2`, fixing OpenCV 5.x index-gap failures and unlocking full 1280×720 HD MJPG capture on the NormaCore KD-USB and OBSBOT cameras.
- Enabled 1280×720 MJPG HD capture for V4L2 cameras (OBSBOT Meet SE) and raised JPEG streaming quality to 90 in `src/digital_twin_server.py`.
- Upgraded Table Cam detection to MediaPipe `ObjectDetector` (`efficientdet_lite0.tflite`) in `src/feeding_vision.py` and `src/digital_twin_server.py`: detects real bowls, spoons, cups, and food items with zero false positives on red robot servo wires, and highlights individual food pieces (grapes/chocolate) inside detected bowls.
- Added per-user live Mouth & Distance Calibration in Mission Control (`src/digital_twin.html`, `src/digital_twin_server.py`, `src/feeding_vision.py`): 1-click **1. Capture Closed**, **2. Capture Open**, **Set Eating Distance**, **Reset Defaults**, and manual `MAR`/`Standoff px` inputs persisted to `config/elrobot.json` (`feeding_vision`).
- Tuned `MAR_OPEN_THRESHOLD` to `0.26` from live OBSBOT bench testing (closed `0.00–0.02`, open `0.30–0.50`) and prevented `detect_mouth()` in `src/feeding_vision.py` from falling through to noisy OpenCV skin-tone heuristics when MediaPipe `FaceLandmarker` is active and sees no face (eliminates false yellow box on windows/background and ensures clean face-loss watchdog behavior).
- Implemented MediaPipe `FaceLandmarker` lip-landmark mouth tracking (`MouthStateTracker` with MAR, EMA smoothing, 3-frame mouth-open debounce, and 0.5 s face-loss watchdog) and deterministic `FeedingSafetyFSM` in `src/feeding_vision.py`, wired live MAR/lip overlays into Mission Control (`src/digital_twin_server.py`), documented the plan in `docs/FEEDING_FSM_MEDIAPIPE_PLAN.md`, and added unit tests in `tests/test_pipeline.py`.
- Added readback verification and automatic retries (up to 4×) to `ElRobotHardware.set_torque` (`src/elrobot_hardware.py`) so `./cli.sh hw stop` and `torque off` never leave individual ST3215 motors stuck ON if a broadcast sync-write packet is dropped.
- Fixed `hw_day.py` bus selection in `scripts/reset_bench.py` and `src/digital_twin_server.py` to pass `ELROBOT_BUS` via environment variable instead of a pre-subcommand `--bus` flag.
- Wired `./cli.sh reset` (zero-arg quick bench reset: relaxes leader torque when Station is running or applies manual camera exposure when stopped), replaced Mission Control's Swap button with a safe **Refresh Bench** button (`src/digital_twin.html`, `scripts/reset_bench.py`, `cli.sh`), and included `./cli.sh check` (`scripts/system_health.py`).
- Added team bench recovery & Master/Slave role manager (`scripts/reset_bench.py`) and one-click **Relax Leader (Torque Off)** + **Swap Master / Slave** buttons in Mission Control (`src/digital_twin_server.py`, `src/digital_twin.html`) with live config-driven header serials.
- Fixed inverted Master/Slave defaults in `scripts/teleop_sync.py` to load `leader_bus` (`5B61037051`) and follower `bus` (`5B61034962`) from `config/elrobot.json`, and enforced explicit `torque OFF` on the Leader arm before every teleop session (`scripts/teleop_sync.py`, `src/digital_twin_server.py`).
- Raised `usb-video.resize_target` in `station.yaml` from `224` to `480` for clearer Station camera frames.
- Stacked dual camera layout (`Table Cam` above `Person Cam`) and one-click **Save Default** button in Mission Control (`src/digital_twin.html`, `src/digital_twin_server.py`) that persists the selected camera mappings into `config/elrobot.json`.
- Replaced the offline Three.js `<canvas>` mockup in Mission Control (`src/digital_twin.html`) with full-size dual live camera views (`Table Cam` + `Person Cam`), saved waypoint badges from `config/waypoints.json`, and clean role-specific real detections only (removed fake fallback `BOWL`/`SPOON`/`MOUTH` placeholder overlays in `src/digital_twin_server.py`).
- Confirmed hardware config in `config/elrobot.json` (follower bus `5B61034962`, `table` = `port:3-1.2.2`, `gripper` = `port:3-1.2.4`, `person` = `v4l2:6`) and config-backed default camera selection in `CameraHub` (`src/digital_twin_server.py`).
- Dual live camera discovery and dropdown selection (`Table Cam` + `Person Cam`) in Mission Control (`src/digital_twin_server.py`, `src/digital_twin.html`): automatically discovers both NormaCore Station `usbvideo/*` queues and local `/dev/video*` V4L2 cameras, renders side-by-side annotated feeds with `FeedingVisionDetector` overlays, and streams live detection changes to the event log.
- Explicit policy for AI agents to commit after each implementation and proactively prompt developers to push branches to remote (`AGENTS.md`, `GUIDELINES.md`).
- MCP tools `list_sequences` and `play_sequence(name)`: Claude maps a food request ("I want grapes") to a recorded plan via the `foods` config and runs it in one call. `stop` now skips the tool lock and interrupts a running plan. MCP instructions and the console prompt say recorded plans come first.
- Waypoint sequences: `./cli.sh hw record <seq>` (interactive, moves nothing, saves each pose as a waypoint and the order to `config/sequences.json`), `./cli.sh hw play <seq|wp...>` (plans every leg, one `MOVE` prompt, waits until the arm stops at each waypoint, `--pause`, `--tolerance`) and `./cli.sh hw sequences`. Shared player logic in `src/sequence_player.py`; `load_sequences`/`save_sequences` in `src/elrobot_config.py`.
- `move_and_watch(near_tolerance=..., stall_s=0.8)` in `src/elrobot_hardware.py`: a motor that has stopped within `near_tolerance` of its goal without overload is reported as `near` instead of waiting for the timeout (loaded joints sag 20-35 steps under gravity).
- Camera-guided assistive feeding pipeline (`src/feeding_vision.py`, `scripts/camera_feed_arm.py`, and `./cli.sh feed [grapes|spoon]`): uses the overhead tabletop camera (`/dev/video4` with automatic Station/mock fallback) to detect the grape bowl, spoon holder, and person's mouth, and plans/executes safe slave arm motions stopping at a 5–10 cm facial standoff.
- Mission Control Web Dashboard (`src/digital_twin.html` & `src/digital_twin_server.py`) integration for one-click `Feed Grapes (Bowl -> Mouth)` and `Feed with Spoon (Scoop -> Mouth)` actions with live annotated camera overlays.
- Unit tests for `FeedingVisionDetector` and `run_camera_feeding_cycle` in `tests/test_pipeline.py`.
- Real MCP server for the physical arm, `src/robot_mcp_server.py` (mcp 2.x `MCPServer`, stdio), with tool logic in `src/robot_tools.py`: `look`, `list_cameras`, `get_robot_state`, `list_waypoints`, `go_to_waypoint`, `nudge_joint`, `set_gripper`, `stop`, `enable_torque`, `teach_waypoint`. Motion is off unless `ELROBOT_ALLOW_MOTION=1`; waypoint moves route through `clear`; nudges capped at 5%; Claude cannot turn torque off. Gripper stall while closing is reported as `holding_object`.
- Camera frames from Station `usbvideo/<hash>` queues (`src/elrobot_camera.py`), and `read_recent`/`read_first` queue reads in the hardware bridge.
- `gripper`, `cameras` and `agent` sections in `config/elrobot.json` defaults.
- `tests/test_robot_mcp.py` (14 tests: fake arm, camera decode against the SDK, tool registration). Guide `docs/mcp_server.md`.
- `./cli.sh start`: single-command unified launcher that boots the Station daemon and serves the Mission Control Web UI at `http://localhost:8080`.
- Web Mission Control Dashboard (`src/digital_twin.html` & `src/digital_twin_server.py`):
  * Real-time Master/Slave teleop toggle (50Hz)
  * Emergency E-Stop button (cuts motor torque)
  * Live camera stream with metric mm grid overlay
  * Quick waypoint actions (Home, Pick, Place)
  * One-click Judge Perturbation Recovery demo and test suite trigger
- `scripts/teleop_sync.py` and `./cli.sh teleop`: live 50Hz master/slave mirroring script mapping joint movements from Leader (`5B61034962`) to Follower (`5B61037051`) with overload protection and graceful torque shutdown on exit.
- `docs/NormaCore Hackathon - 4-Corner AprilTags.pdf`: printable PDF containing standard 36h11 fiducial markers for overhead camera homography calibration.

### Changed
- `.mcp.json` and `./cli.sh mcp` now run the real-arm server from `.venv`. Previously `.mcp.json` pointed at `src/mcp_server.py`, which is not an MCP server, so no tools registered.
- `requirements.txt`: `mcp>=2.0.0`, numpy no longer capped below 2 (no 1.x wheels for Python 3.13).
- `config/elrobot.json`: set default follower serial bus to `5B61037051`.
- `cli.sh`: integrated `teleop` command.
- Downgraded numpy to `<2` (1.26.4) to fix OpenCV ABI compatibility on Python 3.12.
- `AGENTS.md`: every finished change is committed before reporting back (explicit paths, CHANGELOG entry, Conventional Commits). Added a team workflow: feature branches, pull requests, single hardware owner, calibration commits, and shared handoffs.
- `AGENTS.md`: after each implementation, agents give 3 prioritized suggestions and record them in `SUGGESTIONS.md`.
- `AGENTS.md`: added setup and safety pointers, where things live, a definition of done, testing, conventions, blocker reporting and privacy rules, plus shared-file etiquette for handoffs.
- `external/norma-core` is now a git submodule of NormaCore (`norma-core/norma-core`), pinned to commit `5f4f805` (release 0.1.0-beta.10). Replaces the manually unpacked archive. `.gitignore` ignores `external/*` except the submodule.
- `FINDINGS.md`: new file for verified observations, each with evidence and status. Rules stay in `GUIDELINES.md`, and ideas in `SUGGESTIONS.md`. `AGENTS.md` now lists where each kind of information belongs.
- `scripts/sdk_check.py`: fails clearly when `external/norma-core` is the old unpacked copy, not the submodule. The old copy differs from `5f4f805` in about 50 files, so it is not supported.
- `docs/team_setup.md`: the submodule is the only supported SDK source. The guide shows how to move an old unpacked copy aside.
- `SUGGESTIONS.md`: restored the protobuf-regeneration guard as suggestion 27. It was removed by mistake, since it was never implemented.
- `scripts/sdk_check.py` and `./cli.sh sdk-check`: read-only check that the SDK submodule is at the pinned commit with no local edits, that its version and two Python imports work, and that `bin/station` reports build 5f4f805. Never moves the arm.
- `scripts/agent_sync.sh` (`./cli.sh sync`) also runs `git submodule update --init --recursive` after a pull.
- `docs/team_setup.md`: clone with `--recurse-submodules`; section 4 is now the submodule pin plus the Station binary; new troubleshooting rows for an empty or dirty submodule.
- `AGENTS.md`, `docs/elrobot_hardware_bridge.md`, `docs/NormaCore_Repositories_and_Tooling.md`: SDK location and pin updated. SDK pin changes must be their own approved commit.
- `scripts/agent_sync.sh` and `./cli.sh sync`: fetch from origin, then fast-forward only when the tree is clean and the branch is behind. Never stashes, resets or force-pulls. Lists commits on `origin/main` since the branch split. Exit codes separate offline, dirty, diverged and no-upstream states. `AGENTS.md` On Start now requires running it before implementing.
- New `docs/team_setup.md` (new-machine setup, serial permissions, cameras, common problems) and `docs/bench_safety.md` (before, during and after motion tests, stop procedure).

### Added (earlier)
- Master CLI runner `cli.sh` providing commands for `test`, `demo`, `digital-twin`, `station`, `setup-serial`, `apriltags`, `view-camera`, `mcp`, and `urdf`.
- Interactive 3D WebGL Digital Twin (`src/digital_twin.html` and `src/digital_twin_server.py`) with Three.js tabletop visualization, live camera feeds, kinematics telemetry, and perturbation triggers.
- Unit test for Digital Twin assets in `tests/test_pipeline.py`.
- Downloaded and verified pre-built Station binary `bin/station` (v0.1.0-beta.10 Linux x86_64).
- Unpacked official source tree and ElRobot hardware manuals into `external/norma-core/`.
- NormaCore GitHub Repositories & Tooling Guide `docs/NormaCore_Repositories_and_Tooling.md`.
- Official Station & ElRobot SDK Reference Guide `docs/NormaCore_Station_SDK_Reference.md` with release binaries, `station --web --tcp` CLI options, Protobuf topics (`st3215/inference`), and ST3215 register structures.
- Direct link to NormaCore's online 3D URDF interactive viewer `https://normacore.dev/elrobot-urdf/`.

- Real-hardware joint-level bridge `src/elrobot_hardware.py` for the ST3215 bus via the NormaCore Station (`ElRobotHardware` async client and `ElRobotHardwareSync` facade). Reads motor registers, sets torque, and moves motors 1–8. Motion is refused without `enable_motion=True`, goals are clamped to calibrated range minus a margin, wrap-around or uncalibrated motors are refused, and any motor fault blocks motion.
- Read-only hardware preflight `scripts/hardware_preflight.py`: confirms all 8 ElRobot motors are visible, calibrated and fault-free. It never moves the arm or changes torque.
- Unit tests `tests/test_elrobot_hardware.py` (14 tests) for the safety helpers: sign-bit decoding, goal clamping, calibration refusal, fault detection, and motion-enable gating. No hardware needed.
- Run logging `src/elrobot_log.py`: each run writes a full DEBUG log to `logs/<tool>-<timestamp>.log` and updates `logs/<tool>-latest.log`. Each log starts with a header (git commit, Python, platform, arguments, SDK path). Uncaught exceptions are written with tracebacks. The console stays short.
- Hardware-day tool `scripts/hw_day.py`, exposed as `./cli.sh hw ...`: a persistent checklist (`status`, `next`, `run <n>`, `done <n>`), joint map (`map`), live table (`motors`), confirmed single-motor move (`jog`, requires typing `MOVE`, max ±200 steps), `stop` (torque off, always available), `logs`, `bundle` (packs logs, state and config for sharing), and `reset`.
- `./cli.sh preflight` (read-only readiness check) and `./cli.sh logs [-f]` (newest run log).
- Runbook `docs/elrobot_hardware_bridge.md` now covers the commands, a common-failures table, and a recommended order for what is not ready yet.
- Config and state are separate. `config/elrobot.json` (joint map, current thresholds, workspace limits) and `config/waypoints.json` are committed. Checklist progress moved to `data/hw_day_state.json` (gitignored), so clearing progress never deletes calibration data.
- Guided motor identification `./cli.sh hw identify`: nudges each motor 30 steps, returns it, and records the joint and physical direction.
- Torque commands `./cli.sh hw torque on|off`. Torque on holds the current pose (goal set before torque is enabled, so there is no jump). Moves are refused while torque is off, with a clear message.
- Overload guard in `move_and_watch`: watches each motor until it arrives, overloads, faults or times out. On overload, fault or timeout it holds the motors still moving. `OverloadDetector` is pure and unit-tested.
- Current probe `./cli.sh hw probe-current <m>`: small move with the guard off. Reports peak current out and back, and offers to save `2 x peak` as the threshold.
- Named waypoints: `./cli.sh hw teach <name>`, `hw waypoints`, `hw goto <name>`. Goto shows a per-motor plan, clamps to calibrated range, refuses moves over 600 steps per motor unless `--allow-large`, and checks arrival afterwards.
- Workspace limits moved to `config/elrobot.json` (`workspace`). `SafetyLimits` and the MCP server read them. Defaults equal the previous hardcoded values. `./cli.sh hw workspace` shows whether they were measured.
- `.gitignore`: `data/`, `station.yaml`, `station_data/`.
- Tests: `tests/test_hw_day.py` runs the identify, jog, probe, teach, goto, torque and stop flows against a fake bridge and in-memory config. 44 tests pass in total.
- Runbook rewritten as a step-by-step walkthrough for each item that was not ready.

### Changed
- Expanded `.gitignore` with comprehensive rules for Python bytecode, virtualenvs, robotics runtime logs, secrets, testing caches, and IDE artifacts.

## [0.2.0] - 2026-11-20

### Added
- Comprehensive team onboarding `README.md` with 5-minute quickstart, architecture diagram, 4-person role split, and hardware instructions.
- Model Context Protocol configuration `.mcp.json` for automatic tool discovery in Claude Code and Cursor.
- Offline simulation engine `src/mock_station.py` simulating Station runtime, ElRobot kinematics, ST3215 servo loads, table objects, and camera feed.
- Perspective homography and metric grid generator `src/vision_homography.py` mapping camera pixels to tabletop millimeters.
- Deterministic Cartesian safety guardrails `src/kinematics_safety.py` enforcing $Z \ge 12\text{mm}$ table floor clamp and workspace boundaries.
- Standard MCP tool server `src/mcp_server.py` exposing `get_calibrated_view`, `pick_at`, `place_at`, `verify_grasp`, `reset_home`.
- Autonomous error recovery orchestrator `src/agent_prompts.py` proving closed-loop re-planning after a simulated judge perturbation.
- Automated test suite `tests/test_pipeline.py` (5/5 unit and integration tests passing).
- Linux USB serial hardware guide `docs/hardware_setup_and_usb_serial.md` and one-click setup script `scripts/setup_usb_serial.sh`.
- AprilTag 36h11 generator `scripts/generate_apriltags.py` generating printable and screen-displayable calibration sheets `docs/apriltags_printable.html`.
- Standard project dependencies file `requirements.txt`.
- Project guidelines `GUIDELINES.md` and preferences `PREFERENCES.md`.
- Implementation plan `.ai-sync/PLAN.md`, progress tracker `.ai-sync/PROGRESS.md`, and handoff `.ai-sync/HANDOFF.md`.

### Changed
- Reorganized documentation files into `docs/` (`NormaCore_Winning_Plan.md`, `NormaCore_Challenge_Guide.md`, `Hackathon_Event_Logistics.md`).
- Restructured workspace into standardized directories (`docs/`, `scripts/`, `src/`, `tests/`, `archive/`).
- Updated `SUGGESTIONS.md` based on user feedback.

## [0.1.0] - 2026-11-20

### Added
- Initial project scaffold with `.ai-sync/`, `AGENTS.md`, `CHANGELOG.md`, `GUIDELINES.md`, `PREFERENCES.md`, `SUGGESTIONS.md`, `README.md`.
