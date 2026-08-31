"""ffmpeg frame extraction."""

from __future__ import annotations

import subprocess
from pathlib import Path


def extract_frames(video_path: Path, output_dir: Path, *, interval: float = 2.0) -> list[Path]:
    """Extract JPEG frames every `interval` seconds."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / "frame_%06d.jpg"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"fps=1/{interval}",
        str(pattern),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is required but was not found") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise RuntimeError(f"ffmpeg frame extraction failed: {stderr}") from exc

    return sorted(output_dir.glob("frame_*.jpg"))
