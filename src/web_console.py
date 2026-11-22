"""Web console for the ElRobot MCP: live table and gripper cameras next to a voice chat box.

    ./cli.sh console            then open http://localhost:8890

Left: the `table` and `gripper` cameras (names from config/elrobot.json -> cameras), read
from the Station exactly like the MCP `look` tool. Right: a chat box with a big microphone
button. Speech is transcribed with OpenAI gpt-transcribe, the same call as src/speech.py
(languages de + en, a keyword list). Needs OPENAI_API_KEY (from .env); without it the page falls
back to the browser's own speech recognition. The audio is sent to OpenAI.

Chat messages go to Claude (src/console_agent.py), which answers and drives the arm through the
same `elrobot` MCP server as Claude Code (motion only if .mcp.json sets ELROBOT_ALLOW_MOTION=1).
"stop" in the chat, or the Stop button, holds the arm without going through Claude.
Needs the Station running (./cli.sh station) and ANTHROPIC_API_KEY for the chat.

Environment:
  OPENAI_API_KEY          OpenAI key for speech-to-text (./cli.sh console loads it from .env)
  WEB_CONSOLE_STT_MODEL   OpenAI transcription model (default gpt-transcribe)
  WEB_CONSOLE_STT_KEYWORDS  comma-separated words to expect; replaces the default list
                          (src/speech.py KEYWORDS plus the English demo foods and commands)
  WEB_CONSOLE_MODEL       Claude model for the chat (default claude-opus-5-5)
  ELROBOT_STATION / ELROBOT_BUS / ELROBOT_CAMERA_QUEUES   same as the MCP server
"""

from __future__ import annotations

import argparse
import contextlib
import io
import logging
import os
import re
import socket
import subprocess
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
import speech  # noqa: E402 - src/speech.py: the gpt-transcribe call and WAV writer

log = logging.getLogger("elrobot.console")

PAGE = Path(__file__).resolve().parent / "web" / "console.html"
DEFAULT_PORT = 8890
MAX_AUDIO_BYTES = 10 * 1024 * 1024
MAX_MESSAGE_CHARS = 2000
# Short commands transcribe better when the model is told which words to expect: the keywords
# from src/speech.py plus the English demo foods and commands the console used before.
DEMO_KEYWORDS = ["grape", "rice", "cheese", "spoon", "another one", "stop", "wait", "done"]
DEFAULT_STT_MODEL = speech.MODEL
DEFAULT_STT_KEYWORDS = list(dict.fromkeys(speech.KEYWORDS + DEMO_KEYWORDS))
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

_SECRET = re.compile(r"sk-[A-Za-z0-9_*.-]+")


def redact(text: str) -> str:
    """Remove anything that looks like an OpenAI key (error messages can echo part of it)."""
    return _SECRET.sub("sk-***", text)


class SpeechToText:
    """OpenAI gpt-transcribe, through the same call as src/speech.py.

    Nothing to load: the state is `ready` when OPENAI_API_KEY is set, otherwise `error`, and
    the page then falls back to the browser's speech recognition.
    """

    def __init__(self, model_name: Optional[str] = None, keywords: Optional[List[str]] = None):
        self.model_name = model_name or DEFAULT_STT_MODEL
        self.keywords = list(DEFAULT_STT_KEYWORDS if keywords is None else keywords)
        self.device = "openai"
        if os.environ.get("OPENAI_API_KEY"):
            self.state = "ready"  # ready | error
            self.error = ""
        else:
            self.state = "error"
            self.error = "OPENAI_API_KEY is not set (put it in .env)"

    def start_loading(self) -> None:
        """Kept for the app lifespan; there is no model to load."""
        if self.state == "ready":
            log.info("speech-to-text ready (%s via OpenAI)", self.model_name)
        else:
            log.warning("speech-to-text unavailable: %s", self.error)

    def transcribe(self, audio: bytes) -> str:
        if self.state != "ready":
            raise RuntimeError(f"speech-to-text is {self.state}")
        samples = decode_audio(audio)
        path = speech.write_wav(samples)  # 16 kHz mono 16-bit WAV, as speech.py sends it
        try:
            text = speech.transcribe(path, model=self.model_name, keywords=self.keywords)
        except Exception as exc:  # noqa: BLE001 - re-raised without the original, which may echo the key
            raise RuntimeError(f"{type(exc).__name__}: {redact(str(exc))}") from None
        finally:
            os.remove(path)
        log.info("heard %.1f s of audio: %r", len(samples) / speech.SAMPLE_RATE, text)
        return text


