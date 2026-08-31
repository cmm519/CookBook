"""yt-dlp-backed video downloader."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.downloader.metadata import VideoMetadata
from app.downloader.provider import DownloadResult, DownloaderProvider

logger = logging.getLogger(__name__)

INSTAGRAM_REEL_PATTERN = re.compile(
    r"^https?://(?:www\.)?instagram\.com/reel/[A-Za-z0-9_-]+/?(?:\?.*)?$",
    re.IGNORECASE,
)
INSTAGRAM_POST_PATTERN = re.compile(
    r"^https?://(?:www\.)?instagram\.com/p/[A-Za-z0-9_-]+/?(?:\?.*)?$",
    re.IGNORECASE,
)
INSTAGRAM_REELS_PATTERN = re.compile(
    r"^https?://(?:www\.)?instagram\.com/reels/[A-Za-z0-9_-]+/?(?:\?.*)?$",
    re.IGNORECASE,
)
INSTAGRAM_SHORTCODE_FROM_PATH = re.compile(r"/(?:reel|reels|p)/([A-Za-z0-9_-]+)")

SubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]


class YtDlpDownloader(DownloaderProvider):
    """Download Instagram reels/posts via yt-dlp."""

    def __init__(
        self,
        *,
        ytdlp_executable: str = "yt-dlp",
        cookies_file: str | Path | None = None,
        cookies_from_browser: str | None = None,
        save_metadata: bool = True,
        metadata_dir: Path | None = None,
        run_command: SubprocessRunner | None = None,
    ) -> None:
        self._ytdlp_executable = ytdlp_executable
        self._cookies_file = Path(cookies_file) if cookies_file else None
        self._cookies_from_browser = cookies_from_browser
        self._save_metadata = save_metadata
        self._metadata_dir = metadata_dir
        self._run_command = run_command or subprocess.run

    def _cookie_args(self) -> list[str]:
        if self._cookies_file is not None:
            return ["--cookies", str(self._cookies_file)]
        if self._cookies_from_browser:
            return ["--cookies-from-browser", self._cookies_from_browser]
        return []

    def validate_url(self, url: str) -> bool:
        normalized = url.strip()
        if not normalized:
            return False
        return bool(
            INSTAGRAM_REEL_PATTERN.match(normalized)
            or INSTAGRAM_POST_PATTERN.match(normalized)
            or INSTAGRAM_REELS_PATTERN.match(normalized)
        )

    def download(self, url: str, output_dir: Path) -> DownloadResult:
        if not self.validate_url(url):
            raise ValueError(f"Unsupported Instagram URL: {url}")

        output_dir.mkdir(parents=True, exist_ok=True)
        reel_id = self.reel_id_from_url(url)
        output_template = str(output_dir / f"{reel_id}.%(ext)s")
        info_json_path = output_dir / f"{reel_id}.info.json"

        completed = self._run_ytdlp(
            [
                self._ytdlp_executable,
                *self._cookie_args(),
                "--no-playlist",
                "--no-warnings",
                "-o",
                output_template,
                "--write-info-json",
                "--write-comments",
                "--print",
                "filepath",
                url,
            ]
        )

        if completed.returncode != 0:
            raise RuntimeError(
                f"yt-dlp failed for {url}: {completed.stderr.strip() or completed.stdout.strip()}"
            )

        lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        video_path = self.find_existing_video(output_dir, reel_id)
        if video_path is None and lines:
            candidate = Path(lines[-1])
            if candidate.is_file():
                video_path = candidate
        if video_path is None:
            raise RuntimeError(f"yt-dlp download completed but no video file found for {url}")

        video_metadata: VideoMetadata | None = None
        metadata_path: Path | None = None
        if self._save_metadata:
            video_metadata, metadata_path = self._save_video_metadata(
                url=url,
                reel_id=reel_id,
                output_dir=output_dir,
                info_json_path=info_json_path,
            )

        metadata: dict[str, Any] = {
            "filename": video_path.name,
            "id": reel_id,
            "downloaded_at": datetime.now(UTC).isoformat(),
        }
        if video_metadata is not None:
            metadata["title"] = video_metadata.title
            metadata["author"] = video_metadata.author
            metadata["author_username"] = video_metadata.author_username
            metadata["caption"] = video_metadata.caption
            metadata["comment_count"] = video_metadata.comment_count
            if metadata_path is not None:
                metadata["metadata_path"] = str(metadata_path)

        return DownloadResult(
            video_path=video_path,
            metadata=metadata,
            source_url=url,
            title=video_metadata.title if video_metadata else metadata.get("title"),
            reel_id=reel_id,
        )

    def download_batch(
        self,
        urls: Sequence[str],
        output_dir: Path,
        limit: int = 50,
    ) -> list[DownloadResult]:
        capped_limit = max(1, min(limit, 50))
        selected_urls = list(urls[:capped_limit])
        results: list[DownloadResult] = []

        total = len(selected_urls)
        for index, url in enumerate(selected_urls, start=1):
            normalized = url.strip()
            if not normalized:
                continue

            if not self.validate_url(normalized):
                logger.warning("Skipping unsupported URL (%s/%s): %s", index, total, normalized)
                continue

            reel_id = self.reel_id_from_url(normalized)
            existing = self.find_existing_video(output_dir, reel_id)
            if existing is not None:
                logger.info(
                    "Skipping existing download (%s/%s): %s -> %s",
                    index,
                    total,
                    normalized,
                    existing,
                )
                results.append(
                    DownloadResult(
                        video_path=existing,
                        metadata={"skipped": True, "id": reel_id},
                        source_url=normalized,
                        title=None,
                        reel_id=reel_id,
                    )
                )
                continue

            logger.info("Downloading (%s/%s): %s", index, total, normalized)
            try:
                result = self.download(normalized, output_dir)
            except Exception as exc:  # noqa: BLE001 - batch continues on per-URL failure
                logger.error("Download failed (%s/%s): %s — %s", index, total, normalized, exc)
                continue

            results.append(result)
            logger.info(
                "Downloaded (%s/%s): %s -> %s",
                index,
                total,
                normalized,
                result.video_path,
            )

        return results

    def extract_urls_from_page(self, hub_url: str, limit: int = 50) -> list[str]:
        capped_limit = max(1, min(limit, 50))
        hub = hub_url.strip()
        if not hub:
            return []

        completed = self._run_ytdlp(
            [
                self._ytdlp_executable,
                *self._cookie_args(),
                "--flat-playlist",
                "-j",
                "--no-warnings",
                hub,
            ]
        )

        if completed.returncode != 0:
            logger.warning(
                "Could not extract URLs from hub page via yt-dlp (%s). "
                "Instagram hub pages often do not expose reel URLs through --flat-playlist. "
                "Provide a URLs file with --urls-file instead.",
                completed.stderr.strip() or completed.stdout.strip() or hub,
            )
            return []

        urls: list[str] = []
        seen: set[str] = set()

        for line in completed.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                logger.debug("Skipping non-JSON yt-dlp line: %s", line)
                continue

            candidate = self._entry_url(entry)
            if not candidate or candidate in seen:
                continue
            if not self.validate_url(candidate):
                continue

            seen.add(candidate)
            urls.append(candidate)
            if len(urls) >= capped_limit:
                break

        if len(urls) < capped_limit:
            logger.warning(
                "Hub page yielded %s/%s Instagram reel/post URLs. "
                "Instagram hub pages may not expose all reels via yt-dlp. "
                "Use --urls-file with a plain-text list (one URL per line) to reach the limit.",
                len(urls),
                capped_limit,
            )

        return urls

    def fetch_metadata(self, url: str, output_dir: Path) -> VideoMetadata:
        """Fetch metadata only (no video download) for an existing or new URL."""
        if not self.validate_url(url):
            raise ValueError(f"Unsupported Instagram URL: {url}")

        reel_id = self.reel_id_from_url(url)
        completed = self._run_ytdlp(
            [
                self._ytdlp_executable,
                *self._cookie_args(),
                "--no-download",
                "--write-comments",
                "--dump-single-json",
                "--no-warnings",
                url,
            ]
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"yt-dlp metadata fetch failed for {url}: "
                f"{completed.stderr.strip() or completed.stdout.strip()}"
            )
        info = json.loads(completed.stdout)
        video_metadata = VideoMetadata.from_ytdlp_info(info, source_url=url, reel_id=reel_id)
        metadata_dir = self._resolve_metadata_dir(output_dir)
        metadata_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = metadata_dir / f"{reel_id}.json"
        metadata_path.write_text(video_metadata.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return video_metadata

    def _save_video_metadata(
        self,
        *,
        url: str,
        reel_id: str,
        output_dir: Path,
        info_json_path: Path,
    ) -> tuple[VideoMetadata | None, Path | None]:
        info: dict[str, Any] | None = None
        if info_json_path.is_file():
            try:
                info = json.loads(info_json_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning("Could not parse yt-dlp info json: %s", info_json_path)

        if info is None:
            try:
                return self.fetch_metadata(url, output_dir), None
            except Exception as exc:  # noqa: BLE001
                logger.warning("Metadata fetch failed for %s: %s", url, exc)
                return None, None

        video_metadata = VideoMetadata.from_ytdlp_info(info, source_url=url, reel_id=reel_id)
        metadata_dir = self._resolve_metadata_dir(output_dir)
        metadata_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = metadata_dir / f"{reel_id}.json"
        metadata_path.write_text(video_metadata.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return video_metadata, metadata_path

    def _resolve_metadata_dir(self, output_dir: Path) -> Path:
        if self._metadata_dir is not None:
            return self._metadata_dir
        return output_dir.parent / "metadata"

    def _run_ytdlp(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        return self._run_command(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

    @staticmethod
    def reel_id_from_url(url: str) -> str:
        parsed = urlparse(url.strip())
        match = INSTAGRAM_SHORTCODE_FROM_PATH.search(parsed.path)
        if match:
            return match.group(1)

        digest = hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:16]
        return f"url_{digest}"

    @staticmethod
    def _entry_url(entry: dict[str, Any]) -> str | None:
        for key in ("url", "webpage_url", "original_url"):
            value = entry.get(key)
            if isinstance(value, str) and value.startswith("http"):
                return value

        entry_id = entry.get("id")
        if isinstance(entry_id, str) and entry_id:
            return f"https://www.instagram.com/reel/{entry_id}/"

        return None

    @staticmethod
    def find_existing_video(output_dir: Path, reel_id: str) -> Path | None:
        if not output_dir.exists():
            return None

        for extension in (".mp4", ".mkv", ".webm", ".mov"):
            candidate = output_dir / f"{reel_id}{extension}"
            if candidate.exists():
                return candidate
        return None
