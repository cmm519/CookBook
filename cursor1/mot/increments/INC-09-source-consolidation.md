# INCREMENT 9: Source Consolidation

**Status:** Standard  
**Dependencies:** INC-06 (Transcription interface + Whisper), INC-08 (Vision / OCR interface)

## Capability Specification

Merge transcript, vision/OCR, video metadata, and user-provided inputs into a single validated `ConsolidatedSourceInput` object for the recipe formatter. After this increment, Step 6 produces consolidation JSON that preserves raw evidence separately and never overwrites source artifacts.

**What changes:** Add `app/extraction/consolidate.py` and `ConsolidateStep`; define consolidation schema in `app/models/consolidation.py`.

**What must remain unchanged:**

- Raw files on disk (`transcript.txt`, `transcript.json`, `vision.json`, metadata sidecars) — consolidation reads only
- Formatter / Ollama calls — deferred to INC-10
- Storage and recipe package writes — deferred to INC-09+ / INC-11

## Implementation Instructions

1. Create consolidation module:

```text
app/extraction/
├── __init__.py
└── consolidate.py     # build_consolidated_input()
```

2. **Define `ConsolidatedSourceInput`** in `app/models/consolidation.py` (SRD §3 + §11):

```python
class ConsolidatedSourceInput(BaseModel):
    source_url: HttpUrl
    reel_id: str | None
    metadata: VideoMetadata | dict[str, Any]      # caption, comments, author
    transcript: TranscriptResult                   # full segments preserved
    vision: VisionResult | None                    # None when video_processing disabled
    user_comment: str | None
    custom_instruction: str | None
    video_processing_enabled: bool
    consolidated_at: datetime                      # ISO 8601
    pipeline_version: str
```

3. **`build_consolidated_input(...) -> ConsolidatedSourceInput`**:
   - Load transcript from `transcript_json_path` (required)
   - Load metadata from `metadata_path` or manifest entry (optional but recommended)
   - Load vision from `vision_json_path` when `video_processing_enabled` and file exists
   - Attach `user_comment` and `custom_instruction` from `StepContext`
   - Never mutate input files; deep-copy segment lists

4. **Conflict handling** (document, do not resolve with LLM here):
   - Include both transcript text and OCR text as separate fields
   - Add optional `evidence_notes: list[str]` for human-readable conflict hints (e.g. "OCR frame 12: '2 tbsp' vs transcript silent")

5. **Add `app/steps/step06_consolidate.py`**:
   - `ConsolidateStep`: `step_number=6`, `requires=[3]` (transcript required)
   - When vision enabled, `requires=[3, 5]` — validate vision artifact present or explicit skip
   - Output: `working/{job_id}/consolidated.json`
   - Artifacts: `consolidated_json_path`
   - Metrics: `transcript_segment_count`, `vision_frame_text_count`, `has_caption`, `has_comments`

6. **Testing GUI preview** (SRD §6): consolidated JSON is the Step 6 inspector artifact.

7. Add `tests/test_consolidation.py`:
   - Fixture transcript + metadata + vision → valid `ConsolidatedSourceInput`
   - Transcript-only path (`video_processing_enabled=False`, `vision=None`)
   - Schema round-trip JSON serialize/deserialize
   - Assert input files unchanged after consolidation (checksum or mtime)

8. Add `tests/fixtures/consolidation/` — sample transcript.json, vision.json, metadata.json.

Reference: SRD §3 (raw evidence immutability), §10 (`extraction/` consolidation, `step06_consolidate.py`), §11 (`ConsolidateStep`); [`MASTER_CONTEXT.md`](../MASTER_CONTEXT.md) §1 (evidence separation).

## Verification Protocol

**Quantitative success criteria** (from [`TRACKING_MATRIX.md`](../TRACKING_MATRIX.md)):

- [ ] **Consolidation object schema valid:** 100% — all fixture combinations parse as `ConsolidatedSourceInput`; invalid fixtures raise `ValidationError`

**Test cases:**

```bash
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_consolidation.py -v
docker compose -f docker-compose.test.yml run --rm cookbook python -c "
import json
from pathlib import Path
from app.models.consolidation import ConsolidatedSourceInput
p = Path('tests/fixtures/consolidation/full.json')
obj = ConsolidatedSourceInput.model_validate_json(p.read_text())
print('ok', obj.source_url, len(obj.transcript.segments))
"
```

**Combination matrix (all must pass validation):**

| Case | Transcript | Vision | Metadata |
|---|---|---|---|
| A | ✓ | ✓ | ✓ |
| B | ✓ | ✗ (disabled) | ✓ |
| C | ✓ | ✗ (skipped) | ✗ |

**Expected output:** 100% schema validation on matrix; `consolidated.json` written to working dir in step test; source artifact files unmodified.

## Rollback Procedure

1. Remove `app/extraction/consolidate.py` and `app/steps/step06_consolidate.py`.
2. Delete `working/*/consolidated.json` outputs from failed runs.
3. Re-run INC-06 and INC-08 tests independently — both must remain green.
4. Do not proceed to INC-10 (formatter) until consolidation schema validation is 100%.
