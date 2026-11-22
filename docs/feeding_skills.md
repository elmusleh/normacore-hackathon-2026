# Feeding skills

Two Claude Code project skills (`.claude/skills/<name>/SKILL.md`) take the arm from a request to a fed
person. The person or operator only says one of two things:

- **"grab the &lt;object&gt;"**: pick it up from the table and hold it.
- **"feed the &lt;object&gt;"** (or "feed me a grape"): bring it to the mouth. It grabs the object first if
  the arm is not already holding it, so "feed me a grape" alone does the whole job.

Written 2026-11-22 (simplified from a 17-skill list the same day at Jafer's request: "as smooth as
possible"). Follows [FEEDING_ASSISTANT_PLAN.md](FEEDING_ASSISTANT_PLAN.md) and its IK decision banner.
Motion runs through `./cli.sh calib goto|line` (table frame + URDF IK) and the elrobot MCP tools. The
recorded plans (`play_sequence("grapes")`, `play_sequence("choc")`) are the fallback if a step fails twice.

## `grab <object>`

1. **Ready check** (reads only): HANDOFF names the hardware owner, camera frame < 2 s old, teleop off.
2. **Find it:** `look("table")`, centre pixel -> table mm (`calib pixel`). Not seen or ambiguous: ask, do not move.
3. **Hover** 70 mm above it: the existing `hover-above-object` procedure.
4. **Centre:** gripper camera, small x/y corrections (z unchanged, at most 3) until the object sits between
   the fingers. Removes the ~3 cm table-camera error.
5. **Grasp:** open to the food's width, go straight down slowly (`calib line`), close to the food's grasp
   width, check `holding_object` and the gripper camera.
6. **Lift** back to hover height. Missed: one retry from step 2, then stop and say so.

## `feed <object>`

1. Not holding the object yet: run `grab <object>`.
2. **Carry:** lift to 150 mm, move slowly to the `serve` pose about 15 cm in front of the face. Say what
   is about to happen.
3. **Approach:** local mouth tracker (`find_mouth`, MediaPipe) keeps the mouth centred and stops at the
   5-10 cm standoff. Face lost: stop and back off. **Never closes the last gap.**
4. **Handover:** wait for the mouth to open, the person leans in, detect the bite (mouth closes on the food
   and/or a pull on the gripper), open the gripper.
5. **Return:** back to `serve`, then `clear`.

On any fault or a "stop" at any point: hold, look, report; retreat to `clear` only once the owner agrees.
Voice "stop" is not part of the skills: it is the always-on local process `scripts/voice_stop.py` (plan
3.3), which freezes the arm whatever a skill is doing.

## What still has to exist for the steps to work

| Needed by | Piece | Plan task | State |
| :--- | :--- | :--- | :--- |
| grab 3 | Hover procedure | - | Done (`hover-above-object`) |
| grab 4 | Finger-centre pixel in the gripper camera | - | To measure |
| grab 5 | Gripper direction verified, current probed, grasp width per food in `foods` config | 1.2-1.4, 4.1 | Open |
| feed 2 | `serve` pose (waypoint or table-frame point) | 2.3 | Open |
| feed 3 | `find_mouth` tool + approach loop (local code, owner-reviewed) | 2.1, 2.2, 2.4 | Partly in `src/feeding_vision.py` |
| feed 4 | Bite detection | 2.5 | Open |

## Autonomy

`grab` steps 1-3 run without asking (standing OK for hover, Jafer, 2026-11-22). Grasping (step 5) and all of
`feed` need the hardware owner's typed confirmation, once per request, until the owner writes a wider
standing OK into the skill file.

## Later (Could tier)

Spoon and rice is one more skill, `feed rice`, using the same `feed` steps 2-5 with "pick spoon, scoop"
instead of `grab`, and "keep holding, return spoon" instead of opening. A whole meal ("another one",
"I'm done") needs no new skill: the agent just runs `feed` again.
