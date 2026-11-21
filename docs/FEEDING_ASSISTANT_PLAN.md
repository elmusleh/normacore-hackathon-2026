# Feeding Assistant: Team Plan

**Read this first if you are a teammate or an AI agent working in this repo.** It replaces the earlier
Cartesian pick_at/place_at plan. **Diagrams:** [FEEDING_ASSISTANT_DIAGRAMS.md](FEEDING_ASSISTANT_DIAGRAMS.md). Last updated 2026-11-21 (Saturday afternoon). Demo is Sunday.

> **Decision 2026-11-21 late (Jafer): the ACT imitation-learning approach is dropped.** Motion now
> targets come from one calibrated **table frame**: 4 AprilTags (36h11, IDs 0-3) on the table corners
> give camera pixel -> table mm, fingertip touches give the arm base pose and joint zeros, and URDF
> inverse kinematics turns a table point (x, y, z) into joint steps. Runbook: [tcp_calibration.md](tcp_calibration.md),
> command `./cli.sh calib`. Where section 2 below says "no x/y/z control", this decision replaces it
> once the calibration is measured (`config/calibration.json`, all `measured` flags true) and a
> Cartesian move command has been reviewed by the hardware owner. Waypoints and recorded plans stay
> as the fallback.

## 1. The goal

An assistive feeding robot for a person who cannot move their arms. The person **says** what they want,
the robot **sees** what is on the table, picks the right **tool** for that food, and brings a bite to
their **mouth**, stopping just in front of it so the person leans in and takes it.

The demo scenario:

> On the table: a bowl of rice, a plate of grapes, a spoon in a holder.
> Person: *"I want to eat rice."*
> Robot: *"Getting you some rice."* It recognises the rice in the bowl, picks up the spoon, scoops rice,
> finds the person's mouth and holds the spoon just in front of it. The person leans in and eats.
> Person: *"Now a grape."* The robot puts the spoon back, picks a grape with the gripper and serves it.
> Person: *"Stop!"* The arm freezes instantly.

### Priority tiers

The demo must work even if the hardest parts do not. Build in this order, and keep each tier working:

| Tier | What it shows | Status needed for the demo |
| :--- | :--- | :--- |
| **Must** | Grape picked with the gripper and delivered to the mouth (stages 1 and 2) | Reliable, rehearsed |
| **Should** | Voice request chooses between two foods, both picked with the gripper (e.g. grape vs cheese cube), plus voice "stop" (stages 3 and 4) | Working |
| **Could** | Rice with a spoon: pick spoon, scoop, serve, return spoon (stage 5) | Show if reliable, else a "next step" slide |
| **Could** | A whole meal: several requests in a row, "another one", "I'm done" (stage 6) | Show if time allows |

## 2. Core design: Claude decides, local code acts fast

Claude (through MCP tools) takes a few seconds per image or decision. That is fine for choosing food and
tools, and too slow for following a face or stopping the arm. So:

| Job | Who does it | Why |
| :--- | :--- | :--- |
| Understand the request ("I want rice") | Speech-to-text locally, then **Claude** | Claude handles any wording |
| Which food is where, which tool it needs | **Claude** looking at the table camera | Open-ended visual reasoning |
| Order of steps, recovery when something fails | **Claude** | Planning |
| Find the mouth, approach, detect the bite | **Local code** (MediaPipe, ~30 FPS) | Speed and safety |
| Voice "stop" | **Local keyword listener**, straight to the arm | Must act in well under a second |
| Speed, force, range limits | **Local code** (`src/robot_tools.py`, `src/elrobot_hardware.py`) | Never left to a model |

**The arm moves between taught joint poses ("waypoints") plus small capped nudges.** There is no x/y/z
(Cartesian) control: the Station only takes joint targets, and no kinematics model is verified on this arm.
Do not build on `pick_at`/`place_at` in `src/mcp_server.py`; that file is an offline simulator only.

