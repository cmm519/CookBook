"""Transcription interface plus a dependency-free mock backend.

The real backend (e.g. faster-whisper) is optional and kept behind this
interface. :class:`MockTranscriber` lets the pipeline and tests run end-to-end
without any model download or GPU.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str


class Transcript(BaseModel):
    language: str = "en"
    text: str = ""
    segments: list[TranscriptSegment] = Field(default_factory=list)


class Transcriber(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> Transcript:  # pragma: no cover - interface
        raise NotImplementedError


class MockTranscriber(Transcriber):
    """Return a fixed transcript. Useful for tests and offline demos."""

    def __init__(self, transcript: Transcript | None = None) -> None:
        self._transcript = transcript or Transcript(
            language="en",
            text="This is a placeholder transcript.",
            segments=[TranscriptSegment(start=0.0, end=2.0, text="This is a placeholder transcript.")],
        )

    def transcribe(self, audio_path: str) -> Transcript:
        return self._transcript
