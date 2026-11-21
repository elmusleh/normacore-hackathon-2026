---
last_agent: antigravity
timestamp: 2026-11-21T18:24:00Z
status: dual-camera-dashboard-live
current_phase: "Phase 3: Dual-Camera Mission Control & Live Hardware Bring-Up"
current_task: "Dual live camera dropdowns (Station + V4L2) and live detection log in Mission Control"
stop_reason: ready-for-user-selection
hardware_owner: "steve"
previous_session: antigravity 2026-11-21T17:25 — commit-and-push-policy-updated
---

## Latest session (2026-11-21 evening): Dual Live Camera Dropdowns & Hardware Bring-Up

- **What Changed:**
  - Added `scripts/reset_bench.py` (`--status`, `--relax-leader`, `--swap-arms`, `--set-arms`, `--clean-cameras`) and one-click **Relax Leader (Torque Off)** + **Swap Master / Slave** buttons in Mission Control (`src/digital_twin_server.py`, `src/digital_twin.html`) so any teammate can reset cameras, relax a stiff leader arm, or adjust Master/Slave roles without editing JSON.
  - Fixed inverted Leader/Follower roles in `scripts/teleop_sync.py` to read `leader_bus` (`5B61037051`) and `bus` (`5B61034962`) from `config/elrobot.json`, and enforced explicit `set_torque(..., enable=False)` on the Leader arm before enabling Follower torque on every teleop start. Updated `teleop_start` in `src/digital_twin_server.py` to pass `--leader` and `--follower` explicitly.
  - Raised `usb-video.resize_target` in `station.yaml` from `224` to `480` and restarted Station (`http://localhost:8889`) and Mission Control (`http://localhost:8080`). Note: `sudo apt-get install v4l-utils` requires interactive sudo password from the user to apply manual exposure (`./cli.sh cameras`).
  - Stacked `Table Cam` above `Person Cam` in `src/digital_twin.html` and added a **Save Default** button (`save_camera_defaults` in `src/digital_twin_server.py`) that persists the chosen cameras to `config/elrobot.json`.
  - Merged `origin/main` into `feat/agent-commit-and-push-policy` (bringing in `config/waypoints.json` with `clear` and `grape_hover`, `src/console_agent.py`, updated `scripts/hw_day.py`, and `src/web_console.py`).
  - Removed the static offline Three.js `<canvas>` mockup from `src/digital_twin.html` so `Table Cam` and `Person Cam` fill the left viewport, added live saved waypoint chips from `config/waypoints.json`, and updated `src/digital_twin_server.py` to separate table vs. person detectors and hide hardcoded fallback `BOWL`/`SPOON`/`MOUTH` boxes.
  - Confirmed physical hardware mapping from hardware owner (`steve`) and saved to `config/elrobot.json`: follower bus `5B61034962`, leader bus `5B61037051`, `table` camera `port:3-1.2.2` (KD-USB), `gripper` camera `port:3-1.2.4` (KD-USB), `person` camera `v4l2:6` (OBSBOT Meet SE).
  - Updated `CameraHub.discover()` in `src/digital_twin_server.py` to default `Table Cam` and `Person Cam` from `config/elrobot.json`.
  - Upgraded `src/digital_twin_server.py` with `CameraHub` (auto-discovers NormaCore Station `usbvideo/*` queues + local V4L2 `/dev/video*` cameras + mock fallback), `ThreadingHTTPServer`, `GET /api/cameras`, `GET /api/frame?role=table|person`, and `select_camera` action.
  - Upgraded `src/digital_twin.html` with side-by-side **Table Cam** and **Person Cam** live feeds, camera selector dropdowns, refresh button, per-camera live detection bars, and automatic detection-change logging in the Live Terminal & Event Log.
  - Verified live on hardware: NormaCore Station (`http://localhost:8889`) and Mission Control (`http://localhost:8080`) running; both ElRobot arms (`5B61034962` torque ON, `5B61037051` torque OFF) passed read-only preflight (all 8 motors visible, calibrated, fault-free). All 3 live cameras (`port:3-1.2.4` KD-USB, `port:3-1.2.2` KD-USB, `/dev/video6` OBSBOT Meet SE) confirmed streaming annotated JPEGs. No arm motion was commanded.
- **Files Changed:** `src/digital_twin_server.py`, `src/digital_twin.html`, `CHANGELOG.md`, `SUGGESTIONS.md`, `.ai-sync/HANDOFF.md`.
- **Build Status:** `python3 -m py_compile src/digital_twin_server.py` (OK), `python3 -m pytest tests/` (68 passed, 1 skipped).
- **Next Steps:**
  1. User opens `http://localhost:8080` and selects which camera is `Table Cam` and which is `Person Cam` from the dropdowns.
  2. Save the confirmed camera roles and follower bus serial (`5B61034962`) in `config/elrobot.json`.
  3. Teach initial safe waypoints (`home`, `table_hover`, `zone_a`, `serve`) and test dry-run -> live AI-guided move.

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
