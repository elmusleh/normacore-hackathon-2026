"""Hands-free voice command transcription for the feeding robot arm.

Listens continuously on the microphone, cuts utterances with silero-vad,
transcribes them with OpenAI gpt-transcribe and prints recognised commands.

Usage:
    python speech.py              # live microphone
    python speech.py --debug      # also show discarded utterances
    python speech.py --file x.wav # run a file through the same logic
"""

import argparse
import collections
import os
import queue
import re
import sys
import tempfile
import threading
import time
import wave

import numpy as np

WAKE_WORD = "Robo"
WAKE_VARIANTS = {"robo", "robbo", "roboh", "robot"}
STOP_WORDS = {"stopp", "stop", "halt"}
RESUME_WORD = "weiter"  # after STOP, only "Robo, weiter" resumes
WAKE_FOLLOWUP_S = 5.0   # after a bare "Robo", the next utterance within this time is a command
LANGUAGES = ["de", "en"]
KEYWORDS = ["Robo", "Joghurt", "Pudding", "Löffel", "Stopp", "Halt", "weiter", "fertig", "mehr"]
MODEL = "gpt-transcribe"

SAMPLE_RATE = 16000
CHUNK = 512  # samples per VAD frame (32 ms at 16 kHz), required by silero-vad
VAD_THRESHOLD = 0.5       # speech probability that starts an utterance
VAD_NEG_THRESHOLD = 0.35  # below this, a frame inside an utterance counts as silence
PRE_ROLL_S = 0.3
SILENCE_END_S = 0.8
MAX_UTTERANCE_S = 8.0
MIN_UTTERANCE_S = 0.1  # a fast "Stopp"/"Halt" can be under 0.3 s of detected speech

_client = None


def transcribe(path: str, model: str = MODEL, keywords: list[str] | None = None) -> str:
    """Transcribe an audio file with gpt-transcribe and return the text.

    `model` and `keywords` default to this module's settings; the web console
    (src/web_console.py) passes its own keyword list.
    """
    global _client
    if _client is None:
        from openai import OpenAI

        _client = OpenAI(timeout=15.0, max_retries=1)
    kw = KEYWORDS if keywords is None else keywords
    with open(path, "rb") as f:
        try:
            result = _client.audio.transcriptions.create(
                model=model,
                file=f,
                languages=LANGUAGES,
                keywords=kw,
            )
        except TypeError:
            # openai SDK <3.57 (e.g. 2.x) uses `prompt` instead of `languages`/`keywords`
            f.seek(0)
            compat_model = "gpt-4o-mini-transcribe" if model == "gpt-transcribe" else model
            result = _client.audio.transcriptions.create(
                model=compat_model,
                file=f,
                prompt=", ".join(kw),
            )
    return result.text.strip()


def parse_command(text: str) -> str | None:
    """Return "STOP", the command without the wake word, or None if discarded."""
    words = re.sub(r"[^\w\s]", " ", text.lower()).split()
    if STOP_WORDS.intersection(words):
        return "STOP"
    m = re.match(r"\W*(\w+)(.*)", text, re.DOTALL)
    if not m or m.group(1).lower() not in WAKE_VARIANTS:
        return None
    command = m.group(2).strip(" \t\n,.:;!?-")
    return command or None


def _words(text: str) -> list[str]:
    return re.sub(r"[^\w\s]", " ", text.lower()).split()


def is_bare_wake_word(text: str) -> bool:
    words = _words(text)
    return len(words) == 1 and words[0] in WAKE_VARIANTS


# Session state, only touched by the transcription thread.
paused = False          # after STOP: ignore commands until "Robo, weiter"
wake_until = 0.0        # after a bare "Robo": next utterance starting before this counts as a command


def handle_file(path: str, debug: bool, start: float = 0.0, end: float = 0.0) -> None:
    """Transcribe one file, apply the stop/wake-word logic and print the result.

    start/end are the utterance's monotonic timestamps (live mode); they are used
    for the follow-up window after a bare wake word.
    """
    global paused, wake_until
    t0 = time.perf_counter()
    try:
        text = transcribe(path)
    except Exception as e:
        print(f"[error] transcription failed: {e}", flush=True)
        return
    tag = f"[{time.perf_counter() - t0:.2f}s]"

    command = parse_command(text)
    if command is None and _words(text) and not is_bare_wake_word(text) and wake_until and start <= wake_until:
        command = text.strip(" \t\n,.:;!?-")  # follow-up after a bare "Robo"
    wake_until = 0.0

    if command == "STOP":
        paused = True
        print(f"{tag} STOP  (paused, say \"{WAKE_WORD}, {RESUME_WORD}\" to resume)", flush=True)
    elif command is None:
        if is_bare_wake_word(text):
            wake_until = end + WAKE_FOLLOWUP_S
            print(f"{tag} listening... ({WAKE_FOLLOWUP_S:.0f}s)", flush=True)
        elif debug:
            reason = "no wake word" if _words(text) else "empty"
            print(f"{tag} discarded ({reason}): {text!r}", flush=True)
    elif paused:
        if RESUME_WORD in _words(command):
            paused = False
            print(f"{tag} {command}  (resumed)", flush=True)
        elif debug:
            print(f"{tag} ignored (paused): {command!r}", flush=True)
    else:
        print(f"{tag} {command}", flush=True)


