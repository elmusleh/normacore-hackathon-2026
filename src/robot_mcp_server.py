"""MCP server that lets Claude see and move the real ElRobot through the NormaCore Station.

Run by Claude Code from .mcp.json (stdio). Needs the Station running (./cli.sh station)
and the `mcp` package (.venv, see README). Motion is OFF unless ELROBOT_ALLOW_MOTION=1;
until then every motion tool returns its plan without moving anything.

Environment:
  ELROBOT_ALLOW_MOTION=1        allow the arm to move
  ELROBOT_STATION / ELROBOT_BUS Station host and bus serial (default: config/elrobot.json)
  ELROBOT_CAMERA_QUEUES         comma-separated usbvideo/<hash> queues (default: discovered)

The simulator tools (pick_at, place_at on a mock table) stay in src/mcp_server.py.
Logs go to logs/mcp-*.log and stderr. Never print to stdout: it carries the MCP protocol.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp.server.mcpserver import Image, MCPServer  # noqa: E402

from elrobot_config import load_config  # noqa: E402
from elrobot_hardware import ElRobotHardwareSync  # noqa: E402
from elrobot_log import setup_logging  # noqa: E402
from robot_tools import RobotTools, motion_allowed  # noqa: E402

log = logging.getLogger("elrobot.mcp")

INSTRUCTIONS = """\
You control a real ElRobot arm (7 joints + gripper) on a table, through joint-level tools.
There are no x/y/z moves: the arm moves between named waypoints that a human taught on the
arm, plus small joint nudges and the gripper.

Recorded feeding plans come first. A human recorded and tested whole motion plans
(pick a food, bring it to the person, return). list_sequences() shows them and, under
"foods", which food each plan serves. When the person asks for a food ("I want grapes",
"can I have some chocolate"), pick the matching plan yourself and run play_sequence(name)
once; it runs the whole plan in one call. Do not add moves before or after it, and do not
rebuild a plan from single waypoints. If the request matches no food, or the plan is not
ready, say which foods are available and do not move. If two foods could match, ask.

For anything else, work in a loop: look -> act -> look again.
1. look() at the table camera and get_robot_state() before acting.
2. list_waypoints() to see which poses exist (e.g. clear, pick_1, bin_a).
3. Move with go_to_waypoint(). It routes through 'clear' so the arm does not sweep the table.
4. Grasp with set_gripper(0). result 'holding_object' means it closed on something;
   'closed_empty' means it missed. Then look() to confirm.
5. After every move, look() again. If an object moved, re-plan instead of repeating blindly.

