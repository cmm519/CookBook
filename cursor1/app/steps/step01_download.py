"""Step 1: Download video + metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import load_config
from app.downloader import YtDlpDownloader
from app.steps.base import PipelineStep


class DownloadStep(PipelineStep):
    name = "download"
    step_number = 1
    requires: list[int] = []

    def execute(self, context) -> tuple[dict[str, Any], dict[str, Any]]:
        config = load_config()
        output_dir = context.working_dir / "raw"
        output_dir.mkdir(parents=True, exist_ok=True)
        downloader = YtDlpDownloader(
            cookies_file=config.ytdlp_cookies_file,
            cookies_from_browser=config.ytdlp_cookies_from_browser,
            save_metadata=config.save_metadata,
        )
        result = downloader.download(context.source_url, output_dir)

        # YtDlpDownloader already parses the real yt-dlp info.json into a
        # VideoMetadata and writes it to result.metadata["metadata_path"].
        # Read that back rather than re-deriving metadata here: result.metadata
        # itself is an already-flattened summary dict (different key shape
        # than raw yt-dlp info), so feeding it through from_ytdlp_info() again
        # silently nulls out caption/author/etc.
        metadata_path_str = result.metadata.get("metadata_path")
        metadata_path = Path(metadata_path_str) if metadata_path_str else None

        artifacts = {
            "video_path": str(result.video_path),
            "reel_id": result.reel_id,
            "metadata_path": metadata_path_str,
        }
        if metadata_path and metadata_path.is_file():
            artifacts["metadata"] = json.loads(metadata_path.read_text(encoding="utf-8"))
        return artifacts, {"bytes": Path(result.video_path).stat().st_size}
