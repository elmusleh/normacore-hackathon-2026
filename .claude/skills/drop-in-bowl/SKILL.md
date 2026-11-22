---
name: drop-in-bowl
description: Drop the object the ElRobot gripper is holding into the bowl (e.g. "drop it in the bowl", "put the grape in the bowl"). The pre-stage for dropping food into a mouth. One look, one command, one look. Use for any "drop / put / place <object> in the bowl" request.
---

# Drop into the bowl (fast)

Authorization: Jafer (hardware owner) asked for this on 2026-11-22 and wants it fast: no extra questions,
no dry runs unless a move is refused. Check once per session that `.ai-sync/HANDOFF.md` names `hardware_owner: "jafer"`.

Worked first on 2026-11-22: blue bowl right of centre, table centre about (365, 28) mm, rim ~5 cm high.

## Steps (3 calls)

1. **Look.** `look("table")`. Find the bowl's centre pixel: the middle of the rim ellipse, a little lower
   (toward the camera) because the rim is raised. `./cli.sh calib pixel U V --size 1920x1080` -> (X, Y).
   Bowl not visible: say so, do not move. Not holding anything: say so (or run `grip-object` first if asked).
2. **Move and drop in one command:**
   `./cli.sh calib goto X Y 130 --travel-z 130 --mm-per-s 70 --open-after --yes`
   130 mm commanded ends ~95-100 mm by joints (sag): well above the rim. It lifts, crosses, and opens the gripper.
   Refused: change `--travel-z` (120 / 150) once; still refused, report the message.
3. **Check.** `look("table")`: the object is in the bowl, jaws open. Report it in one line.

## Next stage (mouth)

The same command with the mouth's position and a standoff instead of the bowl: needs the mouth finder
(plan 2.1) and the `serve` pose first. Do not drop toward a person with this skill.

## Stop if unsafe

Overload stop, strange path, bowl knocked: `./cli.sh hw stop` (or MCP `stop()`), tell the human.
