#!/usr/bin/env python3
"""
Sync / Teleoperation Bridge for Leader (Master) and Follower (Slave).
Automatically identifies the Leader and Follower arms on the NormaCore Station,
safely enables torque on the Follower, and mirrors every joint in real time.
"""

import argparse
import asyncio
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Any, Tuple, Optional, Dict

# NormaCore SDK path
SDK_ROOT = Path(__file__).resolve().parent.parent / "external" / "norma-core"
sys.path.insert(0, str(SDK_ROOT))
sys.path.insert(0, str(SDK_ROOT / "software" / "station" / "examples" / "st3215-remote-teleop-py"))

from software.station.shared.station_py import new_station_client
from target.gen_python.protobuf.drivers.st3215 import st3215

from config import MAX_DATA_AGE_NS, MotorConfig, TELEOP_REFRESH_INTERVAL_S
from commands import send_motor_commands, set_torque
from mirror import ProtectionTable, compute_motor_command
from state import parse_motor_state

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("teleop-sync")


class BusReader:
    def __init__(self, client, label: str):
        self.client = client
        self.label = label
        self.latest: st3215.InferenceStateReader | None = None
        self.latest_arrival_ns: int = 0
        self.queue: asyncio.Queue = asyncio.Queue()
        self.client.follow("st3215/inference", self.queue)

    async def run(self):
        while True:
            entry = await self.queue.get()
            if entry is None:
                logger.error("%s: st3215/inference closed", self.label)
                break
            self.latest = st3215.InferenceStateReader(entry.Data)
            self.latest_arrival_ns = time.monotonic_ns()


async def identify_arms(client: Any) -> tuple[str, str]:
    """Identify which serial is Leader and which is Follower."""
    q = asyncio.Queue()
    client.follow("st3215/inference", q)
    logger.info("Detecting arms on Station...")
    entry = await asyncio.wait_for(q.get(), timeout=5.0)
    inf = st3215.InferenceStateReader(entry.Data)
    buses = inf.get_buses() or []
    
    if len(buses) < 2:
        raise RuntimeError(f"Expected at least 2 buses for sync, found {len(buses)}")
    
    serials = [b.get_bus().get_serial_number() for b in buses if b.get_bus()]
    logger.info(f"Connected arm buses: {serials}")

    # Standard hackathon convention:
    # Confirmed on the arm 2026-11-21 (matches config/elrobot.json):
    # 5B61037051 is Leader (Master)
    # 5B61034962 is Follower (Slave)
    if "5B61037051" in serials and "5B61034962" in serials:
        return "5B61037051", "5B61034962"
    
    # Return first as leader, second as follower if unknown
    return serials[0], serials[1]


async def run_teleop_sync(leader_bus: str | None = None, follower_bus: str | None = None):
    client = await new_station_client("localhost", logger)
    
    if not leader_bus or not follower_bus:
        auto_leader, auto_follower = await identify_arms(client)
        leader_bus = leader_bus or auto_leader
        follower_bus = follower_bus or auto_follower

    print("\n" + "=" * 65)
    print(f"  ARM TELEOPERATION SYNC ACTIVE")
    print(f"  MASTER (Leader / Unpowered input):  Bus {leader_bus}")
    print(f"  SLAVE  (Follower / Powered robot):  Bus {follower_bus}")
    print("=" * 65)
    print("  Hold the Master arm gently. The Slave arm will mirror your motion.")
    print("  Press Ctrl+C to stop and release slave torque.\n")

    reader = BusReader(client, "station")
    reader_task = asyncio.create_task(reader.run())

    # Wait for first frame
    while reader.latest is None:
        await asyncio.sleep(0.05)

    motor_cfg = MotorConfig(
        deadband=15,
        safety_margin=15,
        min_speed=400,
        max_speed=2500,
        min_accel=10,
        max_accel=80,
        current_threshold=150,
    )
    protections = ProtectionTable()

    # Step 1: Read follower motor IDs and enable torque on Follower only
    # (Master remains limp so the human can move it)
    follower_b = next((b for b in (reader.latest.get_buses() or []) if b.get_bus() and b.get_bus().get_serial_number() == follower_bus), None)
    if not follower_b:
        raise RuntimeError(f"Follower bus {follower_bus} not found")
    
    f_motor_ids = [m.get_id() for m in (follower_b.get_motors() or [])]
    logger.info(f"Enabling holding torque on Follower ({follower_bus}) motors: {f_motor_ids}")
    await set_torque(client, follower_bus, f_motor_ids, enable=True)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    last_log_t = time.monotonic()
    tick_count = 0

    try:
        while not stop_event.is_set():
            t0 = asyncio.get_running_loop().time()
            inf = reader.latest
            if inf is not None:
                buses = {b.get_bus().get_serial_number(): b for b in (inf.get_buses() or []) if b.get_bus()}
                if leader_bus in buses and follower_bus in buses:
                    l_motors = {m.get_id(): parse_motor_state(m) for m in (buses[leader_bus].get_motors() or [])}
                    f_motors = {m.get_id(): parse_motor_state(m) for m in (buses[follower_bus].get_motors() or [])}
                    
                    commands = []
                    for mid, l_state in l_motors.items():
                        if mid in f_motors:
                            f_state = f_motors[mid]
                            prot = protections.get(mid)
                            cmd = compute_motor_command(mid, l_state, f_state, prot, motor_cfg)
                            if cmd:
                                commands.append(cmd)
                    
                    if commands:
                        await send_motor_commands(client, follower_bus, commands)
                    
                    tick_count += 1

            if time.monotonic() - last_log_t >= 2.0:
                print(f"[Sync Heartbeat] 50Hz Loop Running | Ticks: {tick_count} | Mirroring {leader_bus} -> {follower_bus}", end="\r")
                last_log_t = time.monotonic()

            elapsed = asyncio.get_running_loop().time() - t0
            await asyncio.sleep(max(0.001, TELEOP_REFRESH_INTERVAL_S - elapsed))

    except asyncio.CancelledError:
        pass
    finally:
        print("\n[+] Disabling follower torque (relaxing arm)...")
        await set_torque(client, follower_bus, f_motor_ids, enable=False)
        reader_task.cancel()
        client.close_connection()
        print("[+] Teleop sync stopped cleanly.")


def main():
    parser = argparse.ArgumentParser(description="Master/Slave Teleop Sync")
    parser.add_argument("--leader", default=None, help="Leader (Master) bus serial")
    parser.add_argument("--follower", default=None, help="Follower (Slave) bus serial")
    parser.add_argument("--swap", action="store_true", help="Swap Master and Slave roles")
    args = parser.parse_args()

    leader = args.leader
    follower = args.follower
    if args.swap:
        leader = "5B61034962"
        follower = "5B61037051"

    try:
        asyncio.run(run_teleop_sync(leader, follower))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