**Fixed table zones.** Because moves are waypoints, food and tools sit in fixed **zones** with taught poses
(e.g. `zone_a` plate, `zone_b` bowl, `spoon_holder`). Claude's vision job is to say *what is in which zone*,
not to compute coordinates. Mark the zones on the table with tape.

## 3. Current state (what works today)

| Thing | State |
| :--- | :--- |
| Station | `./cli.sh station` from the repo root. Web viewer: http://localhost:8889 |
| Arms | Follower bus `5B61034962` (`/dev/ttyACM0`), leader bus `5B61037051`. Both calibrated (calibration persists in `station_data/`) |
| Teleop | Works: on the follower's card in the web viewer, pick the leader serial in the dropdown. Set back to **(Self-controlled)** before Claude moves the arm |
| MCP server | `src/robot_mcp_server.py`, registered in `.mcp.json` as `elrobot`. Tested offline and read-only on the real arm. **No motion run yet** |
| Cameras | `table` (USB port 3-2.4) and `gripper` (port 3-2.2). Need `scripts/99-normacore-cameras.rules` installed (done on the main laptop) |
| Camera exposure | Auto exposure washes out under the Station. Fixed exposure in `config/elrobot.json` → `camera_settings`; apply with `./cli.sh cameras` **while the Station is stopped**; find a value with `./cli.sh cameras --tune`. Not yet confirmed that the Station keeps it after restart. `look()` returns the camera's own picture, with no software clean-up |
| Waypoints | None taught yet (`config/waypoints.json` is empty) |
| Gripper | Direction (which end is "open") **not verified**. Grasp detection is tuned for firm objects, not grapes |
| Voice, mouth tracking, food zones | Not started |
| Tests | `.venv/bin/python -m pytest tests/` → 60 pass |

### MCP tools Claude has (server `elrobot`)

`look(camera)`, `list_cameras`, `get_robot_state`, `list_waypoints`, `go_to_waypoint(name, via_clear=True)`,
`nudge_joint(motor, delta_percent)` (max 5%), `set_gripper(open_percent)` (0 closed, 100 open),
`stop`, `enable_torque`, `teach_waypoint(name)`.

Planned additions (this plan): `find_mouth`, `serve_to_mouth`, `listen`, `say`, and food/zone config.

Motion is **off** unless `ELROBOT_ALLOW_MOTION` is `"1"` in `.mcp.json`. With it off, motion tools return a
`dry_run` plan. Full details: [docs/mcp_server.md](mcp_server.md).

## 4. Safety rules (non-negotiable)

These apply to every person and every agent. The arm works near a human face.

1. **One hand on the follower's power plug** whenever motion is enabled.
2. **Never send raw register writes** or bypass `src/elrobot_hardware.py` / `src/robot_tools.py`. Those enforce
   calibrated-range clamps, torque checks, speed caps and the overload guard.
3. **Do not raise** `agent.max_speed`, `agent.max_nudge_percent` or current thresholds without the team agreeing.
4. **Near the face: the robot never closes the last gap.** It stops at a standoff (5 to 10 cm) and the person
   leans in. Speed and force near the face must be lower than on the table.
5. **Stop on doubt:** face lost from view, unexpected resistance, or any fault means stop and retreat.
6. **Voice "stop" goes straight to the arm**, never through Claude. It **holds** the arm in place
   (it must not turn torque off: the arm would drop onto the person).
7. Test the face stage on a teammate who agrees to it, with soft food only. **The spoon goes near the face only
   after the gripper version is reliable**, at the same standoff, with rounded edges facing the person.
8. Teleop off (Self-controlled) before Claude drives the follower.
9. `ELROBOT_ALLOW_MOTION` is never committed as `"1"`.

## 5. Stage 1: pick-and-place into a box (Must)

