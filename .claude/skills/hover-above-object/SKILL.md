---
name: hover-above-object
description: Move the ElRobot gripper to hover above an object seen on the table camera (e.g. "move above the grape", "go to the cup", "move towards it"). Uses the AprilTag table frame + URDF IK (`./cli.sh calib pixel|reach|goto`). Always follow this procedure for any "move to / above / towards <object>" request.
---

# Hover above an object (camera -> table frame -> IK -> goto)

Standing authorization: on 2026-11-22 the hardware owner (Jafer) said to execute this move
automatically, without asking each time. That covers ONLY the hover move below (the fingertip
stops above the object, at or above the safety floor). It does not cover grasping, going lower,
gripper commands, `--down` without a clean `reach`, or any other motion. Anything else still needs
typed confirmation (AGENTS.md rule 7).

Before moving, check that `.ai-sync/HANDOFF.md` still names `hardware_owner: "jafer"`. If the
owner changed, stop and ask the new owner.

## Steps

1. **Look.** `look("table")` (MCP `mcp__elrobot__look`). Check `age_seconds` < 2. Find the object
   and its centre pixel (u, v) in the returned `width` x `height` frame. If you cannot see it,
   or two objects could match, say so and ask. Do not move.
2. **Pixel -> table.** `./cli.sh calib pixel U V --size WxH` gives table (x, y) mm on the surface.
3. **Height.** Hover z = **70 mm**. The planner refuses anything below 50 mm + the calibration fit
   error (16 mm on 2026-11-22, so 66 mm). Never lower the floor and never edit
   `GOTO_MIN_Z_MM`. If `goto` refuses for height, raise z to the floor it prints + 4 mm, once.
4. **Plan (no motion).** `./cli.sh calib reach X Y Z`. Go on only if the IK error is <= 5 mm and
   no motor goes outside its range. Use the wrist as it is (no `--down`) unless the user asked for
   fingers down AND `reach ... --down` is in range with >= 50 steps margin on every motor.
5. **Move.** `./cli.sh calib goto X Y Z --yes` (lift to 150 mm, across, down; 25 mm/s). Run it
   once. If it fails, read the message and do not retry the same command more than once.
6. **Check.** `look("table")` again. Report the joint-reading fingertip position from the goto
   output, the fingertip's pixel vs the object's pixel, and the apparent offset (remember a
   fingertip 7 cm up looks further *back* in the table camera than the point under it).
7. **Stop if unsafe.** Anything unexpected (arm hits something, strange path, object knocked):
   `./cli.sh hw stop` (or MCP `stop()`), then tell the human. The 12 V switch is the real stop.

## Do not

- Do not descend to grasp, close the gripper or play sequences as part of this skill.
- Do not guess a target you cannot see, and do not "correct" by nudging joints in a loop.
- A "Connection lost while reading" line from the bus has been seen before successful moves;
  if a move itself stops with a bus error, stop and report instead of retrying.
