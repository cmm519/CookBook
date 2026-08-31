"""Single-recipe import workflow."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.bugreport.debug_log import DebugLogWriter
from app.config import CookBookConfig, load_config
from app.models import ImportJob, ImportJobStatus, LogLevel
from app.steps.base import StepContext, StepExecutionError
from app.workflow.factory import build_orchestrator


def run_import(
    source_url: str,
    *,
    config: CookBookConfig | None = None,
    user_comment: str | None = None,
    custom_instruction: str | None = None,
    video_processing_enabled: bool | None = None,
) -> tuple[ImportJob, str | None]:
    config = config or load_config()
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    working_dir = config.working_dir / job_id
    working_dir.mkdir(parents=True, exist_ok=True)

    job = ImportJob(
        job_id=job_id,
        source_url=source_url,
        status=ImportJobStatus.running,
        working_dir=str(working_dir),
        user_comment=user_comment,
        custom_instruction=custom_instruction,
        video_processing_enabled=(
            video_processing_enabled
            if video_processing_enabled is not None
            else config.video_processing_default
        ),
    )

    debug = DebugLogWriter(config.working_dir, job_id=job_id)
    debug.set_model_versions(
        whisper=config.whisper_model,
        formatter=config.formatter_model,
        formatter_provider=config.formatter_provider,
    )
    debug.append(0, LogLevel.info, f"Import started for {source_url}")

    context = StepContext(
        job_id=job_id,
        source_url=source_url,
        working_dir=working_dir,
        repository_path=config.repository_path,
        dataset_raw_dir=config.dataset_raw_dir,
        video_processing_enabled=job.video_processing_enabled,
        user_comment=user_comment,
        custom_instruction=custom_instruction,
    )

    orchestrator = build_orchestrator(config)
    orchestrator.debug_writer = debug

    try:
        orchestrator.run_all(context)
        job.status = ImportJobStatus.completed
        job.current_stage = 9
        job.completed_at = datetime.now(UTC).isoformat()
        slug = context.artifact("slug")
        debug.append(9, LogLevel.info, f"Import complete: slug={slug}")
        job.working_dir = str(working_dir)
        return job, slug
    except (StepExecutionError, Exception) as exc:
        job.status = ImportJobStatus.failed
        job.error_message = str(exc)
        job.completed_at = datetime.now(UTC).isoformat()
        debug.append(job.current_stage or 0, LogLevel.error, str(exc))
        raise
