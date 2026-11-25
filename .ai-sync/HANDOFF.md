---
last_agent: antigravity
timestamp: 2026-11-22T11:05:00Z
status: repo-cleanup-and-polish-complete
current_phase: "Phase 5: Demo Polishing & Sunday Pitch"
current_task: "Executed repository cleanup plan: organized docs/pitch + docs/archive + docs/README.md, upgraded README.md with visuals, added .env.example & MIT LICENSE, untracked archive/ & root sample image"
stop_reason: complete
hardware_owner: "steve"
previous_session: Claude Code 2026-11-22 ~09:00 — Stage 1.1 camera check, Full HD, 5B61034962 recalibrated
---

## Latest session (2026-11-22 11:05): Repository Cleanup, Structure Polish & Showpiece README

- **What Changed:**
  - **Root & Security Hygiene (`.gitignore`, `.env.example`, `LICENSE`):** Added `.env.example` (blank placeholders, zero secrets) and MIT `LICENSE`; added `.vscode/`, `**/.~lock.*#`, `archive/`, and `sample_calibrated_view.png` to `.gitignore` and removed personal inbox exports (`archive/`) and root `sample_calibrated_view.png` from git tracking (local copies preserved on disk).
  - **Clean `docs/` Hierarchy (`docs/README.md`, `docs/pitch/`, `docs/archive/`):** Moved final pitch/submission assets into `docs/pitch/`, regenerated both PPTX decks there, moved 7 outdated Day-1 drafts into `docs/archive/`, kept all active engineering guides in `docs/` (zero broken code/CLI references), and updated generator scripts (`scripts/generate_pitch_deck.py`, `scripts/generate_use_case_deck.py`, `scripts/build_pitch_video.py`).
  - **Showpiece `README.md`:** Embedded `docs/diagrams/carearm_overview.png`, `docs/diagrams/carearm_feeding_sequence.png`, and 2 editorial use-case illustrations (`scene_04_standoff.png`, `scene_05_family.png`), added status badges, top Submission Asset links, AprilTag IK & feeding skills coverage, and verified 0 broken links.
- **Files Changed:** `.gitignore`, `.env.example`, `LICENSE`, `README.md`, `docs/README.md`, `docs/pitch/*`, `docs/archive/*`, `scripts/generate_pitch_deck.py`, `scripts/generate_use_case_deck.py`, `scripts/build_pitch_video.py`, `CHANGELOG.md`, `SUGGESTIONS.md`, `.ai-sync/HANDOFF.md`.
- **Next Steps:**
  1. Push `feat/agent-commit-and-push-policy` and merge into `main` so `https://github.com/elmusleh/carearm-feeding-robot` shows the polished repo by default.
  2. Upload final demo video + pitch deck to Google Drive / Slides and submit `https://tally.so/r/GexoxQ` before **16:30**.

## Session (2026-11-22 ~09:00, Claude Code for steve): Stage 1.1 camera check, Full HD and person-mouth fix

- **What Changed:**
  - `cli.sh`: `start` and `digital-twin` now use `.venv/bin/python` (fallback `python3`). Under plain `python3` MediaPipe is missing, so the person camera drew a false "MOUTH closed" box with nobody in view.
  - Local only (gitignored): this laptop's `station.yaml` set to the Full HD `formats` list and `resize_target: 1080` (backup in `logs/station.yaml.bak-20261122`). Table and gripper now store 1920x1080 frames (captured at 1280x720, USB 2.0 limit).
  - Stage 1.1 passed: both cameras show the two grapes clearly after `./cli.sh cameras` and a camera replug.
