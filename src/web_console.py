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

    v4l2_lock = threading.Lock()
    v4l2_state: Dict[str, Any] = {"caps": {}, "last_frame": {}, "last_jpeg": {}}
    vision_lock = threading.Lock()
    vision_box: Dict[str, Any] = {"detector": None}

    def _get_vision_detector():
        det = vision_box["detector"]
        if det is None:
            from feeding_vision import FeedingVisionDetector
            det = FeedingVisionDetector()
            vision_box["detector"] = det
        return det

    def _annotate_bgr(bgr, role: str):
        """Draw the same MediaPipe person/table overlays as Mission Control plus Stage 0 gripper crosshair."""
        if role not in ("person", "table", "gripper") or bgr is None:
            return bgr
        import cv2
        with vision_lock:
            det = _get_vision_detector()
            out = bgr.copy()
            if role == "gripper":
                h, w = out.shape[:2]
                info = det.analyze_gripper_roi(bgr)
                x1, y1, x2, y2 = info["roi_px"]
                cx = w // 2
                # Vertical center alignment guide
                cv2.line(out, (cx, 0), (cx, h), (90, 170, 255), 1, cv2.LINE_AA)
                box_color = (60, 220, 120) if info["in_jaws"] else (140, 155, 175)
                cv2.rectangle(out, (x1, y1), (x2, y2), box_color, 2)
                if info["centroid_px"] is not None:
                    px, py = info["centroid_px"]
                    cv2.circle(out, (px, py), 6, (0, 255, 255), -1)
                    tag = f"IN JAWS (dx={info['offset_x_pct']:+.2f})"
                else:
                    tag = "JAW ZONE (empty)"
                cv2.putText(out, tag, (max(8, x1), max(22, y1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)
                return out
            if role == "person":
                mouth = det.detect_mouth(bgr)
                if mouth and not (mouth.extra or {}).get("fallback", False):
                    extra = dict(mouth.extra or {})
                    u, v, w, h = mouth.u_px, mouth.v_px, mouth.width_px, mouth.height_px
                    at_standoff = bool(extra.get("at_standoff", False))
                    mouth_open = bool(extra.get("mouth_open", False))
                    confirmed = bool(extra.get("mouth_open_confirmed", False))
                    mar = extra.get("mar")
                    color = (0, 220, 120) if not at_standoff else (0, 165, 255)
                    cv2.rectangle(out, (u - w // 2, v - h // 2), (u + w // 2, v + h // 2), color, 2)
                    for pt in extra.get("lip_points") or []:
                        cv2.circle(out, (int(pt[0]), int(pt[1])), 3, (0, 255, 255), -1)
                    mouth_tag = "OPEN!" if confirmed else ("opening" if mouth_open else "closed")
                    mar_tag = f" MAR={mar:.2f}" if mar is not None else ""
                    cv2.putText(
                        out,
                        f"MOUTH {mouth_tag}{mar_tag} ({extra.get('standoff_cm', '?')}cm)",
                        (max(8, u - 75), max(22, v - h // 2 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2,
                    )
            elif role == "table":
                if det._object_detector is not None:
                    for t in det.detect_table_objects(bgr):
                        u, v, w, h = t.u_px, t.v_px, t.width_px, t.height_px
                        extra = dict(t.extra or {})
                        color = (180, 60, 240) if t.label == "bowl" else (50, 210, 100)
                        cv2.rectangle(out, (u - w // 2, v - h // 2), (u + w // 2, v + h // 2), color, 2)
                        tag = f"{t.label.upper()} ({int(t.confidence * 100)}%)"
                        if extra.get("food_piece_count"):
                            tag += f" [{extra['food_piece_count']} pcs]"
                        cv2.putText(
                            out, tag,
                            (max(8, u - w // 2), max(22, v - h // 2 - 6)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2,
                        )
                        for fp in extra.get("food_pieces_px") or []:
                            fu, fv, fw, fh = fp
                            cv2.circle(out, (int(fu), int(fv)), max(4, int(max(fw, fh) // 2)), (80, 255, 160), 2)
            return out

    def _annotate_jpeg(jpeg: bytes, role: str) -> bytes:
        """Decode JPEG, apply role overlay, re-encode; returns original bytes on any decode error."""
        if role not in ("person", "table", "gripper"):
            return jpeg
        try:
            import cv2
            import numpy as np
            arr = np.frombuffer(jpeg, dtype=np.uint8)
            bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if bgr is None:
                return jpeg
            annotated = _annotate_bgr(bgr, role)
            ok, buf = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            return buf.tobytes() if ok else jpeg
        except Exception:  # noqa: BLE001 - fall back to raw frame cleanly
            return jpeg

    def _v4l2_device_for(cam_name: str) -> Optional[str]:
        target = load_config().get("cameras", {}).get(cam_name)
        if isinstance(target, list):
            target = next((t for t in target if str(t).startswith("v4l2:")), None)
        if isinstance(target, str) and target.startswith("v4l2:"):
            return f"/dev/video{target[5:]}"
        return None

    def _release_v4l2(dev_path: Optional[str] = None) -> None:
        with v4l2_lock:
            keys = [dev_path] if dev_path else list(v4l2_state["caps"])
            for k in keys:
                cap = v4l2_state["caps"].pop(k, None)
                if cap is not None:
                    try:
                        cap.release()
                    except Exception:  # noqa: BLE001
                        pass

    def _grab_v4l2_frame(dev_path: str):
        """Capture a BGR frame + JPEG bytes from a local V4L2 camera, yielding cleanly while agent is busy."""
        import cv2
        from robot_tools import read_mouth_gate_state

        agent = agent_box["agent"]
        live_gate = read_mouth_gate_state(max_age_s=2.0)
        if (agent and agent.busy) or (live_gate and live_gate.get("waiting")):
            _release_v4l2(dev_path)
            return v4l2_state["last_frame"].get(dev_path), v4l2_state["last_jpeg"].get(dev_path), ""

        with v4l2_lock:
            cap = v4l2_state["caps"].get(dev_path)
            if cap is None or not cap.isOpened():
                cap = cv2.VideoCapture(dev_path, cv2.CAP_V4L2)
                if not cap.isOpened():
                    return None, None, f"cannot open local camera {dev_path}"
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                v4l2_state["caps"][dev_path] = cap
            ok, bgr = cap.read()
            if not ok or bgr is None:
                try:
                    cap.release()
                except Exception:  # noqa: BLE001
                    pass
                v4l2_state["caps"].pop(dev_path, None)
                return None, None, f"empty frame from local camera {dev_path}"
            enc_ok, buf = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            jpeg = buf.tobytes() if enc_ok else None
            v4l2_state["last_frame"][dev_path] = bgr
            if jpeg is not None:
                v4l2_state["last_jpeg"][dev_path] = jpeg
            return bgr, jpeg, ""

    async def frame(request: Request):
        name = request.path_params["camera"]
        dev_path = _v4l2_device_for(name)
        if dev_path is not None:
            bgr, jpeg, err = await run_in_threadpool(_grab_v4l2_frame, dev_path)
            if jpeg is None:
                return JSONResponse({"ok": False, "error": err or f"camera {name!r} unavailable"}, status_code=503)
            if bgr is not None and name in ("person", "table"):
                jpeg = await run_in_threadpool(_annotate_jpeg, jpeg, name)
            h, w = bgr.shape[:2] if bgr is not None else (0, 0)
            return Response(jpeg, media_type="image/jpeg", headers={
                "Cache-Control": "no-store",
                "X-Frame-Age": "0.0",
                "X-Frame-Size": f"{w}x{h}",
            })
        if not await run_in_threadpool(station_up):
            return JSONResponse({"ok": False, "error": "the Station is not running (./cli.sh station)"},
                                status_code=503)
        result = await run_in_threadpool(tools.call, lambda: tools.look(name))
        if isinstance(result, dict):  # tools.call turned an exception into {"ok": False, ...}
            return JSONResponse(result, status_code=503)
        meta, jpeg = result
        if jpeg is None:
            return JSONResponse(meta, status_code=503)
        if name in ("person", "table", "gripper"):
            jpeg = await run_in_threadpool(_annotate_jpeg, jpeg, name)
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


    async def stop(request: Request):
        agent = agent_box["agent"]
        label = "Stop (button)"
        try:
            body = await request.json()
            if isinstance(body, dict) and body.get("source") == "voice":
                heard = str(body.get("text", "")).strip()
                label = f'Stop (voice: "{heard}")' if heard else "Stop (voice)"
        except Exception:  # noqa: BLE001 - empty POST body from STOP button is normal
            pass
        chat.add("user", label)
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
        from robot_tools import mouth_gate_timeout_s
        cfg = load_config()
        fv = dict(cfg.get("feeding_vision") or {})
        if request.method == "GET":
            return JSONResponse({
                "enabled": bool(fv.get("mouth_gate_enabled", False)),
                "timeout_s": mouth_gate_timeout_s(cfg),
            })
        body = await request.json()
        enabled = bool(body.get("enabled", False))
        fv["mouth_gate_enabled"] = enabled
        cfg["feeding_vision"] = fv
        save_config(cfg)
        return JSONResponse({"ok": True, "enabled": enabled, "timeout_s": mouth_gate_timeout_s(cfg)})

    mouth_probe_lock = threading.Lock()
    mouth_probe_state: Dict[str, Any] = {"ts": 0.0, "data": None, "tools": None}

    def _poll_mouth_status() -> Dict[str, Any]:
        from robot_tools import RobotTools, mouth_gate_timeout_s, read_mouth_gate_state
        cfg = load_config()
        fv = cfg.get("feeding_vision") or {}
        enabled = bool(fv.get("mouth_gate_enabled", False))
        timeout_s = mouth_gate_timeout_s(cfg)

        # If play_sequence is actively polling OBSBOT in the MCP subprocess, reuse its fresh state
        # so we never contend on V4L2 /dev/video*!
        live = read_mouth_gate_state(max_age_s=2.0)
        if live and live.get("waiting"):
            return {
                "ok": bool(live.get("ok", True)),
                "enabled": enabled,
                "timeout_s": timeout_s,
                "waiting_for_mouth": True,
                "waiting_waypoint": str(live.get("waypoint", "")),
                "face_detected": bool(live.get("face_detected", False)),
                "mouth_open": bool(live.get("mouth_open", False)),
                "mouth_open_confirmed": bool(live.get("mouth_open_confirmed", False)),
                "mar": live.get("mar"),
                "error": live.get("error", ""),
            }

        now = time.monotonic()
        with mouth_probe_lock:
            if mouth_probe_state["data"] is not None and (now - mouth_probe_state["ts"]) < 0.5:
                cached = dict(mouth_probe_state["data"])
                cached.update(enabled=enabled, timeout_s=timeout_s, waiting_for_mouth=False, waiting_waypoint="")
                return cached
            dev_path = _v4l2_device_for("person") or "/dev/video2"
            bgr, _jpeg, err = _grab_v4l2_frame(dev_path)
            if bgr is None:
                out = {
                    "ok": False, "enabled": enabled, "timeout_s": timeout_s,
                    "waiting_for_mouth": False, "waiting_waypoint": "",
                    "face_detected": False, "mouth_open": False, "mouth_open_confirmed": False,
                    "mar": None, "error": err or f"cannot open person camera {dev_path}",
                }
            else:
                with vision_lock:
                    det = _get_vision_detector()
                    m = det.detect_mouth(bgr)
                extra = dict(m.extra or {})
                out = {
                    "ok": True,
                    "enabled": enabled,
                    "timeout_s": timeout_s,
                    "waiting_for_mouth": False,
                    "waiting_waypoint": "",
                    "face_detected": bool(extra.get("face_detected", False)) and not bool(extra.get("fallback", False)),
                    "mouth_open": bool(extra.get("mouth_open", False)),
                    "mouth_open_confirmed": bool(extra.get("mouth_open_confirmed", False)),
                    "mar": extra.get("mar"),
                    "error": "",
                }
            mouth_probe_state["data"] = out
            mouth_probe_state["ts"] = time.monotonic()
            return out

    async def mouth_status(_: Request):
        data = await run_in_threadpool(_poll_mouth_status)
        return JSONResponse(data, headers={"Cache-Control": "no-store"})

    async def trace_log(request: Request):
        agent = agent_box["agent"]
        try:
            after = int(request.query_params.get("after", "0"))
        except ValueError:
            after = 0
        entries = agent.trace_after(after) if agent is not None else []
        return JSONResponse({"entries": entries}, headers={"Cache-Control": "no-store"})

    async def trace_clear(_: Request):
        agent = agent_box["agent"]
        if agent is not None:
            agent.clear_trace()
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
            _release_v4l2()
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
        Route("/api/mouth_status", mouth_status),
        Route("/api/trace", trace_log),
        Route("/api/trace/clear", trace_clear, methods=["POST"]),
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
