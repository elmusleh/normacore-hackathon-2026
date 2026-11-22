---
last_agent: antigravity
timestamp: 2026-11-22T03:38:00Z
status: mouth-status-badge-cue-and-timeout-live
current_phase: "Phase 3: Full Team Integration (Hands-Free Voice Console + OBSBOT MediaPipe Mouth-Open Gate)"
current_task: "Added live OBSBOT mouth-status badge, waiting-for-mouth amber banner + spoken TTS cue, and clamped mouth_gate_timeout_s"
stop_reason: complete
hardware_owner: "steve"
previous_session: antigravity 2026-11-22T03:26 — hands-free-voice-chimes-and-mouth-gate-live
---

## Latest session (2026-11-22 03:38): Live OBSBOT Mouth Badge, Waiting Cue & Configurable Timeout

- **What Changed:**
  - **Configurable & Clamped Timeout (`src/robot_tools.py`):** Added `mouth_gate_timeout_s(cfg)` reading `feeding_vision.mouth_gate_timeout_s` (default `12.0s`, clamped to `[3.0, 30.0]s`), plus atomic `data/mouth_gate_state.json` telemetry written by `_mouth_gate_check`.
  - **Zero-Contention Live Mouth Status Endpoint (`src/web_console.py`):** Added `GET /api/mouth_status` (reuses `data/mouth_gate_state.json` while `play_sequence` holds OBSBOT, or polls OBSBOT with a 500 ms cache & persistent `FeedingVisionDetector` otherwise).
  - **Live Badge + Visual/Spoken Waiting Cue (`src/web/console.html`):** Added `#mouth-badge` (`Mouth: OPEN ✓` / `Closed` / `No Face` / `OBSBOT: Offline`) next to the `Wait for Mouth-Open (OBSBOT)` checkbox and `#mouth-banner` amber cue + TTS prompt (*"Ready. Open your mouth when you want the bite."*) whenever `play_sequence` pauses for mouth-open confirmation.
  - **Tests (`tests/test_robot_mcp.py`):** Added unit tests for `mouth_gate_timeout_s` clamping and `data/mouth_gate_state.json` round-trip/staleness.
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