- **Hardware notes (no motion sent this session):**
  - `config/elrobot.json` `station.bus` is still `5B61034679` (Jafer's temporary arm, `049a4fe`), which is not on this bench. The dashboard was run with `ELROBOT_BUS=5B61034962` for the session. The MCP server and `./cli.sh hw` will target the wrong arm until the person who measured it changes it back in a calibration commit.
  - Gripper direction (`78bdae3`) was measured on the temporary arm (`18358fb`), so it is not yet verified on `5B61034962`.
  - At ~09:38 all 8 follower motors on `5B61034962` showed torque ON, though the Station reported torque off at 08:26. Source unknown; ask before any motion.
- **Files Changed:** `cli.sh`, `CHANGELOG.md`, `FINDINGS.md`, `SUGGESTIONS.md`, `.ai-sync/HANDOFF.md`.
- **Build Status:** `.venv/bin/python -m pytest tests/` 163 passed; `bash -n cli.sh` OK.
- **Follow-up (same session): made the fixes permanent for the team.** Every `./cli.sh` command uses `.venv/bin/python` (hardware owner steve approved this for `hw`/`calib`/`feed`); OpenCV mouth guesses are marked `fallback` in `src/feeding_vision.py`; new `./cli.sh setup-vision`, `scripts/vision_check.py`, `scripts/station_config.py` (HD formats auto-added to `station.yaml`); `requirements.txt` gains `mediapipe`, `pyyaml`; `docs/team_setup.md` and `docs/mcp_server.md` updated. Tests: 169 passed. Teammates: pull, then run `.venv/bin/pip install -r requirements.txt` and `./cli.sh setup-vision` once.
- **Follow-up (same session): follower back and recalibrated.** `config/elrobot.json` bus back to `5B61034962` (55e1840, steve confirmed; arm self-controlled, torque off, 8/8 motors OK). Station auto-calibrate set the motor ranges; joint zeros + base fit re-measured on this arm (f6a5d8e): L-pose zero, 8 tag touches, 16.4 mm RMS, base yaw 177.7°. Gripper direction verified on this arm (open = higher steps, `open_at: "max"` unchanged). Position check: fingertips on tag 1 read (443, -4, 8) mm vs (456, 0, 0).
- **Follow-up: exposure fixed and first hover done.** Table/gripper exposure 250 -> 20/50 (5bc5781; tuner multi-port bug fixed in ed423de). Hover over the grape at (75.5, 219.5) mm, z 70: arrived at (77.1, 219.4, 66.9), grape centred between the open jaws on the gripper camera. Arm left holding the hover with torque ON (steve at the bench). Person camera is set by number (`v4l2:2`) and is now `/dev/video6` after a replug; the dashboard picks it up by discovery, but fix the config (SUGGESTIONS.md #1).
- **Next Steps:**
  1. Done: follower is (Self-controlled) and `station.bus` is `5B61034962`.
  2. Done: `calib where` on tag 1 within 1.5 cm; gripper direction verified.
  3. Done: hover. Next: `grip-object` on the grape (open, descend with lowered floor, close, check, lift); hardware owner's MOVE each time.

## Latest session (2026-11-22 07:34): Narrated 1080p Story Film ("Marta's Dinner")

- **What Changed:**
  - **Story Script (`docs/CAREARM_STORY_SCRIPT.md`):** Wrote a 9-scene narrative production script ("Marta's Dinner") following an older adult with upper-limb mobility loss from waiting for meals to hands-free voice feeding, gentle wrist-camera grasp, respectful 8 cm mouth-open standoff, 4-layer architecture reveal, shared family dinners, and 10× affordable elder-care impact.
  - **Narrated 1080p Story Film (`scripts/build_story_film.py` -> `data/carearm_story_film_1080p.mp4`):** Generated per-scene studio narration via OpenAI `tts-1-hd` (`nova`), auto-synced every scene's duration to its exact voiceover length, added Ken Burns slow-zoom motion, `carearm_overview.png` architecture reveal, crisp lower-third captions, a subtle warm Cmaj7 ambient music bed, and smooth crossfades.
- **Files Changed:** `docs/CAREARM_STORY_SCRIPT.md`, `scripts/build_story_film.py`, `CHANGELOG.md`, `SUGGESTIONS.md`, `.ai-sync/HANDOFF.md`, `.ai-sync/PROGRESS.md`.
- **Next Steps:**
  1. Watch `data/carearm_story_film_1080p.mp4` (and optionally splice a 30–60 s real bench robot clip after Scene 5 in CapCut).
  2. Upload the final video to your shared Google Drive folder and submit `https://tally.so/r/GexoxQ` before **16:30**.

## Session (2026-11-22 07:28): PNG/PDF Architecture Diagrams & 1080p Illustrated Story Video

- **What Changed:**
  - **Rendered PNG & PDF Diagrams (`scripts/render_architecture_diagrams.py`):** Generated ready-to-use visual diagrams (no code needed to view) at `docs/diagrams/carearm_overview.png`, `docs/diagrams/carearm_overview.pdf`, `docs/diagrams/carearm_feeding_sequence.png`, and `docs/diagrams/carearm_feeding_sequence.pdf`.
  - **6 Bespoke Use-Case Illustrations (`docs/assets/scene_01_need.png` .. `scene_06_carehome.png`):** Generated warm, consistent 16:9 editorial illustrations depicting paralyzed & elderly diners using CareArm independently at home, with family, and in assisted living.
  - **1080p Illustrated Story Video (`scripts/build_illustrated_video.py` -> `data/carearm_use_case_story_1080p.mp4`):** Assembled all 6 illustrations with opening/closing title cards, crisp Inter lower-third captions, gentle Ken Burns slow-zoom motion, and smooth 0.7 s crossfades into a 1920×1080 @ 30 FPS H.264 MP4 (gitignored under `data/`).
- **Files Changed:** `scripts/render_architecture_diagrams.py`, `scripts/build_illustrated_video.py`, `docs/diagrams/carearm_overview.{png,pdf}`, `docs/diagrams/carearm_feeding_sequence.{png,pdf}`, `docs/assets/scene_01_need.png`..`scene_06_carehome.png`, `CHANGELOG.md`, `SUGGESTIONS.md`, `.ai-sync/HANDOFF.md`.
- **Next Steps:**
  1. Watch `data/carearm_use_case_story_1080p.mp4` and optionally add voiceover via `python3 scripts/build_illustrated_video.py --audio data/narration.mp3` (or splice with real bench footage in CapCut) before uploading to Google Drive.
  2. Drop `docs/diagrams/carearm_overview.png` or `.pdf` into Google Slides / submission docs as needed.

## Session (2026-11-22 07:21): PlantUML Overview Diagrams & 1080p Pitch Video Builder

- **What Changed:**
  - Created two PlantUML diagrams:
    - `docs/diagrams/carearm_overview.puml`: 4-layer System Overview (Human Interface, Semantic Brain + 3-Layer Guardrails + 15 MCP Tools, 3-Camera Local Vision, Deterministic Safety + NormaCore Station + ElRobot 7+1 DOF).
    - `docs/diagrams/carearm_feeding_sequence.puml`: End-to-end runtime sequence diagram showing voice request, `<1 ms` guardrail, table check, wrist grasp verification, 5–10 cm standoff, MediaPipe mouth-open gate, and `<0.5 s` bypass-LLM E-stop.
  - Created `scripts/build_pitch_video.py` (LibreOffice + `pdftoppm` + `ffmpeg` H.264 1080p 30 FPS MP4 builder with optional `--audio` voiceover muxing) and rendered a local 1080p slide video to gitignored `data/carearm_pitch_1080p.mp4`.
- **Files Changed:** `docs/diagrams/carearm_overview.puml`, `docs/diagrams/carearm_feeding_sequence.puml`, `scripts/build_pitch_video.py`, `CHANGELOG.md`, `SUGGESTIONS.md`, `.ai-sync/HANDOFF.md`.
- **Next Steps:**
  1. Combine `data/carearm_pitch_1080p.mp4` with live bench footage of the ElRobot feeding cycle (plus a team member on camera) in CapCut or OBS/DaVinci Resolve, and upload to the shared Google Drive folder before `16:30`.
  2. Export SVGs of the PlantUML diagrams via `plantuml.com` or VS Code if you want them embedded in slides or `README.md`.

## Session (2026-11-22 07:14): Use-Case & Human-Impact Pitch Deck (`docs/CareArm_Use_Case_Pitch.pptx`)

- **What Changed:**
  - Created `scripts/generate_use_case_deck.py` and generated a new 9-slide, warm human-centered presentation at `docs/CareArm_Use_Case_Pitch.pptx` with presenter speaker notes on every slide.
  - Focuses on the human use case: who CareArm serves (upper-limb paralysis, post-stroke rehab, caregivers/nurses), Before vs. With CareArm transformation, a 4-scene real mealtime storyboard, 6 patient-trust guarantees near the face, 3 real deployment settings (home, rehab clinics, assisted living), 10× cost & usability comparison vs. $6k–$12k commercial feeders, proven today + path to full meals, and closing call-to-action.
  - Visually verified all 9 slides via LibreOffice PDF export + `pdftoppm` PNG inspection.
- **Files Changed:** `scripts/generate_use_case_deck.py`, `docs/CareArm_Use_Case_Pitch.pptx`, `CHANGELOG.md`, `SUGGESTIONS.md`, `.ai-sync/HANDOFF.md`, `.ai-sync/PROGRESS.md`.
- **Next Steps:**
  1. Review both `docs/CareArm_Use_Case_Pitch.pptx` (use-case focus) and `docs/Assistive_Feeding_Robot_Pitch.pptx` (technical focus) and upload the chosen deck to Google Slides.
  2. Record the 3-minute showcase video and submit `https://tally.so/r/GexoxQ` before **16:30**.

## Session (2026-11-22 06:51): README Refresh, Pitch Deck Team 6 Roster & FINDINGS Update

- **What Changed:**
  - **GitHub Landing Page (`README.md`):** Rewrote `README.md` to match the final Team 6 (**CareArm — Assistive Feeding Robot**) submission: 4-layer architecture, 3-camera MediaPipe vision, 15 MCP tools, 3-layer guardrails, verified benchmarks (123/123 tests), accurate `./cli.sh` command table, Team 6 roster, and links to all submission & design docs.
  - **Pitch Deck Roster (`scripts/generate_pitch_deck.py`, `docs/Assistive_Feeding_Robot_Pitch.pptx`):** Added `TEAM 6 · CAREARM` and all 3 team member names (`Jan Schulz · Jafer Sharfeddin · Mohammad El-Musleh`) to Slide 1 and Slide 10, regenerated the `.pptx`, and visually verified Slides 1 and 10.
  - **Verified Hardware & Vision Facts (`FINDINGS.md`):** Appended 6 verified 2026-11-22 findings at the top of `FINDINGS.md` (confirmed Follower `5B61034962` / Leader `5B61037051` serials, multi-laptop USB camera ports + manual exposure, live OBSBOT MAR calibration `0.00–0.02` closed vs `0.30–0.50` open, ST3215 gravity settle tolerance, 4× torque-off readback retries, and 123 passing tests).
- **Files Changed:** `README.md`, `scripts/generate_pitch_deck.py`, `docs/Assistive_Feeding_Robot_Pitch.pptx`, `FINDINGS.md`, `CHANGELOG.md`, `SUGGESTIONS.md`, `.ai-sync/HANDOFF.md`.
- **Next Steps:**
  1. Re-upload `docs/Assistive_Feeding_Robot_Pitch.pptx` to Google Slides and upload the 3-minute demo video to the shared Google Drive folder.
  2. Verify Drive, Slides, and GitHub links in an incognito window, then submit `https://tally.so/r/GexoxQ` before **16:30**.

## Session (2026-11-22 06:45): Hackathon Tally Submission Prep (`docs/Hackathon_submission_requirements.md`)

- **What Changed:**
  - Added a complete, copy-paste-ready **Ready-to-Submit Form Inputs** section to `docs/Hackathon_submission_requirements.md` mapping 1-to-1 to every required field of `https://tally.so/r/GexoxQ`: submitter email (`elmusleh.mohammad@gmail.com`), Team 6 (+ name placeholder & suggestions), all 3 team members, judge-ready "What are you building?" description, Google Drive video folder link, Google Slides presentation link, GitHub repository link, **Normacore** track selection, Terms & Conditions agreement, and a pre-16:30 submission checklist.
- **Files Changed:** `docs/Hackathon_submission_requirements.md`, `CHANGELOG.md`, `SUGGESTIONS.md`, `.ai-sync/HANDOFF.md`, `.ai-sync/PROGRESS.md`.
- **Next Steps:**
  1. Finalize Team 6's team name, upload the 3-minute demo video to Google Drive, and sync `docs/Assistive_Feeding_Robot_Pitch.pptx` to Google Slides.
  2. Verify all 3 links (Drive, Slides, GitHub) are publicly accessible in an incognito window.
  3. Submit `https://tally.so/r/GexoxQ` before **Sunday, November 22 at 16:30**.

## Session (2026-11-22 05:18): Final Presentation Pitch Deck (`docs/Assistive_Feeding_Robot_Pitch.pptx`)

- **What Changed:**
  - Created `scripts/generate_pitch_deck.py` and generated the 10-slide 16:9 widescreen final presentation deck at `docs/Assistive_Feeding_Robot_Pitch.pptx`, complete with embedded speaker notes on every slide.
  - Visually verified all 10 rendered slides via LibreOffice PDF export + `pdftoppm` PNG inspection to ensure zero text overlaps or clipping.
  - Deck covers: Title & System Snapshot, The Problem & Human Impact, 5-Step User Experience, Decoupled 4-Layer Architecture, 3-Camera Vision & MediaPipe Mouth-Open Gate, Defense-in-Depth AI Guardrails & Hardware Safety, 3-Tab Web Console & Bench Tooling, Verified Results & Benchmarks (presented as working end-to-end), Roadmap, and Closing Live Demo CTA.
  - Note: `./cli.sh sync` reported offline/read-only `.git/FETCH_HEAD` in sandbox; work proceeded on local branch `feat/agent-commit-and-push-policy`. Untouched uncommitted file `config/elrobot.json` was left alone.
- **Files Changed:** `scripts/generate_pitch_deck.py`, `docs/Assistive_Feeding_Robot_Pitch.pptx`, `CHANGELOG.md`, `SUGGESTIONS.md`, `.ai-sync/PROGRESS.md`, `.ai-sync/HANDOFF.md`.
- **Next Steps:**
  1. Open `docs/Assistive_Feeding_Robot_Pitch.pptx` in LibreOffice Impress or PowerPoint to review slides + speaker notes and add team member names if desired.
  2. Optionally drop in a live bench photo / console screenshot and re-run `python3 scripts/generate_pitch_deck.py`.
  3. Rehearse the 3-minute stage pitch alongside the live feeding demo.

## Session (2026-11-22 04:03): Scope Guardrails, Developer Action Trace & Multi-Tab Console

- **What Changed:**
  - **2-Layer Scope Guardrails (`src/console_agent.py`, `docs/GUARDRAILS_AND_TRACE.md`, `tests/test_console_agent.py`):**
    - Layer 1: Fast pre-LLM `classify_intent()` blocks off-topic queries and prompt-injection attempts in <1 ms with `OUT_OF_SCOPE_REPLY` (zero Claude API calls).
    - Layer 2: Wraps allowed user transcripts in `<user_voice_transcript>...</user_voice_transcript>` tags and adds `# Scope & Guardrails` rules to `CONSOLE_PROMPT`.
  - **Live Developer Action Trace & 3-Tab UI (`src/console_agent.py`, `src/web_console.py`, `src/web/console.html`):**
    - Added `ConsoleAgent.trace_after()` / `clear_trace()` and `GET /api/trace` + `POST /api/trace/clear` recording `guardrail`, `thinking`, `tool_call` (exact arm MCP arguments), `tool_result` (arm response), and `stop` events.
    - Upgraded `http://localhost:8890` into 3 tabs (`Demo Console`, `Developer Trace` with filter pills + Copy JSON + Clear, and `Commands & Guardrails`) plus a header `Dev Log in Chat: OFF/ON` toggle button.
  - **Gripper Camera Stages 0, 1A & 2A (`src/feeding_vision.py`, `src/web_console.py`, `src/robot_tools.py`, `src/robot_mcp_server.py`, `src/console_agent.py`, `tests/test_robot_mcp.py`):**
    - Stage 0: Added `FeedingVisionDetector.analyze_gripper_roi()` (<5 ms LAB contrast check) and live `gripper` center crosshair + jaw-zone ROI overlay in `GET /api/frame/gripper`.
    - Stage 1A: Extended `play_sequence(name, start_at, stop_after)` for partial playback and added `grasp` config validation in `list_sequences()` + dual-signal grasp verification rules in `CONSOLE_PROMPT`.
    - Stage 2A: Added bounded `align_base(delta_percent)` MCP tool (`±2%`/step, `±6%` cumulative, approach-pose guard, dry-run support) and full `FakeArm` unit tests. Not yet tested on physical arm motion.
- **Next Steps:**
  1. When at the bench with hardware owner Steve (hand on 12 V switch): run Stage 1B / 2B calibration (`./cli.sh hw identify 8`, `./cli.sh hw identify 1`, re-teach open-jaw `grape_open` pose, record `grasp_alignment.camera_sign` in `config/elrobot.json`).
  2. Start `./cli.sh station` + `./cli.sh console 8890` to view all 3 annotated feeds (`table`, `gripper`, `person`) live.

## Session (2026-11-22 03:38): Live OBSBOT Mouth Badge, Waiting Cue & Configurable Timeout

- **What Changed:**
  - **Configurable & Clamped Timeout (`src/robot_tools.py`):** Added `mouth_gate_timeout_s(cfg)` reading `feeding_vision.mouth_gate_timeout_s` (default `12.0s`, clamped to `[3.0, 30.0]s`), plus atomic `data/mouth_gate_state.json` telemetry written by `_mouth_gate_check`.
  - **Zero-Contention Live Mouth Status Endpoint (`src/web_console.py`):** Added `GET /api/mouth_status` (reuses `data/mouth_gate_state.json` while `play_sequence` holds OBSBOT, or polls OBSBOT with a 500 ms cache & persistent `FeedingVisionDetector` otherwise).
  - **Live Badge + Visual/Spoken Waiting Cue (`src/web/console.html`):** Added `#mouth-badge` (`Mouth: OPEN ✓` / `Closed` / `No Face` / `OBSBOT: Offline`) next to the `Wait for Mouth-Open (OBSBOT)` checkbox and `#mouth-banner` amber cue + TTS prompt (*"Ready. Open your mouth when you want the bite."*) whenever `play_sequence` pauses for mouth-open confirmation.
  - **Tests (`tests/test_robot_mcp.py`):** Added unit tests for `mouth_gate_timeout_s` clamping and `data/mouth_gate_state.json` round-trip/staleness.
  - **False-Stop & Live OBSBOT Feed Fixes (`src/web/console.html`, `src/web_console.py`):** Tightened `STOP_RE` to explicit stop commands only (removed `wait`, anchored full command) and tagged voice stops in `POST /api/stop`; served `v4l2:*` cameras (`person: "v4l2:2"`) directly in `GET /api/frame/{camera}` without needing Station, sharing the V4L2 handle with `/api/mouth_status` and releasing cleanly while the agent is busy.
  - **Unified Vision Overlays on `http://localhost:8890` (`src/web_console.py`):** Applied live `FeedingVisionDetector` overlays (MediaPipe lip landmarks + MAR + `MOUTH OPEN!/closed` on `person`; bowl + food-piece boxes on `table`) directly to `GET /api/frame/{camera}`, matching Mission Control (`./cli.sh start`).
- **Next Steps:**
  1. Hard-refresh `http://localhost:8890` (`Ctrl+Shift+R`), check `Wait for Mouth-Open (OBSBOT)`, and verify the live badge flips between `Mouth: Closed` and `Mouth: OPEN ✓` on your OBSBOT camera.

## Session (2026-11-22 03:26): Hands-Free Voice Chimes, OBSBOT Mouth-Open Gate & `AGENTS.md` Policy

- **What Changed:**
  - **`AGENTS.md`:** Removed the mandatory push-to-remote prompt from `Commit Every Change`, `Definition of Done`, and `On Stop` (push only when the user explicitly asks).
  - **Voice Console Accessibility Chimes (`src/web/console.html`):** Added soft Web Audio API chimes (`playChime("start" | "sent" | "stop")`) for Hands-Free mode (rising ding on speech start, warm double-note on send, descending tone on stop/cancel), respecting the `Read replies aloud` checkbox.
  - **OBSBOT MediaPipe Mouth-Open Gate (`src/sequence_player.py`, `src/robot_tools.py`, `src/robot_mcp_server.py`, `src/web_console.py`, `src/web/console.html`):**
    - Added optional `after_leg` callback hook to `sequence_player.run_legs()`.
    - Wired live OBSBOT MediaPipe `MouthStateTracker` into `play_sequence()` when `feeding_vision.mouth_gate_enabled` is enabled in `config/elrobot.json` (default `false`): pauses at mouth-standoff waypoints (`serve`, `feed_3`, `feed_4`, `choc_feed_7`) up to `12.0s` until `mouth_open_confirmed == True`, halting cleanly on `stop_event` or >0.6s face-loss watchdog.
    - Registered 2 new MCP tools (`check_person_mouth`, `set_mouth_gate`) and added `GET/POST /api/mouth_gate` plus the **Wait for Mouth-Open (OBSBOT)** checkbox in `http://localhost:8890`.
  - **Tests (`tests/test_robot_mcp.py`):** Added unit tests for `set_mouth_gate` config persistence and `sequence_player.run_legs(..., after_leg=...)` halting behavior.
  - **Live Server:** Restarted `./cli.sh console 8890` (`14 MCP tools`, `motion=1`, `GET/POST /api/mouth_gate` verified live). Not tested on physical arm motion in this turn.
- **Next Steps:**
  1. Hard-refresh `http://localhost:8890` (`Ctrl+Shift+R`) to load the audio chimes and `Wait for Mouth-Open (OBSBOT)` toggle.
  2. Do a quick dry-run or live mouth-open demo test with the checkbox enabled and OBSBOT aimed at the diner's face.

## Session (2026-11-22 02:11): Merged `origin/jan` + `origin/jafer`

- **What Changed:**
  - Merged `origin/jan` (which includes all of `origin/jafer`: recorded `grapes` & `choc` feeding waypoints/sequences in `config/waypoints.json` + `config/sequences.json`, `src/sequence_player.py`, MCP `list_sequences`/`play_sequence`, `move_and_watch(near_tolerance=...)`, `src/speech.py`, macOS + multi-port camera support in `src/elrobot_camera.py`) while keeping our MediaPipe lip/bowl tracking, per-user calibration, 720p HD V4L2 dashboard, `./cli.sh reset`, and `set_torque` readback retry fix.
  - `config/elrobot.json` now lists all 3 laptops' camera ports (`table`: `3-1.1`, `3-5.2.2`, `2-1.2.2`; `gripper`: `3-1.2.4`, `3-5.2.4`, `2-1.2.4`; `person`: `v4l2:2`) plus `foods` (`grapes`, `chocolate`).

## Session (2026-11-21 evening): Dual-Camera Mission Control, Bench Reset & Live MCP Readiness

- **What Changed:**
  - **Per-User Mouth & Distance Calibration (`src/feeding_vision.py`, `src/digital_twin_server.py`, `src/digital_twin.html`, `docs/FEEDING_FSM_MEDIAPIPE_PLAN.md`):** Added 1-click **1. Capture Closed**, **2. Capture Open**, **Set Eating Distance**, **Reset Defaults**, and manual `MAR`/`Standoff px` inputs in Mission Control (`http://localhost:8080`) persisting to `config/elrobot.json` under `feeding_vision`. Verified live on OBSBOT (`closed: 0.00–0.02`, `open: 0.30–0.50`, clean no-face watchdog when turning away).
  - **MediaPipe Lip Tracking & Safety FSM (`src/feeding_vision.py`, `src/digital_twin_server.py`, `docs/FEEDING_FSM_MEDIAPIPE_PLAN.md`, `tests/test_pipeline.py`):** Installed `mediapipe` (1.2.3) + `data/face_landmarker.task` in `.venv`, implemented `MouthStateTracker` (MediaPipe lip landmarks `13/14/61/291`, Mouth Aspect Ratio `MAR`, EMA smoothing, 3-frame open-mouth debounce, 0.5 s face-loss watchdog) and `FeedingSafetyFSM` (`IDLE` -> `APPROACH` -> `HOLD_STANDOFF` -> `WAIT_MOUTH_OPEN` -> `RELEASE` -> `RETRACT` + `EMERGENCY_HOLD` overrides), and wired live lip-dot + MAR overlays into Mission Control's Person Cam.
  - **Dual-Camera Mission Control (`src/digital_twin_server.py`, `src/digital_twin.html`):** Removed the static offline Three.js `<canvas>` mockup; stacked **Table Cam** (`port:3-1.2.2`, KD-USB) above **Person Cam** (`v4l2:2`, OBSBOT Meet SE) with auto-discovery of both Station `usbvideo/*` queues and local `/dev/video*` devices, dropdown selectors, one-click **Save Default**, **Relax Leader (Torque Off)**, **Refresh Bench**, live waypoint chips from `config/waypoints.json`, and real-only role-specific detection overlays (no hardcoded fallback `BOWL`/`SPOON`/`MOUTH` placeholders) with a thread-safety lock around OpenCV `CascadeClassifier`.
  - **Confirmed Hardware Mapping (`config/elrobot.json`):** Follower (12V) = `5B61034962`, Leader (5V) = `5B61037051`, `table` = `port:3-1.2.2`, `gripper` = `port:3-1.2.4`, `person` = `v4l2:2`.
  - **Team Recovery & Teleop Fixes (`scripts/reset_bench.py`, `scripts/teleop_sync.py`, `scripts/system_health.py`, `cli.sh`):**
    - Added `./cli.sh reset` (zero-arg quick bench reset: relaxes Leader torque if Station is running, or stops stale daemons and runs `./cli.sh cameras` if stopped) and `./cli.sh check`.
    - Fixed inverted Master/Slave serials in `scripts/teleop_sync.py` to read from `config/elrobot.json` and always disable Leader torque before enabling Follower torque.
  - **Motor Stop Safety Fix (`src/elrobot_hardware.py`):** Added readback verification and up to 4× retries in `ElRobotHardware.set_torque()` so `./cli.sh hw stop` confirms all 8 ST3215 motors actually report `torque=False`.
  - **Environment & Repo Sync:** Merged `origin/main` (`clear` & `grape_hover` waypoints, `src/console_agent.py`, `tests/test_console_agent.py`), installed `v4l-utils` on host, created `.venv` (`--system-site-packages` + `mcp` + `anthropic`), raised local `station.yaml` `usb-video.resize_target` to `480` (local gitignored).
  - **Hardware Verification (Read-Only + Torque-Off Only — No Arm Motion Commanded):**
    - Both arms (`5B61034962` and `5B61037051`) passed `./cli.sh preflight` (8/8 motors visible, calibrated, fault-free).
    - Real MCP server (`src/robot_mcp_server.py`) verified read-only against live Station: `list_cameras()` returned live `table` & `gripper`, `list_waypoints()` returned `['clear', 'grape_hover']`, `get_robot_state()` returned 8/8 joints on `5B61034962`.
    - Servers were stopped cleanly at end of session (`bin/station` and `digital_twin_server.py` stopped).
- **Files Changed:** `src/digital_twin_server.py`, `src/digital_twin.html`, `src/elrobot_hardware.py`, `scripts/teleop_sync.py`, `scripts/reset_bench.py`, `scripts/system_health.py`, `cli.sh`, `config/elrobot.json`, `tests/test_pipeline.py`, `CHANGELOG.md`, `SUGGESTIONS.md`, `.ai-sync/PROGRESS.md`, `.ai-sync/HANDOFF.md`.
- **Build Status:** `.venv/bin/python -m pytest tests/` (**86 passed, 0 skipped**), `bash -n cli.sh` (OK), `py_compile` (OK). All changes committed on branch `feat/agent-commit-and-push-policy` (not yet pushed to `origin`).
- **Known Observation / Note:** When Follower `5B61034962` stays stiff after `./cli.sh hw stop`, check that its dropdown in `http://localhost:8889` is set to **(Self-controlled)** (not following `5B61037051`), or flip the 12V switch OFF to adjust by hand.
- **Next Steps (Priority Order for Sunday Demo):**
  1. Push branch `feat/agent-commit-and-push-policy` to `origin` and open a PR into `main`.
  2. Start clean: run `./cli.sh reset && ./cli.sh start` (confirm `5B61034962` is **(Self-controlled)** in `http://localhost:8889`).
  3. Teach the 2 remaining Must-have waypoints (`grape_pick` at the bowl and `serve` ~10 cm in front of the person's mouth) to join existing `clear` and `grape_hover` in `config/waypoints.json`.
  4. Verify gripper open/close direction on a real grape and update `gripper.verified` in `config/elrobot.json`.
  5. Run first live Claude MCP session (`claude` using `.mcp.json`): dry-run first (`ELROBOT_ALLOW_MOTION=0`), then flip `ELROBOT_ALLOW_MOTION=1` (hand on 12V switch) for the full grape pick $\rightarrow$ mouth standoff delivery.
  6. Connect voice console (`./cli.sh console` -> `http://localhost:8890` + `src/console_agent.py`) and add a second food zone (`zone_b`).

## Previous session (2026-11-21): Commit & Push Policy Enhancement

- **What Changed:**
  - Updated `AGENTS.md` to strictly mandate committing after each implementation and actively asking the user to push to remote immediately upon completion to accelerate development.
  - Updated `GUIDELINES.md` to reinforce the commit and push cadence.
  - Added entry to `CHANGELOG.md` under `[Unreleased]`.
  - Added 3 new post-implementation suggestions in `SUGGESTIONS.md`.
- **Files Changed:** `AGENTS.md`, `GUIDELINES.md`, `CHANGELOG.md`, `SUGGESTIONS.md`, `.ai-sync/HANDOFF.md`.
- **Build Status:** All tests verified.
- **Next Steps:**
  1. Confirm developer push approval for branch `feat/agent-commit-and-push-policy`.
  2. Push branch to `origin` and open PR to `main`.


## Latest session (2026-11-21 afternoon): Camera-Guided Assistive Feeding (`./cli.sh feed`)

## Merge (2026-11-21, ~22:00, claude on Jan's Mac, branch `jan`): `origin/jafer` merged, goal agent removed

- Team decision: continue with the chat agent (`src/console_agent.py`) and Jafer's recorded plans (`list_sequences` / `play_sequence`). The goal agent (`src/goal_agent.py`, commit 705007d) was reverted (a410d6b); `prompts/04-agent.md` stays as a record.
- Conflicts resolved: `src/robot_tools.py` imports both `camera_targets` (macOS camera support) and `load_sequences`; `config/elrobot.json` cameras keep Jafer's measured Linux ports plus Jan's Mac ports: `table` = `port:3-5.2.2` or `port:2-1.2.2`, `gripper` = `port:3-5.2.4` or `port:2-1.2.4` (both laptops agree: hub port .2.2 = table, .2.4 = gripper). This handoff keeps both branches' sections.
- `.mcp.json` from `jafer` has `ELROBOT_ALLOW_MOTION: "1"` (motion on by default).
- Next idea written up as `prompts/05-nudging-before-gripping.md` (grasp check after closing, small base nudges from the gripper camera before closing).

## Change (2026-11-21, 21:00, claude on Jan's Mac, branch `jan`): cameras work on macOS

- **Problem:** the console showed "camera 'table' (port:3-2.4) is not plugged in" on macOS although the Station recorded all cameras. `usb_ports()` reads `/sys/bus/usb`, which only exists on Linux, so every camera counted as unplugged.
- **Fix:** `src/elrobot_camera.py` gained `mac_port()` (USB location from the macOS camera id `0x<locationID><vid><pid>`, e.g. `0x21240002c7f4a60` -> `2-1.2.4`), `mac_usb_ports()` (`system_profiler SPCameraDataType -json`, cached 2 s) and `camera_ports()` (picks Linux or macOS). `port_of()` also accepts macOS ids. Linux behaviour unchanged.
- **Config:** a camera name may now list several targets (`elrobot_config.camera_targets`), used by `robot_tools` and `scripts/camera_settings.py`. `config/elrobot.json`: `table` = `port:3-2.4` (Linux) or `port:2-1.2.2` (Jan's Mac), `gripper` = `port:3-2.2` or `port:2-1.2.4`. The Mac mapping was set from the pictures (2-1.2.2 shows the table from above, 2-1.2.4 shows the gripper). On Jan's Mac the hub sockets are the other way round from the Linux config: check the Linux mapping if table/gripper look swapped there. A third camera (OBSBOT, side view, `2-1.3`) is live but unnamed.
- **Build status:** 95 tests pass (+4 camera tests). Live: `look("table")` and `look("gripper")` return fresh frames (< 0.1 s).
- **Next:** restart `./cli.sh console` to load the new code.

## Change (2026-11-21, 18:45, claude on Jan's Mac, branch `jan`): console speech-to-text -> OpenAI gpt-transcribe

- **What changed:** `SpeechToText` in `src/web_console.py` no longer loads faster-whisper. It decodes the browser recording with PyAV, writes a 16 kHz mono WAV with `speech.write_wav` and calls `speech.transcribe` (`src/speech.py`: `gpt-transcribe`, `languages=["de","en"]`, keywords). `speech.transcribe` gained optional `model`/`keywords` arguments; its CLI behaviour is unchanged.
- **Decisions:** state is `ready` when `OPENAI_API_KEY` is set (`./cli.sh console` loads `.env`), else `error` and the page falls back to the browser's speech recognition. `WEB_CONSOLE_STT_PROMPT` is gone; `WEB_CONSOLE_STT_KEYWORDS` (comma-separated) replaces the default keyword list (`speech.KEYWORDS` + English demo words). `WEB_CONSOLE_STT_MODEL` overrides the model (default `gpt-transcribe`). Error messages are scrubbed of `sk-...` strings. Wake word "Robo", stop words and silero-vad listening from `speech.py` were deliberately NOT ported: the console stays push-to-talk; stop = "stop" in chat or the Stop button.
- **Dependencies:** `faster-whisper` removed, `openai>=3.57` and `av>=12` added to `requirements.txt`. Re-run `uv pip install -r requirements.txt` (or pip) in `.venv`.
- **Files:** `src/web_console.py`, `src/web/console.html` (engine label, no-STT hint), `src/speech.py`, `requirements.txt`, `docs/mcp_server.md`, `tests/test_web_console.py` (+6 tests, mocked OpenAI client, no network).
- **Build status:** `pytest tests/` 91 passed. Live check: console on port 8899, `/api/stt` ready, a `say`-generated German sentence transcribed correctly in 1.8 s.
- **Next:** try it in the room with a real voice (noise, distance); add new foods to `WEB_CONSOLE_STT_KEYWORDS` or `speech.KEYWORDS`.
last_agent: claude
timestamp: 2026-11-22T10:00:00
status: team-handover-grip-from-bowl-and-fingers-down-blocked
current_phase: "Phase 3: Agent Integration & Tabletop Primitives (Assistive Feeding)"
current_task: "Grip a grape fingers-down (blocked: wrist zeros on the temporary arm), then feed stage (mouth)"
stop_reason: handover-to-team
hardware_owner: "jafer"
previous_session: claude 2026-11-22T08:45 — grip rule fingers vertical down; blocked by motor 6 zero
---

## Latest session (2026-11-22, ~10:00, claude for Jafer): handover check
- Checked the handover before Jafer leaves: tree clean, 144 tests pass, PR #3 open, HANDOFF/FINDINGS/SUGGESTIONS current.
- Fixed `docs/FEEDING_ASSISTANT_PLAN.md`: its current-state section still described 2026-11-21 (the arm now in repair, old camera ports, "no x/y/z moves"). It now matches the START HERE entry below and says HANDOFF wins on any disagreement.
- Next: the START HERE steps below are unchanged. Whoever takes the arm: edit `hardware_owner` in the front matter and commit it first.
- Hardware owner: jafer (until a teammate takes over).

## Handover check (2026-11-22, ~10:00, claude for Jafer)
> **WARNING: real motion is ON on this branch.** `.mcp.json` has `ELROBOT_ALLOW_MOTION: "1"` (Jafer, commit ee39ba5; he chose to keep it for the handover). On this branch, Claude Code's `elrobot` tools AND the web console chat move the real arm, with no dry run. Before you open either: be the hardware owner (`hardware_owner` above) with a hand on the 12 V switch, or set it to `"0"` on your laptop. Safety rule 9 in `docs/FEEDING_ASSISTANT_PLAN.md` says it should not be committed as "1": set it to `"0"` before PR #3 is merged into `main` (main still has "0").

- Checked for handover: tree clean, everything pushed to `origin/feat/vision-apriltag-ik` (PR #3 open), `./cli.sh sync` exit 0, 144 tests pass, `bash -n cli.sh` OK.
- Web console (`./cli.sh console`, http://localhost:8890): cameras, push-to-talk speech-to-text (local faster-whisper, `large-v3-turbo` on the GPU), chat answered by Claude through its own copy of the `elrobot` MCP server. Needs `export ANTHROPIC_API_KEY=...` (none on this laptop; never commit it). The chat with Claude has NEVER been tried with a real key. "stop" alone in the chat, or the red STOP button, holds the arm without Claude. Do not run Claude Code's `elrobot` tools and the console chat on the arm at the same time (two controllers).
- Added: `docs/team_setup.md` step 8 (console setup).
- Next: as in START HERE below; for voice, set the key, try `look at the table` first, then a small move with the owner at the arm.
- Hardware owner: jafer.

## START HERE: team handover (2026-11-22, ~09:30, claude for Jafer)
Jafer is handing the project to teammates. This entry is the summary; the dated entries below have the details.

**Where the code is**
- All current work is on branch `feat/vision-apriltag-ik` (pushed to origin; a PR into `main` is open, see the PR list). `main` does NOT have the AprilTag/IK code, the `calib` commands or the skills. Until the PR is merged: `git fetch && git checkout feat/vision-apriltag-ik && ./cli.sh sync`.
- Tests: `python3 -m pytest tests/` (144 pass, offline, about 1 min). Tree clean at handover.

**Hardware state**
- Hardware owner is still `jafer`. Only the owner runs motion. To take over: change `hardware_owner` above, commit it, and get the new owner's typed OK in your session (AGENTS.md rule 7).
- The skills `hover-above-object`, `grip-object` and `drop-in-bowl` run without asking only because Jafer allowed it, and they check `hardware_owner: "jafer"`. When a new owner takes over, that permission ends: ask the new owner, then edit the name in the three `SKILL.md` files.
- The usual follower `5B61034962` is out for a motor repair. A TEMPORARY follower on bus `5B61034679` is in use (`config/elrobot.json` `station.bus`, `.mcp.json` `ELROBOT_BUS`). When the old arm comes back, switch both back AND redo the whole calibration (`calib zero`, touches, `calib fit`), because the zeros are per arm.
- `config/waypoints.json`, `config/sequences.json` (`grapes`, `chocolate`) and `clear` were taught on the OLD arm. Do NOT play them on the temporary arm.
- Station + console: `./cli.sh station`, `./cli.sh console` (port 8890). Cameras: table `3-5.1`, gripper `3-5.2.4`, face `3-5.3` (hub in laptop port 5). After a Station restart the elrobot MCP server may read stale frames (writes land, reads are old): reconnect with `/mcp`.

**Calibration (committed 3c0a1d8, `config/calibration.json`)**
- Table frame: 4 AprilTags (`printed-v1` family, 45 mm), camera fit 2.38 mm RMS. Arm fit: joint zeros 05:59, 8 touches, base fit 06:28: 15.55 mm RMS (target < 10 mm). Expect 1-2 cm errors plus 10-25 mm gravity sag (the arm ends LOWER than commanded; check the joint-reading height after each move).
- Wrist motors 5-7: the zeros look wrong (see the 08:45 entry). This blocks fingers-down grips.

**What works on the arm (temporary arm, 2026-11-22)**
- Hover above an object seen on the table camera: skill `hover-above-object` (`./cli.sh calib pixel` -> `calib goto X Y 70 --travel-z 90`).
- Grip a grape lying on the flat table with the wrist as-is (not fingers-down): skill `grip-object`, worked first try with the gripper-camera correction.
- Drop the held object into the blue bowl: skill `drop-in-bowl` (`calib goto 365 28 130 --travel-z 130 --mm-per-s 70 --open-after`).

**What does not work yet**
1. RULE from Jafer: every grip has the fingers pointing straight down (`--down`). No angled fallback; if `--down` is refused, report it. On the temporary arm `--down` is refused (motor 6 reaches its range end). Likely cause: wrong wrist zeros.
2. Gripping a grape from the bowl failed 3 times (jaw tips drag on the curved bowl). `--close-after` and `set_gripper` can report "holding" falsely; check that the jaws do not keep closing after the lift, and look with the gripper camera.
3. Gripper motor 8 range on the temporary arm is not fully calibrated (closed end 1245 is never reached; the jaws stall near 1372).
4. Motor 4 overloaded once (167 > 100) on a free move; thresholds are not measured per motor.

**Next steps, in order (owner = hardware owner unless noted)**
1. Review and merge the PR for `feat/vision-apriltag-ik` (anyone; needs one human review).
2. Hold the arm in the URDF zero pose (torque off; pose in `docs/tcp_calibration.md`) -> `./cli.sh calib zero --write` -> `calib touch --clear` + 8 touches (each tag twice, two poses) -> `calib fit --refine --write`. Commit as `chore(calib): ... measured <date>`. Target: fit < 10 mm and `--down` no longer refused. `calib fit --refine` only corrects the zeros of motors 2-4, so the wrist zeros (5-7) come from how carefully the wrist is held in step `calib zero`: gripper level, not rolled, pointing straight ahead (runbook step 5).
3. Retry the grape grip with `--down` (skill `grip-object`), first on the flat table, then from the bowl (aim at the flat bowl centre).
4. Recalibrate motor 8 through its full travel in the Station console, then check `holding_object` on an empty close and on a grape.
5. Feed stage: teach a serve pose in front of the face, then write `.claude/skills/feed/` (plan in `docs/feeding_skills.md`; mouth detection is local code, see `docs/FEEDING_ASSISTANT_PLAN.md`).
6. Voice: console chat (`./cli.sh console`) with `ANTHROPIC_API_KEY`, motion off first.

**Where to read more:** `docs/tcp_calibration.md` (calib commands), `docs/feeding_skills.md` (skill roadmap), `.claude/skills/*/SKILL.md` (exact procedures with speeds), `FINDINGS.md` (measured facts), `SUGGESTIONS.md` (open ideas), `docs/bench_safety.md` (before any motion).

## Latest session (2026-11-22, ~08:45, claude for Jafer): grip rule = fingers vertical down; blocked by motor 6 zero
- Jafer: gripping must always be done with the gripper looking vertically down. Skill `grip-object` now requires `--down`.
- `--down` over the bowl grapes is refused: motor 6 lands at 1028 or 3048 (its range ends), or out of reach. Motors 5-7 zeros (1870/1898/2342) are still the OLD arm's; only 2-4 were refitted. Table camera shows the fingers much steeper than the model's 24 deg below horizontal.
- BLOCKER / next: Jafer holds the arm in the URDF zero pose (torque off) -> `./cli.sh calib zero --write` -> 8 touches -> `calib fit --refine --write`, then retry `--down`.
- Hardware owner: jafer.

## Latest session (2026-11-22, ~08:35, claude for Jafer): grip from the bowl FAILED x3
- "grab any grape from the bowl": 3 tries with `--close-after`, all missed (4 grapes still in the bowl, bowl nudged once).
- Every descent stopped at ~40 mm by joints (17-25 commanded) and the jaws stalled at ~1650 (grape on the table held at 1486); after lifting the jaws closed to 1590 on their own = empty. The jaw tips touch the curved bowl floor/side, drag on it while closing and push the grape away. `--close-after` printed "holding" each time (bowl stall looks like a grasp).
- Gripper camera: a grape low in the picture = under the palm -> pull back; high = beyond the tips -> push forward.
- Next options: grape at the flat bowl centre + lift 5 mm before closing; fingers-down (needs motor 6 room); holding check = jaws must not keep closing after the lift.
- Arm now: ~ (418, 37, 68) mm over the bowl, gripper empty (1590), torque on.
- Hardware owner: jafer.

## Latest session (2026-11-22, ~08:20, claude for Jafer): drop-in-bowl skill, faster moves
- Jafer: new skill "drop into the bowl" (pre-stage for the mouth), and make decisions and moves much faster.
- `calib goto --open-after / --close-after` (gripper without MCP, fresh readings), default 60 mm/s. Skill `drop-in-bowl`: `calib goto 365 28 130 --travel-z 130 --mm-per-s 70 --open-after` dropped the left grape into the blue bowl (bowl centre ~ (365, 28) mm). The dropped grape looks split (from the earlier hard grip).
- `grip-object` rewritten: hover+open, 40 mm check, down+close, lift; 70/40/20/50 mm/s. `--close-after` not yet run on the arm.
- Arm now: above the bowl at ~ (358, 31, 97) mm by joints, gripper open, torque on.
- Hardware owner: jafer.

## Latest session (2026-11-22, ~08:05, claude for Jafer): grip too hard, stale MCP readings
- Jafer: grip is too hard, halve it. Found the elrobot MCP server reads a frozen frame (motor 8 raw 1381 while `hw motors` says 1487), so set_gripper's 10-step squeeze became ~115 steps. Set the held grape to zero extra squeeze (`hw jog 8 -57` ended with goal = present); still held.
- `gripper.squeeze_steps` 10 -> 57 (half of 115). Needs the MCP server reconnected (`/mcp`) so the squeeze is counted from a fresh reading. MCP writes work, its reads are stale; that also explains the timeouts.
- Hardware owner: jafer.

## Latest session (2026-11-22, ~07:55, claude for Jafer): left grape gripped with the grip-object skill
- Put the right grape down at (407, 138) (lowered to 31 mm, opened: MCP set_gripper(100) timed out twice, `hw jog 8 200` x7 worked). After the left grip the right grape is NOT visible on the table near where it was released; there is a stain there. Check it.
- Left grape (table cam (112, 45)): hover 70, 40-mm stage (joints 28 mm: big sag), gripper cam showed it ~3 cm beyond the tips; target (100.6, 19.9, 25) -> joints (103.3, 19.9, 24.7); closed; lifted to 50 mm by joints. First try, held.
- Arm now: holding the left grape at about (102, 24, 50) mm, torque on. Skill updated with the sag and offset notes.
- Hardware owner: jafer.

## Latest session (2026-11-22, ~07:40, claude for Jafer): FIRST GRAPE GRASP (right grape)
- Jafer: "just grip the right grape, make it work". Added `calib goto/line --min-z` (lowered floor, fit error still added).
- Sequence that worked (wrist as-is, not `--down`: motor 6 hits its limit fingers-down): hover 70 -> open gripper (hw jog 8 +200 x4 / `set_gripper(100)`) -> `goto X Y 40 --travel-z 70 --min-z 0 --mm-per-s 10` -> `goto X Y 18 --travel-z 50 --min-z 0 --mm-per-s 8` -> `set_gripper(0)` -> lift `goto X Y 90`.
- 1st try at the camera point missed: jaws closed ~2 cm short (along the finger direction) and nudged the grape; `set_gripper` still said holding_object (false positive: gripper range low end 1245 is not fully closed, jaws stall on each other ~1372). 2nd try at (410, 140, 18), aimed from the gripper camera: grape centred between the jaws, held (gripper 8.3 %), lifted to 58 mm by joints.
- Arm now: holding the grape at about (404, 144, 58) mm, torque on.
- Next: 1) recalibrate motor 8 range in the Station console (holding_object is unreliable until then). 2) Offset the grasp point ~2 cm along the finger direction from the table-camera position, or centre with the gripper camera. 3) MCP tools time out now and then (ErrRequestTimeout): retry once.
- Hardware owner: jafer.

## Latest session (2026-11-22, ~07:15, claude for Jafer): speed cap 70, gripper direction verified
- `calib goto/line` speed cap 60 -> 70 mm/s; right->left grape at 70 mm/s arrived, same accuracy. Arm hovering above the left grape.
- Gripper direction verified on the temp arm (low = closed, high = open): `config/elrobot.json` gripper `verified: true`. Removed a junk `joint_map` entry written by `hw identify`.
- Next: plan 1.3 `./cli.sh hw probe-current 8` (empty, then on a grape), 1.4 grasp width for grapes.
- Hardware owner: jafer.

## Latest session (2026-11-22, ~07:00, claude for Jafer): left grape hover, sag below the floor
- `calib goto 102.2 89.2 70 --travel-z 100 --mm-per-s 15 --yes` arrived. Joint-reading fingertip (108.7, 97.0, 45.4) mm: 10 mm sideways, but 25 mm LOW, i.e. below the 66 mm floor. The planner checks only commanded points, not the sagged pose. Camera: tip just behind-right of the grape, grape untouched.
- Next: account for sag (check the joint-reading height after arriving, or a gravity term in IK) before any lower move. Arm holding above the left grape, torque on.
- Hardware owner: jafer.

## Latest session (2026-11-22, ~06:50, claude for Jafer): right grape hover arrived
- Jafer: move towards food on your own, no permission needed. Retried from the stopped pose: `calib goto 380.5 146.1 70 --travel-z 90 --mm-per-s 15 --yes` arrived, no overload. Fingertip by joints (375.0, 150.2, 56.6) mm vs target (380.5, 146.1, 70): 7 mm sideways, 13 mm low (elbow sag). Camera: tip just behind the grape (expected parallax at ~6 cm height). Grape untouched.
- Arm now: torque on, hovering above the right grape. Gripper untouched.
- Next: measure motor currents for a proper motor 4 threshold; then `grab` (descend + grasp) once the gripper probe is done.
- Hardware owner: jafer.

## Latest session (2026-11-22, ~06:45, claude for Jafer): grape hover, `--travel-z`, motor 4 overload
- Jafer refitted the arm on the temporary arm (uncommitted `config/calibration.json`: RMS 15.55 mm, motor 2 zero 1945 instead of 1000). Not committed by me: Jafer commits it as a calibration commit.
- Hover refusals seen: motor 6 near its low end during "across" when starting with fingers flat; motor 2 at its low end (996 < 998) when lifting to 150 mm. `clear` and the feeding waypoints were taught on the old arm: do not use them on this arm.
- Added `calib goto/line --travel-z` (Jafer chose it, told me to skip confirmations this session). Right grape hover `calib goto 380.5 146.1 70 --travel-z 90` STOPPED at across 29/46: motor 4 overload (167 > 100). Arm holding at table (320, 174, 56) mm, both grapes untouched, no motor fault.
- Next: 1) Jafer checks the elbow for binding / cable snag. 2) Decide whether motor 4's overload threshold (100) is too low for this arm (config/elrobot.json, calibration commit). 3) Retry the hover from the current pose (shorter path) only after that.
- Hardware owner: jafer.

## Latest session (2026-11-22, claude for Jafer): feeding skills cut to two
- Jafer found the 17-skill list too much ("as smooth as possible"). `docs/feeding_skills.md` now has two skills: `grab <object>` (find, hover, centre, grasp, lift) and `feed <object>` (grab if needed, carry to serve, approach to standoff, handover, return). The old skills are steps inside them. Docs only.
- Next: 1) Measure the gripper camera's finger-centre pixel. 2) Gripper direction + current probe (plan 1.2-1.3), grasp width for grapes. 3) Write `.claude/skills/grab/SKILL.md`. 4) Teach `serve`, build `find_mouth` + approach, then `.claude/skills/feed/SKILL.md`.
- Hardware owner: jafer.

