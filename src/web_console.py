"""Web console for the ElRobot MCP: live table and gripper cameras next to a voice chat box.

    ./cli.sh console            then open http://localhost:8890

Left: the `table` and `gripper` cameras (names from config/elrobot.json -> cameras), read
from the Station exactly like the MCP `look` tool. Right: a chat box with a big microphone
button. Speech is transcribed locally with faster-whisper (offline, plan stage 3); if that is
not installed the page falls back to the browser's own speech recognition.

Chat messages are kept in memory and served at /api/messages, so an MCP `listen`/`say` tool
(plan 3.2 / 3.4) can read what was said and post replies later.

Read-only: nothing here moves the arm. Needs the Station running (./cli.sh station).

Environment:
  WEB_CONSOLE_STT_MODEL   faster-whisper model (default small.en; base.en is faster)
  ELROBOT_STATION / ELROBOT_BUS / ELROBOT_CAMERA_QUEUES   same as the MCP server
"""

from __future__ import annotations

import argparse
import contextlib
import io
import logging
import os
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from starlette.applications import Starlette  # noqa: E402
from starlette.concurrency import run_in_threadpool  # noqa: E402
from starlette.requests import Request  # noqa: E402
from starlette.responses import FileResponse, JSONResponse, Response  # noqa: E402
from starlette.routing import Route  # noqa: E402

from elrobot_config import load_config  # noqa: E402

log = logging.getLogger("elrobot.console")

PAGE = Path(__file__).resolve().parent / "web" / "console.html"
DEFAULT_PORT = 8890
MAX_AUDIO_BYTES = 10 * 1024 * 1024
MAX_MESSAGE_CHARS = 2000
STATION_PORT = 8888  # the Station's TCP port (the SDK default)


def station_reachable() -> bool:
    """Fast TCP check, so a stopped Station fails in milliseconds instead of a 10 s connect."""
    server = os.environ.get("ELROBOT_STATION", load_config()["station"]["server"])
    host, _, port = server.partition(":")
    try:
        with socket.create_connection((host or "localhost", int(port or STATION_PORT)), timeout=0.5):
            return True
    except OSError:
        return False


# -- speech to text -----------------------------------------------------------

