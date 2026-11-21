# Prompt: export the Station calibration so a teammate can import it

Paste everything below the line into Claude Code, opened in the `normacore-hackathon-2026` repo on the laptop where the ElRobot was calibrated.

---

I calibrated the ElRobot arms in my NormaCore Station and froze the calibration. My teammate Jan needs the same calibration in the Station on his Mac. Please package it so his Station can restore it.

## Background (already checked, no need to re-check)

- `calibration/elrobot_*.json` (my earlier export) is a record only. It can't be imported. The only Station command that loads ranges is `FreezeCalibrationCommand`, and that command also writes new position offsets into the motor EEPROM (`software/drivers/st3215/src/port.rs`, `freeze_calibration`). Re-sending the exported ranges would shift the calibration.
- On startup the Station restores frozen calibration from its own storage, without writing to the motors. `software/drivers/st3215/src/port_meta.rs` reads the newest entry of the bus's meta queue (`st3215/meta`) and, if it is a `MET_FREEZE_CALIBRATION` envelope, applies its arcs with `update_bounds`.
- That queue lives in `station_data/` (normfs), under a generated ID folder like `station_data/<64-hex-id>/.../st3215/meta`. Jan's Station uses a different ID folder.
- Buses: follower `5B61034962`, leader `5B61037051`.

## Rules

- Do not move the arm, change torque, or send any command to the Station. No freeze, no reset calibration, no auto-calibrate.
- Do not recalibrate. The motors' EEPROM offsets must match what we export.
- Do not commit `station_data/` to git (it's gitignored and may be large).

## Steps

1. **Find out where the ID folder name comes from.** Look in the NormaCore source (in `external/norma-core`) for how the `station_data/<id>` folder name is derived: random per install, from the machine, from `station.yaml`, or from something else. Tell me whether a Station on another machine will read a copied `station_data/` folder as-is, or whether the ID needs to match (for example, by setting it in config or renaming the folder). Quote the code you base this on.
2. **Check that the calibration is in the meta queue.** While the Station is running, read the newest entry of the `st3215/meta` queue for each bus. Use the Python SDK the same way `src/elrobot_hardware.py` does (`read_from_tail`). Decode it and show, per bus, the envelope type and the arcs (motor_id, min_angle, max_angle). Confirm it is `MET_FREEZE_CALIBRATION` and that the follower arcs match `calibration/elrobot_follower_5B61034962.json`.
3. **Stop the Station** (ask me to press Ctrl-C if it's running in my terminal), so the files on disk are complete.
4. **Package it.** Report `du -sh station_data` and the size of each subfolder. If camera (`usbvideo`) queues make it large, leave them out and keep only what the st3215 calibration needs. Then create `station_calibration_export.zip` in the repo root containing:
   - the needed parts of `station_data/`
   - `station.yaml`
   - a `README.txt` with the Station version (`bin/station --version`, or the release name), the OS, the export time, the bus serials, and exact import steps for Jan's Mac (macOS, Station `v0.1.0-beta.10`, his own `station_data/<different id>/` already exists).
5. **Report back.** List the zip contents and size, the answer from step 1, the arcs from step 2, and the import steps. Don't send the zip anywhere. I'll share it myself.