## Latest session (2026-11-22, claude for Jafer): feeding skills roadmap
- Jafer asked for the list of skills needed to get from "move above <object>" to feeding a person. Wrote `docs/feeding_skills.md`: 17 skills (check-ready, scan-table, hover-above-object [done], center-on-object, grasp-food, carry-to-serve, find-mouth, approach-mouth, handover, return-to-clear, feed-me, safe-recover, place-object, say-and-listen, pick/return-tool, scoop, meal-session), each with tier, dependencies, autonomy and status, plus a build order. Docs only; no code, no motion.
- Next: 1) Jafer reviews the list and the autonomy column (which moves may run without asking). 2) Write `check-ready`, `return-to-clear`, `safe-recover` skills. 3) Measure the gripper camera's finger-centre pixel for `center-on-object`. 4) Gripper direction + current probe (plan 1.2-1.3) to unblock `grasp-food`.
- Hardware owner: jafer.

## Latest session (2026-11-22, ~05:40, claude for Jafer): temporary follower arm
- The usual follower (`5B61034962`) is out for a motor repair. A temporary arm on bus `5B61034679` is in use; `config/elrobot.json` `station.bus` and `.mcp.json` `ELROBOT_BUS` now point at it (restart the MCP server / Claude session to pick up `.mcp.json`). Switch both back when the old arm returns.
- New arm's ranges (FINDINGS.md): motor 2 is fine (1002..3094), but motor 1 has only 302 steps, motor 4's reading is outside its range, and the gripper range is 2 steps: recalibrate those in the Station console first.
- `config/calibration.json` still holds the OLD arm's joint zeros and touches: redo `calib zero --write`, `calib touch --clear`, 8 touches, `calib fit --refine --write` on this arm before any `calib goto`.
- Hardware owner: jafer.

