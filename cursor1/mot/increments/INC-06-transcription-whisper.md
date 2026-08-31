# INCREMENT 6: Transcription Interface + Whisper (Local)

**Status:** Standard  
**Dependencies:** INC-05 (Media / audio extraction)

## Capability Specification

Formalize and verify the **existing** faster-whisper transcription implementation; add pipeline Step 3 wrapper. After this increment, batch transcribe (`MODE=transcribe`) and single-file transcription produce timestamped outputs in `dataset/transcripts/`, update manifest, and expose a reusable `TranscriptionProvider` for the import pipeline.

**What changes:** Audit existing code; add `TranscribeStep`; ensure audio flows through `app/media/` (INC-05); document Phase 0 batch path; close manifest field gaps.

**What must remain unchanged:**

- Raw transcript immutability — formatter must never overwrite `transcript.txt` / `transcript.json` (SRD §3)
- Downloader and dataset layout
- No vision, consolidation, or recipe formatting in this increment

## Existing Implementation (document before editing)

| Component | Path | Role |
|---|---|---|
| Provider ABC | `app/transcription/provider.py` | `TranscriptionProvider`, `TranscriptResult`, `TranscriptSegment` |
| Whisper backend | `app/transcription/whisper.py` | `FasterWhisperTranscription` — video→WAV→transcribe |
| Batch CLI | `app/cli/transcribe.py` | `run_batch_transcribe()`, manifest update, skip/force |
| Entrypoint | `scripts/docker-entrypoint.sh` | `MODE=transcribe` → `python -m app.cli transcribe` |
| Config | `app/config/settings.py` | `WHISPER_MODEL`, `WHISPER_DEVICE` |
| Tests | `tests/test_transcription.py` | Fake provider, batch manifest, mocked Whisper |

**Already implemented behaviors:**

- Transcribe from video (ffmpeg extract) or audio directly
- Write `{reel_id}.txt` and `{reel_id}.json` to `dataset/transcripts/`
- Skip existing transcripts unless `force=True` / `TRANSCRIBE_FORCE=true`
- Update manifest: `transcript_path`, `transcript_json_path`, `transcribed_at`, `transcript_status`
- Per-video failure continues batch; errors in manifest
- Device validation: `cuda` | `cpu`; compute_type auto (`float16` / `int8`)

## Implementation Instructions

1. **Gap audit** against SRD §5 `batch-transcribe`:
   - Confirm empty `dataset/raw/` exits with clear message
   - Confirm GPU-unavailable error is actionable when `WHISPER_DEVICE=cuda`
   - Align `TranscriptResult` with INC-02 models if migrated

2. **Add `app/steps/step03_transcribe.py`** (SRD §10/§11):
   - `TranscribeStep`: `step_number=3`, `requires=[2]` (or `[1]` if transcribing directly from video when Step 2 skipped in Testing GUI)
   - Input artifact: `audio_path` (preferred) or `video_path`
   - Output artifacts: `transcript_txt_path`, `transcript_json_path`, `segment_count`, `language`
   - Metrics: `duration_ms`, `segments_per_minute`

3. **Wire CLI** `app/cli/__main__.py` transcribe subcommand:
   - Confirm entrypoint dispatches correctly
   - Support env: `TRANSCRIBE_FORCE`, `TRANSCRIBE_ONLY=<reel_id>`

4. **Use shared media module** (INC-05):
   - `FasterWhisperTranscription` must call `app.media.audio.extract_audio` for video inputs

5. **GPU sequential lock** (document only — enforce in orchestrator INC-13):
   - Step 3 loads Whisper; must not overlap Step 7 formatter GPU use

6. Extend `tests/test_transcription.py`:
   - `TranscribeStep.run()` with fake provider
   - Segments-per-minute metric calculation
   - `TRANSCRIBE_ONLY` filter

Reference: SRD §3 (transcript artifacts), §5 (`batch-transcribe`), §10 (`transcription/`, `step03_transcribe.py`), §11 (`TranscribeStep`, `TranscriptResult`).

## Verification Protocol

**Quantitative success criteria** (from [`TRACKING_MATRIX.md`](../TRACKING_MATRIX.md)):

- [ ] **Transcription segments / video minute:** ≥ 8 (green) on fixture video; 4–7 yellow; < 4 red
- [ ] **Transcription latency (fixture, seconds):** < 60 green; 60–120 yellow; > 120 red

**Test cases:**

```bash
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_transcription.py -v
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_transcribe_step.py -v   # if added
```

**Manual smoke (GPU compose, fixture video):**

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm \
  -e MODE=transcribe -e WHISPER_MODEL=base -e WHISPER_DEVICE=cuda \
  -v ./dataset:/data/dataset cookbook
ls dataset/transcripts/
```

**Measure segments/minute:**

```python
# segments_per_minute = len(segments) / (duration_seconds / 60)
```

**Expected output:** Unit tests pass; for a ≥1 min fixture reel, segment count ≥ 8; transcript `.txt` and `.json` present; manifest shows `transcript_status: completed`.

## Rollback Procedure

1. Revert `TranscribeStep` and CLI changes if batch path breaks.
2. Keep `app/transcription/whisper.py` and `app/cli/transcribe.py` — do not remove working Phase 0 code.
3. Remove partial transcripts for failed videos from `dataset/transcripts/` before re-run.
4. Re-run downloader + transcription unit tests; do not proceed to INC-07 if latency red on fixture.
