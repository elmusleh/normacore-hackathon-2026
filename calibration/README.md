# ElRobot calibration export

Exported on 2026-11-21 from the running NormaCore Station (`st3215/inference`), read-only.

| File | Arm | Bus serial |
|---|---|---|
| `elrobot_follower_5B61034962.json` | Follower (the arm the MCP server drives) | 5B61034962 |
| `elrobot_leader_5B61037051.json` | Leader (teleop, calibrated by hand at 5 V) | 5B61037051 |

Per motor (IDs 1-8, 8 = gripper):

- `range_min` / `range_max`: the calibrated arc in servo steps (0..4095). This is what the Station
  and `src/elrobot_hardware.py` use to clamp goals.
- `range_frozen`: the calibration was frozen in the Station viewer.
- `eeprom_*`: angle limits and position offset read from the servo registers (offset is the raw u16).
- `registers_hex`: the full register block at export time, for reference.

The Station keeps the live calibration in `station_data/`. These files are a snapshot; re-export
after recalibrating.
