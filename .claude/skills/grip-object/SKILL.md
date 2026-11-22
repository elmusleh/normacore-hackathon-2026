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

## RULE: grip only with the fingers pointing vertically down (Jafer, 2026-11-22)

Every grasp move uses `--down` (hover, the 40 mm check and the descent+close). If `--down` is refused, do NOT fall
back to the angled wrist: report the refusal. On the temporary arm `--down` is refused over the bowl because motor 6
lands on its range ends; motors 5-7 zeros in `config/calibration.json` are still the old arm's -> redo
`calib zero --write` (arm in the zero pose) and `calib fit --refine --write` first.

## Steps (fast: Jafer wants quick decisions and quick moves; no dry runs unless a move is refused)

1. **Look.** `look("table")`. Find the object's centre pixel. Two could match: ask. Cannot see it: say so.
   `./cli.sh calib pixel U V --size 1920x1080` -> (X, Y).
   Pre-correct for the jaws landing short: add about **25 mm along the finger direction** (left side of the
   table: about (-11, -25) mm in table x/y; right side: about (+15, -10)). Torque off? `./cli.sh hw torque on`.
2. **Hover + open in one command:** `./cli.sh calib goto X Y 70 --travel-z 100 --mm-per-s 70 --open-after --yes`.
   Add `--down`. Refused: retry once with `--travel-z` 90 or 120; still refused, stop and report (see RULE).
3. **Down to 40 mm:** `./cli.sh calib goto X Y 40 --travel-z 70 --min-z 0 --mm-per-s 40 --yes`, then `look("gripper")`.
   The object should be between the jaws at the fingertips; correct X/Y by what the picture shows
   (object beyond the tips -> move along the finger direction). Note the joint-reading z (sag).
4. **Down + close in one command:** `./cli.sh calib goto X Y Z --travel-z 50 --min-z 0 --mm-per-s 20 --close-after --yes`
   with Z = 18, or 25 if the 40 mm stage read well below 40 (sag). Closing stops where the jaws stall and keeps
   `gripper.squeeze_steps` (57) of squeeze on a fresh reading. Output says "holding" or "closed empty".
   Prefer this to MCP `set_gripper`: the MCP server's readings can be stale (squeeze far too hard).
5. **Lift:** `./cli.sh calib goto X Y 90 --travel-z 90 --mm-per-s 50 --yes`, then one `look("gripper")`:
   object pinched between the jaw tips. "closed empty" or nothing in the jaws = miss.
6. **Missed?** Retries are OK: step 2 again from where the object is now (it may have moved), up to 3 tries, then report.

## Known limits (2026-11-22)

- **Inside a bowl it fails**: the angled jaw tips touch the curved bowl and stall (~1650) before reaching the grape;
  `--close-after` then says "holding" falsely. Only grip from a bowl at its flat centre, and check the jaws after the
  lift (`hw motors`: if motor 8 kept closing well past the stall value, it is empty).
- Gripper camera: object low in the picture = under the palm (pull back); high = beyond the tips (push forward).

## Stop if unsafe

Overload stop, a strange path, the object crushed or knocked off the table, or the arm touching something it
should not: `./cli.sh hw stop` (or MCP `stop()`), then tell the human. The 12 V switch is the real stop.

## Report

What was gripped, how many tries, the joint-reading fingertip position after the lift, and what the gripper camera shows.
