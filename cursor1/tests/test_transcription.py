"""Tests for transcription providers and batch CLI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.cli.transcribe import run_batch_transcribe
from app.config.settings import CookBookConfig
from app.transcription.provider import TranscriptResult, TranscriptSegment
from app.transcription.whisper import FasterWhisperTranscription


class FakeTranscriber:
    def transcribe(self, audio_or_video_path: Path) -> TranscriptResult:
        return TranscriptResult(
            language="en",
            text="hello world",
            segments=[
                TranscriptSegment(start=0.0, end=1.2, text="hello"),
                TranscriptSegment(start=1.2, end=2.0, text="world"),
            ],
        )


def test_transcript_result_schema_roundtrip():
    result = TranscriptResult(
        language="en",
        text="hello world",
        segments=[TranscriptSegment(start=0.0, end=1.0, text="hello world")],
    )
    payload = json.loads(result.model_dump_json())
    assert payload["language"] == "en"
    assert payload["text"] == "hello world"
    assert payload["segments"][0] == {"start": 0.0, "end": 1.0, "text": "hello world"}


def test_batch_transcribe_from_raw_scan(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    transcripts_dir = tmp_path / "transcripts"
    manifest_path = tmp_path / "manifest.json"
    raw_dir.mkdir()
    video_path = raw_dir / "reel123.mp4"
    video_path.write_bytes(b"fake-video")

    config = CookBookConfig(
        _env_file=None,
        DATASET_RAW_DIR=str(raw_dir),
        DATASET_MANIFEST_PATH=str(manifest_path),
    )

    summary = run_batch_transcribe(config=config, provider=FakeTranscriber())

    assert summary.transcribed_count == 1
    assert summary.skipped_count == 0
    assert (transcripts_dir / "reel123.txt").read_text(encoding="utf-8").strip() == "hello world"
    transcript_json = json.loads((transcripts_dir / "reel123.json").read_text(encoding="utf-8"))
    assert transcript_json["language"] == "en"
    assert len(transcript_json["segments"]) == 2

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = manifest["entries"][0]
    assert entry["reel_id"] == "reel123"
    assert entry["transcript_path"] == str(transcripts_dir / "reel123.txt")
    assert entry["transcript_json_path"] == str(transcripts_dir / "reel123.json")
    assert entry["transcribed_at"]
    assert summary.transcribed[0]["transcript_path"] == entry["transcript_path"]


def test_batch_transcribe_skips_existing_unless_force(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    transcripts_dir = tmp_path / "transcripts"
    manifest_path = tmp_path / "manifest.json"
    raw_dir.mkdir()
    transcripts_dir.mkdir()
    (raw_dir / "reel123.mp4").write_bytes(b"fake-video")
    (transcripts_dir / "reel123.txt").write_text("existing\n", encoding="utf-8")
    (transcripts_dir / "reel123.json").write_text("{}", encoding="utf-8")

    config = CookBookConfig(
        _env_file=None,
        DATASET_RAW_DIR=str(raw_dir),
        DATASET_MANIFEST_PATH=str(manifest_path),
    )

    skipped = run_batch_transcribe(config=config, provider=FakeTranscriber())
    assert skipped.skipped_count == 1
    assert skipped.transcribed_count == 0

    forced = run_batch_transcribe(config=config, force=True, provider=FakeTranscriber())
    assert forced.transcribed_count == 1
    assert (transcripts_dir / "reel123.txt").read_text(encoding="utf-8").strip() == "hello world"


def test_batch_transcribe_updates_manifest_entry(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    transcripts_dir = tmp_path / "transcripts"
    manifest_path = tmp_path / "manifest.json"
    raw_dir.mkdir()
    (raw_dir / "abc.mp4").write_bytes(b"fake-video")
    manifest_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "url": "https://instagram.com/reel/abc",
                        "reel_id": "abc",
                        "filename": "abc.mp4",
                        "status": "downloaded",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    config = CookBookConfig(
        _env_file=None,
        DATASET_RAW_DIR=str(raw_dir),
        DATASET_MANIFEST_PATH=str(manifest_path),
    )

    summary = run_batch_transcribe(config=config, provider=FakeTranscriber())
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = manifest["entries"][0]

    assert summary.transcribed_count == 1
    assert entry["transcript_path"] == str(transcripts_dir / "abc.txt")
    assert entry["transcript_json_path"] == str(transcripts_dir / "abc.json")
    assert entry["transcribed_at"]
    assert entry["transcript_status"] == "completed"


@patch("app.transcription.whisper.subprocess.run")
@patch("app.transcription.whisper.WhisperModel")
def test_faster_whisper_transcribe_audio(mock_model_cls, mock_subprocess_run, tmp_path: Path):
    segment = MagicMock(start=0.0, end=1.5, text=" test ")
    info = MagicMock(language="en")
    mock_model = mock_model_cls.return_value
    mock_model.transcribe.return_value = ([segment], info)

    audio_path = tmp_path / "clip.wav"
    audio_path.write_bytes(b"fake-audio")

    provider = FasterWhisperTranscription(model="base", device="cpu")
    result = provider.transcribe(audio_path)

    mock_model_cls.assert_called_once_with("base", device="cpu", compute_type="int8")
    mock_model.transcribe.assert_called_once_with(str(audio_path))
    mock_subprocess_run.assert_not_called()
    assert result.language == "en"
    assert result.text == "test"
    assert result.segments[0].text == "test"


@patch("app.transcription.whisper.subprocess.run")
@patch("app.transcription.whisper.WhisperModel")
def test_faster_whisper_extracts_video_audio(mock_model_cls, mock_subprocess_run, tmp_path: Path):
    segment = MagicMock(start=0.0, end=2.0, text="from video")
    info = MagicMock(language="en")
    mock_model = mock_model_cls.return_value
    mock_model.transcribe.return_value = ([segment], info)

    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"fake-video")

    provider = FasterWhisperTranscription(model="base", device="cpu")
    result = provider.transcribe(video_path)

    assert mock_subprocess_run.call_count == 1
    ffmpeg_cmd = mock_subprocess_run.call_args.args[0]
    assert ffmpeg_cmd[0] == "ffmpeg"
    assert str(video_path) in ffmpeg_cmd
    assert "-ac" in ffmpeg_cmd and "1" in ffmpeg_cmd
    assert "-ar" in ffmpeg_cmd and "16000" in ffmpeg_cmd
    assert result.text == "from video"


def test_faster_whisper_rejects_invalid_device():
    with pytest.raises(ValueError, match="WHISPER_DEVICE"):
        FasterWhisperTranscription(model="base", device="tpu")
