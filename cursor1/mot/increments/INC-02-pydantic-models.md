# INCREMENT 2: Pydantic Data Models

**Status:** Standard  
**Dependencies:** INC-01 (Project skeleton + config + Docker)

## Capability Specification

Define all domain Pydantic models in `app/models/` so pipeline steps, storage, and future web layers share one validated schema. After this increment, fixture JSON round-trips through models without validation errors, and downstream increments import from `app.models` instead of ad-hoc dicts.

**What changes:** Empty `app/models/` package → complete typed domain model layer aligned with SRD §3 and §11.

**What must remain unchanged:**

- Config loading (`app/config/`) — no schema changes to `CookBookConfig`
- Existing downloader/transcription provider models (`DownloadResult`, `TranscriptResult`) may remain in provider modules until refactored; new domain models must be compatible
- No pipeline steps, storage I/O, or Docker changes in this increment

## Implementation Instructions

1. Create model modules under `app/models/` (export from `app/models/__init__.py`):

```text
app/models/
├── __init__.py          # re-export public models
├── recipe.py            # Recipe, Ingredient, Instruction
├── package.py           # RecipePackage manifest / package metadata
├── job.py               # ImportJob, JobStatus enum
├── metadata.py          # VideoMetadata, CommentEntry (or re-export from downloader)
├── transcript.py        # TranscriptResult, TranscriptSegment (domain aliases)
├── vision.py            # VisionFrame, VisionResult
├── consolidation.py     # ConsolidatedSourceInput
├── user.py              # UserNote, Rating
├── shopping.py          # ShoppingListItem, AisleCategory enum
└── debug.py             # BugReport, DebugLog, DebugLogEntry
```

2. Implement **Recipe** models per SRD §3:
   - `Ingredient`: `item` (required), `quantity`, `preparation`, `notes`, `confidence` (0.0–1.0)
   - `Instruction`: `step` (int ≥ 1), `text` (required), `duration`, `temperature`
   - `Recipe`: `title`, `description`, `servings`, `prep_time`, `cook_time`, `total_time`, `ingredients` (min 1), `instructions` (min 1, sequential steps), `notes`, `tags`, `source_url` (HttpUrl), `source_creator`
   - Validators: non-empty title; instruction steps sequential starting at 1; `confidence` in range when present

3. Implement **ImportJob** per SRD §3:
   - `job_id`, `source_url`, `status` (`pending` | `running` | `completed` | `failed`)
   - `current_stage` (1–9), `working_dir`, `user_comment`, `custom_instruction`
   - `video_processing_enabled`, `error_message`, `created_at`, `completed_at` (ISO 8601)

4. Implement **RecipePackage** descriptor (filesystem layout metadata, not file I/O):
   - Fields for expected artifact paths: `slug`, `video_path`, `transcript_txt`, `transcript_json`, `vision_json`, `recipe_json`, `recipe_md`, `metadata_json`, `thumbnail_jpg`
   - `metadata.json` shape: `source_url`, `creator`, `date_added`, `pipeline_version`

5. Implement **DatasetVideoMetadata** per SRD §3 (align with existing `app/downloader/metadata.py`):
   - Either move `VideoMetadata` / `CommentEntry` here and re-export from downloader, or subclass/alias — avoid duplicate conflicting schemas
   - Fields: `reel_id`, `source_url`, `title`, `author`, `author_username`, `caption`, `comments`, `comment_count`, `like_count`, `upload_date`, `extracted_at`

6. Implement **Vision** models (used by INC-07/08):
   - `VisionFrame`: `timestamp`, `frame_path`, `text`, `confidence` (optional)
   - `VisionResult`: `frames: list[VisionFrame]`, `provider`, `model_version`

7. Implement **ConsolidatedSourceInput** stub (filled in INC-09):
   - `source_url`, `metadata`, `transcript`, `vision` (optional), `user_comment`, `custom_instruction`

8. Implement **UserNote**, **Rating**, **ShoppingListItem** (`AisleCategory` enum: deli, produce, meat, bread, cooking, frozen, snacks, dairy, other), **BugReport**, **DebugLog** per SRD §3.

9. Add fixture JSON under `tests/fixtures/models/` for each primary entity (valid + one invalid case per model).

10. Add `tests/test_models.py`:
    - Round-trip serialize/deserialize for every model
    - Validation failures for required-field violations
    - Recipe instruction step ordering check

Reference: SRD §3 (Data Requirements), §10 (Architecture — domain models in `app/models/`), §11 (Model / Core Logic — domain models list).

## Verification Protocol

**Quantitative success criteria** (from [`TRACKING_MATRIX.md`](../TRACKING_MATRIX.md)):

- [ ] **Pydantic model validation (fixtures):** 100% of valid fixture files parse; 100% of invalid fixtures raise `ValidationError`

**Test cases:**

```bash
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_models.py -v
docker compose -f docker-compose.test.yml run --rm cookbook python -c "
from app.models import Recipe, Ingredient, Instruction
r = Recipe(
    title='Test',
    source_url='https://www.instagram.com/reel/ABC/',
    ingredients=[Ingredient(item='salt')],
    instructions=[Instruction(step=1, text='Mix')],
)
print(r.model_dump_json())
"
```

**Expected output:** All model tests pass; sample Recipe JSON prints without error; invalid fixtures (empty title, missing ingredients) fail validation.

## Rollback Procedure

1. Delete new files under `app/models/` (except empty `__init__.py` if reverting fully).
2. Remove `tests/fixtures/models/` and `tests/test_models.py`.
3. Re-run `pytest` to confirm INC-01 baseline still passes.
4. Do not proceed to INC-03 until fixture validation returns 100%.
