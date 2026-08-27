"""Downloader interface and URL validation.

The concrete downloader (e.g. a ``yt-dlp`` backend) is intentionally kept
behind an interface so it can be swapped or mocked. Only URL validation is
implemented here; it has no network dependency and is unit-testable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from urllib.parse import urlparse

SUPPORTED_HOSTS = (
    "instagram.com",
    "www.instagram.com",
    "tiktok.com",
    "www.tiktok.com",
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
)


class UnsupportedURLError(ValueError):
    """Raised when a URL is not a supported video source."""


def is_supported_url(url: str) -> bool:
    """Return ``True`` when ``url`` looks like a supported video URL."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    return parsed.netloc.lower() in SUPPORTED_HOSTS


@dataclass
class DownloadResult:
    video_path: str
    source_url: str
    title: str | None = None
    uploader: str | None = None
    upload_date: str | None = None
    metadata: dict = field(default_factory=dict)


class Downloader(ABC):
    """Interface for downloading a video from a supported URL."""

    @abstractmethod
    def download(self, url: str, dest_dir: str) -> DownloadResult:  # pragma: no cover - interface
        raise NotImplementedError

    def validate(self, url: str) -> None:
        if not is_supported_url(url):
            raise UnsupportedURLError(f"Unsupported or invalid URL: {url!r}")
