# INCREMENT 16: Ratings + User Notes

**Status:** Standard  
**Dependencies:** INC-15 (Recipe editor)

## Capability Specification

Add **per-recipe ratings (1–5)** and **user notes** to the Production Web UI. Persist `Rating` and `UserNote` entities (SRD §3) alongside recipe packages — stored in SQLite with optional JSON sidecar in package metadata.

**What changes:** Recipe detail page shows star rating control and notes list; users can add/edit/delete notes and set rating.

**What must remain unchanged:**

- Canonical `recipe.json` schema — ratings/notes are user metadata, not merged into Recipe ingredients/instructions unless explicitly edited via INC-15.
- Recipe package evidence files unchanged.

## Implementation Instructions

1. Extend SQLite schema (`app/search/schema.sql`):
   - Table `ratings`: `recipe_slug` PK, `score` INTEGER 1–5, `created_at`, `updated_at`
   - Table `user_notes`: `note_id` PK, `recipe_slug`, `text`, `created_at`, `updated_at`
2. Add `app/storage/user_meta.py`:
   - `set_rating(slug, score)`, `get_rating(slug) -> Rating | None`
   - `add_note(slug, text) -> UserNote`, `update_note(note_id, text)`, `delete_note(note_id)`, `list_notes(slug)`
3. Extend **`RecipeController`**:
   - `POST /recipes/{slug}/rating` — body `{ "score": 1-5 }`
   - `POST /recipes/{slug}/notes` — create note
   - `PUT /notes/{note_id}`, `DELETE /notes/{note_id}`
   - Include rating + notes in recipe detail context
4. Templates:
   - Star rating widget (1–5) on `recipe_detail.html`
   - Notes section with add form and edit/delete per note
5. Optional: mirror `user_meta.json` in `recipes/<slug>/` for filesystem backup of user data.
6. Tests:
   - `tests/test_ratings_notes.py` — CRUD, score validation (reject 0, 6), slug FK behavior

**Architectural constraints (SRD §3):**

- One rating per recipe per server (single-user); schema allows future multi-user extension.
- Notes require non-empty `text`.

## Verification Protocol

**Quantitative success criteria:**

- [ ] Rating persists across page reload
- [ ] Scores outside 1–5 rejected with 422
- [ ] Notes CRUD works; empty note rejected
- [ ] Rating and notes survive `reindex_all()` (stored outside FTS tables)
- [ ] `pytest tests/test_ratings_notes.py` passes

**Test cases:**

```bash
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_ratings_notes.py -v
```

**Expected output:** Recipe detail shows saved rating and notes; API returns correct JSON.

## Rollback Procedure

1. Remove rating/notes routes and UI widgets — recipe viewer/editor unchanged.
2. Drop `ratings` and `user_notes` tables via migration rollback (data loss for user metadata only).
3. Canonical recipes on disk unaffected.
