"""Debug log writer."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.models import BugReport, BugReportStatus, DebugLog, DebugLogEntry, LogLevel


class DebugLogWriter:
    def __init__(self, working_dir: Path, *, job_id: str, pipeline_version: str = "0.1.0") -> None:
        self.job_dir = Path(working_dir) / job_id
        self.job_dir.mkdir(parents=True, exist_ok=True)
        self._debug_log = DebugLog(
            log_id=f"dbg-{uuid.uuid4().hex[:8]}",
            job_id=job_id,
            pipeline_version=pipeline_version,
        )
        self._path = self.job_dir / "debug.log"

    @property
    def debug_log(self) -> DebugLog:
        return self._debug_log

    @property
    def path(self) -> Path:
        return self._path

    def set_model_versions(self, **versions: str) -> None:
        self._debug_log.model_versions.update(versions)

    def append(self, stage: int, level: LogLevel, message: str) -> None:
        self._debug_log.entries.append(
            DebugLogEntry(
                ts=datetime.now(UTC).isoformat(),
                stage=stage,
                level=level,
                message=message,
            )
        )
        self.flush()

    def flush(self) -> Path:
        self._path.write_text(
            self._debug_log.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        return self._path


def save_bug_report(
    working_dir: Path,
    *,
    description: str,
    debug_log_path: str,
    related_job_id: str | None = None,
    related_recipe_slug: str | None = None,
) -> BugReport:
    report = BugReport(
        report_id=f"bug-{uuid.uuid4().hex[:8]}",
        description=description,
        debug_log_path=debug_log_path,
        related_job_id=related_job_id,
        related_recipe_slug=related_recipe_slug,
        status=BugReportStatus.open,
    )
    reports_dir = Path(working_dir) / "bugreports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{report.report_id}.json"
    path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return report
