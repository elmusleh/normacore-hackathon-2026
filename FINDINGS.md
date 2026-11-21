# Findings

Verified observations about the hardware, the SDK and the setup, each with its evidence. Owner: whoever observed it. Add new findings at the top. Never delete a finding. Mark it resolved and say how.

- **Rules** (how to act) live in `GUIDELINES.md` and `docs/bench_safety.md`.
- **Current state** (what is happening now) lives in `.ai-sync/HANDOFF.md`.
- **Ideas and next steps** live in `SUGGESTIONS.md`.

This file holds facts that stay true, with the evidence behind them.

| Date | Finding | Evidence | Status |
|---|---|---|---|
| 2026-11-21 | The NormaCore SDK is now the submodule at `5f4f805`. It contains `target/gen_python` and the Station client, and both imports work. | `git submodule status`; `./cli.sh sdk-check` passes | Resolved. Setup uses the submodule only. |
| 2026-11-21 | The old unpacked SDK copy is not the same code as `5f4f805`. About 50 files differ, including Station Rust source and the Station client. The version string matches in both, so the version check cannot tell them apart. | `diff -rq` between `external/norma-core-snapshot` and the submodule | Open. The old copy is not supported. Suggestion 26 removes it. |
| 2026-11-21 | A USB hub on bus 3, port 4, dropped both serial adapters and two cameras at once. | dmesg: `clear tt 1 (90d2) error -71`, then disconnects of ports 3-4.1 to 3-4.4 | Open. Cause unknown. Reseating the cable brought the devices back. Check the cable and hub power before each bench session. |
| 2026-11-21 | The Station does not recover on its own after a USB drop. It exited and had to be restarted. | Process list before and after the drop; `logs/station/` | Open. Restart the Station after any USB drop. |
| 2026-11-21 | After a replug, the serial ports were `root:dialout`, mode 660. The user was not in `dialout`, so the Station got `Permission denied` on both ports. | `ls -l /dev/ttyACM*`; Station log `st3215::port ... Permission denied` | Open until `./cli.sh setup-serial` has been run and the cables replugged on each machine. |
| 2026-11-21 | With two serial adapters plugged in, `--bus auto` refuses to run. | `preflight` output: `--bus auto needs exactly one bus` | Resolved by design. Always pass `--bus <serial>`. |
| 2026-11-21 | Two identical KD-USB cameras share a USB name. Camera numbers changed after the replug. Overhead is `/dev/video4` (both arms on the table). Wrist is `/dev/video2` (gripper fingers and floor). | Test frames from each node, viewed directly | Partly resolved. The assignment held for this replug only. Record stable port paths (suggestion 16). |
| 2026-11-21 | The USB2.0 FHD webcam (`/dev/video0`) returned `No such device` after the replug. | `cv2` capture attempt | Open. Not needed for the arm checks. |
| 2026-11-21 | The Station's serial-bus serial numbers are `5B61034962` (`ttyACM0`) and `5B61037051` (`ttyACM1`). Which one is the leader is not confirmed by any measurement. | `udevadm` and dmesg serial strings. The teleop CHANGELOG entry names the leader; `docs/team_setup.md` says it is unconfirmed. | Open. Confirm on the bench before anything else uses the labels. |
| 2026-11-21 | `GUIDELINES.md` §2 says agents must never command raw joint angles. The hardware bridge is joint-level by design. | Compare `GUIDELINES.md` §2 with `.ai-sync/HANDOFF.md` "Key Decisions" | Open decision. The rule and the design cannot both stand. The owner must choose one. |
| 2026-11-21 | Offline suite: 44 tests pass. | `python3 -m pytest tests/ -q` | Resolved. |
