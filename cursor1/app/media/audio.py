"""ffmpeg audio extraction."""

from __future__ import annotations

import subprocess
from pathlib import Path


def extract_audio_mono_16k(video_path: Path, wav_path: Path) -> None:
    """Extract mono 16 kHz WAV from video."""
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(wav_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is required but was not found") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise RuntimeError(f"ffmpeg failed: {stderr}") from exc

    if not wav_path.is_file() or wav_path.stat().st_size == 0:
        raise RuntimeError(f"ffmpeg produced empty or missing WAV: {wav_path}")
