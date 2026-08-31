"""Step 1: Download video + metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import load_config
from app.downloader import YtDlpDownloader
from app.downloader.metadata import VideoMetadata
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
        )
        result = downloader.download(context.source_url, output_dir)
        metadata_path = None
        if config.save_metadata and result.reel_id:
            meta_dir = context.working_dir / "metadata"
            meta_dir.mkdir(parents=True, exist_ok=True)
            metadata = VideoMetadata.from_ytdlp_info(
                result.metadata,
                source_url=context.source_url,
                reel_id=result.reel_id,
            )
            metadata_path = meta_dir / f"{result.reel_id}.json"
            metadata_path.write_text(metadata.model_dump_json(indent=2) + "\n", encoding="utf-8")

        artifacts = {
            "video_path": str(result.video_path),
            "reel_id": result.reel_id,
            "metadata_path": str(metadata_path) if metadata_path else None,
        }
        if metadata_path:
            artifacts["metadata"] = json.loads(metadata_path.read_text(encoding="utf-8"))
        return artifacts, {"bytes": Path(result.video_path).stat().st_size}
