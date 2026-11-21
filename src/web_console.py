"""Web console for the ElRobot MCP: live table, gripper and face cameras next to a voice chat box.

    ./cli.sh console            then open http://localhost:8890

Left: the `table`, `gripper` and `face` cameras (names from config/elrobot.json -> cameras), read
from the Station exactly like the MCP `look` tool. Right: a chat box with a big microphone
button. Speech is transcribed locally with faster-whisper (offline, plan stage 3); if that is
not installed the page falls back to the browser's own speech recognition.

Chat messages go to Claude (src/console_agent.py), which answers and drives the arm through the
same `elrobot` MCP server as Claude Code (motion only if .mcp.json sets ELROBOT_ALLOW_MOTION=1).
"stop" in the chat, or the Stop button, holds the arm without going through Claude.
Needs the Station running (./cli.sh station) and ANTHROPIC_API_KEY for the chat.

Environment:
  WEB_CONSOLE_STT_MODEL   faster-whisper model (default large-v3-turbo on a GPU, small.en on CPU)
  WEB_CONSOLE_STT_PROMPT  words to expect, as a hint to Whisper (default: the demo foods and commands)
  WEB_CONSOLE_MODEL       Claude model for the chat (default claude-opus-5-5)
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
# Whisper is much better at short commands when told which words to expect.
DEFAULT_STT_PROMPT = ("Requests to a feeding robot: I want a grape. Some rice, please. Cheese. "
                      "Use the spoon. Another one. Stop. Wait. I'm done.")
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

    def __init__(self, model_name: Optional[str] = None, prompt: str = DEFAULT_STT_PROMPT):
        self.model_name = model_name or ""  # empty: chosen when loading, by GPU or CPU
        self.prompt = prompt
        self.device = ""
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
            import ctranslate2  # noqa: WPS433 - installed with faster-whisper
            gpu = ctranslate2.get_cuda_device_count() > 0
            self.device = "cuda" if gpu else "cpu"
            self.model_name = self.model_name or ("large-v3-turbo" if gpu else "small.en")
            self._model = WhisperModel(self.model_name, device=self.device,
                                       compute_type="float16" if gpu else "int8")
            self.state = "ready"
            log.info("speech-to-text ready (%s on %s)", self.model_name, self.device)
        except Exception as exc:  # noqa: BLE001 - reported to the page
            self.state = "unavailable"
            self.error = f"{type(exc).__name__}: {exc}"
            log.warning("speech-to-text unavailable: %s", self.error)

    def transcribe(self, audio: bytes) -> str:
        if self.state != "ready":
            raise RuntimeError(f"speech-to-text is {self.state}")
        with self._lock:  # one transcription at a time; the model is not shared across threads
            samples = decode_audio(audio)
            segments, _ = self._model.transcribe(
                samples, language="en", beam_size=5, initial_prompt=self.prompt or None,
                condition_on_previous_text=False,
                # Keep VAD (it stops Whisper inventing words in silence) but pad generously so
                # short commands and first/last syllables are not cut.
                vad_filter=True, vad_parameters={"speech_pad_ms": 500, "min_silence_duration_ms": 800},
            )
            text = " ".join(s.text.strip() for s in segments).strip()
            log.info("heard %.1f s of audio: %r", len(samples) / 16000, text)
            return text


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


def create_app(tools=None, stt: Optional[SpeechToText] = None, station_up=None,
               agent_factory=None) -> Starlette:
    """`tools` is a RobotTools (or a fake with .look/.call); `stt` a SpeechToText or None;
    `station_up` a callable returning whether the Station accepts connections;
    `agent_factory(post)` builds the chat agent (ConsoleAgent), or None for no agent."""
    if tools is None:
        tools = _default_tools()
        station_up = station_up or station_reachable
    station_up = station_up or (lambda: True)
    chat = ChatLog()
    agent_box: Dict[str, Any] = {"agent": None}

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
        return JSONResponse({"state": stt.state, "model": stt.model_name, "device": stt.device,
                             "error": stt.error})

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
            agent = agent_box["agent"]
            return JSONResponse({"messages": chat.after(after), "busy": bool(agent and agent.busy),
                                 "agent": agent.state if agent else "off",
                                 "agent_error": agent.error if agent else ""})
        body = await request.json()
        text = str(body.get("text", "")).strip()[:MAX_MESSAGE_CHARS]
        role = body.get("role", "user")
        if not text or role not in ("user", "robot"):
            return JSONResponse({"ok": False, "error": "need text and role user|robot"}, status_code=400)
        msg = chat.add(role, text)
        if role == "user" and agent_box["agent"] is not None:
            await agent_box["agent"].submit(text)
        return JSONResponse({"ok": True, "message": msg})

    async def stop(_: Request):
        agent = agent_box["agent"]
        chat.add("user", "Stop (button)")
        if agent is None:
            chat.add("error", "No agent running, nothing to stop here. Use the power plug if the arm moves.")
            return JSONResponse({"ok": False}, status_code=503)
        await agent.emergency_stop()
        return JSONResponse({"ok": True})

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        if stt is not None:
            stt.start_loading()
        if agent_factory is not None:
            agent_box["agent"] = agent_factory(chat.add)
            await agent_box["agent"].start()
        try:
            yield
        finally:
            if agent_box["agent"] is not None:
                await agent_box["agent"].close()

    return Starlette(routes=[
        Route("/", index),
        Route("/api/cameras", cameras),
        Route("/api/frame/{camera}", frame),
        Route("/api/stt", stt_status),
        Route("/api/transcribe", transcribe, methods=["POST"]),
        Route("/api/messages", messages, methods=["GET", "POST"]),
        Route("/api/stop", stop, methods=["POST"]),
    ], lifespan=lifespan)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1",
                        help="bind address (the microphone only works on localhost or https)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-stt", action="store_true", help="skip faster-whisper; use the browser's")
    parser.add_argument("--no-agent", action="store_true", help="chat only, no Claude")
    parser.add_argument("--mode", choices=("plans", "stepwise"), default=os.environ.get("WEB_CONSOLE_MODE", "plans"),
                        help="plans: recorded plans and waypoints (default); stepwise: Claude steers every "
                             "move with look + small nudges, no waypoints (env WEB_CONSOLE_MODE)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    for noisy in ("httpx", "httpx2", "huggingface_hub"):  # model download chatter
        logging.getLogger(noisy).setLevel(logging.WARNING)
    stt = None if args.no_stt else SpeechToText(os.environ.get("WEB_CONSOLE_STT_MODEL") or None,
                                                os.environ.get("WEB_CONSOLE_STT_PROMPT", DEFAULT_STT_PROMPT))

    import uvicorn  # noqa: WPS433
    print(f"ElRobot console: http://{'localhost' if args.host == '127.0.0.1' else args.host}:{args.port}",
          flush=True)
    agent_factory = None
    if not args.no_agent:
        from console_agent import ConsoleAgent  # noqa: WPS433
        mode = args.mode
        agent_factory = lambda post: ConsoleAgent(post, mode=mode)  # noqa: E731
        print(f"Agent mode: {mode}", flush=True)
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("Note: ANTHROPIC_API_KEY is not set; the chat cannot reach Claude.", flush=True)
    uvicorn.run(create_app(stt=stt, agent_factory=agent_factory), host=args.host, port=args.port,
                log_level="warning")


if __name__ == "__main__":
    main()
