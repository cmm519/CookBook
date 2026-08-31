# INCREMENT 15: Recipe Editor (Manual Override)

**Status:** Standard  
**Dependencies:** INC-14 (Production Web UI skeleton + viewer)

## Capability Specification

Add **recipe editing** to the Production Web UI so users can manually correct formatter mistakes. Edits update `recipe.json` on disk, regenerate `recipe.md` deterministically, and re-index SQLite **atomically**.

**What changes:** `GET/POST /recipes/{slug}/edit` — form for title, ingredients, instructions, notes, tags; save persists package + index.

**What must remain unchanged:**

- Raw evidence files (`transcript.txt`, `vision.json`, `video.mp4`) — editor does not modify.
- Deterministic markdown from INC-11 — `render_markdown()` used on save, no LLM.
- Duplicate slug rules — title change may require slug rename with redirect or uniqueness suffix.

## Implementation Instructions

1. Extend **`RecipeController`** in `app/web/production/`:
   - `GET /recipes/{slug}/edit` — load `recipe.json` into form
   - `POST /recipes/{slug}/edit` — validate with Pydantic `Recipe`; atomic save
2. Add `app/storage/editor.py`:
   - `save_recipe_edit(slug: str, recipe: Recipe) -> str` — returns final slug (may change on title edit)
   - Write flow: validate → write `recipe.json.tmp` → `render_markdown()` → write `recipe.md` → `SearchIndex.upsert_recipe()` → rename atomically
   - On slug change: rename package directory `recipes/<old>` → `recipes/<new>`; update index delete+insert
   - Rollback on any failure — keep previous package intact
3. Templates:
   - `recipe_edit.html` — editable fields for all Recipe schema sections
   - Ingredient rows: item, quantity, preparation, notes, confidence (read-only display optional)
   - Instruction rows: step number, text, duration, temperature
   - Save / Cancel buttons; validation errors inline
4. Viewer (`recipe_detail.html`) — add "Edit" link when authenticated or always (single-user server).
5. Tests:
   - `tests/test_recipe_editor.py` — edit save updates json, md, and sqlite consistently
   - Slug rename collision handling
   - Failed validation does not corrupt existing package

**Architectural constraints (SRD §3, §10):**

- Filesystem is source of truth; SQLite must match after every successful save.
- Editor uses `formatting/markdown.py` only — no formatter/Ollama calls.

## Verification Protocol

**Quantitative success criteria:**

- [ ] Edit save updates `recipe.json`, `recipe.md`, and SQLite row in one transaction
- [ ] Search finds recipe by new title after title edit
- [ ] Invalid edit (empty ingredients) rejected with 422 and no file change
- [ ] `transcript.txt` checksum unchanged after edit
- [ ] `pytest tests/test_recipe_editor.py` passes

**Test cases:**

```bash
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_recipe_editor.py -v
```

**Expected output:** Edited recipe visible in viewer and search; markdown reflects edits.

## Rollback Procedure

1. Remove edit routes and template — viewer remains read-only.
2. Restore `recipe.json` from git or backup if bad edit saved (operator responsibility).
3. Run `SearchIndex.reindex_all()` if index drift detected.
