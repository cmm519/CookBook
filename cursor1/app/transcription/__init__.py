"""Speech-to-text transcription providers."""

from app.transcription.provider import (
    TranscriptionProvider,
    TranscriptResult,
    TranscriptSegment,
)
from app.transcription.whisper import FasterWhisperTranscription

__all__ = [
    "FasterWhisperTranscription",
    "TranscriptionProvider",
    "TranscriptResult",
    "TranscriptSegment",
]