def decode_audio(audio: bytes, rate: int = speech.SAMPLE_RATE):
    """Browser recording (webm/ogg/wav) -> mono float32 samples at `rate` Hz."""
    import av  # noqa: WPS433 - PyAV, listed in requirements.txt
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

    def synthesize_speech(text: str) -> tuple[bytes, str]:
        """Synthesize spoken audio via OpenAI TTS (MP3) with offline espeak-ng (WAV) fallback."""
        clean = text.strip()[:600]
        if os.environ.get("OPENAI_API_KEY", "").strip():
            try:
                from openai import OpenAI

                client = OpenAI(timeout=15.0, max_retries=1)
                resp = client.audio.speech.create(model="tts-1", voice="nova", input=clean)
                return resp.content, "audio/mpeg"
            except Exception as exc:  # noqa: BLE001 - fall back to local espeak-ng
                log.warning("OpenAI TTS failed, falling back to espeak-ng: %s", exc)
        proc = subprocess.run(["espeak-ng", "--stdout", clean], capture_output=True, timeout=10)
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout, "audio/wav"
        raise RuntimeError("No TTS backend available (OpenAI TTS and espeak-ng both failed)")


    async def stop(_: Request):
        agent = agent_box["agent"]
        chat.add("user", "Stop (button)")
        if agent is None:
            chat.add("error", "No agent running, nothing to stop here. Use the power plug if the arm moves.")
            return JSONResponse({"ok": False}, status_code=503)
        await agent.emergency_stop()
        return JSONResponse({"ok": True})

    async def tts(request: Request):
        body = await request.json()
        text = str(body.get("text", "")).strip()
        if not text:
            return JSONResponse({"ok": False, "error": "no text"}, status_code=400)
        try:
            audio_bytes, media_type = await run_in_threadpool(synthesize_speech, text)
        except Exception as exc:  # noqa: BLE001 - reported to browser
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
        return Response(audio_bytes, media_type=media_type, headers={"Cache-Control": "no-store"})

    async def mouth_gate(request: Request):
        from elrobot_config import save_config
        cfg = load_config()
        fv = dict(cfg.get("feeding_vision") or {})
        if request.method == "GET":
            return JSONResponse({"enabled": bool(fv.get("mouth_gate_enabled", False))})
        body = await request.json()
        enabled = bool(body.get("enabled", False))
        fv["mouth_gate_enabled"] = enabled
        cfg["feeding_vision"] = fv
        save_config(cfg)
        return JSONResponse({"ok": True, "enabled": enabled})

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
        Route("/api/tts", tts, methods=["POST"]),
        Route("/api/mouth_gate", mouth_gate, methods=["GET", "POST"]),
        Route("/api/messages", messages, methods=["GET", "POST"]),
        Route("/api/stop", stop, methods=["POST"]),
    ], lifespan=lifespan)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1",
                        help="bind address (the microphone only works on localhost or https)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-stt", action="store_true", help="skip OpenAI speech-to-text; use the browser's")
    parser.add_argument("--no-agent", action="store_true", help="chat only, no Claude")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    for noisy in ("httpx", "httpx2", "openai"):  # per-request chatter
        logging.getLogger(noisy).setLevel(logging.WARNING)
    keywords_env = os.environ.get("WEB_CONSOLE_STT_KEYWORDS", "")
    keywords = [k.strip() for k in keywords_env.split(",") if k.strip()] or None
    stt = None if args.no_stt else SpeechToText(os.environ.get("WEB_CONSOLE_STT_MODEL") or None, keywords)
    if stt is not None and stt.state != "ready":
        print(f"Note: {stt.error}; the page uses the browser's speech recognition.", flush=True)

    import uvicorn  # noqa: WPS433
    print(f"ElRobot console: http://{'localhost' if args.host == '127.0.0.1' else args.host}:{args.port}",
          flush=True)
    agent_factory = None
    if not args.no_agent:
        from console_agent import ConsoleAgent  # noqa: WPS433
        agent_factory = ConsoleAgent
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("Note: ANTHROPIC_API_KEY is not set; the chat cannot reach Claude.", flush=True)
    uvicorn.run(create_app(stt=stt, agent_factory=agent_factory), host=args.host, port=args.port,
                log_level="warning")


if __name__ == "__main__":
    main()