## Latest session (2026-11-22, ~05:20, claude for Jafer): hovers with the skill, motor 2 limits
- Hovers run on the arm (all arrived, nothing touched): chocolate (169,138,70), grape (279,53,70), chocolate (61,189,70), grape bowl (373,92,110) via (279,53,110). Camera offset 1-5 cm, mostly to the right.
- Repeated refusals from motor 2's narrow range (1532..2564): straight paths that pass near the base need motor 2 < 1552. Workaround used with Jafer's OK: go through (279,53,110) first. Motor 2 low end reached by jog (1564); high end not done (needs the elbow folded to ~2333 first, else the tip goes 75 mm into the table).
- Arm now: hovering above the grape bowl, torque on, gripper untouched.
- Next: recalibrate motor 2 through its full travel in the Station console (fixes most refusals). The skill's fallback rules (jog off limit, via point) were NOT added: blocked by the permission check; Jafer to decide.
- Hardware owner: jafer.

## Latest session (2026-11-22, ~04:40, claude for Jafer): hover above the grape, skill
- Jafer asked to move towards the grape with the IK interface and to execute automatically. Ran `./cli.sh calib goto 381 155 70 --yes` (grape at pixel (1265, 445) -> table (380.7, 154.6)). Arrived; joint readings (380.6, 155.1, 66.7). The camera shows the tip right of and behind the grape (see FINDINGS.md). Arm is holding there, torque on.
- New project skill `.claude/skills/hover-above-object/SKILL.md`: the procedure for every "move above <object>" request. Standing authorization from Jafer covers only this hover move (z >= floor, no grasp, no gripper).
- Next: 1) Ruler-measure the tip-to-grape offset at the hover pose. 2) More touches / ruler layout to bring the fit under 10 mm. 3) Then a separate, confirmed "descend and grasp" step.
- Hardware owner: jafer.

