"""Downloader provider interface."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DownloadResult(BaseModel):
    """Result of a single video download."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    video_path: Path
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_url: str = ""
    title: str | None = None
    reel_id: str | None = None


class DownloaderProvider(ABC):
    """Abstract interface for video download backends."""

    @abstractmethod
    def validate_url(self, url: str) -> bool:
        """Return True when the URL is supported for download."""

    @abstractmethod
    def download(self, url: str, output_dir: Path) -> DownloadResult:
        """Download a single video into output_dir."""

    @abstractmethod
    def download_batch(
        self,
        urls: list[str],
        output_dir: Path,
        limit: int = 50,
    ) -> list[DownloadResult]:
        """Download up to limit URLs with progress logging."""

    @abstractmethod
    def extract_urls_from_page(self, hub_url: str, limit: int = 50) -> list[str]:
        """Extract individual media URLs from a hub/profile page."""