class SpeechToText:
    """faster-whisper, loaded once in the background so the first click is not slow."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.state = "idle"  # idle | loading | ready | unavailable
        self.error = ""
        self._model = None
        self._lock = threading.Lock()

    def start_loading(self) -> None:
        if self.state != "idle":
            return
        self.state = "loading"
        threading.Thread(target=self._load, name="stt-load", daemon=True).start()

    def _load(self) -> None:
        try:
            from faster_whisper import WhisperModel  # noqa: WPS433 - optional dependency
            self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
            self.state = "ready"
            log.info("speech-to-text ready (%s)", self.model_name)
        except Exception as exc:  # noqa: BLE001 - reported to the page
            self.state = "unavailable"
            self.error = f"{type(exc).__name__}: {exc}"
            log.warning("speech-to-text unavailable: %s", self.error)

    def transcribe(self, audio: bytes) -> str:
        if self.state != "ready":
            raise RuntimeError(f"speech-to-text is {self.state}")
        with self._lock:  # one transcription at a time; the model is not shared across threads
            segments, _ = self._model.transcribe(decode_audio(audio), language="en", vad_filter=True)
            return " ".join(s.text.strip() for s in segments).strip()


def decode_audio(audio: bytes, rate: int = 16000):
    """Browser recording (webm/ogg/wav) -> mono float32 samples at `rate` Hz, as Whisper wants.

    Done here with PyAV instead of faster-whisper's decode_audio, which breaks on newer PyAV.
    """
    import av  # noqa: WPS433 - installed with faster-whisper
    import numpy as np  # noqa: WPS433

    resampler = av.AudioResampler(format="s16", layout="mono", rate=rate)
    parts = []
    with av.open(io.BytesIO(audio)) as container:
        for frame in container.decode(audio=0):
            parts.extend(r.to_ndarray().reshape(-1) for r in resampler.resample(frame))
    parts.extend(r.to_ndarray().reshape(-1) for r in resampler.resample(None))
    if not parts:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(parts).astype(np.float32) / 32768.0


# -- chat log -------------------------------------------------------------------

class ChatLog:
    def __init__(self):
        self._messages: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def add(self, role: str, text: str) -> Dict[str, Any]:
        with self._lock:
            msg = {"id": len(self._messages) + 1, "role": role, "text": text, "time": time.time()}
            self._messages.append(msg)
            return msg

    def after(self, after_id: int) -> List[Dict[str, Any]]:
        with self._lock:
            return [m for m in self._messages if m["id"] > after_id]


# -- app ------------------------------------------------------------------------

def _default_tools():
    # The MCP server module only builds objects at import; it connects on first use.
    from robot_mcp_server import tools  # noqa: WPS433
    return tools


def create_app(tools=None, stt: Optional[SpeechToText] = None, station_up=None) -> Starlette:
    """`tools` is a RobotTools (or a fake with .look/.call); `stt` a SpeechToText or None;
    `station_up` a callable returning whether the Station accepts connections."""
    if tools is None:
        tools = _default_tools()
        station_up = station_up or station_reachable
    station_up = station_up or (lambda: True)
    chat = ChatLog()

    async def index(_: Request):
        return FileResponse(PAGE, headers={"Cache-Control": "no-store"})

    async def cameras(_: Request):
        return JSONResponse({"cameras": list(load_config().get("cameras", {}))})

    async def frame(request: Request):
        name = request.path_params["camera"]
        if not await run_in_threadpool(station_up):
            return JSONResponse({"ok": False, "error": "the Station is not running (./cli.sh station)"},
                                status_code=503)
        result = await run_in_threadpool(tools.call, lambda: tools.look(name))
        if isinstance(result, dict):  # tools.call turned an exception into {"ok": False, ...}
            return JSONResponse(result, status_code=503)
        meta, jpeg = result
        if jpeg is None:
            return JSONResponse(meta, status_code=503)
        age = meta.get("age_seconds")
        return Response(jpeg, media_type="image/jpeg", headers={
            "Cache-Control": "no-store",
            "X-Frame-Age": "" if age is None else str(age),
            "X-Frame-Size": f"{meta.get('width')}x{meta.get('height')}",
        })

    async def stt_status(_: Request):
        if stt is None:
            return JSONResponse({"state": "unavailable", "error": "disabled"})
        return JSONResponse({"state": stt.state, "model": stt.model_name, "error": stt.error})

    async def transcribe(request: Request):
        if stt is None or stt.state != "ready":
            return JSONResponse({"ok": False, "error": f"speech-to-text is {stt.state if stt else 'disabled'}"},
                                status_code=503)
        audio = await request.body()
        if not audio:
            return JSONResponse({"ok": False, "error": "no audio"}, status_code=400)
        if len(audio) > MAX_AUDIO_BYTES:
            return JSONResponse({"ok": False, "error": "recording too long"}, status_code=413)
        started = time.monotonic()
        try:
            text = await run_in_threadpool(stt.transcribe, audio)
        except Exception as exc:  # noqa: BLE001 - shown in the page
            log.exception("transcription failed")
            return JSONResponse({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, status_code=500)
        return JSONResponse({"ok": True, "text": text, "seconds": round(time.monotonic() - started, 2)})

    async def messages(request: Request):
        if request.method == "GET":
            try:
                after = int(request.query_params.get("after", "0"))
            except ValueError:
                after = 0
            return JSONResponse({"messages": chat.after(after)})
        body = await request.json()
        text = str(body.get("text", "")).strip()[:MAX_MESSAGE_CHARS]
        role = body.get("role", "user")
        if not text or role not in ("user", "robot"):
            return JSONResponse({"ok": False, "error": "need text and role user|robot"}, status_code=400)
        return JSONResponse({"ok": True, "message": chat.add(role, text)})

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        if stt is not None:
            stt.start_loading()
        yield

    return Starlette(routes=[
        Route("/", index),
        Route("/api/cameras", cameras),
        Route("/api/frame/{camera}", frame),
        Route("/api/stt", stt_status),
        Route("/api/transcribe", transcribe, methods=["POST"]),
        Route("/api/messages", messages, methods=["GET", "POST"]),
    ], lifespan=lifespan)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1",
                        help="bind address (the microphone only works on localhost or https)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-stt", action="store_true", help="skip faster-whisper; use the browser's")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    for noisy in ("httpx", "httpx2", "huggingface_hub"):  # model download chatter
        logging.getLogger(noisy).setLevel(logging.WARNING)
    stt = None if args.no_stt else SpeechToText(os.environ.get("WEB_CONSOLE_STT_MODEL", "small.en"))

    import uvicorn  # noqa: WPS433
    print(f"ElRobot console: http://{'localhost' if args.host == '127.0.0.1' else args.host}:{args.port}",
          flush=True)
    uvicorn.run(create_app(stt=stt), host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
