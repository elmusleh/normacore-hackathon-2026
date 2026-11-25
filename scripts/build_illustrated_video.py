#!/usr/bin/env python3
"""Assemble a cinematic 1080p illustrated use-case story video for CareArm (Team 6).

Takes the 6 generated editorial illustrations in docs/assets/scene_01..06*.png,
adds crisp Inter-font lower-third captions + opening/closing title cards, applies
gentle Ken Burns slow-zoom motion and crossfade transitions via ffmpeg, and exports
a 1920x1080 @ 30 FPS H.264 MP4 (universally playable on Google Drive & YouTube).

Usage:
    python3 scripts/build_illustrated_video.py
    python3 scripts/build_illustrated_video.py --audio data/narration.mp3
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080

SCENES = [
    (
        "scene_01_need.png",
        "01 · THE DAILY CHALLENGE",
        "Eating Independently Shouldn’t Depend on Someone Else’s Schedule",
        "Millions of elderly and paralyzed individuals wait for assistance for every single bite — 1,095 meals every year.",
        7.5,
    ),
    (
        "scene_02_voice.png",
        "02 · HANDS-FREE VOICE CONTROL",
        "“Give me a grape.” — Just Speak Naturally",
        "No chin-switches or joysticks. CareArm listens in English or German and responds with calm spoken feedback.",
        7.5,
    ),
    (
        "scene_03_grasp.png",
        "03 · GENTLE VISION & VERIFIED GRASP",
        "Sees the Plate. Grasps Gently Without Crushing.",
        "Overhead and wrist cameras verify every pick in under 5 ms, backed by servo load protection.",
        7.5,
    ),
    (
        "scene_04_standoff.png",
        "04 · RESPECTFUL 5–10 CM STANDOFF",
        "You Lead Every Bite — CareArm Waits for Your Mouth to Open",
        "30 FPS MediaPipe lip tracking confirms readiness. Look away or say “Stop!” for an instant pose-hold pause.",
        8.5,
    ),
    (
        "scene_05_family.png",
        "05 · DIGNITY RESTORED AT HOME",
        "Shared Family Dinners — Together Again",
        "Caregivers and loved ones can finally enjoy their own warm meal alongside the person they care for.",
        7.5,
    ),
    (
        "scene_06_carehome.png",
        "06 · CARE HOMES & REHAB IMPACT",
        "10× More Affordable Care — Built for Real Dining Rooms",
        "Open NormaCore hardware brings dignified, independent dining to homes, rehab clinics, and elder care.",
        8.0,
    ),
]


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
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


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


def _make_title_card(
    out_path: Path,
    eyebrow: str,
    title: str,
    subtitle: str,
    footer: str,
) -> None:
    img = Image.new("RGBA", (W, H), (17, 24, 39, 255))
    draw = ImageDraw.Draw(img)

    # Top teal accent bar
    draw.rectangle([(0, 0), (W, 14)], fill=(45, 212, 191, 255))

    f_eye = _load_font(28, bold=True)
    f_title = _load_font(86, bold=True)
    f_sub = _load_font(38, bold=False)
    f_foot = _load_font(26, bold=False)

    # Centered text
    draw.text((W // 2, 230), eyebrow, font=f_eye, fill=(45, 212, 191, 255), anchor="mm")

    y = 380
    for line in title.split("\n"):
        draw.text((W // 2, y), line, font=f_title, fill=(255, 255, 255, 255), anchor="mm")
        y += 108

    y += 30
    for line in subtitle.split("\n"):
        draw.text((W // 2, y), line, font=f_sub, fill=(203, 213, 225, 255), anchor="mm")
        y += 54

    draw.text((W // 2, H - 90), footer, font=f_foot, fill=(148, 163, 184, 255), anchor="mm")
    img.convert("RGB").save(out_path, quality=95)


def _make_caption_overlay(out_path: Path, tag: str, headline: str, body: str) -> None:
    """Create a transparent 1920x1080 PNG with a sleek bottom gradient & Inter captions."""
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Smooth bottom dark gradient band (y=720..1080)
    band_top = 720
    for y in range(band_top, H):
        t = (y - band_top) / (H - band_top)
        alpha = int(215 * (t ** 1.35))
        draw.line([(0, y), (W, y)], fill=(11, 18, 32, alpha))

    # Left vertical teal accent bar next to caption block
    draw.rounded_rectangle([(96, 838), (108, 1008)], radius=6, fill=(45, 212, 191, 255))

    f_tag = _load_font(24, bold=True)
    f_head = _load_font(44, bold=True)
    f_body = _load_font(29, bold=False)

    draw.text((134, 840), tag, font=f_tag, fill=(45, 212, 191, 255))
    draw.text((134, 878), headline, font=f_head, fill=(255, 255, 255, 255))
    draw.text((134, 944), body, font=f_body, fill=(226, 232, 240, 255))

    overlay.save(out_path)


def build_illustrated_video(
    assets_dir: Path,
    output_path: Path,
    fps: int = 30,
    audio_path: Path | None = None,
) -> Path:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found in PATH.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="carearm_story_") as tmp:
        tmp_dir = Path(tmp)
        clips: list[tuple[Path, float]] = []

        # 0. Opening Title Card (4.5s)
        open_img = tmp_dir / "00_open.png"
        _make_title_card(
            open_img,
            "TEAM 6 · CAREARM  |  NORMACORE TRACK",
            "Restoring Mealtime\nIndependence",
            "Hands-free, voice-controlled assistive feeding for\nparalyzed and elderly individuals who deserve dignity at every table.",
            "Jan Schulz  ·  Jafer Sharfeddin  ·  Mohammad El-Musleh  |  Berlin Robotics & AI Hackathon 2026",
        )
        open_mp4 = tmp_dir / "00_open.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y", "-loop", "1", "-t", "4.5", "-i", str(open_img),
                "-vf", f"fps={fps},format=yuv420p",
                "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                str(open_mp4),
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        clips.append((open_mp4, 4.5))

        # 1..6 Illustrated scenes with gentle Ken Burns zoom + crisp caption overlay
        for idx, (fname, tag, headline, body, dur) in enumerate(SCENES, start=1):
            src = assets_dir / fname
            if not src.exists():
                raise FileNotFoundError(f"Missing scene illustration: {src}")

            # Pre-scale image slightly larger (2240x1260) for silky Ken Burns zoom
            base_img = _cover_resize(Image.open(src).convert("RGB"), 2240, 1260)
            base_path = tmp_dir / f"{idx:02d}_base.png"
            base_img.save(base_path)

            cap_path = tmp_dir / f"{idx:02d}_cap.png"
            _make_caption_overlay(cap_path, tag, headline, body)

            clip_mp4 = tmp_dir / f"{idx:02d}_clip.mp4"
            frames = int(dur * fps)
            # Gentle 1.00 -> 1.08 zoom centered slightly above bottom captions
            zoom_expr = f"zoompan=z='min(1.08,1+0.08*on/{frames})':x='iw/2-(iw/zoom/2)':y='ih*0.44-(ih/zoom*0.44)':d={frames}:s={W}x{H}:fps={fps}"
            filter_complex = f"[0:v]{zoom_expr}[bg];[bg][1:v]overlay=0:0,format=yuv420p[v]"

            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", str(base_path),
                    "-i", str(cap_path),
                    "-filter_complex", filter_complex,
                    "-map", "[v]",
                    "-t", f"{dur:.2f}",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                    str(clip_mp4),
                ],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            clips.append((clip_mp4, dur))

        # 7. Closing Title Card (5.0s)
        close_img = tmp_dir / "99_close.png"
        _make_title_card(
            close_img,
            "DIGNITY  ·  TRUST  ·  ACCESS",
            "CareArm",
            "Eating independently is a human right.\nBuilt with Claude MCP, 3-Camera Vision & NormaCore ElRobot.",
            "Team 6: Jan Schulz · Jafer Sharfeddin · Mohammad El-Musleh  |  github.com/elmusleh/carearm-feeding-robot",
        )
        close_mp4 = tmp_dir / "99_close.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y", "-loop", "1", "-t", "5.0", "-i", str(close_img),
                "-vf", f"fps={fps},format=yuv420p",
                "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                str(close_mp4),
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        clips.append((close_mp4, 5.0))

        # 8. Stitch all clips with smooth 0.7s crossfade transitions
        fade = 0.7
        cmd = ["ffmpeg", "-y"]
        for clip_path, _ in clips:
            cmd += ["-i", str(clip_path)]
        if audio_path and audio_path.exists():
            cmd += ["-i", str(audio_path)]

        fc_parts: list[str] = []
        offset = clips[0][1] - fade
        prev_label = "[0:v]"
        for i in range(1, len(clips)):
            out_label = f"[v{i}]" if i < len(clips) - 1 else "[vout]"
            fc_parts.append(f"{prev_label}[{i}:v]xfade=transition=fade:duration={fade}:offset={offset:.2f}{out_label}")
            prev_label = out_label
            offset += clips[i][1] - fade

        cmd += ["-filter_complex", ";".join(fc_parts), "-map", "[vout]"]
        if audio_path and audio_path.exists():
            cmd += ["-map", f"{len(clips)}:a", "-c:a", "aac", "-b:a", "192k", "-shortest"]
        cmd += [
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(output_path),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print(f"Built illustrated 1080p story video -> {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build 1080p illustrated CareArm use-case story video.")
    parser.add_argument("--assets", type=Path, default=Path("docs/assets"))
    parser.add_argument("--output", type=Path, default=Path("data/carearm_use_case_story_1080p.mp4"))
    parser.add_argument("--audio", type=Path, default=None, help="Optional voiceover audio track (.mp3/.wav)")
    args = parser.parse_args()
    build_illustrated_video(args.assets, args.output, audio_path=args.audio)


if __name__ == "__main__":
    main()
