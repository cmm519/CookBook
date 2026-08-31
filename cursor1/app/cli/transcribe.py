"""Batch transcription for dataset videos."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import CookBookConfig, load_config
from app.transcription.provider import TranscriptResult
from app.transcription.whisper import FasterWhisperTranscription

_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v", ".mpeg", ".mpg"}


class TranscribeSummary:
    """Aggregate result from a batch transcription run."""

    def __init__(self) -> None:
        self.transcribed: list[dict[str, str]] = []
        self.skipped: list[str] = []
        self.failed: list[dict[str, str]] = []

    @property
    def transcribed_count(self) -> int:
        return len(self.transcribed)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped)

    @property
    def failed_count(self) -> int:
        return len(self.failed)

    def as_dict(self) -> dict[str, Any]:
        return {
            "transcribed_count": self.transcribed_count,
            "skipped_count": self.skipped_count,
            "failed_count": self.failed_count,
            "transcribed": self.transcribed,
            "skipped": self.skipped,
            "failed": self.failed,
        }


def _dataset_transcripts_dir(config: CookBookConfig) -> Path:
    return config.dataset_raw_dir.parent / "transcripts"


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.is_file():
        return {"entries": []}
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"entries": data}
    if isinstance(data, dict) and isinstance(data.get("entries"), list):
        return data
    raise ValueError(f"Invalid manifest format: {manifest_path}")


def _save_manifest(manifest_path: Path, manifest: dict[str, Any]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _entry_reel_id(entry: dict[str, Any]) -> str | None:
    reel_id = entry.get("reel_id") or entry.get("id")
    if isinstance(reel_id, str) and reel_id:
        if "/" in reel_id or reel_id.endswith(".mp4"):
            return Path(reel_id).stem
        return reel_id
    filename = entry.get("filename")
    if isinstance(filename, str) and filename:
        return Path(filename).stem
    video_path = entry.get("video_path")
    if isinstance(video_path, str) and video_path:
        return Path(video_path).stem
    return None


def _resolve_video_path(raw_dir: Path, entry: dict[str, Any]) -> Path | None:
    video_path = entry.get("video_path")
    if isinstance(video_path, str) and video_path:
        candidate = Path(video_path)
        if candidate.is_file():
            return candidate
        candidate = raw_dir / Path(video_path).name
        if candidate.is_file():
            return candidate

    filename = entry.get("filename")
    if isinstance(filename, str) and filename:
        candidate = raw_dir / filename
        if candidate.is_file():
            return candidate

    reel_id = _entry_reel_id(entry)
    if reel_id:
        for ext in _VIDEO_EXTENSIONS:
            candidate = raw_dir / f"{reel_id}{ext}"
            if candidate.is_file():
                return candidate
    return None


def _collect_videos_from_manifest(raw_dir: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for entry in manifest.get("entries", []):
        if not isinstance(entry, dict):
            continue
        video_path = _resolve_video_path(raw_dir, entry)
        if video_path is None:
            continue
        reel_id = _entry_reel_id(entry) or video_path.stem
        items.append({"entry": entry, "video_path": video_path, "reel_id": reel_id})
    return items


def _collect_videos_from_raw(raw_dir: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not raw_dir.is_dir():
        return items
    for video_path in sorted(raw_dir.iterdir()):
        if not video_path.is_file():
            continue
        if video_path.suffix.lower() not in _VIDEO_EXTENSIONS:
            continue
        reel_id = video_path.stem
        items.append(
            {
                "entry": {"reel_id": reel_id, "filename": video_path.name},
                "video_path": video_path,
                "reel_id": reel_id,
            }
        )
    return items


def _find_manifest_entry(manifest: dict[str, Any], reel_id: str) -> dict[str, Any] | None:
    for entry in manifest.get("entries", []):
        if isinstance(entry, dict) and _entry_reel_id(entry) == reel_id:
            return entry
    return None


def _ensure_manifest_entry(manifest: dict[str, Any], reel_id: str, filename: str) -> dict[str, Any]:
    entry = _find_manifest_entry(manifest, reel_id)
    if entry is None:
        entry = {"reel_id": reel_id, "filename": filename}
        manifest.setdefault("entries", []).append(entry)
    return entry


def _already_transcribed(transcripts_dir: Path, reel_id: str) -> bool:
    return (transcripts_dir / f"{reel_id}.txt").is_file() and (
        transcripts_dir / f"{reel_id}.json"
    ).is_file()


def _write_transcript_outputs(
    transcripts_dir: Path,
    reel_id: str,
    result: TranscriptResult,
) -> tuple[Path, Path]:
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    txt_path = transcripts_dir / f"{reel_id}.txt"
    json_path = transcripts_dir / f"{reel_id}.json"
    txt_path.write_text(result.text + "\n", encoding="utf-8")
    json_path.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return txt_path, json_path


def run_batch_transcribe(
    *,
    config: CookBookConfig | None = None,
    force: bool = False,
    provider: Any | None = None,
) -> TranscribeSummary:
    """Transcribe dataset videos and update manifest metadata."""
    config = config or load_config()
    raw_dir = config.dataset_raw_dir
    transcripts_dir = _dataset_transcripts_dir(config)
    manifest_path = config.dataset_manifest_path
    summary = TranscribeSummary()

    if not raw_dir.is_dir():
        raise FileNotFoundError(f"Dataset raw directory not found: {raw_dir}")

    manifest = _load_manifest(manifest_path)
    if manifest.get("entries"):
        items = _collect_videos_from_manifest(raw_dir, manifest)
    else:
        items = _collect_videos_from_raw(raw_dir)

    if not items:
        raise FileNotFoundError(f"No video files found in {raw_dir}")

    transcriber = provider or FasterWhisperTranscription(
        model=config.whisper_model,
        device=config.whisper_device,
    )

    for item in items:
        reel_id = item["reel_id"]
        video_path: Path = item["video_path"]
        entry = _ensure_manifest_entry(manifest, reel_id, video_path.name)

        if not force and _already_transcribed(transcripts_dir, reel_id):
            summary.skipped.append(reel_id)
            continue

        try:
            result = transcriber.transcribe(video_path)
            txt_path, json_path = _write_transcript_outputs(transcripts_dir, reel_id, result)
            transcribed_at = datetime.now(UTC).isoformat()
            entry["transcript_path"] = str(txt_path)
            entry["transcript_json_path"] = str(json_path)
            entry["transcribed_at"] = transcribed_at
            entry["transcript_status"] = "completed"
            entry.pop("transcript_error", None)
            summary.transcribed.append(
                {
                    "reel_id": reel_id,
                    "transcript_path": str(txt_path),
                    "transcript_json_path": str(json_path),
                }
            )
        except Exception as exc:
            entry["transcript_status"] = "failed"
            entry["transcript_error"] = str(exc)
            summary.failed.append({"reel_id": reel_id, "error": str(exc)})

    _save_manifest(manifest_path, manifest)
    return summary