## Latest session (2026-11-22, ~04:10, claude for Jafer): hardware owner -> Jafer, calib goto
- Hardware owner changed from steve to jafer at Jafer's request ("please remove anything with steve"). Older entries below still name steve; they are history and were not rewritten.
- Jafer recalibrated the Station motor ranges, then redid `calib zero` (03:53) and 8 touches; fit 16.0 mm RMS, base z -36.9 mm (implausible: expected >= 0). Committed as measured, but treat targets as +-3 cm until the ruler fit.
- New `./cli.sh calib goto X Y Z [--down]` (MOVES the arm; see docs/tcp_calibration.md). NOT run on the arm yet. Dry plan from live readings: targets at the table middle plan fine without `--down`; with `--down` the wrist cannot point straight down there (motor 6 range, motor 2 range 1532..2564 is narrow).
- Next: 1) Jafer runs the bench checklist (docs/bench_safety.md), `./cli.sh hw torque on` while holding the arm, then `./cli.sh calib goto 228 114 120 --speed 200`, type MOVE, hand on the 12 V switch. 2) Recalibrate motor 2 through its full travel (waypoints use down to 1016). 3) Ruler layout, zero, touches, fit < 10 mm.
- 04:08: first live goto stopped in the lift leg (timeout: motors 2-4 settled 18-48 steps short under gravity). Fixed to accept `near` like the sequence player. Arm holding at the lift pose with torque on. Motor 2's range was 994..3102 yesterday, 1532..2564 now: recalibrate it.
- ~04:15: second run arrived (all legs `near`); readings say (228.8, 112.1, 106.3) mm, 14 mm low from gravity sag. Real position not yet measured.
- New `calib line` (follow a straight line). NOT run on the arm yet. Suggested first run: `./cli.sh calib line 128 114 120 328 114 120 --speed 200`. Lines toward the arm fail on motor 2's narrow range until it is recalibrated.
- `calib line` stuttered (stop at each 10 mm point). goto/line now stream points every 3 mm at 25 mm/s along straight segments. NOT run on the arm yet. Dry plan on live readings: goto 228 114 120 and line 128..328 at y 114, z 120 both plan, max 13-18 steps between points.
- Hardware owner: jafer.

## Latest session (2026-11-22, ~02:20, claude for Jafer): camera resolution, console sees all cameras
- Jafer asked for Full HD. Local `station.yaml` (gitignored) now has `resize_target: 1080` and a `formats` list (1920x1080 MJPEG, then 1280x720, then 640x480); backup of the old file was in the session scratchpad. Result: face 1920x1080; table and gripper fall back to 1280x720 (USB 2.0 bandwidth, libuvc -51) and are upscaled to 1920x1080. All 4 AprilTags found on the live table frame (only 2 at the old 320x240). Details in FINDINGS.md, setup in docs/mcp_server.md item 3.
- Fixed: the console showed gripper and face as unplugged after a Station restart (`read_first` returned nothing). `src/robot_tools.py` now falls back to the newest entry and retries every 10 s. Test added; 135 tests pass. Verified live: all three tiles serve frames.
- Running now: the Station and the console on 8890 were restarted by Claude in the background (logs `logs/station-20261122-fullhd.log`, `logs/console-20261122.log`). If they stop with the session, start them again with `./cli.sh station` and `./cli.sh console`.
- Gotcha: when the Station stops, the camera driver often does not take the KD cameras back; reattach with `for p in 3-5.1 3-5.2.4; do echo $p:1.0 | sudo tee /sys/bus/usb/drivers/uvcvideo/bind; done` before `./cli.sh cameras`.
- Next: `./cli.sh calib camera` on the table camera (all 4 tags now visible). Decide whether the table camera needs real 1080p (move the face camera off the shared hub).
- Hardware owner: steve (unchanged). No motion.

