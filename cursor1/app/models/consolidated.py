"""Consolidated source input for recipe formatting."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.downloader.metadata import VideoMetadata
from app.transcription.provider import TranscriptResult


class VisionFrameEvidence(BaseModel):
    timestamp: float
    text: str
    confidence: float | None = None


class VisionEvidence(BaseModel):
    frames: list[VisionFrameEvidence] = Field(default_factory=list)
    combined_text: str = ""


class ConsolidatedSourceInput(BaseModel):
    raw_transcript: str
    transcript: TranscriptResult | None = None
    metadata: VideoMetadata | None = None
    vision: VisionEvidence | None = None
    user_comment: str | None = None
    custom_instruction: str | None = None
    source_url: str
    extra: dict[str, Any] = Field(default_factory=dict)