| # | Task | Done when |
| :--- | :--- | :--- |
| 1.1 | Restart Station, check both camera feeds are not washed out (browser and `look`) | Grape visible and clear in both cameras |
| 1.2 | Verify gripper direction: `./cli.sh hw identify 8`. Set `gripper.open_at` and `gripper.verified: true` in `config/elrobot.json` | `set_gripper(100)` opens, `set_gripper(0)` closes |
| 1.3 | Probe gripper current: `./cli.sh hw probe-current 8`, closing on nothing and on a grape | Threshold saved; grape not crushed |
| 1.4 | Grape grasp: close to a fixed width (e.g. `set_gripper(30)`) instead of fully. Add a per-food grasp width in config | 5 grasps in a row without crushing or dropping |
| 1.5 | Mark zones with tape. Teach waypoints (torque off, pose by hand, `./cli.sh hw teach <name>`): `clear`, `zone_a_hover`, `zone_a`, `box_hover`, `box` | Each reachable with `./cli.sh hw goto <name>` |
| 1.6 | Claude run with motion on: look → zone_a_hover → zone_a → grasp → verify → box_hover → box → open → look | 5 successful runs in a row |
| 1.7 | Variable position inside a zone: teach `zone_a_1..4` (small grid), Claude picks the nearest from the table camera. Optional: fine alignment with `nudge_joint` from the gripper camera | Grape anywhere in the zone is picked |

Waypoint tips: teach `clear` first (above the table, gripper open). Go hover → grasp with `via_clear=false`.
Waypoints are only valid while the arm base, table and zones do not move.

## 6. Stage 2: deliver to the mouth (Must)

| # | Task | Done when |
| :--- | :--- | :--- |
| 2.1 | Mouth detector `src/mouth_tracker.py`: MediaPipe Face Mesh on gripper camera frames. Returns mouth centre in the image, mouth-open ratio, mouth width in pixels (distance proxy), face found yes/no | 10+ FPS live; unit tests on saved images |
| 2.2 | MCP tool `find_mouth()` exposing 2.1 to Claude | Claude can say where the mouth is and whether it is open |
| 2.3 | Teach `serve` waypoint: about 15 cm in front of where the person's face usually is | Reachable from `clear` |
| 2.4 | Approach routine `serve_to_mouth()` (local code, not Claude step by step): small capped nudges keeping the mouth centred, slow, stopping when the mouth width reaches the standoff size (5 to 10 cm). Aborts if the face is lost | Stops at the standoff every time; never moves closer |
| 2.5 | Handover: wait for mouth open, person leans in, detect the bite (mouth closes on food and/or pull on the gripper motor), then open the gripper and retreat to `serve` | Grape handed over 5 times in a row on a teammate |
| 2.6 | Claude orchestration: "feed me a grape" runs stages 1 + 2 end to end | Full run without help except the person eating |

## 7. Stage 3: voice (Should)

Runs on the main laptop's microphone (or a USB mic near the person). Work offline: venue Wi-Fi is unreliable.

| # | Task | Done when |
| :--- | :--- | :--- |
| 3.1 | Speech-to-text module `src/voice.py`: push-to-talk or voice-activity detection, then local transcription (e.g. `faster-whisper`, small English model). Returns the text | "I want to eat rice" transcribed correctly 9/10 times in the room noise |
| 3.2 | MCP tool `listen(timeout_s)`: waits for one utterance, returns the text. Claude then decides what it means | Claude reacts to spoken requests |
| 3.3 | **Voice stop** `scripts/voice_stop.py`: a separate always-on process with a small keyword listener (e.g. Vosk with a tiny grammar: "stop", "wait"). On a hit it holds every motor through `ElRobotHardwareSync.hold()` directly, independent of Claude and the MCP server | Arm freezes within 0.5 s of "stop", 10/10 times, also while Claude is mid-move |
| 3.4 | MCP tool `say(text)`: spoken feedback via local text-to-speech (e.g. `piper` or `espeak-ng`) | Robot says what it is about to do before every move near the person |

Running the session: a Claude Code session in this repo with the `elrobot` server, given a "meal assistant"
prompt that loops `listen` → decide → act → `say`. If time allows, B can move this into a small standalone
app (Claude Agent SDK) for a cleaner demo.