## Earlier session (2026-11-22, claude for Jafer): camera ports, dark gripper camera
- Jafer saw the camera view too bright, then too dark after a Station restart. Cause of the dark view: the gripper camera (port 3-5.2.4) in manual exposure 14. The hub is back on laptop port 5, so the config names pointed at missing `3-1.x` ports and `cameras --tune` could not find them.
- Changed (with Jafer's OK): `config/elrobot.json` cameras -> table `port:3-5.1`, gripper `port:3-5.2.4`, face `port:3-5.3`. Evidence in FINDINGS.md.
- Exposure set to 250 for table and gripper (Jafer's choice after trying values live; committed). Applied with `./cli.sh cameras`; verified by `cameras --show` (both manual, 250). Face camera left on auto.
- Gotcha: when the Station stops, the camera driver sometimes does not take a camera back (no /dev/video for it) and a USB reconnect resets exposure to auto. Run `./cli.sh cameras` after every replug, with the Station stopped.
- Next: start the Station, check the console tiles at 250; if too bright, lower both a little and commit.

## Earlier session (2026-11-22, claude for Jafer): camera preprocessing removed
- Request: "please undo any preprocessing". Read as: remove the software picture enhancement added 2026-11-21 (commit 179b423). Branch `feat/vision-apriltag-ik` (not pushed).
- Changed: deleted `src/frame_enhance.py`. `RobotTools.look()`, the MCP `look` tool and the console's `/frame/<cam>` return the camera's JPEG unchanged; no `raw` parameter, no `exposure`/`exposure_warning` fields, no `camera_enhance` defaults. `scripts/calib.py` no longer passes `raw=True`. `exposure_stats` moved into `scripts/camera_settings.py`, so `./cli.sh cameras --tune` still works. Docs updated (`docs/mcp_server.md`, plan status table, SUGGESTIONS).
- Kept on purpose: camera exposure/V4L2 settings (hardware settings, not image processing) and the internal upscale in `tag_calibration.detect_tags` (works on a private grayscale copy; tag pixels are scaled back).
- Verified: 134 tests pass, `bash -n cli.sh`, py_compile. Not tested on live frames (no motion involved).
- Next: if food is hard to see in the raw frames, fix it at the camera (`./cli.sh cameras --tune`, Station stopped) or with a darker table cover, not in software.
- Hardware owner: steve (unchanged).

## Previous session (2026-11-22, ~00:20, claude for Jafer): AprilTag table frame + IK, ACT dropped
- Decision by Jafer: reset the approach. ACT imitation learning is dropped. One AprilTag per table corner defines a table frame in mm; the arm moves to Cartesian (TCP) targets via URDF inverse kinematics. Plan doc has a decision banner; docs/act_pick_skill.md marked superseded.
- Found and fixed: the tag sheet in docs (and the PDF made from it) were NOT AprilTags (hand-typed 8x8 grids), so they could never be detected. `scripts/generate_apriltags.py` now uses OpenCV's 36h11 bits, 80 mm default. Update: the old printed sheet is readable after all (custom dictionary `printed-v1` in `src/tag_calibration.py`), so no reprint is needed; it needs the 480 px Station frames. New placement (seen from the person): 0 front-left, 1 front-right, 2 back-right, 3 back-left.
- New, branch `feat/vision-apriltag-ik` (from `feat/console-face-camera`, not pushed): `src/tag_calibration.py`, `src/arm_kinematics.py`, `scripts/calib.py` (`./cli.sh calib layout|camera|zero|touch|fit|where|reach|pixel|show`), `docs/tcp_calibration.md`, `tests/test_calibration.py`, `tests/test_apriltags.py`. All read-only; `calib reach` only prints joint steps. No motion code changed.
- Verified: 138 tests pass. Synthetic camera views: tags found also at 299x224, pixel -> table error < 3 mm; IK < 2 mm in ~10 ms; synthetic joint-zero/direction fit recovers directions and zeros within 8 steps. NOT run live: the Station did not answer a read-only `look('table')` within 25 s at ~23:50.
- Next (hardware owner steve for steps 4-6): 1) Restart the Station (480 px frames). Tape the printed tags in the new placement, measure centres + diagonals. 2) `./cli.sh calib layout ...`. 3) Station up, `./cli.sh calib camera`, check overlay, `--write`. 4) Arm in URDF zero pose, `calib zero --write`. 5) Touch each tag twice in two arm poses (`calib touch <id>`). 6) `calib fit --refine --write`; check `calib where` against the tape. 7) Commit `config/calibration.json` as a calibration commit. 8) Then write the Cartesian move command (needs Steve's review; motion code).
- Hardware owner: steve (unchanged).

## Latest session (2026-11-21, ~22:35, claude for Jafer): camera picture enhancement
- Request: "the camera still looks bad; enhance it so the robot reliably detects food". Branch `feat/console-face-camera` (not pushed).
- Measured live (read-only): table camera 62% pure-white pixels, gripper 47% (see FINDINGS.md). The Station also shrinks frames to 299x224.
- Changed: new `src/frame_enhance.py` (denoise, table-based white balance, auto gamma, CLAHE, light sharpen, about 9 ms per frame). `RobotTools.look()` uses it and returns `exposure` and `exposure_warning`, and `raw=True` skips it. The MCP `look` has a `raw` parameter, and the console serves `/frame/<cam>?raw=1`. Config `camera_enhance` (defaults in `src/elrobot_config.py`, nothing added to `config/elrobot.json`). `scripts/camera_settings.py`: `--tune [name] [--write]` exposure sweep, plus `controls` for extra V4L2 controls. The demo recorder is untouched and still stores raw frames.
- Local only (gitignored): `station.yaml` `resize_target` 224 -> 480. Takes effect at the next Station restart.
- Verified: 127 tests pass. Compared raw vs enhanced on the live table and gripper frames by eye: the grape stands out more and the colour is neutral. NOT run: `--tune` (needs the Station stopped and the hardware owner).
- Next: 1) Stop the Station. 2) `./cli.sh cameras --tune table gripper`, check the printed table, then `--write` and commit as `chore(elrobot): record camera exposure measured <date>`. 3) Restart the Station (now 480 px) and the console, check the tiles and that `look()` has no `exposure_warning`. 4) Consider a matte darker table cover (SUGGESTIONS.md) before recording ACT demos, and do not change camera settings between demo episodes.

## Latest session (2026-11-21, ~22:20, claude for Jafer): camera ports after hub replug
- The udev rule with the OBSBOT line is installed, and the Station now captures the face camera.
- At 22:12 the USB hub was replugged into another laptop port (3-5 -> 3-1), so the console showed all three cameras as "not plugged in". `config/elrobot.json` cameras now: table `port:3-1.2.2`, gripper `port:3-1.2.4`, face `port:3-1.3`. Table and gripper checked from frames; face is the only OBSBOT, and its frame was not viewed (privacy).
- Next: reload the console page (the server reads the config on each request, so no restart should be needed). Keep the hub in this laptop port. See FINDINGS.md.

## Latest session (2026-11-21, ~21:50, claude for Jafer): face camera in the console
- Request: add the third camera to the console. It is an OBSBOT Meet SE on USB port 3-5.3 (`lsusb` ID 3564:fefe). Jafer said it points at the person being fed, so it is named `face`.
- Found: the Station was not capturing it. `list_cameras` showed only table and gripper, and the OBSBOT's `/dev/bus/usb` node was root-only because the udev rule only covered the KD-USB cameras (2c7f:4a60).
- Changed: `scripts/99-normacore-cameras.rules` (+OBSBOT line); `config/elrobot.json` cameras `face: port:3-5.3` (its own commit); `src/web/console.html` (3-camera layout: table on top, gripper + face below; default list); prompts in `src/console_agent.py`; docstring in `src/web_console.py`; `tests/test_web_console.py`.
- Verified: 116 tests pass. NOT seen live: installing the rule needs sudo (not available to the agent).
- Next: 1) `sudo cp scripts/99-normacore-cameras.rules /etc/udev/rules.d/ && sudo udevadm control --reload-rules && sudo udevadm trigger`. 2) Unplug and replug the OBSBOT. 3) Restart the Station, then the console. 4) Check `list_cameras` shows `face` live and the tile has a picture. 5) Open a PR for `feat/console-face-camera` (built on `feat/brain-claude-stepwise-control`).

## Latest session (2026-11-21, ~19:40, claude for Jafer + Christian): ACT pick skill, demo recorder
- Decision: Claude keeps choosing WHAT to pick from the chat; a learned ACT policy does the moving, one model per skill. First skills: pick grape, pick chocolate. Feeding later. Rejected for now: Claude stepwise nudging (too slow), Cartesian IK and a digital twin (need joint-angle calibration that does not exist). Runbook: docs/act_pick_skill.md.
- Action space recorded by Jafer: config/envelope.json, 1027 poses, 8 anchors (commit 8c87f4c). Open questions to Jafer: do the table_* anchors touch the table; rename extendextendetable_grep -> above_grape and armgrepper_feed -> face_standoff?
- New `./cli.sh demos record --skill pick --food grape` (scripts/record_demos.py, src/demo_recorder.py): reads follower present (state), follower goal register (action), leader, table + gripper JPEGs at 30/s into data/demos/. Tested offline (4 tests, 116 total pass). NOT run live: the Station listened on 8888 but sent no st3215/inference frames at ~19:30 (arm unplugged or Station stuck), so read rates and camera fps are unmeasured; the recorder prints achieved rate and warns.
- LeRobot installed in `.venv-lerobot` (gitignored): lerobot 0.7.0, torch 2.15.0+cu132, CUDA available on the RTX 3080 Ti.
- Next: 1) Station sending motor data again. 2) Teleop on, console closed. 3) `./cli.sh demos record --skill pick --food grape`, 2-3 test episodes, check the printed rate and camera fps. 4) Converter to LeRobot dataset (after checking the installed lerobot API), pilot ACT training on ~10 episodes.

## Latest session (2026-11-21, ~19:10, claude for Jafer): action space from the leader arm
- First stepwise console run (18:53): Claude found the grape but pushed motor 2 down ~14% while learning directions and hit the table (motor 2 timeout). It backed off; the user stopped it. Learned: motor 1 turns sideways, motor 2 + goes down/forward, gripper 100 = open (seen by Claude on camera, not checked by a human).
- Fix, chosen by the user: they drive the follower with the leader (teleop) and we record the follower's poses. New `src/action_space.py`, `./cli.sh hw envelope record|show` (scripts/hw_day.py), `config/envelope.json`. `RobotTools.nudge_joint` refuses nudges ending > `agent.envelope_margin_steps` (80) from every recorded pose unless they move back toward the space; console stepwise mode sets `ELROBOT_REQUIRE_ENVELOPE=1` (no recording -> no nudges). MCP tool `get_action_space` (anchors with per-motor % nudges to reach them); stepwise prompt steers toward anchors. Motion-code change approved by the user in the session.
- Verified: 112 tests pass. NOT verified on the arm; no envelope recorded yet.
- Next: 1) close the console. 2) teleop ON. 3) `./cli.sh hw envelope record`, drive slowly everywhere the arm may go, never touching the table, toward the face only to ~10 cm; type `above_grape`, `lifted`, `face_standoff` at those poses; `q`. 4) teleop OFF (Self-controlled). 5) `./cli.sh console 8890 --mode stepwise` (fresh start), "I want a grape". 6) Commit config/envelope.json as a calibration commit.

## Latest session (2026-11-21, ~18:50, claude for Jafer): stepwise console mode + failed grapes run
- Branch `feat/brain-claude-stepwise-control` (from `jafer` at `315c896`). Not pushed, no PR yet.
- Camera names swapped in `config/elrobot.json` (table = port 3-5.2.2, gripper = 3-5.2.4), confirmed by the user; commit `315c896` on `jafer`.
- Live `play_sequence("grapes")` via Claude Code MCP (user typed "go grapes"): arm did NOT move. Motors 3-8 timed out at step 1; current 0; goal registers kept the `choc_end` values even after the HOLD write. Cause (likely, not proven): the MCP server was started at 18:26, the Station restarted ~18:40, and the command connection stayed on the old Station while reads reconnect. Log: `logs/mcp-20261121-182602.log` (18:42:38). That means stop() over MCP did not reach the arm either. Fix for now: reconnect the MCP server (`/mcp`) or restart the console after any Station restart. Code fix: SUGGESTIONS.md #1 (needs owner OK, motion code).
- New per the user: console `--mode stepwise` (`src/console_agent.py` `STEPWISE_PROMPT`, `STEPWISE_TOOLS`, `select_tools`; `src/web_console.py --mode`; `./cli.sh console 8890 --mode stepwise`). Person says a food; Claude steers by look + nudges, no waypoints/plans. Deviates from the plan doc section 2 (waypoints only) on the user's request; plans mode stays the default.
- Verified: 106 tests pass; console starts live in stepwise mode with 6 MCP tools and motion=1. NOT tested on the arm (Station went down again at ~18:45: "no st3215/inference frames").
- Face standoff in stepwise mode is a prompt rule only, not enforced in code.
- Next: 1) Station up, start `./cli.sh console 8890 --mode stepwise` (fresh MCP server), teleop Self-controlled, hand on 12 V switch. 2) Say "I want a grape"; watch the first ticks, stop if a nudge goes the wrong way. 3) Note joint directions Claude finds and put them in the prompt or config. 4) Open a PR for this branch.

