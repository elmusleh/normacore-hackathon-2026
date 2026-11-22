"""Web console routes, with a fake camera source and fake speech-to-text (no Station needed)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

pytest.importorskip("httpx")
from starlette.testclient import TestClient  # noqa: E402

from web_console import SpeechToText, create_app  # noqa: E402

JPEG = b"\xff\xd8fake-jpeg\xff\xd9"


class FakeTools:
    def call(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - mirrors RobotTools.call
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    def look(self, camera=""):
        if camera == "table":
            return {"ok": True, "width": 298, "height": 224, "age_seconds": 0.1}, JPEG
        if camera == "broken":
            raise ConnectionError("cannot reach the Station")
        return {"ok": False, "error": f"camera {camera!r} is not plugged in"}, None


class FakeSTT(SpeechToText):
    def __init__(self):
        super().__init__("fake")
        self.state = "ready"

    def start_loading(self):
        pass

    def transcribe(self, audio):
        return "I want a grape"


@pytest.fixture
def client():
    with TestClient(create_app(tools=FakeTools(), stt=FakeSTT())) as c:
        yield c


def test_page_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "ElRobot Console" in r.text


def test_frame_returns_jpeg_with_age(client):
    r = client.get("/api/frame/table")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    assert r.content == JPEG
    assert r.headers["x-frame-age"] == "0.1"
    assert r.headers["x-frame-size"] == "298x224"


def test_frame_errors_are_json(client):
    r = client.get("/api/frame/gripper")
    assert r.status_code == 503 and "not plugged in" in r.json()["error"]
    r = client.get("/api/frame/broken")
    assert r.status_code == 503 and "Station" in r.json()["error"]


def test_cameras_from_config(client):
    assert set(client.get("/api/cameras").json()["cameras"]) >= {"table", "gripper", "face"}


def test_transcribe(client):
    assert client.get("/api/stt").json()["state"] == "ready"
    r = client.post("/api/transcribe", content=b"audio-bytes")
    assert r.json() == {"ok": True, "text": "I want a grape", "seconds": r.json()["seconds"]}
    assert client.post("/api/transcribe", content=b"").status_code == 400


def test_frame_when_station_down():
    with TestClient(create_app(tools=FakeTools(), stt=None, station_up=lambda: False)) as c:
        r = c.get("/api/frame/table")
        assert r.status_code == 503 and "not running" in r.json()["error"]


def _wav_bytes(rate=48000, seconds=0.5):
    """A short tone as the browser might send it (other rate than 16 kHz on purpose)."""
    import io
    import math
    import struct
    import wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(i / 10)))
                               for i in range(int(rate * seconds))))
    return buf.getvalue()


class FakeOpenAI:
    """Records what speech.transcribe sends; never touches the network."""

    def __init__(self, text="ich möchte Joghurt", error=None):
        self.calls = []
        self._text, self._error = text, error
        self.audio = self
        self.transcriptions = self

    def create(self, **kwargs):
        f = kwargs["file"]
        self.calls.append({**kwargs, "name": f.name, "data": f.read()})
        if self._error:
            raise self._error
        return type("Result", (), {"text": f"  {self._text} "})()


@pytest.fixture
def fake_openai(monkeypatch):
    import speech
    fake = FakeOpenAI()
    monkeypatch.setattr(speech, "_client", fake)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-a-real-key")
    return fake


def test_stt_ready_with_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-a-real-key")
    stt = SpeechToText()
    assert (stt.state, stt.model_name, stt.device) == ("ready", "gpt-transcribe", "openai")


def test_stt_error_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    stt = SpeechToText()
    assert stt.state == "error" and "OPENAI_API_KEY" in stt.error
    with TestClient(create_app(tools=FakeTools(), stt=stt)) as c:
        assert c.get("/api/stt").json()["state"] == "error"  # page falls back to the browser
        assert c.post("/api/transcribe", content=b"x").status_code == 503


def test_transcribe_sends_wav_to_gpt_transcribe(fake_openai):
    import io
    import wave
    import speech
    with TestClient(create_app(tools=FakeTools(), stt=SpeechToText())) as c:
        r = c.post("/api/transcribe", content=_wav_bytes(), headers={"Content-Type": "audio/wav"})
    assert r.json()["ok"] and r.json()["text"] == "ich möchte Joghurt"
    (call,) = fake_openai.calls
    assert call["model"] == "gpt-transcribe"
    assert call["languages"] == ["de", "en"]
    assert set(speech.KEYWORDS) <= set(call["keywords"]) and "grape" in call["keywords"]
    assert call["name"].endswith(".wav")
    with wave.open(io.BytesIO(call["data"])) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2)


def test_transcribe_custom_keywords(fake_openai):
    stt = SpeechToText(keywords=["Apfel", "Banane"])
    assert stt.transcribe(_wav_bytes()) == "ich möchte Joghurt"
    assert fake_openai.calls[0]["keywords"] == ["Apfel", "Banane"]


def test_transcribe_error_hides_key(monkeypatch):
    import speech
    secret = "sk-proj-abcDEF123_secret"
    monkeypatch.setattr(speech, "_client", FakeOpenAI(error=ValueError(f"Incorrect API key provided: {secret}")))
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    with TestClient(create_app(tools=FakeTools(), stt=SpeechToText())) as c:
        r = c.post("/api/transcribe", content=_wav_bytes())
    assert r.status_code == 500
    assert secret not in r.text and "Incorrect API key" in r.json()["error"]


def test_transcribe_without_stt():
    with TestClient(create_app(tools=FakeTools(), stt=None)) as c:
        assert c.get("/api/stt").json()["state"] == "unavailable"
        assert c.post("/api/transcribe", content=b"x").status_code == 503


def test_messages_roundtrip(client):
    assert client.post("/api/messages", json={"role": "user", "text": "  feed me  "}).json()["ok"]
    assert client.post("/api/messages", json={"role": "robot", "text": "Getting a grape"}).json()["ok"]
    assert client.post("/api/messages", json={"role": "user", "text": ""}).status_code == 400
    assert client.post("/api/messages", json={"role": "admin", "text": "x"}).status_code == 400
    msgs = client.get("/api/messages").json()["messages"]
    assert [m["text"] for m in msgs] == ["feed me", "Getting a grape"]
    assert client.get(f"/api/messages?after={msgs[0]['id']}").json()["messages"][0]["role"] == "robot"


class FakeAgent:
    def __init__(self, post):
        self.post, self.state, self.error, self.busy = post, "ready", "", False
        self.submitted, self.stops = [], 0

    async def start(self):
        pass

    async def close(self):
        pass

    async def submit(self, text):
        self.submitted.append(text)
        self.post("robot", f"echo: {text}")

    async def emergency_stop(self):
        self.stops += 1


def test_user_message_goes_to_agent_and_stop_button():
    made = []

    def factory(post):
        made.append(FakeAgent(post))
        return made[0]

    with TestClient(create_app(tools=FakeTools(), stt=None, agent_factory=factory)) as c:
        c.post("/api/messages", json={"role": "user", "text": "look at the table"})
        d = c.get("/api/messages").json()
        assert [m["role"] for m in d["messages"]] == ["user", "robot"]
        assert d["agent"] == "ready" and d["busy"] is False
        assert c.post("/api/stop").json()["ok"]
    assert made[0].submitted == ["look at the table"] and made[0].stops == 1
