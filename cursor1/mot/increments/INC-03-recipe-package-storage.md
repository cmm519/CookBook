# INCREMENT 3: Recipe Package Storage

**Status:** Standard  
**Dependencies:** INC-02 (Pydantic data models)

## Capability Specification

Implement filesystem storage for complete recipe packages under `recipes/<slug>/`. After this increment, a validated `Recipe` and associated artifact paths can be written atomically to disk and read back with identical content. SQLite indexing is out of scope (INC-12).

**What changes:** Empty `app/storage/` → read/write module for recipe package layout per SRD §3 RecipePackage entity.

**What must remain unchanged:**

- Downloader, transcription, and CLI batch modes — no changes to `dataset/` Phase 0 flow
- Pydantic model definitions in `app/models/` — storage consumes them, does not redefine schemas
- No pipeline steps or web UI in this increment

## Implementation Instructions

1. Implement `app/storage/package.py`:

```text
app/storage/
├── __init__.py          # export PackageStorage
└── package.py           # PackageStorage class
```

2. **Slug generation** (`slugify(title: str) -> str`):
   - Lowercase, replace spaces/punctuation with hyphens, strip unsafe chars
   - Append numeric suffix (`-2`, `-3`) on collision within `repository_path`
   - Max slug length 80 chars

3. **Package layout** (SRD §3 RecipePackage):

```text
recipes/<slug>/
├── video.mp4
├── transcript.txt
├── transcript.json
├── vision.json          # optional
├── recipe.json
├── recipe.md            # optional until INC-11; stub empty or omit
├── metadata.json
└── thumbnail.jpg        # optional
```

4. **PackageStorage** API:

   - `write_package(base_dir: Path, slug: str, artifacts: RecipePackageWrite) -> Path`
     - `RecipePackageWrite` dataclass/Pydantic: paths or in-memory content for each artifact
     - Write to temp dir `base_dir/.tmp/<slug>-<uuid>/`, then `rename` to final path (atomic on same filesystem)
   - `read_package(base_dir: Path, slug: str) -> RecipePackageRead`
     - Load `recipe.json` via `Recipe` model; load `metadata.json`; return paths for binary assets
   - `package_exists(base_dir: Path, slug: str) -> bool`
   - `find_by_source_url(base_dir: Path, url: str) -> str | None` — scan `metadata.json` for duplicate detection (SRD §3 uniqueness)

5. **metadata.json** fields:
   - `source_url`, `source_creator`, `date_added` (ISO 8601), `pipeline_version`, `slug`, `reel_id` (optional)

6. Validation before write:
   - `recipe.json` must pass `Recipe` Pydantic validation
   - `transcript.txt` / `transcript.json` treated as immutable raw evidence — storage never modifies content on read
   - Reject write if `slug` directory already exists unless `overwrite=True` (explicit flag)

7. Wire config:
   - Use `CookBookConfig.repository_path` as default `base_dir`

8. Add tests in `tests/test_storage.py`:
   - Round-trip: write sample package → read → compare `Recipe` equality
   - Collision: two packages with same title get distinct slugs
   - Duplicate URL detection returns existing slug
   - Atomic write: simulate failure mid-write leaves no partial final directory

Reference: SRD §3 (RecipePackage entity, uniqueness constraints), §4 (Persistence — filesystem source of truth), §10 (`storage/` package layout).

## Verification Protocol

**Quantitative success criteria** (from [`TRACKING_MATRIX.md`](../TRACKING_MATRIX.md)):

- [ ] **Storage round-trip (write/read package):** pass — written `recipe.json` and `metadata.json` match on read; slug directory contains all required files

**Test cases:**

```bash
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_storage.py -v
docker compose -f docker-compose.test.yml run --rm cookbook python -c "
from pathlib import Path
from tempfile import TemporaryDirectory
from app.models import Recipe, Ingredient, Instruction
from app.storage import PackageStorage
with TemporaryDirectory() as td:
    base = Path(td)
    storage = PackageStorage()
    recipe = Recipe(
        title='Garlic Pasta',
        source_url='https://www.instagram.com/reel/TEST1/',
        ingredients=[Ingredient(item='garlic')],
        instructions=[Instruction(step=1, text='Saute')],
    )
    slug = storage.write_package(base, recipe=recipe, transcript_txt='hello', transcript_json={'text':'hello'})
    pkg = storage.read_package(base, slug)
    assert pkg.recipe.title == 'Garlic Pasta'
    print('OK', slug)
"
```

**Expected output:** All storage tests pass; round-trip script prints `OK <slug>`.

## Rollback Procedure

1. Remove `app/storage/package.py` and revert `app/storage/__init__.py` to stub.
2. Delete `tests/test_storage.py` and any packages written under `recipes/` during manual testing.
3. Re-run `pytest tests/test_models.py` to confirm INC-02 intact.
4. Do not proceed to INC-04 until storage round-trip metric is green.
