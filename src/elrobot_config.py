"""Robot configuration (committed) and run state (local), kept in separate files.

  config/elrobot.json     robot facts you decide once and commit: joint map, current
                          thresholds, workspace limits. Edit by hand or with ./cli.sh hw.
  config/waypoints.json   named joint poses taught on the arm (./cli.sh hw teach).
  config/sequences.json   named lists of waypoints played in order (./cli.sh hw record / play).
  data/hw_day_state.json  checklist progress for this machine. Local, gitignored.

The workspace defaults equal the values the code used before this file existed,
so nothing changes until you measure the real table and edit config/elrobot.json.
"""

from __future__ import annotations

import copy
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = Path(os.environ.get("ELROBOT_CONFIG_DIR", ROOT / "config"))
DATA_DIR = Path(os.environ.get("ELROBOT_DATA_DIR", ROOT / "data"))
CONFIG_FILE = CONFIG_DIR / "elrobot.json"
WAYPOINTS_FILE = CONFIG_DIR / "waypoints.json"
SEQUENCES_FILE = CONFIG_DIR / "sequences.json"
STATE_FILE = DATA_DIR / "hw_day_state.json"

# Current threshold in raw ST3215 current units. 100 is the NormaCore teleop
# example's default. It is NOT measured on this arm: run ./cli.sh hw probe-current.
DEFAULT_CURRENT_THRESHOLD = 100

DEFAULTS: Dict[str, Any] = {
    # leader_bus: serial of the leader (master) arm's bus, read by ./cli.sh hw leader. Never written to.
    "station": {"server": "localhost", "bus": "auto", "leader_bus": ""},
    # motor id (string) -> {"joint": ..., "direction": ..., "note": ...}; filled by ./cli.sh hw identify
    "joint_map": {},
    # motor id (string) -> current threshold; missing motors use the default
    "current_threshold": {},
    "default_current_threshold": DEFAULT_CURRENT_THRESHOLD,
    # Gripper (motor 8). open_at: which end of the calibrated range is OPEN ("max" or "min").
    # Not checked on the arm yet: run ./cli.sh hw identify and set verified to true.
    "gripper": {"motor": 8, "open_at": "max", "verified": False, "squeeze_steps": 10},
    # Friendly camera names for the MCP server, e.g. {"table": "usbvideo/<hash>"}.
    "cameras": {},
    # Fixed exposure per named camera, applied by ./cli.sh cameras (auto exposure washes out under the Station).
    "camera_settings": {},
    # Limits for moves requested by Claude through the MCP server (src/robot_mcp_server.py).
    "agent": {
        "max_speed": 500,
        "max_waypoint_delta_steps": 1500,
        "max_nudge_percent": 5.0,
        "clear_waypoint": "clear",
        # play_sequence (recorded plans, config/sequences.json): speed, pause at each waypoint (s),
        # and how far short of a waypoint a stopped motor may be (loaded joints sag 20-45 steps).
        "sequence_speed": 300,
        "sequence_pause_s": 1.5,
        "sequence_tolerance_steps": 60,
    },
    # What Claude can serve: food name -> {"sequence": <name in config/sequences.json>, "note": ...}.
    # Claude picks the plan from the person's request ("I want grapes" -> the grapes sequence).
    "foods": {},
    "workspace": {
        # Measured on the real table with a tape measure. Relative to the arm base, in mm.
        "x_min_mm": -180.0,
        "x_max_mm": 180.0,
        "y_min_mm": 90.0,
        "y_max_mm": 270.0,
        "z_table_floor_mm": 12.0,
        "z_transit_mm": 70.0,
        "z_hover_mm": 45.0,
        "z_grasp_mm": 14.0,
        "measured": False,
    },
}

log = logging.getLogger("elrobot.config")


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config() -> Dict[str, Any]:
    """Defaults overlaid with config/elrobot.json. A broken file falls back to defaults and says so."""
    if not CONFIG_FILE.exists():
        return copy.deepcopy(DEFAULTS)
    try:
        return _deep_merge(DEFAULTS, json.loads(CONFIG_FILE.read_text()))
    except (OSError, json.JSONDecodeError) as exc:
        log.error("config/elrobot.json is unreadable (%s); using defaults. Fix the file.", exc)
        return copy.deepcopy(DEFAULTS)


def save_config(cfg: Dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2) + "\n")
    tmp.replace(CONFIG_FILE)


def load_waypoints() -> Dict[str, Dict[str, int]]:
    if not WAYPOINTS_FILE.exists():
        return {}
    try:
        return json.loads(WAYPOINTS_FILE.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        log.error("config/waypoints.json is unreadable (%s); no waypoints loaded.", exc)
        return {}


def save_waypoints(points: Dict[str, Dict[str, int]]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = WAYPOINTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(points, indent=2, sort_keys=True) + "\n")
    tmp.replace(WAYPOINTS_FILE)


def load_sequences() -> Dict[str, List[str]]:
    if not SEQUENCES_FILE.exists():
        return {}
    try:
        return json.loads(SEQUENCES_FILE.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        log.error("config/sequences.json is unreadable (%s); no sequences loaded.", exc)
        return {}


def save_sequences(seqs: Dict[str, List[str]]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SEQUENCES_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(seqs, indent=2, sort_keys=True) + "\n")
    tmp.replace(SEQUENCES_FILE)


def load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            log.warning("data/hw_day_state.json is corrupt; starting the checklist fresh")
    return {"done": {}}


def save_state(state: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n")
    tmp.replace(STATE_FILE)


def current_threshold_for(cfg: Dict[str, Any], motor_id: int) -> int:
    return int(cfg["current_threshold"].get(str(motor_id), cfg["default_current_threshold"]))


def workspace_limits(cfg: Dict[str, Any]) -> Dict[str, Any]:
    return dict(cfg["workspace"])


def describe_joint_map(cfg: Dict[str, Any]) -> List[str]:
    lines = []
    for mid in sorted(cfg["joint_map"], key=int):
        j = cfg["joint_map"][mid]
        note = f" ({j['note']})" if j.get("note") else ""
        lines.append(f"motor {mid}: {j['joint']} dir {j['direction']}{note}")
    return lines
