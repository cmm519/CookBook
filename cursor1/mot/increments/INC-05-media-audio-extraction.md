# INCREMENT 5: Media / Audio Extraction (ffmpeg)

**Status:** Standard  
**Dependencies:** INC-04 (Downloader interface + yt-dlp)

## Capability Specification

Extract mono 16 kHz WAV audio from downloaded video via ffmpeg in a dedicated `app/media/` module. After this increment, pipeline Step 2 and transcription can call shared audio extraction instead of duplicating ffmpeg logic inside `FasterWhisperTranscription`.

**What changes:** Empty `app/media/` → `extract_audio()` and `probe_duration()` utilities; optional `ExtractAudioStep` wrapper.

**What must remain unchanged:**

- Downloader output format and paths (`dataset/raw/{reel_id}.mp4`)
- Whisper transcription provider interface — may delegate to `app/media/` internally but API unchanged
- Batch transcribe CLI behavior until INC-06 refactors to use shared media module

## Implementation Instructions

1. Create `app/media/audio.py`:

```text
app/media/
├── __init__.py
└── audio.py
```

2. **`extract_audio(video_path: Path, output_wav: Path) -> Path`**:
   - ffmpeg command: `-i <video> -ac 1 -ar 16000 -y <output.wav>`
   - `-hide_banner -loglevel error`
   - Raise `MediaExtractionError` with stderr on failure
   - Raise clear error if ffmpeg not found

3. **`probe_duration(media_path: Path) -> float`**:
   - Use `ffprobe -v error -show_entries format=duration -of csv=p=0`
   - Return duration in seconds (float)
   - Used by INC-07 frame count validation

4. **Output contract** (SRD §10 Step 2):
   - Import pipeline: `working/{job_id}/audio.wav`
   - Must be valid WAV: mono, 16000 Hz, PCM

5. **Add `app/steps/step02_extract_audio.py`**:
   - `ExtractAudioStep`: `step_number=2`, `requires=[1]`
   - Read `video_path` from `StepContext.artifacts`
   - Write `audio.wav` to `context.working_dir`
   - Set artifacts: `audio_path`, `duration_seconds`

6. **Refactor** `app/transcription/whisper.py`:
   - Replace inline `_extract_audio()` with call to `app.media.audio.extract_audio`
   - Preserve existing behavior and tests

7. Add `tests/test_media_audio.py`:
   - Mock `subprocess.run` / use tiny fixture video if available in CI
   - Assert ffmpeg command contains `-ac 1`, `-ar 16000`
   - Assert `probe_duration` parses ffprobe output
   - WAV validation: use `wave` module to check channels=1, rate=16000

8. Add `tests/fixtures/media/` — optional 1-second silent test clip (generate in test setup if not committed).

Reference: SRD §10 (`media/` — ffmpeg audio/frame ops, `step02_extract_audio.py`), §11 (`ExtractAudioStep`).

## Verification Protocol

**Quantitative success criteria** (from [`TRACKING_MATRIX.md`](../TRACKING_MATRIX.md)):

- [ ] **Audio extraction (fixture video):** WAV valid — mono, 16 kHz, non-empty file; not corrupt/missing

**Test cases:**

```bash
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_media_audio.py -v
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_transcription.py -v   # regression
```

**Manual smoke:**

```bash
docker compose run --rm cookbook python -c "
from pathlib import Path
from app.media.audio import extract_audio, probe_duration
# assumes a video in dataset/raw/
p = next(Path('/data/dataset/raw').glob('*.mp4'), None)
if p:
    wav = Path('/data/working/test-audio.wav')
    extract_audio(p, wav)
    print('duration', probe_duration(p), 'wav_ok', wav.stat().st_size)
"
```

**Expected output:** Unit tests pass; WAV file size > 44 bytes (header + samples); transcription tests still pass after refactor.

## Rollback Procedure

1. Revert `app/transcription/whisper.py` to inline ffmpeg if shared module causes regressions.
2. Remove `app/media/audio.py` and `app/steps/step02_extract_audio.py`.
3. Delete `tests/test_media_audio.py`.
4. Re-run full pytest suite; INC-04 downloader tests must remain green.
