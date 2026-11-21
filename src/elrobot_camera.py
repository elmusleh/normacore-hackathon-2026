"""Camera frames from the NormaCore Station, for the MCP server.

The Station's usbvideo driver writes one queue per camera, named
`usbvideo/<md5 of the camera's unique id>`. Each frame entry is a
`usbvideo.RxEnvelope` of type ET_FRAMES holding one JPEG, already resized so its
shortest side is `resize_target` pixels (station.yaml, default 224).

The Station has no "list queues" call, so cameras are found by listing
`<station data folder>/usbvideo/*/wal`, which works when the Station runs on this
machine (./cli.sh station runs it from the repo root, data in ./station_data).
Set ELROBOT_CAMERA_QUEUES=usbvideo/<hash>,... to skip discovery.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATION_DATA = ROOT / "station_data"

# How far back from the newest entry to look for a frame. Non-frame entries
# (connect/disconnect events) are rare, so a few is plenty.
MAX_LOOKBACK = 5


@dataclass
class CameraFrame:
    jpeg: bytes
    width: int
    height: int
    local_stamp_ns: int

    @property
    def age_s(self) -> Optional[float]:
        """Seconds since capture, by wall clock. None if the frame has no stamp."""
        if not self.local_stamp_ns:
            return None
        return max(0.0, (time.time_ns() - self.local_stamp_ns) / 1e9)


def discover_camera_queues(station_data: Optional[Path] = None) -> List[str]:
    """Camera queue ids, from ELROBOT_CAMERA_QUEUES or the Station's data folder."""
    env = os.environ.get("ELROBOT_CAMERA_QUEUES", "").strip()
    if env:
        return [q.strip() for q in env.split(",") if q.strip()]
    base = Path(os.environ.get("ELROBOT_STATION_DATA", station_data or DEFAULT_STATION_DATA))
    # Queues live in <base>/<station id>/usbvideo/<hash>/wal (older layouts: <base>/usbvideo/...).
    found = {f"usbvideo/{wal.parent.name}"
             for pattern in ("usbvideo/*/wal", "*/usbvideo/*/wal") for wal in base.glob(pattern)}
    return sorted(found)


SYS_USB = Path("/sys/bus/usb/devices")


def usb_ports(sys_usb: Path = SYS_USB) -> dict:
    """Map (bus, device number) -> USB port path like '3-2.4' for devices plugged in now.

    The Station's camera unique_id is 'vendor:product:bus:device'. The device number
    changes on every replug, so each replug makes a new queue. The port path does not
    change while the cable stays in the same socket, so cameras are named by port.
    """
    ports = {}
    if not sys_usb.is_dir():
        return ports
    for dev in sys_usb.iterdir():
        try:
            bus = int((dev / "busnum").read_text())
            num = int((dev / "devnum").read_text())
        except (OSError, ValueError):
            continue
        ports[(bus, num)] = dev.name
    return ports


def mac_port(unique_id: str) -> Optional[str]:
    """USB port path like '2-1.2.4' from a macOS camera unique id, or None.

    On macOS the Station reports AVFoundation's id: '0x' + USB locationID + vendor (4 hex)
    + product (4 hex), e.g. '0x21240002c7f4a60'. The locationID is the bus in the top byte,
    then one hub port per nibble until the first 0 (0x02124000 -> bus 2, ports 1.2.4).
    It depends on the socket, not on replugging, like the Linux port path.
    """
    if not unique_id.startswith("0x") or len(unique_id) <= 10:
        return None
    try:
        location = int(unique_id[2:-8], 16)
    except ValueError:
        return None
    bus = location >> 24
    hops = []
    for shift in range(20, -1, -4):
        nibble = (location >> shift) & 0xF
        if nibble == 0:
            break
        hops.append(str(nibble))
    if not bus or not hops:
        return None
    return f"{bus}-{'.'.join(hops)}"


_mac_cache: dict = {"at": 0.0, "ports": {}}
MAC_CACHE_S = 2.0  # system_profiler takes ~0.3 s; the console asks several times a second


def mac_usb_ports(now: Optional[float] = None, run=None) -> dict:
    """macOS: map camera unique id -> USB port path for cameras plugged in now.

    Reads `system_profiler SPCameraDataType -json`, cached for MAC_CACHE_S seconds.
    `run` replaces subprocess.run in tests.
    """
    import json  # noqa: WPS433
    import subprocess  # noqa: WPS433

    now = time.monotonic() if now is None else now
    if now - _mac_cache["at"] < MAC_CACHE_S:
        return _mac_cache["ports"]
    ports = {}
    try:
        out = (run or subprocess.run)(["system_profiler", "SPCameraDataType", "-json"],
                                      capture_output=True, text=True, timeout=5).stdout
        for cam in json.loads(out).get("SPCameraDataType", []):
            uid = cam.get("spcamera_unique-id", "")
            port = mac_port(uid)
            if port:
                ports[uid] = port
    except (OSError, ValueError, subprocess.SubprocessError):
        ports = {}
    _mac_cache.update(at=now, ports=ports)
    return ports


def camera_ports() -> dict:
    """Plugged-in cameras for port_of: Linux sysfs, or the macOS camera list."""
    if sys.platform == "darwin":
        return mac_usb_ports()
    return usb_ports()


def port_of(unique_id: str, ports: dict) -> Optional[str]:
    """USB port of a camera from its Station unique_id, or None if it is not plugged in now.

    Linux ids are 'vendor:product:bus:device' (ports keyed by (bus, device)); macOS ids are
    '0x<locationID><vendor><product>' (ports keyed by the id itself, see mac_usb_ports).
    """
    if unique_id in ports:
        return ports[unique_id]
    parts = unique_id.split(":")
    if len(parts) != 4:
        return None
    try:
        return ports.get((int(parts[2]), int(parts[3])))
    except ValueError:
        return None


def decode_frame(data: bytes) -> Optional[CameraFrame]:
    """Return the JPEG frame in one usbvideo entry, or None for non-frame entries."""
    from target.gen_python.protobuf.drivers.usbvideo import usbvideo  # noqa: WPS433
    from target.gen_python.protobuf.drivers.usbvideo import frame as frame_pb  # noqa: WPS433

    env = usbvideo.RxEnvelopeReader(memoryview(data))
    if env.get_type() != usbvideo.RxEnvelopeType.ET_FRAMES:
        return None
    pack = env.get_frames()
    if pack is None:
        return None
    fmt = pack.get_format()
    if fmt is None or fmt.get_kind() != frame_pb.FrameFormatKind.FF_JPEG:
        # Raw NCHW frames are possible in the protocol but the Station stores JPEG.
        return None
    frames = pack.get_frames_data() or []
    if not frames:
        return None
    stamps = pack.get_stamps() or []
    stamp = stamps[-1].get_local_stamp_ns() if stamps else 0
    return CameraFrame(jpeg=bytes(frames[-1]), width=fmt.get_width(), height=fmt.get_height(),
                       local_stamp_ns=stamp)


def describe_camera(data: Optional[bytes]) -> dict:
    """Product name and ids from a camera's first queue entry (the connect event), if present."""
    if not data:
        return {}
    from target.gen_python.protobuf.drivers.usbvideo import usbvideo  # noqa: WPS433

    cam = usbvideo.RxEnvelopeReader(memoryview(data)).get_camera()
    if cam is None:
        return {}
    return {
        "product": cam.get_product(),
        "manufacturer": cam.get_manufacturer(),
        "unique_id": cam.get_unique_id(),
    }
