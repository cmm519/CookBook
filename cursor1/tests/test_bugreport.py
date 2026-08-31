"""Tests for debug log writer."""

from pathlib import Path

from app.bugreport.debug_log import DebugLogWriter, save_bug_report
from app.models import LogLevel


def test_debug_log_writer(tmp_path: Path):
    writer = DebugLogWriter(tmp_path, job_id="job-1")
    writer.append(1, LogLevel.info, "Download started")
    assert writer.path.is_file()
    assert len(writer.debug_log.entries) == 1


def test_save_bug_report(tmp_path: Path):
    report = save_bug_report(
        tmp_path,
        description="Import failed",
        debug_log_path=str(tmp_path / "job-1" / "debug.log"),
    )
    assert report.report_id.startswith("bug-")