## 8. Stage 4: recognise food, choose the tool (Should)

| # | Task | Done when |
| :--- | :--- | :--- |
| 4.1 | Food config in `config/elrobot.json`: for each food its tool and grasp settings, e.g. `{"grape": {"tool": "gripper", "grasp_open_percent": 30}, "rice": {"tool": "spoon"}}`, and the zones with their waypoints | Config loads; tests cover it |
| 4.2 | Recognition: Claude `look("table")` and reports what is in each zone (prompt plus a zone overlay on the image, e.g. tape outlines or labels drawn on the frame). Optional tool `scan_table()` returning `{"zone_a": "grapes", "zone_b": "rice"}` | Correct food per zone 9/10 times with the demo foods |
| 4.3 | Request to plan: "I want X" → find the zone with X → its tool → the step sequence. Unknown or missing food: Claude says so and asks | Two foods, both with the gripper (grape, cheese cube), chosen correctly by voice |

## 9. Stage 5: spoon and rice (Could)

The hardest part. Use the gripper-only version (tier Should) as the fallback.

| # | Task | Done when |
| :--- | :--- | :--- |
| 5.1 | Spoon that the gripper can hold firmly and always the same way: thick handle or a 3D-printed/taped adapter, in a fixed holder (`spoon_holder`) | Picked and returned 10 times without slipping or turning |
| 5.2 | Teach: `spoon_holder_hover`, `spoon_holder` (grip), `bowl_hover`, `bowl_dip`, `bowl_scoop` (tilted, spoon moved through the rice), `bowl_lift` (spoon level), `serve_spoon` (spoon level, in front of the face) | Scoop sequence picks up rice 4/5 times |
| 5.3 | Rice that stays on the spoon: sticky (sushi) rice, deep bowl. Fallback: rice ball picked by the gripper, or a pre-filled spoon | Rice not dropped on the way to the mouth |
| 5.4 | Spoon handover: same approach and standoff as 2.4. Bite = mouth closes on the spoon; then retreat slowly **without opening the gripper**; return spoon to holder | 5 spoon feeds in a row on a teammate |

## 10. Stage 6: a whole meal (Could)

Several requests in a row: "rice", "another one", "now a grape", "I'm done". Claude keeps track of what was
served and what is left (by looking again), switches tools (returns the spoon before picking a grape), and
ends by putting tools back and going to `home`. Mostly prompt work for B plus reliable stages 1 to 5.

## 11. Team split (4 people)

The bottleneck is **one arm on one laptop**. Only the arm operator moves the arm. Everyone else
builds and tests on their own laptop (fake arm in tests, own webcam and microphone) and brings working code
to the arm.

| Role | Owns | Tasks | Files | Works on |
| :--- | :--- | :--- | :--- | :--- |
| **A. Arm operator** | Physical arm, Station laptop, power plug, zones on the table | 1.1–1.3, 1.5, 1.7, 2.3, 5.1, 5.2, all live runs | `config/elrobot.json`, `config/waypoints.json` | Main laptop |
| **B. Claude brain** | How Claude understands requests, recognises food and runs tasks | 1.4, 1.6, 2.6, 4.1–4.3, stage 6, the meal-assistant prompt | `src/robot_tools.py`, `src/robot_mcp_server.py` (instructions), food config | Own laptop + fake arm tests, then with A |
| **C. Mouth and approach** | Finding the mouth, safe approach, bite detection (gripper and spoon) | 2.1, 2.2, 2.4, 2.5, 5.4 | `src/mouth_tracker.py` + its tools | Own webcam first, then gripper camera with A |
| **D. Voice + demo** | Speech in and out, voice stop, then the demo itself | 3.1–3.4; props (grapes, cheese, rice, bowl, spoon, tape), test person, rehearsals, backup video, slides | `src/voice.py`, `scripts/voice_stop.py`, `docs/`, pitch deck | Own laptop mic first, then main laptop |

Everyone helps with the pitch on Sunday morning. D records every good run from Saturday evening on.

