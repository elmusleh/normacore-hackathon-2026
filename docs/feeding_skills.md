# Feeding skills roadmap

Claude Code project skills (`.claude/skills/<name>/SKILL.md`) that take the arm from "hover above an
object" (done) to "feed a person". Each skill is one procedure an agent runs the same way every time.
Small skills are chained by one orchestrator skill, `feed-me`.

Written 2026-11-22. Follows [FEEDING_ASSISTANT_PLAN.md](FEEDING_ASSISTANT_PLAN.md) (tiers, safety rules)
and the IK decision banner in it. Motion runs through `./cli.sh calib goto|line` (table frame + URDF IK)
and the elrobot MCP tools. The recorded plans (`play_sequence("grapes")`, `play_sequence("choc")`) stay the
fallback for the Must tier if a skill below is not reliable by demo time.

## The chain

```
check-ready -> scan-table -> hover-above-object -> center-on-object -> grasp-food
            -> carry-to-serve -> approach-mouth -> handover -> return-to-clear
                                   (find-mouth runs inside approach-mouth and handover)
feed-me      = the chain above for one request, with fallbacks
meal-session = listen -> feed-me -> "another one" / "I'm done", repeated
safe-recover = after a stop or fault, at any point
```

## Skill list

Autonomy says whether the agent may run the skill without asking. Today only `hover-above-object` has
standing authorization (Jafer, 2026-11-22). Every other move needs the hardware owner's typed
confirmation until the owner extends the authorization in writing in that skill's file.

