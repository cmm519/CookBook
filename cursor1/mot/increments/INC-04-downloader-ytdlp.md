# INCREMENT 4: Downloader Interface + yt-dlp

**Status:** Standard  
**Dependencies:** INC-03 (Recipe package storage)

## Capability Specification

Formalize and verify the **existing** yt-dlp downloader implementation for Instagram reels/posts. After this increment, batch download (`MODE=download`) and single-URL download are production-ready, idempotent, manifest-aware, and aligned with Phase 0 dataset collection. This increment is primarily **documentation + gap closure + verification** — most code already exists.

**What changes:** Audit existing implementation; close any SRD gaps; ensure tests cover batch/manifest/metadata paths; optionally add `DownloadStep` stub in `app/steps/step01_download.py` (thin wrapper only — full orchestrator later).

**What must remain unchanged:**

- Phase 0 volume layout: `dataset/raw/`, `dataset/metadata/`, `dataset/manifest.json`
- Storage module (INC-03) — downloader writes to `dataset/`, not `recipes/`
- Transcription CLI — no changes in this increment

## Existing Implementation (document before editing)

| Component | Path | Role |
|---|---|---|
| Provider ABC | `app/downloader/provider.py` | `DownloaderProvider`, `DownloadResult` |
| yt-dlp backend | `app/downloader/ytdlp.py` | `YtDlpDownloader` — validate URL, download, batch, hub extract, metadata |
| Metadata model | `app/downloader/metadata.py` | `VideoMetadata`, `CommentEntry`, `from_ytdlp_info()` |
| Batch CLI | `app/cli/download.py` | `run_download()`, manifest read/write, `--metadata-only` |
| Entrypoint | `scripts/docker-entrypoint.sh` | `MODE=download` → `python -m app.cli download` |
| Tests | `tests/test_downloader.py`, `tests/test_metadata.py` | Mocked yt-dlp, no live network |

**Already implemented behaviors:**

- Instagram reel/post/reels URL validation
- Deterministic filename `{reel_id}.mp4` (extensions: mp4, mkv, webm, mov)
- Skip existing downloads (idempotent)
- Per-URL failure continues batch; failures recorded in manifest
- Metadata sidecar at `dataset/metadata/{reel_id}.json` (caption, comments)
- Hub URL extraction via `--flat-playlist` with fallback warning to `--urls-file`
- Hard cap `DOWNLOAD_LIMIT=50`
- Cookie support via `YTDLP_COOKIES_FILE` / `YTDLP_COOKIES_FROM_BROWSER`

## Implementation Instructions

1. **Gap audit** against SRD §5 `batch-download`:
   - Confirm manifest entry fields: `id`, `source_url`, `video_path`, `status`, `downloaded_at`, `error`, metadata fields
   - Confirm non-Instagram URLs logged and skipped (not fatal)
   - Confirm batch does **not** run ffmpeg, transcription, or recipe persistence

2. **Align models** with INC-02 (if complete):
   - Re-export or migrate `VideoMetadata` to `app/models/metadata.py`; keep `from_ytdlp_info()` factory

3. **Add `app/steps/step01_download.py`** (thin wrapper per SRD §10/§11):
   - `DownloadStep(PipelineStep)`: `step_number=1`, `requires=[]`
   - `run(context)` → calls `YtDlpDownloader.download()`, sets artifacts: `video_path`, `metadata_path`, `reel_id`
   - Output for import jobs: `working/{job_id}/` or `dataset/raw/` based on context flag — document choice in step docstring

4. **Add `app/steps/base.py`** if not present:
   - `PipelineStep` ABC, `StepContext`, `StepResult`, `StepPrerequisiteError`, `StepExecutionError` per SRD §11

5. **Extend tests** (no live network):
   - Metadata sidecar written on download when `.info.json` present
   - Manifest merge/update on re-run
   - `DownloadStep.run()` with mocked downloader

6. **Config keys** (already in `CookBookConfig`): `DOWNLOAD_LIMIT`, `DOWNLOAD_SOURCE_URL`, `DATASET_URLS_FILE`, cookie vars.

Reference: SRD §3 (DatasetVideoMetadata), §5 (`batch-download` operation), §10 (`downloader/` + `step01_download.py`), §11 (`DownloadStep`).

## Verification Protocol

**Quantitative success criteria** (from [`TRACKING_MATRIX.md`](../TRACKING_MATRIX.md)):

- [ ] **Download success (fixture URL):** pass — mocked yt-dlp returns video file; manifest updated; metadata sidecar optional

**Test cases:**

```bash
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_downloader.py tests/test_metadata.py -v
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_download_step.py -v   # if added
```

**Manual smoke (optional, requires cookies/network):**

```bash
docker compose run --rm -e MODE=download \
  -v ./dataset:/data/dataset \
  cookbook download --urls-file /data/dataset/urls.txt --limit 1
ls dataset/raw/
cat dataset/manifest.json
```

**Expected output:** Unit tests pass 100%; manual run produces `{reel_id}.mp4` in `dataset/raw/` and manifest entry with `status: success`.

## Rollback Procedure

1. Revert any new/changed files in `app/steps/` and test additions if they break baseline.
2. Preserve existing `app/downloader/` and `app/cli/download.py` — do not delete working Phase 0 code.
3. Re-run `pytest tests/test_downloader.py` — must remain green.
4. If manifest format changed, restore `dataset/manifest.json` from git or backup.
