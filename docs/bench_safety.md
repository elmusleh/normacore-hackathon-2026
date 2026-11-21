# Bench Safety

Read this before any command that moves a motor or turns torque on (`hw jog`, `hw goto`, `hw torque on`, `hw identify`, `hw probe-current`). Owner: the hardware owner named in `HANDOFF.md`. Last reviewed 2026-11-21.

## Before the arm is powered
- The hardware owner is named in `HANDOFF.md`. Only that person sends motion commands.
- The workspace is clear. No hands, tools, cables or loose objects in the arm's reach. Mark the area on the table if needed.
- A second person is in the room.
- The 12 V supply switch is within reach.

## During a motion test
- Keep a hand on the 12 V supply switch. This is the real stop.
- Torque on first. Moves are refused while torque is off, so the arm holds its pose.
- Start small. `hw jog` is capped at ±200 steps. Do not use `hw goto --allow-large` on the first run, and do not run any move on a motor whose current threshold has not been measured. The default threshold (100) is not measured on this arm, so run `hw probe-current <m>` first.
- The overload guard holds the arm where it is when it trips. It does not reverse. Treat a trip as a reason to stop and look.

## Stopping
1. Stop the software: `./cli.sh hw stop`. This turns torque off on all motors.
   Torque off means the arm goes limp and can drop. Support any raised part of the arm before you run it.
2. If the arm does not respond, or moves in a way you did not command: cut the 12 V supply at the switch. Do not reach into the arm's reach until it has stopped.
3. Tell the hardware owner, and record what happened in `HANDOFF.md` under Blockers. Attach the output of `./cli.sh logs`.

## Who to call
- Anything on the arm: the hardware owner in `HANDOFF.md`.
- Safety questions and rule changes: whoever holds Systems, Kinematics & Safety in the team split in `README.md`.

## Recordings
Camera frames and logs can show people in the room. Follow the privacy rule in `AGENTS.md`.
