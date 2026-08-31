"""faster-whisper transcription provider."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel

from app.transcription.provider import TranscriptResult, TranscriptSegment, TranscriptionProvider

_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v", ".mpeg", ".mpg"}
_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".aac"}


class FasterWhisperTranscription(TranscriptionProvider):
    """Transcribe audio or video using faster-whisper."""

    def __init__(self, model: str, device: str, *, compute_type: str | None = None) -> None:
        if device not in {"cuda", "cpu"}:
            raise ValueError(f"Unsupported WHISPER_DEVICE: {device!r} (expected 'cuda' or 'cpu')")
        resolved_compute_type = compute_type or ("float16" if device == "cuda" else "int8")
        self._model = WhisperModel(model, device=device, compute_type=resolved_compute_type)

    def transcribe(self, audio_or_video_path: Path) -> TranscriptResult:
        path = Path(audio_or_video_path)
        if not path.is_file():
            raise FileNotFoundError(f"Input file not found: {path}")

        suffix = path.suffix.lower()
        if suffix in _VIDEO_EXTENSIONS:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                wav_path = Path(tmp.name)
            try:
                self._extract_audio(path, wav_path)
                return self._transcribe_audio(wav_path)
            finally:
                wav_path.unlink(missing_ok=True)

        if suffix in _AUDIO_EXTENSIONS or suffix == "":
            return self._transcribe_audio(path)

        raise ValueError(f"Unsupported media extension: {suffix!r}")

    def _extract_audio(self, video_path: Path, wav_path: Path) -> None:
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
            raise RuntimeError("ffmpeg is required for video transcription but was not found") from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            raise RuntimeError(f"ffmpeg failed to extract audio from {video_path}: {stderr}") from exc

    def _transcribe_audio(self, audio_path: Path) -> TranscriptResult:
        segments_iter, info = self._model.transcribe(str(audio_path))
        segments: list[TranscriptSegment] = []
        for segment in segments_iter:
            segments.append(
                TranscriptSegment(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text.strip(),
                )
            )
        text = " ".join(segment.text for segment in segments if segment.text).strip()
        language = info.language or "unknown"
        return TranscriptResult(language=language, text=text, segments=segments)
