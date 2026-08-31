"""Step 3: Transcribe audio."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import CookBookConfig
from app.steps.base import PipelineStep, StepPrerequisiteError
from app.transcription.whisper import FasterWhisperTranscription


class TranscribeStep(PipelineStep):
    name = "transcribe"
    step_number = 3
    requires = [2]

    def __init__(self, config: CookBookConfig) -> None:
        self._config = config
        self._provider: FasterWhisperTranscription | None = None

    def _get_provider(self) -> FasterWhisperTranscription:
        if self._provider is None:
            self._provider = FasterWhisperTranscription(
                self._config.whisper_model,
                self._config.whisper_device,
            )
        return self._provider

    def execute(self, context) -> tuple[dict[str, Any], dict[str, Any]]:
        audio_path = context.artifact("audio_path")
        if not audio_path:
            raise StepPrerequisiteError("audio_path missing from step 2")
        result = self._get_provider()._transcribe_audio(Path(audio_path))
        transcript_dir = context.working_dir / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)
        txt_path = transcript_dir / "transcript.txt"
        json_path = transcript_dir / "transcript.json"
        txt_path.write_text(result.text + "\n", encoding="utf-8")
        json_path.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return {
            "transcript_path": str(txt_path),
            "transcript_json_path": str(json_path),
            "transcript_text": result.text,
            "transcript": result.model_dump(mode="json"),
        }, {"segment_count": len(result.segments), "language": result.language}
