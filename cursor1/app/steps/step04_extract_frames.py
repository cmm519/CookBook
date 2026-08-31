"""Step 4: Extract video frames."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import CookBookConfig
from app.media.frames import extract_frames
from app.steps.base import PipelineStep, StepPrerequisiteError


class ExtractFramesStep(PipelineStep):
    name = "extract_frames"
    step_number = 4
    requires = [1]

    def __init__(self, config: CookBookConfig) -> None:
        self._interval = config.frame_interval

    def execute(self, context) -> tuple[dict[str, Any], dict[str, Any]]:
        if not context.video_processing_enabled:
            return {"frames_dir": None, "frame_paths": []}, {"frame_count": 0}
        video_path = context.artifact("video_path")
        if not video_path:
            raise StepPrerequisiteError("video_path missing from step 1")
        frames_dir = context.working_dir / "frames"
        paths = extract_frames(Path(video_path), frames_dir, interval=self._interval)
        return {
            "frames_dir": str(frames_dir),
            "frame_paths": [str(p) for p in paths],
        }, {"frame_count": len(paths)}