def write_wav(samples: np.ndarray) -> str:
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes((np.clip(samples, -1, 1) * 32767).astype(np.int16).tobytes())
    return path


def transcription_worker(jobs: queue.Queue, debug: bool) -> None:
    while True:
        path, start, end = jobs.get()
        try:
            handle_file(path, debug, start, end)
        finally:
            os.remove(path)


def listen(debug: bool) -> None:
    import sounddevice as sd
    import warnings

    import torch
    from silero_vad import load_silero_vad

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)  # torch.jit.load deprecation in silero-vad
        model = load_silero_vad()
    audio_q: queue.Queue = queue.Queue()
    jobs: queue.Queue = queue.Queue()
    threading.Thread(target=transcription_worker, args=(jobs, debug), daemon=True).start()

    def callback(indata, frames, time_info, status):
        if status and debug:
            print(f"[audio] {status}", file=sys.stderr)
        audio_q.put(indata[:, 0].copy())

    chunk_s = CHUNK / SAMPLE_RATE
    pre_roll = collections.deque(maxlen=round(PRE_ROLL_S / chunk_s))
    silence_end = round(SILENCE_END_S / chunk_s)
    max_chunks = round(MAX_UTTERANCE_S / chunk_s)

    utterance: list[np.ndarray] = []
    speech_chunks = 0  # chunks between first and last speech chunk
    silent_run = 0
    started = 0.0  # monotonic time when speech was detected

    def finish() -> None:
        nonlocal utterance, speech_chunks, silent_run
        speech_s = speech_chunks * chunk_s
        if speech_s < MIN_UTTERANCE_S:
            if debug:
                print(f"[vad] discarded (too short): {speech_s:.2f}s", flush=True)
        else:
            ended = time.monotonic() - silent_run * chunk_s  # end of speech, not of trailing silence
            jobs.put((write_wav(np.concatenate(utterance)), started, ended))
        utterance, speech_chunks, silent_run = [], 0, 0
        model.reset_states()

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                        blocksize=CHUNK, callback=callback):
        print(f"Listening. Say \"{WAKE_WORD}, ...\" or \"Stopp\". Ctrl+C to quit.", flush=True)
        while True:
            try:
                chunk = audio_q.get(timeout=0.2)  # timeout keeps Ctrl+C responsive
            except queue.Empty:
                continue
            if len(chunk) != CHUNK:
                continue
            prob = model(torch.from_numpy(chunk), SAMPLE_RATE).item()
            is_speech = prob >= (VAD_NEG_THRESHOLD if utterance else VAD_THRESHOLD)
            if not utterance:
                if is_speech:
                    utterance = list(pre_roll) + [chunk]
                    speech_chunks, silent_run = 1, 0
                    started = time.monotonic()
                    pre_roll.clear()
                else:
                    pre_roll.append(chunk)
                continue
            utterance.append(chunk)
            if is_speech:
                speech_chunks += silent_run + 1
                silent_run = 0
            else:
                silent_run += 1
            if silent_run >= silence_end or len(utterance) >= max_chunks:
                finish()


def main() -> None:
    parser = argparse.ArgumentParser(description="Hands-free voice commands for the robot arm.")
    parser.add_argument("--file", help="transcribe an existing audio file instead of the microphone")
    parser.add_argument("--debug", action="store_true", help="show discarded utterances")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        keys_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys")
        if os.path.exists(keys_file):
            with open(keys_file) as f:
                m = re.search(r"sk-[A-Za-z0-9_-]+", f.read())
            if m:
                os.environ["OPENAI_API_KEY"] = m.group(0)
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("Error: no OpenAI API key. Set OPENAI_API_KEY or put it in the 'keys' file next to speech.py.")

    try:
        if args.file:
            handle_file(args.file, args.debug)
        else:
            listen(args.debug)
    except KeyboardInterrupt:
        print("\nBye.")


if __name__ == "__main__":
    main()