If a result has ok=false, read the error and hint, look at the camera, and do not retry the
same move more than once. If anything looks unsafe, call stop() and tell the human.
If results say dry_run, motion is disabled: describe what you would do and tell the human
to set ELROBOT_ALLOW_MOTION=1.
"""


def _connect() -> ElRobotHardwareSync:
    cfg = load_config()
    server = os.environ.get("ELROBOT_STATION", cfg["station"]["server"])
    bus = os.environ.get("ELROBOT_BUS", cfg["station"]["bus"])
    hw = ElRobotHardwareSync(server=server, bus=bus)
    try:
        hw.connect(timeout_s=10)
    except Exception as exc:
        hw.close()
        raise ConnectionError(
            f"cannot reach the ElRobot through the Station at {server} (bus={bus}): {exc}. "
            "Is ./cli.sh station running and the arm powered and plugged in? "
            "With two arms connected, set ELROBOT_BUS to the follower's serial."
        ) from exc
    return hw


tools = RobotTools(_connect)
server = MCPServer(name="elrobot", instructions=INSTRUCTIONS)


@server.tool(structured_output=False)
def get_robot_state() -> dict:
    """Read every joint: position as % of its calibrated range, torque, current, faults; the
    gripper opening (0 = closed, 100 = open) and whether it seems to be holding something;
    and which taught waypoint the arm is closest to. Moves nothing."""
    return tools.call(tools.get_robot_state)


@server.tool(structured_output=False)
def look(camera: str = "") -> list:
    """Take the newest picture from a camera. camera: a configured name like 'table' or
    'gripper', a usbvideo queue id, or empty for the table camera (or the first camera).
    Returns frame info and the image. Check age_seconds: an old frame means a stalled camera."""
    result = tools.call(lambda: _look(camera))
    return result if isinstance(result, list) else [result]


def _look(camera: str):
    meta, jpeg = tools.look(camera)
    return [meta] if jpeg is None else [meta, Image(data=jpeg, format="jpeg")]


@server.tool(structured_output=False)
def list_cameras() -> dict:
    """List the cameras the Station is recording, with their queue ids and names."""
    return tools.call(tools.list_cameras)


@server.tool(structured_output=False)
def list_waypoints() -> dict:
    """List the named arm poses taught on this arm (e.g. clear, home, pick_1, bin_a)."""
    return tools.call(tools.list_waypoints)


@server.tool(structured_output=False)
def go_to_waypoint(name: str, via_clear: bool = True, include_gripper: bool = False,
                   speed: Optional[int] = None) -> dict:
    """Move the arm to a taught waypoint and wait until it arrives.
    via_clear (default true) goes through the 'clear' waypoint first, so the arm never sweeps
    across the table; set false only for a short hop between nearby poses (e.g. hover -> grasp).
    include_gripper=false leaves the gripper as it is. A move that is too large is refused.
    Returns per-motor status; ok=false means a motor stopped early (obstacle or overload)."""
    return tools.call(tools.go_to_waypoint, name, via_clear, include_gripper, speed)


@server.tool(structured_output=False)
def nudge_joint(motor: int, delta_percent: float, speed: Optional[int] = None) -> dict:
    """Move one joint (motor 1-7) by a small amount, as % of its calibrated range (max 5%
    per call; positive or negative). For fine alignment after a waypoint. Look first."""
    return tools.call(tools.nudge_joint, motor, delta_percent, speed)


@server.tool(structured_output=False)
def set_gripper(open_percent: float) -> dict:
    """Open or close the gripper: 100 = fully open, 0 = fully closed. When closing, result is
    'holding_object' if it stopped on something (it then keeps a light squeeze), or
    'closed_empty' if it closed fully, meaning the grasp missed."""
    return tools.call(tools.set_gripper, open_percent)


@server.tool(structured_output=False)
def list_sequences() -> dict:
    """List the recorded motion plans and the foods they serve ("foods": food -> plan name,
    whether it is ready). Use it to choose the plan for what the person asked for. Moves nothing."""
    return tools.call(tools.list_sequences)


@server.tool(structured_output=False)
def play_sequence(name: str) -> dict:
    """Run a recorded plan (e.g. the one for grapes) from start to end, in one call: the arm
    goes through every recorded pose, waits until it has stopped at each one, pauses briefly,
    then goes on. Takes about 20-60 s. On any problem (obstacle, overload, not arriving) or a
    stop() call it holds the arm where it is and returns ok=false with the step it stopped at."""
    return tools.call(tools.play_sequence, name)


@server.tool(structured_output=False)
def check_person_mouth() -> dict:
    """Check the live OBSBOT Person Cam with MediaPipe FaceLandmarker: returns face_detected,
    MAR (Mouth Aspect Ratio), mouth_open, mouth_open_confirmed (3-frame debounce), standoff_cm,
    and whether the mouth-open safety gate is enabled. Moves nothing."""
    return tools.call(tools.check_person_mouth)


@server.tool(structured_output=False)
def set_mouth_gate(enabled: bool) -> dict:
    """Enable or disable the OBSBOT MediaPipe mouth-open safety gate during play_sequence.
    When enabled, play_sequence holds at the serve/feed waypoint until the person opens their
    mouth (3 frames confirmed) and stops if they turn away."""
    return tools.call(tools.set_mouth_gate, enabled)


@server.tool(structured_output=False)
def stop() -> dict:
    """Stop: hold every motor where it is right now. Always allowed, also while play_sequence is
    running (it interrupts the plan). Use if anything looks wrong."""
    return tools.stop_now()


@server.tool(structured_output=False)
def enable_torque() -> dict:
    """Turn torque on for all motors, holding the current pose (no jump). Needed before moves
    if get_robot_state shows torque_on=false. Torque can only be turned off by the human."""
    return tools.call(tools.enable_torque)


@server.tool(structured_output=False)
def teach_waypoint(name: str, overwrite: bool = False) -> dict:
    """Save the arm's current pose as a named waypoint (lowercase, digits, - or _).
    Use when the human has positioned the arm and asks you to remember the pose."""
    return tools.call(tools.teach_waypoint, name, overwrite)


def main() -> None:
    path = setup_logging("mcp", console_level=logging.WARNING)
    log.info("ElRobot MCP server starting (motion %s), log %s",
             "ALLOWED" if motion_allowed() else "disabled", path)
    try:
        server.run("stdio")
    finally:
        tools.reset_connection()


if __name__ == "__main__":
    main()
