# INCREMENT 12: SQLite Search Index

**Status:** Standard  
**Dependencies:** INC-11 (Normalized recipe.json + recipe.md)

## Capability Specification

Implement `app/search/` SQLite index and `StoreIndexStep` (Step 9) to persist the **RecipePackage** to `recipes/<slug>/` and maintain a searchable `recipes.db` index. Filesystem remains source of truth; SQLite is a query accelerator.

**What changes:** Working-dir artifacts → complete recipe package on disk + indexed row(s) in SQLite.

**What must remain unchanged:**

- Recipe package layout from INC-03 (`video.mp4`, `transcript.*`, `vision.json`, `recipe.json`, `recipe.md`, `metadata.json`).
- Normalized `recipe.json` content from Step 8 — store step copies, does not reformat.
- Duplicate detection by `source_url` before creating a new package.

## Implementation Instructions

1. Add `app/search/schema.sql` (or migration module):
   - Table `recipes`: `slug` PK, `title`, `description`, `source_url` UNIQUE, `source_creator`, `tags_json`, `date_added`, `package_path`
   - Table `ingredients_index`: `slug`, `item`, `quantity` — for ingredient search
   - FTS5 virtual table `recipes_fts` on title + description + ingredient text (optional but recommended)
   - Indexes on `source_url`, `date_added`
2. Add `app/search/index.py`:
   - `SearchIndex` class: `init_db()`, `upsert_recipe(recipe: Recipe, slug: str, package_path: Path)`, `delete_recipe(slug)`, `search(query: str, limit: int) -> list[SearchResult]`
   - `reindex_all(repository_path)` — rebuild from filesystem (recovery tool)
   - Use `sqlite3` stdlib; `DATABASE_PATH` from config (default `/data/db/recipes.db`)
3. Add `app/storage/package.py` (extend INC-03):
   - `slugify(title) -> str` with uniqueness suffix on collision
   - `store_package(context, recipe, artifacts) -> RecipePackage` — copy/move artifacts from `working/<job_id>/` to `recipes/<slug>/`
   - Write `metadata.json` (import timestamp, pipeline version, job_id, formatter model)
   - Atomic write: temp dir → rename; rollback on failure
4. Implement `app/steps/step09_store_index.py`:
   - Class `StoreIndexStep` (`step_number=9`, `requires=[8]`)
   - Check duplicate `source_url` — if exists, return success with existing slug (idempotent) or configurable `IMPORT_ALLOW_DUPLICATE=false` error
   - Call `store_package` then `SearchIndex.upsert_recipe`
   - Artifacts: `recipe_slug`, `package_path`
5. Add CLI helper: `recipe-search "<query>"` (optional stub for INC-14).
6. Tests:
   - `tests/test_search_index.py` — CRUD, FTS query, duplicate URL
   - `tests/test_step09_store_index.py` — end-to-end store from fixture working dir
   - Temp SQLite file per test (no pollution of dev db)

**Architectural constraints (SRD §10–11):**

- Every write to `recipe.json` on disk must eventually call `SearchIndex.upsert_recipe` (enforced in INC-15 editor).
- Step 9 is the **only** pipeline step that writes to `recipes/` and `recipes.db`.

## Verification Protocol

**Quantitative success criteria:**

- [ ] Search query latency on 100-recipe fixture DB: **< 200ms** green (TRACKING_MATRIX)
- [ ] `upsert` + filesystem package consistent — `recipe.json` in DB matches file on disk
- [ ] Duplicate `source_url` detected — no second package directory created
- [ ] `reindex_all()` rebuilds index from `recipes/` without data loss
- [ ] All Step 9 tests pass in test compose

**Test cases:**

```bash
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_search_index.py tests/test_step09_store_index.py -v
```

**Expected output:** Package at `recipes/<slug>/` with all artifacts; query returns inserted recipe by title and ingredient.

## Rollback Procedure

1. Remove Step 9 from orchestrator — pipeline ends with working-dir outputs only.
2. Drop `recipes.db` and recreate empty schema if index corruption occurs; run `reindex_all()` after code fix.
3. Revert `app/search/` and `app/steps/step09_store_index.py`; filesystem packages remain valid without index.
