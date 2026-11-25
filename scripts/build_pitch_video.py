#!/usr/bin/env python3
"""Render a crisp 1080p MP4 video from a CareArm PowerPoint deck using LibreOffice + ffmpeg.

Usage:
    python3 scripts/build_pitch_video.py \
        --pptx docs/CareArm_Use_Case_Pitch.pptx \
        --seconds-per-slide 8 \
        --output data/carearm_pitch_1080p.mp4

Optional:
    --audio path/to/voiceover.mp3   (mux narrated voiceover; trims/fits to audio length)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


def build_video(
    pptx_path: Path,
    output_path: Path,
    seconds_per_slide: float = 8.0,
    fps: int = 30,
    audio_path: Path | None = None,
) -> Path:
    if not pptx_path.exists():
        raise FileNotFoundError(f"PPTX not found: {pptx_path}")
    for tool in ("soffice", "pdftoppm", "ffmpeg"):
        if shutil.which(tool) is None:
            raise RuntimeError(f"Required tool '{tool}' not found in PATH.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="carearm_vid_") as tmp:
        tmp_dir = Path(tmp)
        lo_profile = tmp_dir / "lo_profile"

        # 1. Convert PPTX -> PDF
        subprocess.run(
            [
                "soffice",
                "--headless",
                f"-env:UserInstallation=file://{lo_profile}",
                "--convert-to",
                "pdf",
                str(pptx_path),
                "--outdir",
                str(tmp_dir),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        pdf_path = tmp_dir / f"{pptx_path.stem}.pdf"
        if not pdf_path.exists():
            raise RuntimeError("LibreOffice PDF export failed.")

        # 2. Render crisp 1920x1080 PNG slides
        subprocess.run(
            [
                "pdftoppm",
                "-png",
                "-scale-to-x",
                "1920",
                "-scale-to-y",
                "1080",
                str(pdf_path),
                str(tmp_dir / "slide"),
            ],
            check=True,
            stderr=subprocess.DEVNULL,
        )
        slides = sorted(tmp_dir.glob("slide-*.png"))
        if not slides:
            raise RuntimeError("No slide PNGs rendered.")

        # 3. Build concat list for ffmpeg
        concat_file = tmp_dir / "slides.txt"
        lines: list[str] = []
        for s in slides:
            lines.append(f"file '{s.as_posix()}'")
            lines.append(f"duration {seconds_per_slide:.2f}")
        # Repeat last frame per ffmpeg concat demuxer spec
        lines.append(f"file '{slides[-1].as_posix()}'")
        concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        # 4. Encode H.264 1080p MP4 (universally playable in Drive/YouTube/Chrome)
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
        ]
        if audio_path and audio_path.exists():
            cmd += ["-i", str(audio_path), "-c:a", "aac", "-b:a", "192k", "-shortest"]
        cmd += [
            "-vf",
            f"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps={fps},format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print(f"Rendered {len(slides)} slides -> {output_path} (1920x1080 @ {fps}fps)")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render 1080p MP4 video from a PPTX pitch deck.")
    parser.add_argument(
        "--pptx",
        type=Path,
        default=Path("docs/archive/pitch-drafts/CareArm_Use_Case_Pitch.pptx"),
        help="Input .pptx file (default: docs/archive/pitch-drafts/CareArm_Use_Case_Pitch.pptx)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/carearm_pitch_1080p.mp4"),
        help="Output .mp4 path (default: data/carearm_pitch_1080p.mp4, gitignored)",
    )
    parser.add_argument(
        "--seconds-per-slide",
        type=float,
        default=8.0,
        help="Display duration per slide in seconds (default: 8.0)",
    )
    parser.add_argument("--fps", type=int, default=30, help="Output frame rate (default: 30)")
    parser.add_argument("--audio", type=Path, default=None, help="Optional voiceover audio track (.mp3/.wav)")
    args = parser.parse_args()
    build_video(args.pptx, args.output, args.seconds_per_slide, args.fps, args.audio)


if __name__ == "__main__":
    main()
