"""Downloader unit tests (no live network)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.cli.download import (
    ManifestEntry,
    download_with_failures,
    read_urls_file,
    results_to_manifest_entries,
    resolve_urls,
    write_manifest,
)
from app.downloader import YtDlpDownloader


@pytest.fixture
def downloader() -> YtDlpDownloader:
    return YtDlpDownloader()


class TestValidateUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.instagram.com/reel/ABC123/",
            "https://instagram.com/reel/ABC123",
            "https://www.instagram.com/p/XYZ789/?utm_source=ig",
            "https://www.instagram.com/reels/SHORT1/",
        ],
    )
    def test_accepts_instagram_reel_and_post_urls(self, downloader: YtDlpDownloader, url: str) -> None:
        assert downloader.validate_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "",
            "https://example.com/video",
            "https://www.instagram.com/username/",
            "not-a-url",
        ],
    )
    def test_rejects_unsupported_urls(self, downloader: YtDlpDownloader, url: str) -> None:
        assert downloader.validate_url(url) is False


class TestExtractUrlsFromPage:
    def test_parses_flat_playlist_json_lines(self, tmp_path: Path) -> None:
        playlist_output = "\n".join(
            [
                json.dumps({"url": "https://www.instagram.com/reel/AAA111/"}),
                json.dumps({"webpage_url": "https://www.instagram.com/p/BBB222/"}),
                json.dumps({"id": "CCC333"}),
            ]
        )

        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            assert "--flat-playlist" in command
            return subprocess.CompletedProcess(command, 0, playlist_output, "")

        downloader = YtDlpDownloader(run_command=fake_run)
        urls = downloader.extract_urls_from_page("https://www.instagram.com/somehub/", limit=50)

        assert urls == [
            "https://www.instagram.com/reel/AAA111/",
            "https://www.instagram.com/p/BBB222/",
            "https://www.instagram.com/reel/CCC333/",
        ]

    def test_returns_empty_and_logs_when_flat_playlist_fails(self, caplog: pytest.LogCaptureFixture) -> None:
        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 1, "", "Unsupported URL")

        downloader = YtDlpDownloader(run_command=fake_run)

        with caplog.at_level("WARNING"):
            urls = downloader.extract_urls_from_page("https://www.instagram.com/hub/", limit=50)

        assert urls == []
        assert any("--urls-file" in record.message for record in caplog.records)

    def test_warns_when_hub_yields_fewer_than_limit(self, caplog: pytest.LogCaptureFixture) -> None:
        playlist_output = json.dumps({"url": "https://www.instagram.com/reel/ONLY1/"})

        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 0, playlist_output, "")

        downloader = YtDlpDownloader(run_command=fake_run)

        with caplog.at_level("WARNING"):
            urls = downloader.extract_urls_from_page("https://www.instagram.com/hub/", limit=50)

        assert len(urls) == 1
        assert any("Hub page yielded 1/50" in record.message for record in caplog.records)


class TestDownload:
    def test_download_parses_ytdlp_output(self, tmp_path: Path) -> None:
        video_path = tmp_path / "ABC123.mp4"
        video_path.write_bytes(b"fake-video")

        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            stdout = str(video_path)
            return subprocess.CompletedProcess(command, 0, stdout, "")

        downloader = YtDlpDownloader(run_command=fake_run)
        result = downloader.download("https://www.instagram.com/reel/ABC123/", tmp_path)

        assert result.video_path == video_path
        assert result.reel_id == "ABC123"
        assert result.reel_id == "ABC123"
        assert result.metadata["filename"] == "ABC123.mp4"

    def test_download_raises_for_invalid_url(self, tmp_path: Path) -> None:
        downloader = YtDlpDownloader()
        with pytest.raises(ValueError, match="Unsupported Instagram URL"):
            downloader.download("https://example.com/not-instagram", tmp_path)


class TestDownloadBatch:
    def test_skips_existing_files(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        existing = tmp_path / "EXIST1.mp4"
        existing.write_bytes(b"already-there")

        run_mock = MagicMock()
        downloader = YtDlpDownloader(run_command=run_mock)

        with caplog.at_level("INFO"):
            results = downloader.download_batch(
                ["https://www.instagram.com/reel/EXIST1/"],
                tmp_path,
                limit=50,
            )

        assert len(results) == 1
        assert results[0].video_path == existing
        run_mock.assert_not_called()


class TestCliManifest:
    def test_read_urls_file_skips_comments_and_blank_lines(self, tmp_path: Path) -> None:
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text(
            "\n".join(
                [
                    "# comment",
                    "https://www.instagram.com/reel/ONE/",
                    "",
                    "https://www.instagram.com/p/TWO/",
                ]
            ),
            encoding="utf-8",
        )

        assert read_urls_file(urls_file) == [
            "https://www.instagram.com/reel/ONE/",
            "https://www.instagram.com/p/TWO/",
        ]

    def test_write_manifest_creates_json_entries(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "manifest.json"
        entries = [
            ManifestEntry(
                id="ABC123",
                source_url="https://www.instagram.com/reel/ABC123/",
                video_path=str(tmp_path / "ABC123.mp4"),
                title="My Reel",
                downloaded_at="2026-08-30T12:00:00+00:00",
            )
        ]

        write_manifest(manifest_path, entries)

        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert loaded == [
            {
                "id": "ABC123",
                "source_url": "https://www.instagram.com/reel/ABC123/",
                "video_path": str(tmp_path / "ABC123.mp4"),
                "title": "My Reel",
                "downloaded_at": "2026-08-30T12:00:00+00:00",
                "status": "success",
            }
        ]

    def test_results_to_manifest_includes_failures(self) -> None:
        from app.cli.download import DownloadFailure
        from app.downloader.provider import DownloadResult

        results = [
            DownloadResult(
                video_path=Path("/data/dataset/raw/GOOD.mp4"),
                metadata={"downloaded_at": "2026-08-30T12:00:00+00:00"},
                source_url="https://www.instagram.com/reel/GOOD/",
                title="Good",
                reel_id="GOOD",
            )
        ]
        failures = [
            DownloadFailure(
                source_url="https://www.instagram.com/reel/BAD/",
                error="rate limited",
            )
        ]

        entries = results_to_manifest_entries(results, failures)
        assert len(entries) == 2
        assert entries[0].status == "success"
        assert entries[1].status == "failed"
        assert entries[1].error == "rate limited"
        assert entries[1].video_path is None

    def test_resolve_urls_prefers_urls_file(self, tmp_path: Path) -> None:
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://www.instagram.com/reel/FILE1/\n", encoding="utf-8")

        downloader = YtDlpDownloader()
        urls = resolve_urls(
            downloader,
            source_url=None,
            urls_file=urls_file,
            fallback_urls_file=None,
            limit=50,
        )
        assert urls == ["https://www.instagram.com/reel/FILE1/"]

    def test_download_with_failures_records_per_url_errors(self, tmp_path: Path) -> None:
        call_count = {"value": 0}

        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            call_count["value"] += 1
            if "flat-playlist" in command:
                return subprocess.CompletedProcess(command, 0, "", "")
            return subprocess.CompletedProcess(command, 1, "", "network error")

        downloader = YtDlpDownloader(run_command=fake_run)
        urls = [
            "https://www.instagram.com/reel/OK1/",
            "https://example.com/not-instagram",
        ]

        results, failures = download_with_failures(downloader, urls, tmp_path, limit=50)

        assert results == []
        assert len(failures) == 2
        assert "network error" in failures[0].error
        assert "Unsupported Instagram URL" in failures[1].error