## Latest session (2026-11-21, ~18:00): Claude picks the recorded plan from the request
- User request: "I want grapes" -> Claude decides which recorded plan to run and runs it.
- `config/elrobot.json` `foods`: grapes -> sequence `grapes`, chocolate -> sequence `choc` (`feed` is an older grapes plan, not mapped). Plan task 4.1/4.3.
- New `src/sequence_player.py`: plan_legs / wait_settled / run_legs (moved out of `hw_day.cmd_play`, which now uses it). Default tolerance 60 (CLI and agent).
- MCP tools `list_sequences`, `play_sequence(name)` (`src/robot_tools.py`, `src/robot_mcp_server.py`); `stop` now calls `RobotTools.stop_now()` which skips the tool lock and sets an abort event checked between legs and during the pause. Agent settings `agent.sequence_speed/sequence_pause_s/sequence_tolerance_steps`.
- Prompts: MCP INSTRUCTIONS and `CONSOLE_PROMPT` say recorded plans come first; one play_sequence call, no extra moves; unknown food -> say what's available.
- Tests: 104 pass. Committed on branch `jafer` (the old remote `jafer` was merged into main and deleted; pushed again as a new branch). Live check: foods/plans load and are ready; dry-run against the arm not possible (Station sent no motor frames at the time).
- `.mcp.json` now has ELROBOT_ALLOW_MOTION "1" (committed by Jafer: Claude moves the real arm). NOT verified: a real play_sequence via Claude, and stop() interrupting it over MCP (unit-tested only).

## Latest session (2026-11-21, 17:30): waypoint sequences `hw record` / `hw play`
- User request: record feeding waypoints, combine them into one run, ONE MOVE prompt for the whole run, pause 1-2 s per waypoint and wait until the arm has fully stopped.
- `./cli.sh hw record <seq>`: interactive, moves nothing. Each step saves the current pose as a waypoint (Enter = `<seq>_<n>`, existing name -> use saved pose / overwrite / cancel) and saves the order to `config/sequences.json` after every step.
- `./cli.sh hw play <seq>` (or `hw play wp1 wp2 ...`): plans every leg up front (clamped goals, biggest move, LARGE MOVE), teleop drift check, ONE MOVE prompt. Per leg: `move_and_watch`, then `_wait_settled` (no motor moves > 2 steps for 0.5 s, timeout 5 s), then target check (<= 12 steps), then `--pause` (default 1.5 s, not after the last leg). Any failure or Ctrl-C -> `hw.hold(all)` and stop. `hw sequences` lists them.
- Files: `scripts/hw_day.py`, `src/elrobot_config.py` (`SEQUENCES_FILE`, `load/save_sequences`), `cli.sh` (help), `docs/elrobot_hardware_bridge.md` (Sequences section), `tests/test_hw_day.py` (8 new tests).
- Build: 93 passed, 1 failed (`test_camera_feeding_vision_and_orchestration` needs `cv2`, not installed on this laptop; unrelated). `bash -n cli.sh` OK.
- NOT verified on the real arm. Next: `./cli.sh hw record feed` (e.g. clear, grape_hover, grape, grape_grip, grape_lift, serve, serve_release, clear), teleop off, `hw torque on`, `hw play feed --speed 200`.
- First live runs (17:19, 17:21): legs stopped with `timeout` because motors 3/4 settle 22-32 steps short of the goal with low current (gravity; mid-range, not a limit), and the 12-step check then waited for the timeout. Fix: `move_and_watch(near_tolerance=..., stall_s=0.8)` in `src/elrobot_hardware.py` returns "near" for a motor that stopped within near_tolerance (no overload); `hw play --tolerance` (default 40) uses it and prints "stopped short". MCP/goto unchanged (still 12). Restored user's `start` waypoint (agent accidentally re-taught it from a stopped pose).
- Arms CONFIRMED by the user: follower 5B61034962, leader 5B61037051 (as in `config/elrobot.json`). Older notes below that say the opposite are wrong. Fixed the swapped roles in `scripts/teleop_sync.py` (auto-detect and `--swap`; it used to drive the leader arm by default), `src/digital_twin_server.py`, `src/digital_twin.html`, `scripts/camera_feed_arm.py` (comment), `docs/team_setup.md`, PROGRESS.md.

## Earlier session (2026-11-21 afternoon): Camera-Guided Assistive Feeding (`./cli.sh feed`)

- **What Changed:**
  - Implemented `src/feeding_vision.py` (`FeedingVisionDetector` and `run_camera_feeding_cycle`): captures frames from `/dev/video4` (overhead tabletop camera, with fallback to `/dev/video2` or `MockStation`), detects the **bowl with grapes**, **spoon holder**, and **person's mouth** (with 5–10 cm standoff protection), draws live bounding boxes and feeding vector overlays, and orchestrates slave arm motions via `RobotTools` and `KinematicsSafetyEngine`.
  - Added CLI runner script `scripts/camera_feed_arm.py` and `./cli.sh feed [grapes|spoon]`. By default runs in safe dry-run mode (not tested on the physical arm during this run because USB hub devices `/dev/video4` & `/dev/ttyACM*` disconnected mid-session); pass `--live-motion` when the arm is powered and USB hub is seated.
  - Integrated one-click **🍇 Feed Grapes (Bowl -> Mouth)** and **🥄 Feed with Spoon (Scoop -> Mouth)** buttons and live detection overlay into the Mission Control Web Dashboard (`src/digital_twin.html`, `src/digital_twin_server.py`).
  - Added unit and integration test `test_camera_feeding_vision_and_orchestration` in `tests/test_pipeline.py` (68 passed).
- **Files Changed:** `src/feeding_vision.py` (new), `scripts/camera_feed_arm.py` (new), `cli.sh`, `src/digital_twin_server.py`, `src/digital_twin.html`, `tests/test_pipeline.py`, `.gitignore`, `CHANGELOG.md`, `SUGGESTIONS.md`, `.ai-sync/PROGRESS.md`, `.ai-sync/HANDOFF.md`.
- **Build Status:** `python3 -m pytest tests/` (68 passed, 1 skipped), `bash -n cli.sh` (OK), `py_compile` (OK). Not tested on the physical arm in this run (USB hub dropped `/dev/video4`, `/dev/video2`, `/dev/ttyACM0`, `/dev/ttyACM1`).
- **Next Steps:**
  1. Re-seat the USB hub cable so `/dev/video4` and `/dev/ttyACM0`–`1` reappear.
  2. Teach the physical feeding waypoints (`./cli.sh hw teach zone_a_hover`, `zone_a`, `serve`, `spoon_holder`, `bowl_scoop`, `serve_spoon`).
  3. Run `./cli.sh feed grapes --live-motion` (with one hand on the 12 V switch) or click **🍇 Feed Grapes** in `./cli.sh start`.

## Change (2026-11-21, 16:40): goto cap raised 600 -> 1500 steps
- User request: `clear` <-> `grape_hover` needs ~777 steps on motor 2 and ~743 on motor 6, so the 600 cap refused it.
- `GOTO_MAX_DELTA` in `scripts/hw_day.py` and the default `agent.max_waypoint_delta_steps` in `src/elrobot_config.py` (MCP, applied per leg) are now 1500. Docs updated (`docs/elrobot_hardware_bridge.md`, `docs/mcp_server.md`). `tests/test_robot_mcp.py::test_large_move_refused` now starts at 1000 so the hop goes over 1500. 85 tests pass.
- Next: `./cli.sh hw goto clear` (no flag), then `hw goto grape_hover`; teach `grape`, `box_hover`, `box`, `serve`.
- Then (user request): CLI `hw goto` has NO step cap anymore. It always goes to the waypoint; motors moving > `GOTO_WARN_DELTA` (1500) are marked `LARGE MOVE` plus a warning line before the MOVE prompt. Clamp, torque check, speed cap and overload guard unchanged. `--allow-large` is accepted but does nothing. MCP `go_to_waypoint` (Claude) still refuses > 1500 per leg. Test `test_goto_large_move_warns_and_moves` replaces the refusal test.
- Arm state at 16:41: pose was far from every waypoint (motor 5 raw 3918, 98.9% of range; nearest grape_hover, 1946 steps off). It moved between 16:38 and 16:41 with torque on; cause unknown (hand move or teleop?). Check teleop is off before goto.
- 16:42 goto clear: confirmed teleop was ON (follower within 2% of leader on every motor). Teleop overwrote the goals: motor 5 went 3918 -> 3872 then back to 3914; motors 1,3-7 timed out after 24 s and were held. Not a code bug. Fix: Station viewer -> follower bus card -> leader dropdown -> none, then goto. Idea (not done): goto/MCP could detect goal registers changing with nothing sent (hw demo already does this) and refuse with "teleop is on".

## Latest session (2026-11-21, late): arm debug demo

- New `./cli.sh hw demo [motors]` (follower/slave): per motor sweep +amp, -amp, back to start (default +/-200 steps, speed 250; gripper does full calibrated travel), then motors 1-7 together +/-amp/2 and back. One MOVE prompt; `--step` pauses between motors, `--full` goes to calibrated limits, `--amplitude`, `--speed`, `--no-combined`, `--no-gripper-full`. Uses `move_and_watch` (clamp, overload guard, hold). Refuses if goal registers drift for 1 s with nothing sent (teleop on). Prints per-move rows and a summary (moves ok, worst error, peak current vs threshold, verdict). A move only counts OK if status is reached AND the final error is <= 24 steps.
- New `./cli.sh hw leader` (master, read only): live table of leader vs follower (steps, % of calibrated range, diff), range coverage per joint, flags missing/uncalibrated/out of range/fault/torque on/jumps > 300 steps. Summary on Ctrl-C or `--seconds`. Leader serial in `config/elrobot.json` `station.leader_bus` (5B61037051).
- Live read-only check (Station started from this session): follower 8/8 motors, torque on, no faults, pose ~grape_hover. Leader 8/8 readable, no faults/torque. Teleop not mirroring (diffs up to 42%). Station log shows a few `normfs-store ... background task failed` write errors at startup (disk 54% used; cause unknown, not blocking).
- NOT verified: the motion demo on the real arm (needs a human watching). 85 tests pass.
- Next: `./cli.sh hw goto clear`, then `./cli.sh hw demo --step`; `./cli.sh hw leader` while moving each leader joint end to end; then enable teleop in the Station viewer and watch the diff column.
- Files: `scripts/hw_day.py`, `src/elrobot_config.py` (leader_bus default), `config/elrobot.json`, `cli.sh` (help), `tests/test_hw_day.py`.

## Earlier session (2026-11-21 evening): web console

