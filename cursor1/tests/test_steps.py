"""Tests for pipeline steps and orchestrator."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.config import CookBookConfig
from app.downloader.provider import DownloadResult
from app.models import Ingredient, Instruction, Recipe
from app.steps.base import StepContext, StepPrerequisiteError
from app.steps.step01_download import DownloadStep
from app.steps.step08_normalize_markdown import NormalizeMarkdownStep
from app.workflow.orchestrator import PipelineOrchestrator


def test_step_prerequisite_error():
    step = NormalizeMarkdownStep()
    context = StepContext(
        job_id="j1",
        source_url="https://example.com",
        working_dir=Path("/tmp/w"),
        repository_path=Path("/tmp/r"),
        dataset_raw_dir=Path("/tmp/d/raw"),
    )
    with pytest.raises(StepPrerequisiteError):
        step.validate_prerequisites(context)


@patch("app.steps.step01_download.YtDlpDownloader")
def test_download_step(mock_downloader_cls, tmp_path: Path):
    video = tmp_path / "raw" / "abc.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"fake")
    mock_instance = MagicMock()
    mock_instance.download.return_value = DownloadResult(
        video_path=video,
        metadata={"title": "Test"},
        source_url="https://instagram.com/reel/abc/",
        reel_id="abc",
    )
    mock_downloader_cls.return_value = mock_instance

    context = StepContext(
        job_id="j1",
        source_url="https://instagram.com/reel/abc/",
        working_dir=tmp_path / "job",
        repository_path=tmp_path / "recipes",
        dataset_raw_dir=tmp_path / "dataset/raw",
    )
    result = DownloadStep().run(context)
    assert result.success
    assert context.artifact("video_path")


def test_orchestrator_runs_ordered_steps(tmp_path: Path):
    class StubStep:
        def __init__(self, number: int):
            self.step_number = number
            self.name = f"step{number}"
            self.requires = [number - 1] if number > 1 else []

        def run(self, context):
            from app.steps.base import StepResult
            context.set_artifact(f"step_{self.step_number}_complete", True)
            return StepResult(step_number=self.step_number, success=True)

    orchestrator = PipelineOrchestrator(
        steps=[StubStep(1), StubStep(2)]  # type: ignore[list-item]
    )
    context = StepContext(
        job_id="j",
        source_url="https://example.com",
        working_dir=tmp_path,
        repository_path=tmp_path,
        dataset_raw_dir=tmp_path,
    )
    results = orchestrator.run_all(context)
    assert len(results) == 2
