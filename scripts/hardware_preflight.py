#!/usr/bin/env python3
"""Read-only check that the ElRobot is ready for motion. Never moves or enables torque.

Usage (with the NormaCore Station running, `./bin/station --web --tcp`):
    python3 scripts/hardware_preflight.py --server localhost --bus auto

Exit code 0 means every ElRobot motor (IDs 1-8) is visible, calibrated, and
reports no fault. Anything else prints the problem and exits 1.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from elrobot_hardware import ELROBOT_MOTOR_IDS, ElRobotHardware  # noqa: E402


def _print_table(readings) -> list:
    problems = []
    header = f"{'ID':>3} {'present':>8} {'range_min':>10} {'range_max':>10} {'torque':>7} {'status':>7} {'current':>8}  note"
    print(header)
    print("-" * len(header))
    for mid in ELROBOT_MOTOR_IDS:
        r = readings.get(mid)
        if r is None:
            print(f"{mid:>3} {'--':>8} {'--':>10} {'--':>10} {'--':>7} {'--':>7} {'--':>8}  MISSING")
            problems.append(f"motor {mid} not on the bus")
            continue
        notes = []
        if not r.calibrated:
            notes.append("UNCALIBRATED")
            problems.append(f"motor {mid} has no valid calibration ({r.range_min}..{r.range_max})")
        if r.faulted:
            notes.append(f"FAULT 0x{r.status:02x}")
            problems.append(f"motor {mid} reports fault status 0x{r.status:02x}")
        print(
            f"{r.motor_id:>3} {r.present:>8} {r.range_min:>10} {r.range_max:>10} "
            f"{'on' if r.torque_on else 'off':>7} {r.status:>#7x} {r.current:>8}  {' '.join(notes)}"
        )
    return problems


async def main_async(args) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    hw = ElRobotHardware(server=args.server, bus=args.bus, logger=logging.getLogger("preflight"))
    try:
        await hw.connect(timeout_s=args.timeout)
    except Exception as exc:  # noqa: BLE001 - report any connection problem plainly
        print(f"FAIL: could not reach the Station at {args.server}: {exc}")
        print("Check that the Station is running (`./bin/station --web --tcp`) and the USB cable is connected.")
        return 1
    try:
        print(f"Station {args.server}, bus {hw.bus_serial}")
        readings = await hw.read()
        problems = _print_table(readings)
    finally:
        await hw.close()

    if problems:
        print("\nNOT READY:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nREADY: all 8 motors visible, calibrated, and fault-free. No motion was commanded.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--server", default="localhost", help="Station host (default localhost)")
    parser.add_argument("--bus", default="auto", help="Bus serial, or 'auto' for a single-bus station")
    parser.add_argument("--timeout", type=float, default=10.0, help="Seconds to wait for the first frame")
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
