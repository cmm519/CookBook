"""Batch download command."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from app.config import CookBookConfig, load_config
from app.downloader import DownloadResult, YtDlpDownloader

logger = logging.getLogger(__name__)


class ManifestEntry(BaseModel):
    """One row in dataset/manifest.json."""

    id: str
    source_url: str
    video_path: str | None = None
    title: str | None = None
    author: str | None = None
    author_username: str | None = None
    caption: str | None = None
    comment_count: int | None = None
    metadata_path: str | None = None
    downloaded_at: str
    status: str = "success"
    error: str | None = None


class DownloadFailure(BaseModel):
    """Per-URL failure captured during batch download."""

    source_url: str
    error: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch-download Instagram reels via yt-dlp.")
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--source-url",
        help="Instagram hub/profile URL to resolve reel URLs from.",
    )
    source_group.add_argument(
        "--urls-file",
        type=Path,
        help="Plain-text file with one Instagram reel/post URL per line.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of URLs to process (default: 50, hard cap: 50).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory for raw videos (default: /data/dataset/raw).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Manifest path (default: /data/dataset/manifest.json).",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Fetch title, author, caption, and comments without re-downloading video.",
    )
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Skip saving metadata sidecar files.",
    )
    return parser


def read_urls_file(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"URLs file not found: {path}")

    urls: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            urls.append(stripped)
    return urls


def resolve_urls(
    downloader: YtDlpDownloader,
    *,
    source_url: str | None,
    urls_file: Path | None,
    fallback_urls_file: Path | None,
    limit: int,
) -> list[str]:
    capped_limit = max(1, min(limit, 50))

    if urls_file is not None:
        urls = read_urls_file(urls_file)
        if len(urls) > capped_limit:
            logger.warning(
                "URLs file contains %s entries; processing only the first %s.",
                len(urls),
                capped_limit,
            )
        return urls[:capped_limit]

    assert source_url is not None
    urls = downloader.extract_urls_from_page(source_url, limit=capped_limit)
    if urls:
        return urls

    if fallback_urls_file is not None and fallback_urls_file.exists():
        logger.warning(
            "Hub page yielded no URLs (%s). Falling back to %s",
            source_url,
            fallback_urls_file,
        )
        urls = read_urls_file(fallback_urls_file)
        return urls[:capped_limit]

    logger.error(
        "No reel/post URLs extracted from hub page: %s. "
        "Add URLs to %s or pass --urls-file.",
        source_url,
        fallback_urls_file or "a urls file",
    )
    return []


def results_to_manifest_entries(
    results: list[DownloadResult],
    failures: list[DownloadFailure],
) -> list[ManifestEntry]:
    entries: list[ManifestEntry] = []
    timestamp = datetime.now(UTC).isoformat()

    for result in results:
        entries.append(
            ManifestEntry(
                id=result.reel_id or result.video_path.stem,
                source_url=result.source_url,
                video_path=str(result.video_path),
                title=result.title or result.metadata.get("title"),
                author=result.metadata.get("author"),
                author_username=result.metadata.get("author_username"),
                caption=result.metadata.get("caption"),
                comment_count=result.metadata.get("comment_count"),
                metadata_path=result.metadata.get("metadata_path"),
                downloaded_at=str(result.metadata.get("downloaded_at", timestamp)),
                status="skipped" if result.metadata.get("skipped") else "success",
            )
        )

    for failure in failures:
        entries.append(
            ManifestEntry(
                id=YtDlpDownloader.reel_id_from_url(failure.source_url),
                source_url=failure.source_url,
                video_path=None,
                title=None,
                downloaded_at=timestamp,
                status="failed",
                error=failure.error,
            )
        )

    return entries


def write_manifest(path: Path, entries: list[ManifestEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [entry.model_dump(exclude_none=True) for entry in entries]
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def download_with_failures(
    downloader: YtDlpDownloader,
    urls: list[str],
    output_dir: Path,
    limit: int,
) -> tuple[list[DownloadResult], list[DownloadFailure]]:
    capped_limit = max(1, min(limit, 50))
    selected_urls = urls[:capped_limit]
    results: list[DownloadResult] = []
    failures: list[DownloadFailure] = []

    total = len(selected_urls)
    for index, url in enumerate(selected_urls, start=1):
        normalized = url.strip()
        if not normalized:
            continue

        if not downloader.validate_url(normalized):
            message = f"Unsupported Instagram URL: {normalized}"
            logger.warning("Skipping (%s/%s): %s", index, total, message)
            failures.append(DownloadFailure(source_url=normalized, error=message))
            continue

        reel_id = YtDlpDownloader.reel_id_from_url(normalized)
        existing = YtDlpDownloader.find_existing_video(output_dir, reel_id)
        if existing is not None:
            logger.info("Skipping existing (%s/%s): %s", index, total, normalized)
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
            result = downloader.download(normalized, output_dir)
        except Exception as exc:  # noqa: BLE001 - continue batch on per-URL errors
            message = str(exc)
            logger.error("Failed (%s/%s): %s — %s", index, total, normalized, message)
            failures.append(DownloadFailure(source_url=normalized, error=message))
            continue

        results.append(result)
        logger.info("Downloaded (%s/%s): %s", index, total, result.video_path)

    return results, failures


def run_download(args: argparse.Namespace) -> int:
    config = load_config()
    output_dir = args.output or config.dataset_raw_dir
    manifest_path = args.manifest or config.dataset_manifest_path
    limit = max(1, min(args.limit or config.download_limit, 50))

    downloader = YtDlpDownloader(
        cookies_file=config.ytdlp_cookies_file,
        cookies_from_browser=config.ytdlp_cookies_from_browser,
        save_metadata=not args.no_metadata,
        metadata_dir=config.dataset_metadata_dir,
    )
    urls = resolve_urls(
        downloader,
        source_url=args.source_url,
        urls_file=args.urls_file,
        fallback_urls_file=config.dataset_urls_file,
        limit=limit,
    )
    if not urls:
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    if args.metadata_only:
        return _run_metadata_only(downloader, urls, output_dir, manifest_path, limit, config)

    results, failures = download_with_failures(downloader, urls, output_dir, limit)
    entries = results_to_manifest_entries(results, failures)
    write_manifest(manifest_path, entries)

    logger.info(
        "Download complete: %s succeeded/skipped, %s failed. Manifest: %s",
        len(results),
        len(failures),
        manifest_path,
    )
    return 0 if results or not failures else 1


def _run_metadata_only(
    downloader: YtDlpDownloader,
    urls: list[str],
    output_dir: Path,
    manifest_path: Path,
    limit: int,
    config: CookBookConfig,
) -> int:
    """Fetch metadata for URLs without downloading video."""
    capped = urls[: max(1, min(limit, 50))]
    entries: list[ManifestEntry] = []
    timestamp = datetime.now(UTC).isoformat()
    failures = 0

    for index, url in enumerate(capped, start=1):
        normalized = url.strip()
        if not normalized or not downloader.validate_url(normalized):
            continue
        reel_id = YtDlpDownloader.reel_id_from_url(normalized)
        logger.info("Fetching metadata (%s/%s): %s", index, len(capped), normalized)
        try:
            meta = downloader.fetch_metadata(normalized, output_dir)
            metadata_path = config.dataset_metadata_dir / f"{reel_id}.json"
            entries.append(
                ManifestEntry(
                    id=reel_id,
                    source_url=normalized,
                    video_path=str(output_dir / f"{reel_id}.mp4")
                    if (output_dir / f"{reel_id}.mp4").is_file()
                    else None,
                    title=meta.title,
                    author=meta.author,
                    author_username=meta.author_username,
                    caption=meta.caption,
                    comment_count=meta.comment_count,
                    metadata_path=str(metadata_path),
                    downloaded_at=timestamp,
                    status="metadata_only",
                )
            )
        except Exception as exc:  # noqa: BLE001
            failures += 1
            logger.error("Metadata failed (%s/%s): %s — %s", index, len(capped), normalized, exc)
            entries.append(
                ManifestEntry(
                    id=reel_id,
                    source_url=normalized,
                    downloaded_at=timestamp,
                    status="failed",
                    error=str(exc),
                )
            )

    write_manifest(manifest_path, entries)
    logger.info("Metadata fetch complete: %s ok, %s failed", len(entries) - failures, failures)
    return 0 if failures == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    return run_download(args)


if __name__ == "__main__":
    sys.exit(main())
