"""Step 5: Vision / OCR."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.steps.base import PipelineStep
from app.vision.provider import VisionProvider


class VisionStep(PipelineStep):
    name = "vision"
    step_number = 5
    requires = [4]

    def __init__(self, provider: VisionProvider) -> None:
        self._provider = provider

    def execute(self, context) -> tuple[dict[str, Any], dict[str, Any]]:
        if not context.video_processing_enabled:
            return {"vision_path": None, "vision": {}}, {"frame_text_count": 0}
        frame_paths = context.artifact("frame_paths") or []
        paths = [Path(p) for p in frame_paths]
        evidence = self._provider.analyze_frames(paths)
        vision_path = context.working_dir / "vision.json"
        vision_path.write_text(evidence.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return {
            "vision_path": str(vision_path),
            "vision": evidence.model_dump(mode="json"),
        }, {"frame_text_count": len(evidence.frames)}
