# INCREMENT 8: Vision / OCR Interface

**Status:** CRITICAL  
**Dependencies:** INC-07 (Frame extraction)

## Capability Specification

Implement a swappable `VisionProvider` that extracts on-screen text from video frames. After this increment, Step 5 produces `vision.json` with per-frame text and confidence scores. OCR quality directly affects recipe quantity accuracy — treat failures as pipeline-critical.

**What changes:** Empty `app/vision/` → provider interface + default implementation; `VisionStep` wrapper; fixture-based OCR validation.

**What must remain unchanged:**

- Raw transcript files — vision output is separate evidence in `vision.json`
- Formatter behavior — deferred to INC-10; vision must not invent quantities
- Frame extraction settings (`FRAME_INTERVAL`) — vision consumes frames, does not re-extract

## Risk Summary

| Risk | Failure mode | Mitigation |
|---|---|---|
| On-screen text is only source for quantities | Missing/garbled ingredient amounts | Preserve frame-level evidence + confidence; pass through to consolidation |
| OCR quality varies by video style | Formatter hallucinates quantities | Confidence scores; mark uncertain values; formatter must not silently fill gaps |
| Heavy OCR deps bloat container | Build failures, slow CI | Default to lightweight provider (e.g. Tesseract); optional GPU provider behind config |
| False positives on background text | Noise in consolidated input | Per-frame confidence threshold; dedupe similar strings |

## Implementation Instructions

1. Create vision module:

```text
app/vision/
├── __init__.py
├── provider.py       # VisionProvider ABC, VisionFrameResult
└── tesseract.py      # Default: pytesseract or subprocess tesseract (configurable)
```

2. **`VisionProvider` interface** (`app/vision/provider.py`):

```python
class VisionFrameResult(BaseModel):
    timestamp: float
    frame_path: str
    text: str
    confidence: float | None = None

class VisionResult(BaseModel):
    provider: str
    model_version: str | None
    frames: list[VisionFrameResult]

class VisionProvider(ABC):
    def analyze_frames(self, frame_paths: list[Path], timestamps: list[float]) -> VisionResult: ...
```

3. **Default implementation** (`TesseractVisionProvider` or equivalent):
   - OCR each JPG; normalize whitespace
   - Optional confidence from tesseract `image_to_data`
   - Skip frames with empty text (do not emit empty entries)

4. **Add `app/steps/step05_vision.py`**:
   - `VisionStep`: `step_number=5`, `requires=[4]`
   - Skip when `video_processing_enabled=False` — write empty `vision.json` with `"skipped": true`
   - Input: `frame_paths`, timestamps from Step 4 artifacts
   - Output: `working/{job_id}/vision.json`
   - Artifacts: `vision_json_path`, `frames_with_text_count`

5. **Align with INC-02 models** — `VisionResult` / `VisionFrame` in `app/models/vision.py`

6. **Fixture frames** under `tests/fixtures/vision/`:
   - At least 5 synthetic frames with known overlay text (e.g. "2 cups flour", "350°F")
   - Generate via PIL in test setup if binaries not committed

7. **Config keys** (add to `CookBookConfig` if missing):
   - `VISION_PROVIDER` (default `tesseract`)
   - `VISION_MIN_CONFIDENCE` (default 0.5)

8. Do **not** call formatter or modify transcripts in this step.

Reference: SRD §3 (`vision.json` in RecipePackage), §10 (`vision/`, `step05_vision.py`), §11 (`VisionStep`); [`INCREMENTS.md`](../INCREMENTS.md) INC-08 critical checkpoint.

## Verification Protocol

**Quantitative success criteria** (from [`TRACKING_MATRIX.md`](../TRACKING_MATRIX.md)):

- [ ] **OCR text detected (fixture frames):** ≥ 80% of known text strings found (green); 50–79% yellow; < 50% red

**Detection formula:**

```text
match_rate = matched_expected_strings / total_expected_strings
```

Use case-insensitive substring match; normalize whitespace and punctuation.

**Test cases:**

```bash
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_vision.py -v
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_vision_step.py -v
```

**Isolation test (required for CRITICAL increment):**

```bash
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_vision.py -v -k "fixture"
# No other pipeline stages — vision only on fixture frames
```

**Expected output:** ≥ 80% string match on fixture set; `vision.json` validates against `VisionResult` schema.

## CRITICAL Isolation Protocol

Execute this protocol if OCR match rate is **yellow or red**, or if downstream consolidation shows invented quantities.

### 1. Isolate

- Run vision **only** on `tests/fixtures/vision/` frames — no download, transcribe, or formatter
- Disable all other pipeline stages in test compose

### 2. Test variants

| Variant | Provider | Notes |
|---|---|---|
| V1 | Tesseract default | Baseline |
| V2 | Tesseract + preprocessing (grayscale, contrast) | Test image prep |
| V3 | Alternate provider (if implemented) | Compare match rates |

Record match_rate per variant in [`TRACKING_MATRIX.md`](../TRACKING_MATRIX.md).

### 3. Analyze component outputs

- Inspect `vision.json` per frame: raw text, confidence, timestamp
- Compare against ground-truth fixture manifest
- Identify failure patterns: small font, motion blur, colored backgrounds

### 4. Verify computational correctness

- Frame count input equals Step 4 output count
- Every `VisionFrameResult.frame_path` exists on disk
- JSON schema validates 100%

### 5. Apply mitigation

- Lower/raise `VISION_MIN_CONFIDENCE` threshold
- Add image preprocessing hook in provider
- Pass low-confidence fields to formatter as uncertain (INC-09/10)
- **Rollback option:** set `video_processing_enabled=False` — pipeline continues transcript-only

### 6. Proceed gate

- Do **not** start INC-09 until match_rate ≥ 80% on fixture set **or** explicit transcript-only fallback documented in session log

## Rollback Procedure

1. Set `VIDEO_PROCESSING_DEFAULT=false` in `.env` to disable vision in import jobs.
2. Remove `app/vision/tesseract.py` (or failed provider); revert to stub `VisionProvider` returning empty frames.
3. Delete `working/*/vision.json` artifacts from failed runs.
4. Re-run INC-07 frame tests — must remain green.
5. Record rollback and variant metrics in [`TRACKING_MATRIX.md`](../TRACKING_MATRIX.md) session log.
6. Pipeline may proceed transcript-only until OCR quality restored.
