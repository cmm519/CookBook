"""CookBook CLI — download and transcribe subcommands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.cli.download import run_download
from app.config import load_config


def cmd_download(args: argparse.Namespace) -> int:
    import logging

    config = load_config()
    if args.limit is None:
        args.limit = config.download_limit
    if args.output is None:
        args.output = config.dataset_raw_dir
    if args.manifest is None:
        args.manifest = config.dataset_manifest_path

    if not args.source_url and not args.urls_file and config.download_source_url:
        args.source_url = config.download_source_url

    if args.source_url or args.urls_file:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        return run_download(args)

    print(
        "download: provide --source-url, --urls-file, or set DOWNLOAD_SOURCE_URL",
        file=sys.stderr,
    )
    return 1


def cmd_transcribe(args: argparse.Namespace) -> int:
    from app.cli.transcribe import run_batch_transcribe

    try:
        summary = run_batch_transcribe(force=args.force)
    except FileNotFoundError as exc:
        print(f"transcribe: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(summary.as_dict(), indent=2))
    return 1 if summary.failed_count else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    download_parser = subparsers.add_parser("download", help="Batch-fetch videos into dataset/raw/")
    source_group = download_parser.add_mutually_exclusive_group(required=False)
    source_group.add_argument("--source-url", help="Instagram hub/profile URL.")
    source_group.add_argument("--urls-file", type=Path, help="File with one URL per line.")
    download_parser.add_argument("--limit", type=int, default=None, help="Max URLs (default: 50).")
    download_parser.add_argument("--output", type=Path, default=None, help="Raw video output dir.")
    download_parser.add_argument("--manifest", type=Path, default=None, help="Manifest JSON path.")
    download_parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Fetch metadata without re-downloading videos.",
    )
    download_parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Skip saving metadata sidecar files.",
    )
    download_parser.set_defaults(func=cmd_download)

    transcribe_parser = subparsers.add_parser(
        "transcribe",
        help="Batch-transcribe videos in dataset/raw/",
    )
    transcribe_parser.add_argument(
        "--force",
        action="store_true",
        help="Re-transcribe videos even when transcript files already exist",
    )
    transcribe_parser.set_defaults(func=cmd_transcribe)

    import_parser = subparsers.add_parser("import", help="Run full import pipeline for one URL")
    import_parser.add_argument("source_url", help="Instagram reel URL")
    import_parser.add_argument("--no-video-processing", action="store_true")
    import_parser.add_argument("--user-comment", default=None)
    import_parser.add_argument("--custom-instruction", default=None)
    import_parser.set_defaults(func=cmd_import)

    args = parser.parse_args(argv)
    return args.func(args)


def cmd_import(args: argparse.Namespace) -> int:
    from app.cli.import_cmd import run_import

    try:
        job, slug = run_import(
            args.source_url,
            user_comment=args.user_comment,
            custom_instruction=args.custom_instruction,
            video_processing_enabled=not args.no_video_processing,
        )
    except Exception as exc:
        print(f"import failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"job_id": job.job_id, "status": job.status, "slug": slug}, indent=2))
    return 0 if job.status.value == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
