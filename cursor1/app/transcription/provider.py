"""Transcription provider interface."""

from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    """A single timed segment of transcribed speech."""

    start: float
    end: float
    text: str


class TranscriptResult(BaseModel):
    """Full transcription output for one audio or video file."""

    language: str
    text: str
    segments: list[TranscriptSegment] = Field(default_factory=list)


class TranscriptionProvider(ABC):
    """Abstract interface for speech-to-text backends."""

    @abstractmethod
    def transcribe(self, audio_or_video_path: Path) -> TranscriptResult:
        """Transcribe an audio or video file."""
