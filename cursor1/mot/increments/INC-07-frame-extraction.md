# INCREMENT 7: Frame Extraction

**Status:** Standard  
**Dependencies:** INC-05 (Media / audio extraction)

## Capability Specification

Extract video frames at configurable intervals via ffmpeg for downstream OCR/vision. After this increment, Step 4 produces a frames directory under the working job folder with predictable naming and count proportional to video duration.

**What changes:** Add `app/media/frames.py` and `ExtractFramesStep`; frames available for INC-08 vision pipeline.

**What must remain unchanged:**

- Audio extraction module (`app/media/audio.py`) — independent code path
- Transcription outputs — frame extraction does not modify transcripts
- Vision/OCR logic — deferred to INC-08

## Implementation Instructions

1. Create `app/media/frames.py`:

```text
app/media/
├── audio.py      # from INC-05
└── frames.py     # new
```

2. **`extract_frames(video_path: Path, output_dir: Path, interval_seconds: float) -> list[Path]`**:
   - Use ffmpeg fps filter: `-vf fps=1/{interval}` or select filter with `fps=1/N`
   - Output pattern: `{output_dir}/frame_{index:05d}.jpg` (or `{timestamp_ms}.jpg`)
   - Create `output_dir` if missing
   - Return sorted list of frame paths
   - Config: `FRAME_INTERVAL` from `CookBookConfig` (default 2.0 seconds)

3. **Frame metadata sidecar** (optional `frames_manifest.json` in output_dir):
   - List `{index, path, timestamp_seconds}` per frame
   - Timestamps: `index * interval_seconds` or parsed from ffprobe when using select filter

4. **Add `app/steps/step04_extract_frames.py`**:
   - `ExtractFramesStep`: `step_number=4`, `requires=[1]`
   - Skip gracefully when `context.video_processing_enabled is False` — return success with empty artifacts and metric `skipped=True`
   - Input: `video_path` from artifacts
   - Output dir: `working/{job_id}/frames/`
   - Artifacts: `frames_dir`, `frame_paths`, `frame_count`
   - Metrics: `duration_seconds`, `interval_seconds`, `expected_frame_count`

5. **Expected frame count formula:**
   - `expected = floor(duration / interval) + 1` (or `ceil(duration / interval)` — document choice)
   - Use `app.media.audio.probe_duration()` from INC-05

6. Add `tests/test_media_frames.py`:
   - Mock ffmpeg; assert output command includes interval
   - Count validation: given duration=10s, interval=2s → expect ~5–6 frames (± tolerance)
   - Step skip when `video_processing_enabled=False`

Reference: SRD §10 (`media/` frame ops, `step04_extract_frames.py`), §11 (`ExtractFramesStep`), §8 (`FRAME_INTERVAL` config).

## Verification Protocol

**Quantitative success criteria** (from [`TRACKING_MATRIX.md`](../TRACKING_MATRIX.md)):

- [ ] **Frame count ≈ duration × interval:** ± 5% green; ± 10% yellow; > ± 10% red

**Test cases:**

```bash
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_media_frames.py -v
```

**Manual validation:**

```bash
docker compose run --rm cookbook python -c "
from pathlib import Path
from app.media.frames import extract_frames
from app.media.audio import probe_duration
video = next(Path('/data/dataset/raw').glob('*.mp4'))
dur = probe_duration(video)
frames = extract_frames(video, Path('/data/working/frames-test'), interval_seconds=2.0)
expected = dur / 2.0
print('duration', dur, 'frames', len(frames), 'expected', expected, 'delta_pct', abs(len(frames)-expected)/max(expected,1)*100)
"
```

**Expected output:** Frame JPG files exist; `abs(actual - expected) / expected <= 0.05` for green zone.

## Rollback Procedure

1. Remove `app/media/frames.py` and `app/steps/step04_extract_frames.py`.
2. Delete `working/*/frames/` test output directories.
3. Re-run INC-05 audio tests — must remain green.
4. Do not proceed to INC-08 until frame count metric is green on fixture video.
