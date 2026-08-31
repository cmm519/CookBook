"""Debug log models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class LogLevel(str, Enum):
    info = "INFO"
    warning = "WARNING"
    error = "ERROR"


class DebugLogEntry(BaseModel):
    ts: str
    stage: int
    level: LogLevel
    message: str


class DebugLog(BaseModel):
    log_id: str
    job_id: str | None = None
    entries: list[DebugLogEntry] = Field(default_factory=list)
    pipeline_version: str = "0.1.0"
    model_versions: dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class BugReportStatus(str, Enum):
    open = "open"
    reviewed = "reviewed"
    resolved = "resolved"


class BugReport(BaseModel):
    report_id: str
    description: str
    debug_log_path: str
    related_job_id: str | None = None
    related_recipe_slug: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    status: BugReportStatus = BugReportStatus.open
