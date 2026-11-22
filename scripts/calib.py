#!/usr/bin/env python3
"""Table + arm calibration from 4 corner AprilTags, and Cartesian (TCP) lookups. Only `calib goto` moves the arm.

Usage (via ./cli.sh calib):
  calib layout --width-mm W --depth-mm D [--tag-size-mm S]   tape-measured tag-centre rectangle
  calib layout --tag 0 0 0 --tag 1 512 3 ...                 or each tag centre on its own
  calib camera [--camera table] [--image f.jpg] [--write]    detect tags, fit pixel -> table mm
  calib zero [--write]                 arm held in the URDF zero pose: record motor steps as zero
  calib touch <0-3 | x,y | x,y,z>      fingertips (closed) touching that point: record the pose
  calib touch --list | --clear
  calib fit [--refine] [--write]       arm base pose in the table frame (+ joint zeros/directions)
  calib where                          current fingertip position in base and table frames
  calib goto X Y Z [--down] [--speed N]  MOVES the arm: lift, across at 150 mm, descend (asks MOVE)
  calib reach X Y Z [--down]           IK: joint steps that put the fingertip at table point X Y Z
  calib pixel U V [--size WxH]         table point under a camera pixel
  calib show                           what is calibrated and how well

The table frame: origin = centre of tag 0 (front-left seen from the person), +x toward tag 1,
+y toward tag 3 (away from the person), z up, mm. See src/tag_calibration.py.
Read-only commands talk to the Station; move the arm by hand (torque off) or with the leader.
Calibration values are written to config/calibration.json only with --write (touch always records).
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from arm_kinematics import (  # noqa: E402
    ARM_MOTORS,
    ArmModel,
    BaseInTable,
    JointCalibration,
    fit_base_in_table,
    plan_cartesian_goto,
    refine_joint_zeros,
    step_delta,
    step_in_range,
)
from tag_calibration import (  # noqa: E402
    CALIBRATION_FILE,
    TableCamera,
    camera_config,
    detect_tags,
    draw_overlay,
    fit_camera,
    load_calibration,
    now_iso,
    rectangle_layout,
    save_calibration,
)

OUT_DIR = Path(os.environ.get("ELROBOT_DATA_DIR", ROOT / "data")) / "calibration"


# -- helpers ----------------------------------------------------------------------------------

def _rel(path: Path) -> str:
    try:
        return str(Path(path).relative_to(ROOT))
    except ValueError:
        return str(path)


def _model(cal: dict) -> ArmModel:
    return ArmModel(tcp_offset_mm=cal["joints"]["tcp_offset_mm"])


def _hw():
    from elrobot_config import load_config
    from elrobot_hardware import ElRobotHardwareSync
    cfg = load_config()
    hw = ElRobotHardwareSync(server=cfg["station"]["server"], bus=cfg["station"]["bus"])
    try:
        hw.connect(timeout_s=10)
    except Exception as exc:  # noqa: BLE001
        hw.close()
        raise SystemExit(f"ERROR: cannot read the follower through the Station: {exc}\n"
                         "Is ./cli.sh station running and the arm powered?")
    return hw


def _read_arm():
    """{motor: steps}, {motor: (min, max)} for motors 1..7. Read only."""
    hw = _hw()
    try:
        snap = hw.snapshot()
    finally:
        hw.close()
    missing = [m for m in ARM_MOTORS if m not in snap]
    if missing:
        raise SystemExit(f"ERROR: no reading for motors {missing}")
    return ({m: snap[m].present for m in ARM_MOTORS},
            {m: (snap[m].range_min, snap[m].range_max) for m in ARM_MOTORS})


def _grab_frame(camera: str):
    import cv2
    from robot_mcp_server import tools  # lazy: connects to the Station
    meta, jpeg = tools.look(camera)  # look() returns the camera's own JPEG
    if not jpeg:
        raise SystemExit(f"ERROR: no frame from camera {camera!r}: {meta.get('error', meta)}")
    return cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)


def _base(cal: dict) -> BaseInTable:
    return BaseInTable.from_config(cal["base_in_table"])


def _fmt(p, nd=1) -> str:
    return "(" + ", ".join(f"{v:.{nd}f}" for v in p) + ")"


def _warn_unmeasured(cal: dict) -> None:
    for key, what in (("table", "tag layout"), ("joints", "joint zeros"), ("base_in_table", "base pose")):
        if not cal[key].get("measured"):
            print(f"  NOTE: {what} not measured yet; numbers in that frame are guesses.")


def _parse_point(text: str, cal: dict):
    if text in {"0", "1", "2", "3"}:
        x, y = cal["table"]["tags_mm"][text]
        return [float(x), float(y), 0.0], f"tag {text}"
    vals = [float(v) for v in text.split(",")]
    if len(vals) == 2:
        vals.append(0.0)
    if len(vals) != 3:
        raise SystemExit("ERROR: point is a tag id 0-3, x,y or x,y,z (mm, table frame)")
    return vals, _fmt(vals, 0)


# -- commands ---------------------------------------------------------------------------------

def cmd_layout(args, cal):
    if args.tag:
        tags = dict(cal["table"]["tags_mm"])
        for tid, x, y in args.tag:
            if tid not in {"0", "1", "2", "3"}:
                raise SystemExit("ERROR: tag id must be 0-3")
            tags[tid] = [float(x), float(y)]
    elif args.width_mm and args.depth_mm:
        tags = rectangle_layout(args.width_mm, args.depth_mm)
    else:
        raise SystemExit("ERROR: give --width-mm and --depth-mm, or --tag ID X Y for each tag")
    cal["table"]["tags_mm"] = tags
    if args.tag_size_mm:
        cal["table"]["tag_size_mm"] = args.tag_size_mm
    cal["table"]["measured"] = True
    save_calibration(cal)
    print(f"Saved tag centres (mm) to {_rel(CALIBRATION_FILE)}:")
    for k in sorted(tags):
        print(f"  tag {k}: {_fmt(tags[k])}")
    d01 = math.dist(tags["0"], tags["1"])
    d03 = math.dist(tags["0"], tags["3"])
    diag = (math.dist(tags["0"], tags["2"]), math.dist(tags["1"], tags["3"]))
    print(f"  0-1 {d01:.0f} mm, 0-3 {d03:.0f} mm, diagonals {diag[0]:.0f} / {diag[1]:.0f} mm "
          "(measure both diagonals: they match only if the tags form a true rectangle)")


def cmd_camera(args, cal):
    import cv2
    img = cv2.imread(args.image) if args.image else _grab_frame(args.camera)
    if img is None:
        raise SystemExit(f"ERROR: cannot read image {args.image}")
    h, w = img.shape[:2]
    dets = detect_tags(img)
    fams = sorted({d.family for d in dets.values()})
    print(f"Frame {w}x{h}; tags found: {sorted(dets) or 'none'}" + (f" (family {', '.join(fams)})" if fams else ""))
    if "printed-v1" in fams:
        print("  Using the 2026-11-21 printed sheet (45 mm tags, not real AprilTags but readable). "
              "Pass the measured black-square size to calib layout --tag-size-mm (about 45).")
    for i in sorted(dets):
        print(f"  tag {i}: centre px {_fmt(dets[i].center)}, about {dets[i].side_px:.0f} px wide")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = now_iso().replace(":", "")
    try:
        cam, report = fit_camera(dets, cal["table"]["tags_mm"], float(cal["table"]["tag_size_mm"]), (w, h))
    except ValueError as exc:
        out = OUT_DIR / f"camera-{stamp}-FAILED.jpg"
        cv2.imwrite(str(out), draw_overlay(img, None, dets, cal["table"]["tags_mm"]))
        raise SystemExit(f"ERROR: {exc}\n  picture with what was found: {out}")
    print(f"Tag squares measured through the fit: {report['tag_square_rms_mm']} mm RMS off "
          f"{cal['table']['tag_size_mm']} mm (small = consistent layout, tag size and camera)")
    for wmsg in report["warnings"]:
        print(f"  WARNING: {wmsg}")
    base = None
    if cal["base_in_table"].get("measured"):
        b = _base(cal)
        base = (b.x_mm, b.y_mm, b.yaw_deg)
    out = OUT_DIR / f"camera-{stamp}.jpg"
    overlay = draw_overlay(img, cam, dets, cal["table"]["tags_mm"], base=base)
    cv2.imwrite(str(out), overlay)
    print(f"Overlay (check the grid lies flat on the table): {out}")
    if not cal["table"].get("measured"):
        print("  NOTE: tag layout is the placeholder; run calib layout first, then calib camera again.")
    if args.write:
        cal["camera"] = camera_config(cam, report, args.camera if not args.image else f"file:{args.image}")
        save_calibration(cal)
        print(f"Saved camera homography to {_rel(CALIBRATION_FILE)}")
    else:
        print("Not saved (add --write).")


def cmd_zero(args, cal):
    steps, _ = _read_arm()
    print("URDF zero pose: upper arm straight up, forearm and gripper level, pointing straight ahead;")
    print("fingers pointing where the base 'faces'. Current readings (motors 1-7):")
    for m in ARM_MOTORS:
        old = cal["joints"]["motors"][str(m)]["zero_steps"]
        print(f"  motor {m}: {steps[m]:5d}   (stored zero {old})")
    if args.write:
        for m in ARM_MOTORS:
            cal["joints"]["motors"][str(m)]["zero_steps"] = int(steps[m])
        cal["joints"]["zero_captured_at"] = now_iso()
        save_calibration(cal)
        print("Saved as zero_steps. Directions are still assumptions until calib fit --refine.")
    else:
        print("Not saved (add --write when the arm is in the zero pose).")


def cmd_touch(args, cal):
    pts = cal["base_in_table"].setdefault("points", [])
    if args.clear:
        cal["base_in_table"]["points"] = []
        save_calibration(cal)
        print("Cleared all touch points.")
        return
    if args.list or not args.point:
        for k, p in enumerate(pts):
            print(f"  {k}: {p['label']:12s} table {_fmt(p['table_mm'])}  steps {p['steps']}")
        print(f"{len(pts)} touch points.")
        return
    target, label = _parse_point(args.point, cal)
    steps, _ = _read_arm()
    model = _model(cal)
    tcp = model.tcp(JointCalibration.from_config(cal["joints"]).to_radians(steps)) * 1000
    pts.append({"label": label, "table_mm": target, "steps": {str(m): int(steps[m]) for m in ARM_MOTORS},
                "at": now_iso()})
    save_calibration(cal)
    print(f"Recorded touch #{len(pts) - 1} at {label} {_fmt(target)}; fingertip in base frame {_fmt(tcp)} mm "
          "(with the current joint zeros)")
    print(f"{len(pts)} points. calib fit needs >= 3; calib fit --refine needs >= 8 "
          "(touch each tag twice, in two clearly different arm poses).")


def _samples(cal):
    return [({int(m): int(s) for m, s in p["steps"].items()}, p["table_mm"]) for p in cal["base_in_table"]["points"]]


def cmd_fit(args, cal):
    samples = _samples(cal)
    model = _model(cal)
    jc = JointCalibration.from_config(cal["joints"])
    if args.refine:
        try:
            jc, base, rms, errs = refine_joint_zeros(model, jc, samples)
        except ValueError as exc:
            raise SystemExit(f"ERROR: {exc}. Touch each tag twice, in two clearly different arm poses "
                             "(calib touch --list shows what you have).")
        print("Joint calibration fitted from the touches:")
        for m in ARM_MOTORS:
            old = cal["joints"]["motors"][str(m)]
            print(f"  motor {m}: zero {old['zero_steps']} -> {jc.zero_steps[m]}, "
                  f"direction {old['direction']:+d} -> {jc.direction[m]:+d}")
    else:
        if len(samples) < 3:
            raise SystemExit(f"ERROR: {len(samples)} touch points; record at least 3 with calib touch")
        pts = [model.tcp(jc.to_radians(s)) for s, _ in samples]
        base, rms, errs = fit_base_in_table(pts, [t for _, t in samples])
    print(f"Arm base in table frame: x {base.x_mm:.1f} mm, y {base.y_mm:.1f} mm, yaw {base.yaw_deg:.1f} deg, "
          f"base z {base.z_mm:.1f} mm")
    print(f"Fit error: {rms:.1f} mm RMS")
    for p, e in zip(cal["base_in_table"]["points"], errs):
        print(f"  {p['label']:12s} {e:6.1f} mm")
    if rms > 15:
        print("  WARNING: > 15 mm. Likely wrong joint zeros or directions (try --refine with >= 8 points),"
              " a touch that missed its target, or a wrong tag layout.")
    if args.write:
        cal["base_in_table"].update({"x_mm": round(base.x_mm, 2), "y_mm": round(base.y_mm, 2),
                                     "yaw_deg": round(base.yaw_deg, 3), "z_mm": round(base.z_mm, 2),
                                     "rms_mm": round(rms, 2), "fitted_at": now_iso(), "measured": True})
        if args.refine:
            for m in ARM_MOTORS:
                cal["joints"]["motors"][str(m)] = {"zero_steps": int(jc.zero_steps[m]),
                                                   "direction": int(jc.direction[m])}
            cal["joints"]["measured"] = True
        save_calibration(cal)
        print(f"Saved to {_rel(CALIBRATION_FILE)}")
    else:
        print("Not saved (add --write).")


def cmd_where(args, cal):
    steps, _ = _read_arm()
    model = _model(cal)
    q = JointCalibration.from_config(cal["joints"]).to_radians(steps)
    p = model.tcp(q)
    a = model.approach(q)
    print(f"Fingertip, base frame:  {_fmt(p * 1000)} mm; fingers point {_fmt(a, 2)}")
    t = _base(cal).base_to_table(p)
    print(f"Fingertip, table frame: {_fmt(t)} mm")
    if cal.get("camera", {}).get("pixel_to_table"):
        u, v = TableCamera.from_config(cal["camera"]).table_to_pixel(t[0], t[1])
        print(f"Table camera pixel under it: ({u:.0f}, {v:.0f}) at {cal['camera']['image_size']}")
    _warn_unmeasured(cal)


def cmd_reach(args, cal):
    model = _model(cal)
    jc = JointCalibration.from_config(cal["joints"])
    target_table = [args.x, args.y, args.z]
    target = _base(cal).table_to_base(target_table)
    if args.offline:
        steps, ranges = {m: jc.zero_steps[m] for m in ARM_MOTORS}, {}
    else:
        steps, ranges = _read_arm()
    seed = jc.to_radians(steps)
    lo, hi = jc.limits_from_ranges(ranges, model)
    q, err = model.solve(target, seed, lower=lo, upper=hi, point_down=args.down, locked=(7,))
    goal = jc.to_steps(q)
    print(f"Target table {_fmt(target_table)} mm = base {_fmt(target * 1000)} mm; IK error {err * 1000:.1f} mm"
          + ("; fingers down" if args.down else ""))
    if err > 0.005:
        print("  NOT REACHABLE within joint limits (error > 5 mm).")
    for m in ARM_MOTORS:
        rng = f"range {ranges[m][0]}..{ranges[m][1]}" if m in ranges else "range unknown (offline)"
        flag = ""
        if m in ranges and not step_in_range(goal[m], *ranges[m]):
            flag = "  OUT OF RANGE"
        print(f"  motor {m}: {steps[m]:5d} -> {goal[m]:5d} ({step_delta(steps[m], goal[m]):+5d})  {rng}{flag}")
    if args.z < 5:
        print("  WARNING: z < 5 mm is at or below the table surface.")
    print("Nothing moved. Motion to Cartesian targets is not wired in yet (needs the hardware owner).")
    _warn_unmeasured(cal)


def cmd_goto(args, cal):
    """Move the fingertip to a table point. The only calib command that moves the arm."""
    import hw_day  # motion helpers: Station connection, MOVE prompt, torque check, speed cap
    from elrobot_config import current_threshold_for
    from elrobot_hardware import DEFAULT_MAX_ACCEL
    for key, what in (("joints", "joint zeros (calib zero + calib fit --refine)"),
                      ("base_in_table", "arm base (calib fit --write)")):
        if not cal[key].get("measured"):
            raise SystemExit(f"Refused: {what} not measured yet. Nothing moved.")
    rms = float(cal["base_in_table"].get("rms_mm") or 0.0)
    model, jc, base = _model(cal), JointCalibration.from_config(cal["joints"]), _base(cal)
    speed = min(args.speed, hw_day.JOG_MAX_SPEED)
    target = [args.x, args.y, args.z]

    def go(hw, cfg):
        readings = hw.snapshot()
        missing = [m for m in ARM_MOTORS if m not in readings]
        if missing:
            print(f"Refused: no reading for motors {missing}. Nothing moved.")
            return 1
        present = {m: readings[m].present for m in ARM_MOTORS}
        ranges = {m: (readings[m].range_min, readings[m].range_max) for m in ARM_MOTORS}
        try:
            legs = plan_cartesian_goto(model, jc, base, present, ranges, target,
                                       point_down=args.down, fit_rms_mm=rms)
        except ValueError as exc:
            print(f"Refused: {exc}. Nothing moved.")
            return 1
        if not hw_day._require_torque(readings, list(ARM_MOTORS)):
            return 1
        print(f"\nGoto table {_fmt(target)} mm" + (", fingers down" if args.down else "")
              + f", speed {speed}. Fit error {rms:.0f} mm: expect the fingertip within ~{2 * rms:.0f} mm.")
        prev = dict(present)
        for label, p, goals in legs:
            print(f"  {label:8s} -> {_fmt(p, 0)} mm: " + ", ".join(
                f"m{m} {prev[m]}->{goals[m]} ({goals[m] - prev[m]:+d})" for m in ARM_MOTORS if goals[m] != prev[m]))
            prev = goals
        print("  Gripper (motor 8) and wrist roll (motor 7) stay as they are.")
        if not hw_day._confirm_motion(args.yes, "Check the path is clear, hand on the 12 V switch."):
            print("Cancelled. Nothing moved.")
            return 0
        thresholds = {m: current_threshold_for(cfg, m) for m in ARM_MOTORS}
        for label, p, goals in legs:
            status = hw.move_and_watch(goals, enable_motion=True, max_speed=speed, max_accel=DEFAULT_MAX_ACCEL,
                                       thresholds=thresholds)
            if not all(st == "reached" for st in status.values()):
                print(f"Stopped during '{label}': " + ", ".join(f"{m}={st}" for m, st in sorted(status.items())))
                print("The arm holds where it stopped. Check for an obstacle, then ./cli.sh logs.")
                return 1
            print(f"  {label}: reached")
        final = hw.snapshot()
        tip = base.base_to_table(model.tcp(jc.to_radians({m: final[m].present for m in ARM_MOTORS})))
        print(f"Arrived. Fingertip by the joint readings: {_fmt(tip)} mm (target {_fmt(target)}).")
        return 0
    try:
        return hw_day._with_station(go)
    except hw_day.StationDown as exc:
        raise SystemExit(f"ERROR: {exc}")


def cmd_pixel(args, cal):
    cam = TableCamera.from_config(cal["camera"])
    size = tuple(int(v) for v in args.size.lower().split("x")) if args.size else None
    x, y = cam.pixel_to_table(args.u, args.v, size)
    print(f"Pixel ({args.u:g}, {args.v:g}) -> table ({x:.1f}, {y:.1f}) mm  (on the table surface, z = 0)")
    if cal["base_in_table"].get("measured"):
        b = _base(cal).table_to_base([x, y, 0.0]) * 1000
        print(f"  = base frame {_fmt(b)} mm")


def cmd_show(args, cal):
    t, c, j, b = cal["table"], cal.get("camera", {}), cal["joints"], cal["base_in_table"]
    print(f"Calibration file: {_rel(CALIBRATION_FILE)}")
    print(f"  table:  tag size {t['tag_size_mm']} mm, measured={t.get('measured')}, centres {t['tags_mm']}")
    if c.get("pixel_to_table"):
        print(f"  camera: {c.get('name')} {c.get('image_size')}, tag squares {c.get('tag_square_rms_mm')} mm RMS, "
              f"at {c.get('calibrated_at')}")
    else:
        print("  camera: not calibrated (calib camera --write)")
    print(f"  joints: measured={j.get('measured')}, tcp offset {j['tcp_offset_mm']} mm, "
          + ", ".join(f"m{m} {v['zero_steps']}/{v['direction']:+d}" for m, v in sorted(j['motors'].items())))
    print(f"  base:   measured={b.get('measured')}, x {b['x_mm']} y {b['y_mm']} yaw {b['yaw_deg']} z {b['z_mm']}, "
          f"rms {b.get('rms_mm')} mm, {len(b.get('points', []))} touch points")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("layout")
    p.add_argument("--width-mm", type=float, help="tag 0 centre to tag 1 centre")
    p.add_argument("--depth-mm", type=float, help="tag 0 centre to tag 3 centre")
    p.add_argument("--tag", nargs=3, action="append", metavar=("ID", "X", "Y"))
    p.add_argument("--tag-size-mm", type=float, help="measured side of the black square")
    p = sub.add_parser("camera")
    p.add_argument("--camera", default="table")
    p.add_argument("--image", help="use a saved picture instead of the live camera")
    p.add_argument("--write", action="store_true")
    p = sub.add_parser("goto", help="MOVE the fingertip to a table point (asks MOVE first)")
    p.add_argument("x", type=float)
    p.add_argument("y", type=float)
    p.add_argument("z", type=float)
    p.add_argument("--down", action="store_true", help="fingers pointing straight down")
    p.add_argument("--speed", type=int, default=200)
    p.add_argument("--yes", action="store_true", help="skip the MOVE prompt")
    p = sub.add_parser("zero")
    p.add_argument("--write", action="store_true")
    p = sub.add_parser("touch")
    p.add_argument("point", nargs="?")
    p.add_argument("--list", action="store_true")
    p.add_argument("--clear", action="store_true")
    p = sub.add_parser("fit")
    p.add_argument("--refine", action="store_true", help="also fit joint zeros (motors 2-4) and directions (1-4)")
    p.add_argument("--write", action="store_true")
    sub.add_parser("where")
    p = sub.add_parser("reach")
    p.add_argument("x", type=float)
    p.add_argument("y", type=float)
    p.add_argument("z", type=float)
    p.add_argument("--down", action="store_true", help="fingers pointing straight down")
    p.add_argument("--offline", action="store_true", help="do not read the arm; seed from the zero pose")
    p = sub.add_parser("pixel")
    p.add_argument("u", type=float)
    p.add_argument("v", type=float)
    p.add_argument("--size", help="WxH of the frame the pixel is from (default: calibration size)")
    sub.add_parser("show")
    args = ap.parse_args()
    cal = load_calibration()
    {"layout": cmd_layout, "camera": cmd_camera, "zero": cmd_zero, "touch": cmd_touch, "fit": cmd_fit,
     "where": cmd_where, "reach": cmd_reach, "goto": cmd_goto, "pixel": cmd_pixel, "show": cmd_show}[args.cmd](args, cal)
    return 0


if __name__ == "__main__":
    sys.exit(main())