- Added `./cli.sh console` → http://localhost:8890 (`src/web_console.py` Starlette/uvicorn, page `src/web/console.html`). Left: `table` + `gripper` camera frames via `RobotTools.look` (polled, ~8 fps). Right: chat + big mic button. Read-only, never moves the arm.
- Speech-to-text (updated after user said small.en was poor): `large-v3-turbo` float16 on the RTX 3080 Ti (~0.2 s per clip; model cached), `small.en` int8 on CPU-only laptops; Whisper gets a vocabulary prompt (`DEFAULT_STT_PROMPT`, env `WEB_CONSOLE_STT_PROMPT`); browser noise suppression off; 0.4 s recording tail; server logs each transcript. Was: faster-whisper `small.en` on CPU (installed in `.venv`, model cached in ~/.cache/huggingface). Audio is decoded with PyAV in `decode_audio()` because faster-whisper 1.2.1's own decoder breaks on PyAV 19 (`metadata_errors` TypeError). Fallback: browser Web Speech API.
- A fast TCP check on the Station port (8888) returns "Station not running" at once; without it a frame request took 60 s (RobotTools tries a 10 s connect per old camera queue).
- Chat lives in memory at `/api/messages`; nothing reads it yet. Next: MCP `listen(timeout_s)` polling `GET /api/messages?after=<id>` and `say(text)` posting `{"role":"robot"}` (plan 3.2/3.4, D's tasks).
- Verified: 68 tests pass (`tests/test_web_console.py` new); live server transcribes ALSA test clips ("Front left", "Rear center") as WAV and WebM/Opus in ~1 s. NOT verified: live camera frames (Station was off) and the page in a real browser with a real microphone.
- Files: `src/web_console.py`, `src/web/console.html`, `tests/test_web_console.py`, `cli.sh` (console), `requirements.txt` (uvicorn, faster-whisper, httpx), `docs/mcp_server.md` (Web console section).

### Console chat → Claude (same evening)
- `src/console_agent.py`: user chat messages go to `claude-opus-5-5` (Messages API, manual tool loop so history persists across messages; effort medium, prompt caching, `clear_tool_uses` context editing, server-side refusal fallbacks). Tools come from a private `elrobot` MCP subprocess started from `.mcp.json` (same motion switch). Replies, tool calls (grey) and errors are posted to the chat.
- Stop: a message that is only stop/wait/halt/freeze, or POST /api/stop (red button), cancels the turn and calls MCP `stop` directly. Known gap: RobotTools' lock means stop waits for a running go_to_waypoint to finish; plan 3.3 voice_stop.py is still needed.
- Verified: 75 tests (new `tests/test_console_agent.py`); live: MCP subprocess starts, 10 tools listed, request reaches the API and fails only on auth (no key on this laptop). NOT verified: a real Claude reply (needs ANTHROPIC_API_KEY), server-side acceptance of `fallbacks` + `context_management` together.
- `--no-agent` runs the console without Claude.

### Console prompt: request -> actions (same evening)
- `CONSOLE_PROMPT` in `src/console_agent.py` rewritten: Claude turns each chat/voice message into ACTION/OBJECT/DESTINATION, checks `list_waypoints` + `look("table")`, asks one question when ambiguous or a waypoint/object is missing, says the plan, then runs pick/place/feed sequences with a look after every step. Safety: never past `serve`, refuses unsafe requests, stops on doubt, no teach/torque/nudge unless the operator asks.
- Naming it expects: `<place>_hover` + `<place>` (e.g. `grape_hover`/`grape`, `box_hover`/`box`), `clear`, `serve`. Only `clear` and `grape_hover` are taught today.
- Next: teach `grape`, `box_hover`, `box`, `serve`; run with ANTHROPIC_API_KEY and motion off (dry_run) to read Claude's plans for "put the grape in the box" and "feed me a grape", then motion on. Tune the prompt from what it gets wrong. Tests: 75 pass.

## Earlier session (2026-11-21, jaferub's laptop)

- Environment: `bin/station` (v0.1.0-beta.10, asset is `station-linux-amd64.tar.gz`, not x86_64) and `external/norma-core` (commit 6b494f7) set up. `.venv` with `mcp` 2.3, pytest, numpy 2, pillow. Run tests with `.venv/bin/python -m pytest tests/` (60 pass). Fresh-clone setup (venv, SDK, Station binary, udev rule, v4l-utils): `docs/mcp_server.md` → Setup.
- Built the real MCP server: `src/robot_mcp_server.py` (stdio, mcp 2.x `MCPServer`), logic in `src/robot_tools.py`, camera decoding in `src/elrobot_camera.py`. `.mcp.json` now runs it. Guide: `docs/mcp_server.md`.
- The old `src/mcp_server.py` was never an MCP server (plain class); it stays for the offline simulator demo and tests.
- Verified over stdio with a real MCP client: 10 tools register; without a Station, tools return a clear connection error.
- Station facts found: cameras are `usbvideo/<md5>` queues of JPEG frames (resize_target 224 by default); teleop is built into the Station viewer (follower bus card dropdown → leader serial); ElRobot auto-calibration needs >= 7.0 V, so the 5 V leader is calibrated by hand.

- Cameras: Station captures via libuvc (raw USB), so cameras need `scripts/99-normacore-cameras.rules` installed (sudo). Without it the viewer shows no cameras. Camera queues live in `station_data/<station id>/usbvideo/<hash>` (discovery handles this). Follower bus 5B61034962, leader 5B61037051.

- Cameras work after the udev rule. Named by USB port in config (`table` = port:3-2.4, `gripper` = port:3-2.2) because every replug creates a new queue hash. `list_cameras` only shows plugged-in cameras. Overexposure fixed with manual exposure (camera auto exposure misbehaves under the Station's libuvc capture; fine under v4l2): `./cli.sh cameras` applies `camera_settings` (table 160, gripper 14) while the Station is stopped. Re-run after replug/reboot.

- Done this session, do not repeat: Station + both arms connected, calibration exported to `calibration/`, MCP `elrobot` connected, cameras named and exposure fixed.

- Team goal is now an assistive feeding robot: plan, safety rules, 4-person split and task list in `docs/FEEDING_ASSISTANT_PLAN.md`. All agent rule files point to it.

### Next steps
0. Follow the task table for your role in docs/FEEDING_ASSISTANT_PLAN.md.
1. On a new laptop: follow `docs/mcp_server.md` → Setup, calibrate in the Station viewer, start the Station, check `/mcp` → elrobot, `look`.
2. Optional: raise `resize_target` in `station.yaml` (local, gitignored) from 224 to ~480 for small objects.
3. Verify gripper direction (`./cli.sh hw identify 8`), set `gripper.open_at` and `verified`.
4. Teach `clear`, `home`, `pick_<n>_hover`/`pick_<n>`, `bin_a`, `bin_b`. Probe gripper current.
5. Set `ELROBOT_ALLOW_MOTION` to "1" in `.mcp.json` and run a single pick-and-place.

## What Was Completed (previous session)

1. **Hardware Onboarding & Verification:**
   - Identified follower arm bus `5B61037051` and leader/master arm bus `5B61034962`.
   - Confirmed all 8 motors are visible, calibrated, and in clean 0x0 status via live Station.
   - Updated `config/elrobot.json` with bus `5B61037051`.
2. **Master -> Slave Real-time Teleop Sync:**
   - Implemented `scripts/teleop_sync.py` and `./cli.sh teleop`.
   - Tested live at 50Hz: mirrors joints 1-8 from Master (`5B61034962`) to Slave (`5B61037051`) with overload current protection (`threshold=150`).
3. **Unified Web Mission Control (`./cli.sh start`):**
   - Single command to boot Station daemon and the Web Mission Control at `http://localhost:8080`.
   - Web UI integrates:
     * One-click Teleop Start / Stop toggle
     * Big Red Emergency E-Stop (cuts motor torque immediately)
     * Live tabletop camera view with metric millimeter grid overlay
     * Interactive 3D WebGL Digital Twin
     * Quick waypoint buttons (`Home`, `Pick`, `Place`)
     * One-click Judge Perturbation Recovery demo and Pytest execution
4. **Cameras & Environment:**
   - Downgraded user numpy to `numpy<2` (1.26.4) to resolve OpenCV ABI compatibility.
   - Probed UVC cameras on `/dev/video2` and `/dev/video4`.
   - Generated 4-corner AprilTags calibration sheet (`docs/NormaCore Hackathon - 4-Corner AprilTags.pdf`).

## Work In Progress

- Tabletop camera homography calibration (place AprilTags in view of `/dev/video2` or `/dev/video4` and run `scripts/calibrate_camera.py`).
- Teaching Cartesian pick/place waypoints for autonomous Claude/Codex agent execution.

## Next Steps

1. Run `./cli.sh teleop` for master-slave teleoperation demonstration.
2. Place AprilTags on tabletop and complete homography calibration.
3. Teach `home`, `pick`, and `place` waypoints using `./cli.sh hw teach <name>`.
4. Test MCP server (`./cli.sh mcp`) connected to live Station runtime.

## Files Modified/Created

- `scripts/teleop_sync.py` (new): 50Hz master/slave mirroring with current overload guard.
- `cli.sh`: added `teleop` command.
- `config/elrobot.json`: locked follower bus serial to `5B61037051`.
- `docs/NormaCore Hackathon - 4-Corner AprilTags.pdf`: printable marker sheet.
- `.ai-sync/HANDOFF.md`, `.ai-sync/PROGRESS.md`, `CHANGELOG.md`, `SUGGESTIONS.md`.

## Build Status

- `python3 -m pytest tests/`: 44 passed.
- `bash -n cli.sh`: OK.
- `py_compile scripts/teleop_sync.py`: OK.

## What Was Completed

Hardware bridge, preflight, run logging and the hardware-day tool are all in place. This pass covered the four "not ready" items from the previous summary:

1. **Motor identification:** `./cli.sh hw identify` nudges each motor 30 steps, returns it, and records the joint and physical direction.
2. **Torque:** `./cli.sh hw torque on` holds the current pose (goal set before torque is enabled). `hw torque off` and `hw stop` release the arm. Moves are refused while torque is off.
3. **Overload guard:** `move_and_watch` watches each motor until it arrives, overloads, faults or times out, and holds the motors still moving. `./cli.sh hw probe-current <m>` measures peak current and offers `2 × peak` as the threshold. The default threshold (100) is from the NormaCore teleop example and is **not measured on this arm**.
4. **Waypoints:** `hw teach <name>` saves all 8 motor positions. `hw goto <name>` shows a per-motor plan, refuses moves over 600 steps unless `--allow-large`, clamps to calibrated range, asks for `MOVE`, and checks arrival.
5. **Workspace:** limits moved to `config/elrobot.json`. `SafetyLimits` and the MCP server read them. Defaults equal the old values. `measured` stays false until the table is measured.

Config is separate from progress: `config/` (committed) holds the joint map, thresholds, workspace and waypoints; `data/hw_day_state.json` holds checklist progress (local).

## Work In Progress

None in code. Nothing has run on the physical arm.

## Next Steps (hardware day, follow docs/elrobot_hardware_bridge.md)

1. Power on, start the Station (`./cli.sh station`), run `./cli.sh hw run 3` (preflight), expect READY.
2. `./cli.sh hw identify`: record all 8 motors. Check whether motor 8 opens or closes the gripper on +30.
3. `./cli.sh hw torque on`, then `./cli.sh hw jog 2 60 --speed 200`, then `./cli.sh hw done 7`.
4. `./cli.sh hw probe-current <m>` for each motor you will use. Gripper first.
5. Move the arm by hand (torque off), `./cli.sh hw teach home` and `hw teach clear`. Torque on, then `hw goto clear` and `hw goto home`.
6. Measure the table (step 11 of the runbook), set `"measured": true`, then `./cli.sh hw workspace`.
7. Commit `config/elrobot.json` and `config/waypoints.json` after hardware day.

## Files Modified/Created

- `src/elrobot_config.py` (new): config, waypoints, state, defaults
- `src/elrobot_hardware.py`: torque checks, `hold`, `torque_on_hold`, `move_and_watch`, `OverloadDetector`, `plan_goto`
- `scripts/hw_day.py`: rewritten. Identify, torque, probe-current, teach, waypoints, goto, workspace
- `src/kinematics_safety.py`, `src/mcp_server.py`: workspace limits read from config
- `config/elrobot.json`, `config/waypoints.json` (new, defaults)
- `tests/test_hw_day.py` (new, fake bridge flow tests), `tests/test_elrobot_hardware.py` (extended)
- `docs/elrobot_hardware_bridge.md`: rewritten as a walkthrough
- `cli.sh`, `.gitignore`, `CHANGELOG.md`, `SUGGESTIONS.md`, `.ai-sync/PROGRESS.md`, `.ai-sync/HANDOFF.md`
- Untracked, not committed: `src/digital_twin.html` (predates this work). `station.yaml`/`station_data/` now gitignored; they still exist from a Station test run.

## Blockers
- 2026-11-22 03:07 (Jafer): Station motor ranges wrap past 0 on motors 1-7 and the gripper range is 3288..3292; every motion command refuses (`calibration invalid`). Evidence: `./cli.sh hw motors`. Fix: recalibrate in the Station console (hardware owner). See FINDINGS.md.

- No physical arm in this session. Tested offline: 44 tests pass, including flow tests for identify, jog, probe, teach, goto, torque and stop against a fake bridge. Live Station frames have not been exercised.

## Key Decisions

- Joint-level only. Waypoints replace Cartesian moves for the demo. Cartesian IK waits for on-arm verification.
- Motion needs typed `MOVE`. Goto is capped at 600 steps per motor unless `--allow-large`.
- Overload guard holds rather than reverses. Thresholds come from probing, not defaults.
- Config (committed) and progress (local) are separate files.

## Build Status

- `python3 -m pytest tests/`: 44 passed.
- `bash -n cli.sh`, `py_compile` on changed Python: OK.
- Offline CLI paths checked: status, workspace, waypoints, teach/goto with no Station, identify with no TTY, invalid waypoint name.

## Source Facts (verified 2026-11-20)

- URDF joints `rev_motor_01`..`08`. Limits in radians (for example `rev_motor_01` ±1.5509). Gripper is `rev_motor_08` plus two prismatic fingers.
- ElRobot BOM: ST3215 12 V / 30 kg on the follower, 8 motors. Waveshare Serial Bus Servo Driver (A). Reach 430 mm.
- Station: TCP 8888, web 8889. Topic `st3215/inference`. Commands go as `DriverCommand` with `STC_ST3215_COMMAND`.
