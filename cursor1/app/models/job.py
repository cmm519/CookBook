"""Import job and related models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class ImportJobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class ImportJob(BaseModel):
    job_id: str
    source_url: str
    status: ImportJobStatus = ImportJobStatus.pending
    current_stage: int = 0
    working_dir: str
    user_comment: str | None = None
    custom_instruction: str | None = None
    video_processing_enabled: bool = True
    error_message: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None


class UserNote(BaseModel):
    note_id: str
    recipe_slug: str
    text: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class Rating(BaseModel):
    recipe_slug: str
    score: int = Field(ge=1, le=5)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
