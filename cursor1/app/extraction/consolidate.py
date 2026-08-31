"""Source consolidation."""

from __future__ import annotations

import json
from pathlib import Path

from app.downloader.metadata import VideoMetadata
from app.models import ConsolidatedSourceInput, VisionEvidence
from app.transcription.provider import TranscriptResult


def build_consolidated_input(
    *,
    source_url: str,
    raw_transcript: str,
    transcript: TranscriptResult | None = None,
    metadata: VideoMetadata | None = None,
    vision: VisionEvidence | None = None,
    user_comment: str | None = None,
    custom_instruction: str | None = None,
) -> ConsolidatedSourceInput:
    return ConsolidatedSourceInput(
        source_url=source_url,
        raw_transcript=raw_transcript,
        transcript=transcript,
        metadata=metadata,
        vision=vision,
        user_comment=user_comment,
        custom_instruction=custom_instruction,
    )


def load_metadata_json(path: Path) -> VideoMetadata:
    return VideoMetadata.model_validate_json(path.read_text(encoding="utf-8"))


def load_transcript_json(path: Path) -> TranscriptResult:
    return TranscriptResult.model_validate_json(path.read_text(encoding="utf-8"))


def load_vision_json(path: Path) -> VisionEvidence:
    return VisionEvidence.model_validate_json(path.read_text(encoding="utf-8"))


def consolidated_to_prompt_dict(consolidated: ConsolidatedSourceInput) -> dict:
    data = consolidated.model_dump(mode="json")
    if consolidated.metadata:
        data["metadata"] = json.loads(consolidated.metadata.model_dump_json())
    return data
