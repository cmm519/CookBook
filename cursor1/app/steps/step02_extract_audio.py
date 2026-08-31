"""Step 2: Extract audio."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.media.audio import extract_audio_mono_16k
from app.steps.base import PipelineStep, StepPrerequisiteError


class ExtractAudioStep(PipelineStep):
    name = "extract_audio"
    step_number = 2
    requires = [1]

    def execute(self, context) -> tuple[dict[str, Any], dict[str, Any]]:
        video_path = context.artifact("video_path")
        if not video_path:
            raise StepPrerequisiteError("video_path missing from step 1")
        wav_path = context.working_dir / "audio.wav"
        extract_audio_mono_16k(Path(video_path), wav_path)
        return {"audio_path": str(wav_path)}, {"wav_bytes": wav_path.stat().st_size}
