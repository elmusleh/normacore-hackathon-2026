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
    video_dir = base / "usbvideo"
    if not video_dir.is_dir():
        return []
    return sorted(f"usbvideo/{p.name}" for p in video_dir.iterdir() if (p / "wal").exists())


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
