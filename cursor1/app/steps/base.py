"""Pipeline step base types."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class StepError(Exception):
    """Base pipeline step error."""


class StepPrerequisiteError(StepError):
    """Required prior step artifacts are missing."""


class StepExecutionError(StepError):
    """Step failed during execution."""


@dataclass
class StepContext:
    job_id: str
    source_url: str
    working_dir: Path
    repository_path: Path
    dataset_raw_dir: Path
    video_processing_enabled: bool = True
    user_comment: str | None = None
    custom_instruction: str | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)

    def artifact(self, key: str, default: Any = None) -> Any:
        return self.artifacts.get(key, default)

    def set_artifact(self, key: str, value: Any) -> None:
        self.artifacts[key] = value


@dataclass
class StepResult:
    step_number: int
    success: bool
    artifacts: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_ms: int = 0


class PipelineStep(ABC):
    name: str
    step_number: int
    requires: list[int]

    def validate_prerequisites(self, context: StepContext) -> bool:
        for step_number in self.requires:
            key = f"step_{step_number}_complete"
            if not context.artifact(key):
                raise StepPrerequisiteError(
                    f"Step {self.step_number} ({self.name}) requires step {step_number}"
                )
        return True

    def run(self, context: StepContext) -> StepResult:
        start = time.perf_counter()
        try:
            self.validate_prerequisites(context)
            artifacts, metrics = self.execute(context)
            context.set_artifact(f"step_{self.step_number}_complete", True)
            for key, value in artifacts.items():
                context.set_artifact(key, value)
            duration_ms = int((time.perf_counter() - start) * 1000)
            return StepResult(
                step_number=self.step_number,
                success=True,
                artifacts=artifacts,
                metrics=metrics,
                duration_ms=duration_ms,
            )
        except StepPrerequisiteError:
            raise
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return StepResult(
                step_number=self.step_number,
                success=False,
                error=str(exc),
                duration_ms=duration_ms,
            )

    @abstractmethod
    def execute(self, context: StepContext) -> tuple[dict[str, Any], dict[str, Any]]:
        """Run step logic; return (artifacts, metrics)."""
