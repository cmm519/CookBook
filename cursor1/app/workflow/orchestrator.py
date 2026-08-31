"""Pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.bugreport.debug_log import DebugLogWriter
from app.models import LogLevel
from app.steps.base import PipelineStep, StepContext, StepExecutionError, StepResult


class OrchestrationError(Exception):
    """Pipeline orchestration failed."""


@dataclass
class PipelineOrchestrator:
    steps: list[PipelineStep] = field(default_factory=list)
    debug_writer: DebugLogWriter | None = None

    def run_step(self, step_number: int, context: StepContext) -> StepResult:
        step = self._get_step(step_number)
        if self.debug_writer:
            self.debug_writer.append(step_number, LogLevel.info, f"{step.name} started")
        result = step.run(context)
        if self.debug_writer:
            level = LogLevel.info if result.success else LogLevel.error
            msg = f"{step.name} complete" if result.success else (result.error or "failed")
            self.debug_writer.append(step_number, level, msg)
        return result

    def run_from(self, step_number: int, context: StepContext) -> list[StepResult]:
        ordered = sorted(self.steps, key=lambda s: s.step_number)
        results: list[StepResult] = []
        for step in ordered:
            if step.step_number < step_number:
                continue
            result = self.run_step(step.step_number, context)
            results.append(result)
            if not result.success:
                raise StepExecutionError(result.error or f"Step {step.step_number} failed")
        return results

    def run_all(self, context: StepContext) -> list[StepResult]:
        return self.run_from(1, context)

    def _get_step(self, step_number: int) -> PipelineStep:
        for step in self.steps:
            if step.step_number == step_number:
                return step
        raise OrchestrationError(f"Unknown step number: {step_number}")
