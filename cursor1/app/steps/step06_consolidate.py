"""Step 6: Consolidate sources."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.downloader.metadata import VideoMetadata
from app.extraction.consolidate import build_consolidated_input
from app.models import VisionEvidence
from app.steps.base import PipelineStep, StepPrerequisiteError
from app.transcription.provider import TranscriptResult


class ConsolidateStep(PipelineStep):
    name = "consolidate"
    step_number = 6
    requires = [3]

    def execute(self, context) -> tuple[dict[str, Any], dict[str, Any]]:
        transcript_text = context.artifact("transcript_text")
        if not transcript_text:
            raise StepPrerequisiteError("transcript_text missing from step 3")

        metadata = None
        metadata_path = context.artifact("metadata_path")
        if metadata_path and Path(metadata_path).is_file():
            metadata = VideoMetadata.model_validate_json(Path(metadata_path).read_text(encoding="utf-8"))
        elif context.artifact("metadata"):
            metadata = VideoMetadata.model_validate(context.artifact("metadata"))

        transcript = None
        transcript_json_path = context.artifact("transcript_json_path")
        if transcript_json_path and Path(transcript_json_path).is_file():
            transcript = TranscriptResult.model_validate_json(
                Path(transcript_json_path).read_text(encoding="utf-8")
            )

        vision = None
        vision_data = context.artifact("vision")
        if vision_data:
            vision = VisionEvidence.model_validate(vision_data)

        consolidated = build_consolidated_input(
            source_url=context.source_url,
            raw_transcript=transcript_text,
            transcript=transcript,
            metadata=metadata,
            vision=vision,
            user_comment=context.user_comment,
            custom_instruction=context.custom_instruction,
        )
        consolidated_path = context.working_dir / "consolidated.json"
        consolidated_path.write_text(consolidated.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return {
            "consolidated_path": str(consolidated_path),
            "consolidated": consolidated.model_dump(mode="json"),
        }, {}
