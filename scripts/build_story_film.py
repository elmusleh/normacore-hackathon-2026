#!/usr/bin/env python3
"""Build a narrated 1080p story film for CareArm (Team 6) from the production script.

Synthesizes per-scene voiceover (OpenAI tts-1-hd 'nova', with edge-tts / espeak-ng
fallback), syncs every scene's duration to its exact narration length + natural pause,
adds Ken Burns slow-zoom motion, crisp Inter captions, subtle warm ambient music bed,
and smooth crossfades.

Usage:
    .venv/bin/python scripts/build_story_film.py
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
FPS = 30
FADE_S = 0.65
PAUSE_AFTER_VOICE_S = 0.75

STORY_SCENES = [
    {
        "id": "00_open",
        "kind": "title",
        "eyebrow": "TEAM 6 · CAREARM  |  BERLIN ROBOTICS & AI HACKATHON",
        "title": "Restoring Mealtime\nIndependence",
        "subtitle": "The story of CareArm — hands-free assistive feeding\nfor elderly and paralyzed individuals.",
        "footer": "Jan Schulz  ·  Jafer Sharfeddin  ·  Mohammad El-Musleh  |  NormaCore Track",
        "narration": "Eating a meal is one of life's simplest joys — until you can no longer lift your own arms.",
    },
    {
        "id": "01_need",
        "kind": "image",
        "path": "docs/assets/scene_01_need.png",
        "tag": "01 · THE HUMAN NEED",
        "headline": "Meet Marta — 1,095 Assisted Meals Every Year",
        "body": "Waiting for someone else’s schedule for every single bite takes away daily autonomy.",
        "narration": "Meet Marta. Like millions of elderly and paralyzed people worldwide, she is completely sharp — yet three times a day, over a thousand meals a year, she has to wait for someone else to feed her every single bite.",
    },
    {
        "id": "02_voice",
        "kind": "image",
        "path": "docs/assets/scene_02_voice.png",
        "tag": "02 · HANDS-FREE VOICE",
        "headline": "“Give Me a Grape.” — Just Speak Naturally",
        "body": "No chin-switches or joysticks. Bilingual English & German voice with calm audio cues.",
        "narration": "We built CareArm to give that independence back. There are no clunky chin-switches or joysticks. Marta simply speaks naturally, in English or German: Give me a grape.",
    },
    {
        "id": "03_grasp",
        "kind": "image",
        "path": "docs/assets/scene_03_grasp.png",
        "tag": "03 · GENTLE VISION & GRASP",
        "headline": "Sees the Plate. Grasps Gently Without Crushing.",
        "body": "Claude plans the pick; wrist-camera LAB vision (<5 ms) and servo load verify the grip.",
        "narration": "Our system separates intelligence from safety. Claude understands her request and inspects the table camera, while a wrist camera and load sensor verify a gentle, non-crushing grip in under five milliseconds.",
    },
    {
        "id": "04_standoff",
        "kind": "image",
        "path": "docs/assets/scene_04_standoff.png",
        "tag": "04 · RESPECTFUL FACE SAFETY",
        "headline": "Pauses 8 cm Away — Waits for Your Mouth to Open",
        "body": "30 FPS MediaPipe lip tracking, 0.6 s face-loss watchdog, and <0.5 s voice “Stop!” freeze.",
        "narration": "Near the face, CareArm never forces a bite. It pauses respectfully eight centimeters away and waits. A real-time MediaPipe camera watches for Marta to open her mouth — and if she looks away or says Stop, all eight motors freeze safely in under half a second.",
    },
    {
        "id": "05_architecture",
        "kind": "diagram",
        "path": "docs/diagrams/carearm_overview.png",
        "tag": "05 · UNDER THE HOOD",
        "headline": "4 Decoupled Layers · 15 MCP Tools · 123 Passing Tests",
        "body": "Claude decides, local code acts fast — protected by 3-layer AI guardrails and NormaCore safety.",
        "narration": "Under the hood, four clean layers work together: hands-free voice, a three-layer guardrailed Claude M-C-P brain, thirty-frame-per-second local vision, and deterministic NormaCore hardware safety — verified by one hundred and twenty-three automated tests.",
    },
    {
        "id": "06_family",
        "kind": "image",
        "path": "docs/assets/scene_05_family.png",
        "tag": "06 · DIGNITY AT HOME",
        "headline": "Shared Family Dinners — Together Again",
        "body": "Caregivers and loved ones can finally enjoy their own warm meal at the same table.",
        "narration": "For Marta and her daughter, dinner changes completely. Her daughter can finally enjoy her own warm meal beside her — laughing together as family again, instead of rushing between bites.",
    },
    {
        "id": "07_carehome",
        "kind": "image",
        "path": "docs/assets/scene_06_carehome.png",
        "tag": "07 · SCALABLE IMPACT",
        "headline": "10× More Affordable — Built for Homes & Elder Care",
        "body": "Open NormaCore hardware brings independent dining to homes, rehab clinics, and assisted living.",
        "narration": "And because CareArm runs on open NormaCore hardware, it costs ten times less than ten-thousand-dollar commercial feeders — bringing dignified, independent dining to homes, rehab clinics, and elder care.",
    },
    {
        "id": "08_close",
        "kind": "title",
        "eyebrow": "DIGNITY  ·  TRUST  ·  ACCESS",
        "title": "CareArm",
        "subtitle": "Eating independently is a human right.\nBuilt in Berlin with Claude MCP & NormaCore ElRobot.",
        "footer": "Team 6: Jan Schulz · Jafer Sharfeddin · Mohammad El-Musleh  |  github.com/elmusleh/carearm-feeding-robot",
        "narration": "CareArm — built in Berlin by Team Six. Because eating independently is a human right.",
    },
]


def _load_env(repo_root: Path) -> None:
    env_file = repo_root / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        [
            "/usr/share/fonts/truetype/inter/Inter-Bold.ttf",
            "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        if bold
        else [
            "/usr/share/fonts/truetype/inter/Inter-Regular.ttf",
            "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    )
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def _synthesize_tts(text: str, out_wav: Path, voice: str = "nova") -> str:
    """Synthesize narration to 48kHz stereo WAV. Tries OpenAI tts-1-hd -> edge-tts -> espeak-ng."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    tmp_mp3 = out_wav.with_suffix(".mp3")

    if api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            resp = client.audio.speech.create(
                model="tts-1-hd",
                voice=voice,
                input=text,
                speed=0.98,
            )
            resp.write_to_file(str(tmp_mp3))
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(tmp_mp3), "-ar", "48000", "-ac", "2", str(out_wav)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            tmp_mp3.unlink(missing_ok=True)
            return f"openai:tts-1-hd:{voice}"
        except Exception as exc:
            print(f"  [TTS] OpenAI unavailable ({type(exc).__name__}), trying edge-tts...")

    if shutil.which("edge-tts"):
        try:
            subprocess.run(
                ["edge-tts", "--voice", "en-US-AriaNeural", "--text", text, "--write-media", str(tmp_mp3)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(tmp_mp3), "-ar", "48000", "-ac", "2", str(out_wav)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            tmp_mp3.unlink(missing_ok=True)
            return "edge-tts:en-US-AriaNeural"
        except Exception as exc:
            print(f"  [TTS] edge-tts unavailable ({type(exc).__name__}), falling back to espeak-ng...")

    raw_wav = out_wav.with_name(out_wav.stem + "_raw.wav")
    subprocess.run(
        ["espeak-ng", "-s", "150", "-p", "48", "-w", str(raw_wav), text],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(raw_wav), "-ar", "48000", "-ac", "2", str(out_wav)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    raw_wav.unlink(missing_ok=True)
    return "espeak-ng"


def _cover_resize(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_ratio = img.width / img.height
    dst_ratio = target_w / target_h
    if src_ratio > dst_ratio:
        new_h = target_h
        new_w = int(target_h * src_ratio)
    else:
        new_w = target_w
        new_h = int(target_w / src_ratio)
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def _contain_diagram(img: Image.Image) -> Image.Image:
    """Place architecture diagram cleanly on a warm ivory 1920x1080 canvas above the caption band."""
    canvas = Image.new("RGB", (W, H), (250, 249, 246))
    max_w, max_h = W - 120, 770
    scale = min(max_w / img.width, max_h / img.height)
    nw, nh = int(img.width * scale), int(img.height * scale)
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    x = (W - nw) // 2
    y = 32 + (max_h - nh) // 2
    canvas.paste(resized, (x, y))
    return canvas


def _make_title_card(out_path: Path, eyebrow: str, title: str, subtitle: str, footer: str) -> None:
    img = Image.new("RGBA", (W, H), (17, 24, 39, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (W, 14)], fill=(45, 212, 191, 255))

    f_eye = _load_font(28, bold=True)
    f_title = _load_font(86, bold=True)
    f_sub = _load_font(38, bold=False)
    f_foot = _load_font(26, bold=False)

    draw.text((W // 2, 225), eyebrow, font=f_eye, fill=(45, 212, 191, 255), anchor="mm")
    y = 375
    for line in title.split("\n"):
        draw.text((W // 2, y), line, font=f_title, fill=(255, 255, 255, 255), anchor="mm")
        y += 108
    y += 32
    for line in subtitle.split("\n"):
        draw.text((W // 2, y), line, font=f_sub, fill=(203, 213, 225, 255), anchor="mm")
        y += 54
    draw.text((W // 2, H - 88), footer, font=f_foot, fill=(148, 163, 184, 255), anchor="mm")
    img.convert("RGB").save(out_path, quality=95)


def _make_caption_overlay(out_path: Path, tag: str, headline: str, body: str) -> None:
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    band_top = 740
    for y in range(band_top, H):
        t = (y - band_top) / (H - band_top)
        alpha = int(222 * (t ** 1.3))
        draw.line([(0, y), (W, y)], fill=(11, 18, 32, alpha))

    draw.rounded_rectangle([(96, 848), (108, 1012)], radius=6, fill=(45, 212, 191, 255))
    f_tag = _load_font(24, bold=True)
    f_head = _load_font(44, bold=True)
    f_body = _load_font(28, bold=False)

    draw.text((134, 848), tag, font=f_tag, fill=(45, 212, 191, 255))
    draw.text((134, 886), headline, font=f_head, fill=(255, 255, 255, 255))
    draw.text((134, 950), body, font=f_body, fill=(226, 232, 240, 255))
    overlay.save(out_path)


def build_story_film(repo_root: Path, output_path: Path, voice: str = "nova") -> Path:
    _load_env(repo_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="carearm_film_") as tmp:
        tmp_dir = Path(tmp)
        clips: list[tuple[Path, Path, float]] = []
        used_engine = ""

        for idx, sc in enumerate(STORY_SCENES):
            sid = sc["id"]
            wav_path = tmp_dir / f"{sid}_voice.wav"
            used_engine = _synthesize_tts(sc["narration"], wav_path, voice=voice)
            speech_dur = _probe_duration(wav_path)
            clip_dur = max(4.2, speech_dur + PAUSE_AFTER_VOICE_S + (0.45 if idx == 0 else 0.25))

            # Pad audio cleanly with slight lead-in (0.3s) and silence tail to exact clip_dur
            padded_wav = tmp_dir / f"{sid}_audio.wav"
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(wav_path),
                    "-af", f"adelay=300|300,apad=whole_dur={clip_dur:.3f},atrim=0:{clip_dur:.3f}",
                    "-ar", "48000", "-ac", "2",
                    str(padded_wav),
                ],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )

            clip_mp4 = tmp_dir / f"{sid}_video.mp4"
            frames = int(round(clip_dur * FPS))

            if sc["kind"] == "title":
                card_img = tmp_dir / f"{sid}_card.png"
                _make_title_card(card_img, sc["eyebrow"], sc["title"], sc["subtitle"], sc["footer"])
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-loop", "1", "-t", f"{clip_dur:.3f}", "-i", str(card_img),
                        "-vf", f"fps={FPS},format=yuv420p",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                        str(clip_mp4),
                    ],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            elif sc["kind"] == "diagram":
                diag_img = _contain_diagram(Image.open(repo_root / sc["path"]).convert("RGB"))
                base_path = tmp_dir / f"{sid}_base.png"
                diag_img.save(base_path)
                cap_path = tmp_dir / f"{sid}_cap.png"
                _make_caption_overlay(cap_path, sc["tag"], sc["headline"], sc["body"])
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-loop", "1", "-t", f"{clip_dur:.3f}", "-i", str(base_path),
                        "-i", str(cap_path),
                        "-filter_complex", f"[0:v]fps={FPS}[bg];[bg][1:v]overlay=0:0,format=yuv420p[v]",
                        "-map", "[v]", "-t", f"{clip_dur:.3f}",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                        str(clip_mp4),
                    ],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            else:
                src_img = _cover_resize(Image.open(repo_root / sc["path"]).convert("RGB"), 2240, 1260)
                base_path = tmp_dir / f"{sid}_base.png"
                src_img.save(base_path)
                cap_path = tmp_dir / f"{sid}_cap.png"
                _make_caption_overlay(cap_path, sc["tag"], sc["headline"], sc["body"])
                zoom_expr = (
                    f"zoompan=z='min(1.07,1+0.07*on/{frames})':"
                    f"x='iw/2-(iw/zoom/2)':y='ih*0.44-(ih/zoom*0.44)':"
                    f"d={frames}:s={W}x{H}:fps={FPS}"
                )
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-i", str(base_path), "-i", str(cap_path),
                        "-filter_complex", f"[0:v]{zoom_expr}[bg];[bg][1:v]overlay=0:0,format=yuv420p[v]",
                        "-map", "[v]", "-t", f"{clip_dur:.3f}",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                        str(clip_mp4),
                    ],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )

            clips.append((clip_mp4, padded_wav, clip_dur))
            print(f"  Scene {sid}: {clip_dur:.1f}s (voice {speech_dur:.1f}s, engine={used_engine})")

        # Stitch video with smooth crossfades + audio with matching acrossfade
        cmd = ["ffmpeg", "-y"]
        for vpath, _, _ in clips:
            cmd += ["-i", str(vpath)]
        for _, apath, _ in clips:
            cmd += ["-i", str(apath)]

        n = len(clips)
        v_parts: list[str] = []
        a_parts: list[str] = []
        offset = clips[0][2] - FADE_S
        prev_v = "[0:v]"
        prev_a = f"[{n}:a]"

        for i in range(1, n):
            out_v = f"[v{i}]" if i < n - 1 else "[vout]"
            out_a = f"[a{i}]" if i < n - 1 else "[voice_all]"
            v_parts.append(f"{prev_v}[{i}:v]xfade=transition=fade:duration={FADE_S}:offset={offset:.3f}{out_v}")
            a_parts.append(f"{prev_a}[{n + i}:a]acrossfade=d={FADE_S}:c1=tri:c2=tri{out_a}")
            prev_v = out_v
            prev_a = out_a
            offset += clips[i][2] - FADE_S

        total_dur = offset + FADE_S

        # Subtle warm Cmaj7 ambient harmonic pad (-27 dB) under narration
        pad_filter = (
            f"aevalsrc='0.18*sin(2*PI*130.81*t)+0.14*sin(2*PI*196.00*t)+0.12*sin(2*PI*246.94*t)+0.10*sin(2*PI*329.63*t)'"
            f":s=48000:d={total_dur:.2f},lowpass=f=650,volume=0.045,"
            f"afade=t=in:st=0:d=2.0,afade=t=out:st={max(0.0, total_dur - 2.5):.2f}:d=2.5[pad];"
            f"[voice_all][pad]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
        )

        filter_complex = ";".join(v_parts + a_parts + [pad_filter])
        cmd += [
            "-filter_complex", filter_complex,
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_path),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    final_dur = _probe_duration(output_path)
    print(f"Built narrated 1080p story film -> {output_path} ({final_dur:.1f}s, TTS={used_engine})")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build narrated 1080p CareArm story film.")
    parser.add_argument("--output", type=Path, default=Path("data/carearm_story_film_1080p.mp4"))
    parser.add_argument("--voice", default="nova", help="OpenAI TTS voice (default: nova)")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    build_story_film(repo_root, repo_root / args.output if not args.output.is_absolute() else args.output, args.voice)


if __name__ == "__main__":
    main()
