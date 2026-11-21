"""Tests for the ElRobot MCP tools (src/robot_tools.py) against a fake arm.

No Station, no hardware. Config and waypoints go to a temp folder.
"""

import asyncio
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import elrobot_config  # noqa: E402
from elrobot_hardware import ELROBOT_MOTOR_IDS, MotorReading  # noqa: E402
from robot_tools import RobotTools  # noqa: E402

SDK = ROOT / "external" / "norma-core"


def reading(m, present=2000, torque=True, rmin=1000, rmax=3000, current=10):
    return MotorReading(motor_id=m, present=present, goal=present, torque_on=torque, status=0,
                        current=current, range_min=rmin, range_max=rmax)


class FakeArm:
    """Like ElRobotHardwareSync: positions jump to goals unless a motor is set to stall at a value."""

    def __init__(self):
        self.readings = {m: reading(m) for m in ELROBOT_MOTOR_IDS}
        self.moves = []
        self.raw_moves = []
        self.stall_at = {}  # motor -> position it stops at
        self.held = []
        self.frames = {}
        self.first = {}  # queue -> first entry bytes (camera connect event)

    def snapshot(self):
        return dict(self.readings)

    def move_and_watch(self, goals, **kw):
        self.moves.append(dict(goals))
        status = {}
        for m, g in goals.items():
            stop = self.stall_at.get(m)
            pos = g if stop is None else stop
            self.readings[m] = replace(self.readings[m], present=pos, goal=g)
            status[m] = "reached" if stop is None else "overload"
        return status

    def move_motors(self, goals, **kw):
        self.raw_moves.append(dict(goals))

    def hold(self, ids):
        self.held.extend(ids)

    def torque_on_hold(self, ids):
        for m in ids:
            self.readings[m] = replace(self.readings[m], torque_on=True)

    def read_recent(self, queue, back=1, timeout_s=3.0):
        items = self.frames.get(queue, [])
        return items[-back] if back <= len(items) else None

    def read_first(self, queue, timeout_s=3.0):
        return self.first.get(queue)

    def close(self):
        pass


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(elrobot_config, "CONFIG_FILE", tmp_path / "elrobot.json")
    monkeypatch.setattr(elrobot_config, "WAYPOINTS_FILE", tmp_path / "waypoints.json")
    monkeypatch.setattr(elrobot_config, "CONFIG_DIR", tmp_path)
    monkeypatch.setenv("ELROBOT_ALLOW_MOTION", "1")
    arm = FakeArm()
    tools = RobotTools(lambda: arm, camera_queues=lambda: ["usbvideo/abc", "usbvideo/old"],
                       usb_ports_fn=lambda: {(3, 26): "3-2.4"})
    return tools, arm, tmp_path


def save_points(tmp_path, points):
    (tmp_path / "waypoints.json").write_text(json.dumps(points))


def pose(value, gripper=2000):
    return {str(m): (gripper if m == 8 else value) for m in ELROBOT_MOTOR_IDS}


def test_motion_disabled_returns_plan_and_moves_nothing(env, monkeypatch):
    tools, arm, tmp = env
    monkeypatch.setenv("ELROBOT_ALLOW_MOTION", "0")
    save_points(tmp, {"clear": pose(2100), "pick_1": pose(2200)})
    res = tools.go_to_waypoint("pick_1")
    assert res["ok"] and all(leg["dry_run"] for leg in res["legs"])
    assert res["route"] == ["clear", "pick_1"]
    assert arm.moves == []


def test_routes_through_clear_and_leaves_gripper(env):
    tools, arm, tmp = env
    save_points(tmp, {"clear": pose(2100, gripper=1500), "pick_1": pose(2300, gripper=1500)})
    res = tools.go_to_waypoint("pick_1")
    assert res["ok"], res
    assert res["route"] == ["clear", "pick_1"]
    assert [set(m) for m in arm.moves] == [set(range(1, 8))] * 2
    assert arm.readings[1].present == 2300 and arm.readings[8].present == 2000


def test_already_at_clear_skips_the_detour(env):
    tools, arm, tmp = env
    save_points(tmp, {"clear": pose(2010), "pick_1": pose(2300)})
    assert tools.go_to_waypoint("pick_1")["route"] == ["pick_1"]


def test_large_move_refused(env):
    tools, arm, tmp = env
    for m in arm.readings:  # start near the bottom of the range so the hop exceeds the 1500 cap
        arm.readings[m] = replace(arm.readings[m], present=1000, goal=1000)
    save_points(tmp, {"far": pose(2900)})
    res = tools.go_to_waypoint("far", via_clear=False)
    assert not res["ok"] and "refused" in res["error"]
    assert arm.moves == []


def test_torque_off_refused(env):
    tools, arm, tmp = env
    arm.readings[3] = replace(arm.readings[3], torque_on=False)
    save_points(tmp, {"near": pose(2050)})
    res = tools.go_to_waypoint("near", via_clear=False)
    assert not res["ok"] and "enable_torque" in res["legs"][0]["error"]


def test_nudge_limits(env):
    tools, arm, tmp = env
    assert not tools.nudge_joint(2, 20)["ok"]
    assert not tools.nudge_joint(8, 1)["ok"]
    res = tools.nudge_joint(2, 5)
    assert res["ok"] and res["delta_steps"] == 100  # 5% of a 2000-step range
    assert arm.readings[2].present == 2100


