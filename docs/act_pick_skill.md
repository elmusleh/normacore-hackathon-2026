# ACT pick skill: grape or chocolate (imitation learning)

> **Superseded 2026-11-21 late:** the team dropped ACT in favour of AprilTag calibration + IK
> ([tcp_calibration.md](tcp_calibration.md)). Kept for history; the recorder still works.

Decided 2026-11-21 (Jafer, Christian): Claude keeps deciding **what** to pick from the chat
("I want grapes" -> grape). A learned **ACT** policy does the **moving**, trained on leader-arm
demonstrations. One ACT model per skill. First skills: `pick grape`, `pick chocolate`.
Feeding (deliver to the mouth) comes later, with the same recorder.

## 1. Record demonstrations (reads only)

1. Station running; teleop **ON** (Station viewer -> follower card -> leader serial).
2. Close the web console and any Claude session that can move the arm.
3. `./cli.sh demos record --skill pick --food grape` (then `--food chocolate`).
4. Per episode: place the food in a new spot, bring the arm to the same start pose (for example
   `arm_rest`) with the leader, Enter, pick the food up and lift it a few cm, Enter, keep or discard.
5. `./cli.sh demos list` counts episodes. Target: 60-100 per food.

Each tick (30 per second) stores the follower's position (state), the follower's goal register
(action: what teleop commanded, already in follower calibration), the leader position, and the
newest frame of the `table` and `gripper` cameras. Saved under `data/demos/<skill>/` (gitignored:
frames can show people).

Good demonstrations:
- Same start pose, same style, slow and smooth, no pauses to think.
- Vary only what will vary in real use: where the food sits. Cover the whole area.
- A few episodes where you correct a near miss teach recovery.
- Do not move the cameras, the table or the arm base between recording and use.

## 2. Next steps (not built yet)

- Convert to a LeRobot dataset (`.venv-lerobot`, separate from `.venv`).
- Train ACT per skill on the RTX 3080 Ti.
- Policy runner: model -> safety filter (calibrated range, recorded action space, step and speed
  caps, time limit, stop) -> follower. MCP tool `run_skill("pick", food)` so Claude can call it.
- Evaluate: 20 attempts per food, success rate and time.