### Timeline

| When | A (arm) | B (brain) | C (mouth) | D (voice + demo) |
| :--- | :--- | :--- | :--- | :--- |
| Sat afternoon | Cameras OK, gripper direction, probe on grape, tape zones, teach `clear`/`zone_a`/`box` | Grasp width per food + tests; pick-and-place prompt | MediaPipe mouth tracker on own webcam | Speech-to-text + `listen` tool; buy props |
| Sat evening | Pick-and-place runs with B; teach zone grids, `serve` | Food config, `scan_table`, request → plan | `find_mouth`, `serve_to_mouth` on gripper camera | Voice stop process; `say`; first recordings |
| Sun morning | Face runs with C; spoon holder and scoop waypoints if Must/Should tiers work | End-to-end voice → food → mouth; meal loop | Handover and bite detection; spoon handover | Integrate voice on main laptop; rehearse twice; backup video |
| Sun before demo | **Freeze.** Only bug fixes | | | Final rehearsal |

### Sync points

- **Checkpoints at 16:00, 19:00, Sunday 09:00:** 10 minutes, each person says what works, what is blocked.
- **Sunday 09:00 decision:** is the spoon (tier Could) in the demo? Only if 4/5 scoops work by then.
- **Freeze:** nothing new merged after the Sunday rehearsal that works.

### Git rules to avoid stepping on each other

- One branch per person (`arm/...`, `brain/...`, `mouth/...`, `voice/...`). Small merges into `main`, tests passing.
- B, C and D all add tools to `src/robot_mcp_server.py`: put logic in your own module and only add a
  short `@server.tool` function at the end of the file. Pull before you edit it.
- New Python dependencies (mediapipe, faster-whisper, vosk, ...) go in `requirements.txt` with a comment
  saying who needs them. Check they install on Python 3.13 in `.venv` before relying on them.
- A commits `config/` changes promptly, because waypoints and gripper settings affect everyone's runs.

### Remote access (optional, untested)

The Station listens on the network (TCP 8888, web 8889). On the same Wi-Fi, B and C can read the arm and cameras
from their laptops with `ELROBOT_STATION=<main laptop IP>` and `ELROBOT_CAMERA_QUEUES=usbvideo/<hash>,...`
(port names only work on the main laptop). Keep `ELROBOT_ALLOW_MOTION` at `"0"` on every laptop except A's.

## 12. How to work in this repo (agents read this)

- Setup on a new laptop: `bin/station` from the NormaCore v0.1.0-beta.10 release
  (`station-linux-amd64.tar.gz`), `git clone --depth 1 https://github.com/norma-core/norma-core external/norma-core`,
  `python3 -m venv .venv && .venv/bin/pip install "mcp>=2" pytest numpy pillow`.
- Run tests before every commit: `.venv/bin/python -m pytest tests/`. New logic gets a test against the fake
  arm in `tests/test_robot_mcp.py` (or a new test file for your module).
- Put new robot behaviour in `src/robot_tools.py` or your own module (testable, no MCP), and expose it in
  `src/robot_mcp_server.py`. Anything that moves the arm goes through `RobotTools` so the safety checks apply.
- Config the team decides goes in `config/elrobot.json`; taught poses in `config/waypoints.json`. Commit both.
  Local state (`data/`, `logs/`, `station_data/`) is gitignored.
- Logs: `logs/mcp-latest.log`, `./cli.sh logs`.
- Update `.ai-sync/HANDOFF.md` and `.ai-sync/PROGRESS.md` when you stop, with exact next steps.
- Stage files explicitly (`git add <path>`), never `git add -A`.

## 13. Key references

- MCP server and tools: [docs/mcp_server.md](mcp_server.md)
- Hardware runbook (identify, teach, goto, probe): [docs/elrobot_hardware_bridge.md](elrobot_hardware_bridge.md)
- NormaCore source: `external/norma-core/` (Station, Python SDK, URDF in `hardware/elrobot/simulation/`)