def test_gripper_stalling_on_object_is_a_grasp(env):
    tools, arm, tmp = env
    arm.readings[8] = replace(arm.readings[8], present=2900)  # open
    arm.stall_at[8] = 1800  # stops on an object, well before closed (1000 + margin)
    res = tools.set_gripper(0)
    assert res["result"] == "holding_object" and res["ok"]
    assert arm.raw_moves == [{8: 1790}]  # light squeeze toward closed
    assert tools.get_robot_state()["gripper"]["likely_holding_object"] is True


def test_gripper_closing_fully_is_a_miss(env):
    tools, arm, tmp = env
    arm.readings[8] = replace(arm.readings[8], present=2900)
    res = tools.set_gripper(0)
    assert res["result"] == "closed_empty"
    assert "warning" in res  # direction not verified yet


def test_teach_waypoint(env):
    tools, arm, tmp = env
    assert tools.teach_waypoint("bin_a")["ok"]
    assert not tools.teach_waypoint("bin_a")["ok"]
    assert tools.teach_waypoint("bin_a", overwrite=True)["ok"]
    assert not tools.teach_waypoint("Bad Name")["ok"]


def test_state_reports_percent_and_nearest(env):
    tools, arm, tmp = env
    save_points(tmp, {"home": pose(2000), "other": pose(2500)})
    st = tools.get_robot_state()
    assert st["joints"][0]["percent_of_range"] == 50.0
    assert st["nearest_waypoint"]["name"] == "home"


def test_stop_allowed_with_motion_disabled(env, monkeypatch):
    tools, arm, tmp = env
    monkeypatch.setenv("ELROBOT_ALLOW_MOTION", "0")
    assert tools.stop()["ok"] and arm.held == list(ELROBOT_MOTOR_IDS)


def test_errors_become_results(env):
    tools, arm, tmp = env

    def boom():
        raise RuntimeError("no st3215/inference frames from station")

    res = tools.call(boom)
    assert res == {"ok": False, "error": "RuntimeError: no st3215/inference frames from station"}


needs_sdk = pytest.mark.skipif(not (SDK / "target" / "gen_python").exists(),
                               reason="norma-core SDK not downloaded")


def _envelopes():
    sys.path.insert(0, str(SDK))
    from target.gen_python.protobuf.drivers.usbvideo import frame, usbvideo

    def frame_entry(jpeg):
        return usbvideo.RxEnvelope(
            type=usbvideo.RxEnvelopeType.ET_FRAMES,
            frames=frame.FramesPack(
                format=frame.FrameFormat(width=298, height=224, kind=frame.FrameFormatKind.FF_JPEG),
                stamps=[frame.FrameStamp(local_stamp_ns=1)],
                frames_data=[jpeg],
            ),
        ).encode()

    def connect_entry(unique_id):
        return usbvideo.RxEnvelope(type=usbvideo.RxEnvelopeType.ET_DEVICE_CONNECTED,
                                   camera=usbvideo.Camera(product="KD-USB Cameras", unique_id=unique_id)).encode()

    return frame_entry, connect_entry


@needs_sdk
def test_look_decodes_station_jpeg(env):
    frame_entry, connect_entry = _envelopes()
    tools, arm, tmp = env
    jpeg = b"\xff\xd8fakejpeg\xff\xd9"
    arm.first["usbvideo/abc"] = connect_entry("11391:19040:3:26")
    arm.first["usbvideo/old"] = connect_entry("11391:19040:3:21")  # unplugged, older queue
    arm.frames["usbvideo/abc"] = [frame_entry(jpeg), connect_entry("x")]  # newest entry is not a frame
    meta, data = tools.look()
    assert data == jpeg and meta["width"] == 298 and meta["queue"] == "usbvideo/abc"
    cams = tools.list_cameras()
    assert [c["queue"] for c in cams["cameras"]] == ["usbvideo/abc"] and cams["unplugged_old_queues"] == 1


@needs_sdk
def test_camera_named_by_usb_port(env):
    frame_entry, connect_entry = _envelopes()
    tools, arm, tmp = env
    (tmp / "elrobot.json").write_text(json.dumps({"cameras": {"table": "port:3-2.4", "gripper": "port:3-2.2"}}))
    arm.first["usbvideo/abc"] = connect_entry("11391:19040:3:26")
    arm.frames["usbvideo/abc"] = [frame_entry(b"jpg")]
    meta, data = tools.look("table")
    assert data == b"jpg" and tools.list_cameras()["cameras"][0]["name"] == "table"
    meta, data = tools.look("gripper")
    assert data is None and "not plugged in" in meta["error"]


def test_server_registers_tools():
    pytest.importorskip("mcp")
    import robot_mcp_server

    names = {t.name for t in asyncio.run(robot_mcp_server.server.list_tools())}
    assert {"look", "get_robot_state", "go_to_waypoint", "set_gripper", "stop",
            "nudge_joint", "list_waypoints", "teach_waypoint", "enable_torque", "list_cameras"} <= names


def test_camera_discovery_finds_station_id_layout(tmp_path, monkeypatch):
    from elrobot_camera import discover_camera_queues

    monkeypatch.delenv("ELROBOT_CAMERA_QUEUES", raising=False)
    (tmp_path / "73c0ff" / "usbvideo" / "aa11" / "wal").mkdir(parents=True)
    (tmp_path / "73c0ff" / "st3215" / "inference" / "wal").mkdir(parents=True)
    assert discover_camera_queues(tmp_path) == ["usbvideo/aa11"]