| # | Skill | Tier | What it does | Builds on | Autonomy | Status |
| :- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `check-ready` | Must | Read-only preflight: hardware owner in HANDOFF, Station answering, camera frames fresh (<2 s), `calibration.json` measured, torque state, teleop set to Self-controlled, `ELROBOT_ALLOW_MOTION`. Prints go / no-go | `preflight`, `hw motors`, `get_robot_state`, `look` | Auto (reads only) | To write |
| 2 | `scan-table` | Should | One `look("table")`, names every food and tool it sees, converts each centre pixel to table mm (`calib pixel`). Returns a list like `grape (381, 155)`, `cheese (300, 90)`, `spoon (120, 200)` | `look`, `calib pixel`, `foods` config | Auto (reads only) | To write |
| 3 | `hover-above-object` | Must | Fingertip to 70 mm above an object seen on the table camera | `calib pixel|reach|goto` | Auto (standing OK) | **Done** |
| 4 | `center-on-object` | Must | From the hover, look through the gripper camera and correct x/y in small `calib goto` steps (z unchanged, at most 3) until the object sits at the "between the fingers" pixel. Removes the ~3 cm table-camera error | 3, gripper camera, a measured finger-centre pixel | Ask (same height as hover, so a good candidate for the next standing OK) | To write; needs the finger-centre pixel measured |
| 5 | `grasp-food` | Must | Open to the food's width, descend to grasp height with `calib line` (slow, straight down), close to the per-food width, check `holding_object` and the gripper camera, lift back to hover. One retry from a new hover, then stop | 4, per-food grasp settings (plan 4.1), gripper direction verified (plan 1.2), current threshold (1.3) | Ask every time (goes below the 66 mm floor; needs its own reviewed floor for grasping) | To write; blocked on 1.2-1.4 |
| 6 | `carry-to-serve` | Must | Lift to 150 mm, move to the `serve` pose about 15 cm in front of the face, slowly. Checks the food is still held on arrival | 5, a taught `serve` waypoint or a table-frame serve point (plan 2.3) | Ask | To write |
| 7 | `find-mouth` | Must | MediaPipe Face Mesh on the face or gripper camera: face found, mouth centre pixel, mouth open ratio, mouth width in px (distance proxy). Read-only; also an MCP tool `find_mouth()` | plan 2.1-2.2, `src/feeding_vision.py` | Auto (reads only) | Code partly in `feeding_vision.py`; skill to write |
| 8 | `approach-mouth` | Must | Local loop (not Claude step by step): small capped moves that keep the mouth centred, slow, stop at the standoff (5-10 cm). Abort and back off if the face is lost. **Never closes the last gap** | 6, 7, plan 2.4 | Ask; motion code needs owner review and a consenting test person | To write |
| 9 | `handover` | Must | Wait for mouth open, person leans in, detect the bite (mouth closes on the food and/or pull on the gripper motor), then open the gripper (food) or keep it closed (spoon) and retreat slowly to `serve` | 8, plan 2.5 / 5.4 | Ask | To write |
| 10 | `return-to-clear` | Must | From anywhere: lift straight up, then go to `clear` (gripper open if empty, closed if holding a tool) | `calib goto`, `go_to_waypoint("clear")` | Auto candidate (moves away from the person and table) | To write |
| 11 | `feed-me` | Must | Orchestrator for one request ("I want a grape"): check-ready -> find the food on the table -> chain 3-10 -> say what happens before each move near the face. If any step fails twice, fall back to the recorded plan for that food (`play_sequence`) or stop and say why | 1-10, `foods` config | Confirmation once per request, at the start | To write |
| 12 | `safe-recover` | Must | After `stop`, a fault, a missed grasp or a dropped bite: hold, look with both cameras, report, then retreat with `return-to-clear` once the owner agrees. Never turns torque off near the person | `stop`, 10 | Hold is auto; retreat asks | To write |
| 13 | `place-object` | Should | Put a held object down at a table point (back in the bowl, or a "reject" spot): hover over it, descend, open, lift | 3, 5 | Ask | To write |
| 14 | `say-and-listen` | Should | Wraps `say(text)` and `listen(timeout_s)` (plan 3.2, 3.4) so every skill announces its next move near the person and can ask a question | plan stage 3 | Auto (no motion) | Tools not built yet |
| 15 | `pick-tool` / `return-tool` | Could | Take the spoon from its holder and put it back, gripping it the same way every time | 3, 5, spoon adapter (plan 5.1) | Ask | To write |
| 16 | `scoop` | Could | With the spoon: hover over the bowl, dip, drag through the rice, lift level | 15, plan 5.2-5.3 | Ask | To write |
| 17 | `meal-session` | Could | Loop: listen -> `feed-me` -> "another one" / "now a grape" (switch tools: return the spoon first) / "I'm done" (tools back, `return-to-clear`). Keeps track of what was served by looking again | 11, 14, 15 | Confirmation per request | To write |

Voice "stop" is **not** a skill: it is the always-on local process `scripts/voice_stop.py` (plan 3.3), so it
works even while a skill runs. Skills must assume it can freeze the arm at any moment.

## Build order

1. `check-ready`, `return-to-clear`, `safe-recover`: cheap, and every later skill calls them.
2. `center-on-object`, then `grasp-food` on a grape (after the gripper is verified and probed).
3. `find-mouth`, `carry-to-serve`, `approach-mouth`, `handover`: on a consenting teammate, soft food only.
4. `feed-me` for grapes end to end. Rehearse 5 runs in a row; keep `play_sequence("grapes")` as the backup.
5. `scan-table` + second food (cheese cube or chocolate) + `say-and-listen`: the Should tier.
6. Spoon skills and `meal-session` only if the Sunday 09:00 decision says the spoon is in.

## Rules every skill file must carry

- Check `.ai-sync/HANDOFF.md` names the hardware owner of this session before any motion.
- Plan first (`calib reach`, no motion), move once, `look` after every move. Do not retry the same failing
  move more than once.
- Heights: never below the floor the planner prints; never edit `GOTO_MIN_Z_MM`. A grasp floor, if added,
  is its own reviewed constant.
- Near the face: standoff 5-10 cm, slower than on the table, stop if the face is lost (plan section 4).
- State the standing authorization (or "ask every time") at the top of the file, with who gave it and when.
