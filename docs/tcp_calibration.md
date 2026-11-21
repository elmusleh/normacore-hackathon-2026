# TCP calibration: AprilTag table frame, arm base and joint zeros

Goal: one table coordinate frame in mm that the camera, the arm and Claude all share, so a
food seen at pixel (u, v) becomes a fingertip target (x, y, z) and then joint steps (IK).
Every command below **reads only**. The arm is moved by hand (torque off) or with the leader
arm. Commands that move the motors are still covered by `docs/bench_safety.md`, and only the
hardware owner named in `.ai-sync/HANDOFF.md` runs them.

Code: `src/tag_calibration.py` (tags, homography), `src/arm_kinematics.py` (URDF FK/IK, base fit,
joint-zero fit), `scripts/calib.py` (`./cli.sh calib ...`). Values: `config/calibration.json`.

## The table frame

```
        back (away from the person)
   tag 3 ------------------------- tag 2
     |                               |
     |   +y                          |
     |   ^                           |
     |   |                           |
   tag 0 ---> +x ----------------- tag 1
        front (the person's side)
```

Origin = centre of tag 0, +x toward tag 1, +y toward tag 3, z up from the table surface.

## Steps (about 45 minutes with the arm)

1. **Tags** (5 min). Either sheet works; `calib camera` detects which one is on the table:
   - The 45 mm sheet printed on 2026-11-21 (`docs/NormaCore Hackathon - 4-Corner AprilTags.pdf`).
     Its patterns are not real AprilTags, so the code reads them as a custom family `printed-v1`.
     At 45 mm they need the 480 px Station frames (`resize_target: 480`); at 299x224 they are
     missed. Use `--tag-size-mm` with the measured black square (about 45).
   - Or new real 36h11 tags, 80 mm: `./cli.sh apriltags`, print at 100 %.
   Measure the black square with a ruler. Use the new placement below (0 front-left), not the
   corner names printed on the old sheet.
2. **Tape the tags flat**, one per corner as labelled, all fully in the table camera's view,
   with nothing on top of them. Keep the camera fixed from now on: moving it means redoing step 4.
3. **Measure the layout** (5 min). Tape-measure centre to centre: 0→1 (width), 0→3 (depth), and
   both diagonals (0→2, 1→3) to check the corners are square.
   `./cli.sh calib layout --width-mm W --depth-mm D --tag-size-mm S`
   If the diagonals differ by more than ~5 mm, give each centre instead:
   `./cli.sh calib layout --tag 0 0 0 --tag 1 W 0 --tag 2 X2 Y2 --tag 3 X3 Y3`.
4. **Camera** (2 min, Station running). `./cli.sh calib camera` and look at the overlay in
   `data/calibration/`: the blue grid must lie flat on the table and pass through the tag centres.
   Then `./cli.sh calib camera --write`. Warnings to act on: *mirrored* (tags 1 and 3 swapped),
   *tag squares N mm off* (re-measure), *only N px wide* (bigger tags or the 480 px Station resize).
5. **Joint zero** (5 min, hardware owner). Torque off (or teleop), hold the arm in the URDF zero
   pose: upper arm straight up, forearm and gripper level, pointing straight ahead from the base.
   `./cli.sh calib zero` shows the readings, then `./cli.sh calib zero --write`.
6. **Touch points** (15 min, hardware owner). Close the gripper. For each tag: put the closed
   fingertips on the tag's centre and run `./cli.sh calib touch <id>`. Do every tag **twice**, with
   the elbow clearly higher or lower the second time. Extra points measured with the tape: `calib touch 250,120`.
7. **Fit** (1 min). `./cli.sh calib fit --refine` fits the base pose, the zeros of motors 2–4 and
   the directions of motors 1–4. Accept with `--write` when the RMS is below ~10 mm; above 15 mm,
   look at which points are bad (`calib touch --list`) and redo them.
8. **Check** (5 min). Put the fingertips on any marked spot and run `./cli.sh calib where`: the
   table coordinates should match the tape measure to ~1 cm. `./cli.sh calib reach X Y Z --down`
   prints the joint steps for a target and flags anything outside the motor ranges. Nothing moves.
9. **Commit** the values (the person who measured): `config/calibration.json` alone, as
   `chore(elrobot): record table and TCP calibration measured <date>`.

## Limits to know

- The camera mapping is only exact on the table surface (z = 0). A 30 mm tall object seen from
  an angle appears shifted away from the camera; use its base (bottom edge) or correct for height.
- Motor 1's zero cannot be told apart from the base yaw: the fit puts it in the yaw.
- The URDF wrist and gripper geometry is assumed correct; the TCP offset (closed fingertip,
  103.5 mm past the Gripper_Base frame) comes from the jaw meshes, not a ruler.
- `calib reach` only computes. Driving the arm to Cartesian targets needs a motion command that
  the hardware owner reviews (see `.ai-sync/HANDOFF.md`).
