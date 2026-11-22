---
name: grip-object
description: Grip an object on the table with the ElRobot gripper and lift it (e.g. "grip the grape", "grip <object>", "grab the right grape", "pick it up"). Hover, open, descend with the lowered floor, close, check with the gripper camera, lift. Always follow this procedure for any "grip / grab / pick up <object>" request.
---

# Grip an object (hover -> open -> descend -> close -> check -> lift)

Authorization: on 2026-11-22 the hardware owner (Jafer) asked for this to run without asking each time,
and said retries are fine. It covers the steps below for an object he named. It does not cover
feeding, carrying the object somewhere else, or playing sequences.

Before moving, check that `.ai-sync/HANDOFF.md` still names `hardware_owner: "jafer"`.

Worked first on 2026-11-22 (right grape, temporary arm `5B61034679`). See the HANDOFF entry "FIRST GRAPE GRASP".

## Steps

1. **Look.** `look("table")`, `age_seconds` < 2. Find the object's centre pixel (u, v). Two objects that
   could match: ask which one. Cannot see it: say so, do not move.
2. **Table point.** `./cli.sh calib pixel U V --size 1920x1080` gives (X, Y) mm.
3. **Torque.** If `hw motors` shows torque off, run `./cli.sh hw torque on` (it holds the current pose).
4. **Hover.** Follow `hover-above-object`: `./cli.sh calib goto X Y 70 --travel-z 100 --mm-per-s 45 --yes`.
   Keep the wrist as it is (no `--down`: fingers-down puts motor 6 at its limit).
   Path refusals: try `--travel-z` 90 / 100 / 120 with `echo no | ./cli.sh calib goto ...` (checks, never moves),
   and run the first one that passes.
5. **Open.** `set_gripper(100)`. If the MCP call times out, retry once, else `./cli.sh hw jog 8 200 --yes`
   until motor 8 is near the top of its range (open = high steps).
6. **Descend in two stages**, slowly:
   - `./cli.sh calib goto X Y 40 --travel-z 70 --min-z 0 --mm-per-s 10 --yes`
   - `look("gripper")`: the object should sit between the jaws, at the fingertips. The table-camera point puts
     the jaws about **2 cm short along the finger direction**; correct X/Y from the gripper picture
     (on 2026-11-22 the fix was about +18 mm in x, -6 mm in y).
     Left grape, same day: object ~3 cm beyond the tips; moved the target 30 mm along the finger direction
     (`calib where` prints it in the base frame; table frame ~ (-bx, -by) with the current base yaw ~180°).
   - `./cli.sh calib goto X Y 18 --travel-z 50 --min-z 0 --mm-per-s 8 --yes` (grape height; taller objects: about half their height).
     Sag: read the joint-reading z after the 40 mm stage. If it is well below 40 (e.g. 28 on the left side),
     command about 25 instead of 18 so the jaws end near grape height (~15-25 mm by joints) and do not hit the table.
   Never go below what `--min-z 0` allows (the fit error stays on top).
7. **Close.** `set_gripper(0)`.
8. **Check with the gripper camera, not the result field.** `holding_object` is unreliable until motor 8's range is
   recalibrated (the jaws stall on each other near 1372). `look("gripper")`: the object must be pinched between the jaw tips.
9. **Lift.** `./cli.sh calib goto X Y 90 --travel-z 90 --mm-per-s 15 --yes`, then `look("gripper")` and `look("table")`:
   the object is in the jaws and gone from the table.
10. **Missed?** Retries are OK. Open, lift to 40 mm, re-find the object (it may have been pushed), correct X/Y
   from the gripper camera, and repeat steps 6-9. Stop after 3 misses and report.

## Stop if unsafe

Overload stop, a strange path, the object crushed or knocked off the table, or the arm touching something it
should not: `./cli.sh hw stop` (or MCP `stop()`), then tell the human. The 12 V switch is the real stop.

## Report

What was gripped, how many tries, the joint-reading fingertip position after the lift, and what the gripper camera shows.
