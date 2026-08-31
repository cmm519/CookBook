# INCREMENT 14: Production Web UI — Server Skeleton + Recipe Viewer

**Status:** Standard  
**Dependencies:** INC-13 (CLI import workflow / orchestrator)

## Capability Specification

Implement the **Production Web UI** (`MODE=web`, port **8080**) using **FastAPI + Jinja2** server-rendered templates. Deliver homescreen (import form), recipe search/browse, and recipe detail viewer. Import triggers `PipelineOrchestrator.run_all()` in a background task.

**What changes:** End users can browse and view stored recipes via browser; submit import jobs from homescreen.

**What must remain unchanged:**

- Step implementations and orchestrator — web layer dispatches only.
- Testing GUI (`MODE=testing-gui`, 8081) and Deployment GUI (`MODE=deployment-gui`, 8082) — separate increments (INC-14a, INC-14b).
- Filesystem + SQLite consistency rules from INC-12.

## Implementation Instructions

1. Add `app/web/production/app.py`:
   - FastAPI application factory `create_production_app()`
   - Mount static files (`app/web/static/`)
   - Jinja2 templates in `app/web/production/templates/`
   - CORS not required (same-origin personal server)
2. Controllers (SRD §12):
   - **`ImportController`** — `POST /import` with `source_url`, `video_processing_enabled`, `user_comment`, `custom_instruction`; enqueue background import via orchestrator; return job_id + redirect/poll URL
   - **`RecipeController`** — `GET /` homescreen, `GET /recipes` search/browse, `GET /recipes/{slug}` detail viewer
   - Search uses `SearchIndex.search()` from INC-12
3. Templates (SRD §13):
   - `home.html` — import URL field, video processing toggle, user comment, custom instruction, link to browse
   - `recipes.html` — search box + result list (title, tags, date)
   - `recipe_detail.html` — render `recipe.md` content or structured fields; link to video; show metadata
   - Shared `base.html` layout (minimal CSS, mobile-friendly)
4. Background import:
   - `asyncio` or `BackgroundTasks` worker with orchestrator worker lock
   - Import status page or poll endpoint `GET /import/{job_id}/status` — show stage 1–9 progress from `job.json`
   - User-dismissible error messages on failure (SRD §9)
5. Entrypoint: `MODE=web` → `uvicorn app.web.production.app:app --host 0.0.0.0 --port 8080`
6. Compose: expose port 8080 on `cookbook` service (Ollama stays internal).
7. Tests:
   - `tests/test_production_web.py` — TestClient for routes with temp DB + fixture recipes
   - No Selenium required in this increment (see INC-14a for Testing GUI)

**Architectural constraints (SRD §10–13):**

- `web/production/` → `workflow/` → `steps/` dependency direction only.
- FastAPI + Jinja is the **default** stack (SRD §21 decision); no SPA required in this increment.
- Recipe editor (INC-15), shopping list (INC-17), bug report (INC-18) are stubs or omitted — add navigation placeholders only.

## Verification Protocol

**Quantitative success criteria:**

- [ ] `GET /` returns 200 with import form fields
- [ ] `GET /recipes` lists indexed fixture recipes
- [ ] `GET /recipes/{slug}` loads in **< 2s** green (TRACKING_MATRIX)
- [ ] `POST /import` with mock orchestrator returns job_id and completes without blocking server
- [ ] Search query returns matching recipes from SQLite index
- [ ] `docker compose up` with `MODE=web` serves on port 8080
- [ ] `pytest tests/test_production_web.py` passes in test compose

**Test cases:**

```bash
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_production_web.py -v
docker compose up -d cookbook
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/
```

**Expected output:** HTTP 200 on homescreen; recipe detail renders markdown; import endpoint accepts JSON/form POST.

## Rollback Procedure

1. Set `MODE=import` for CLI-only operation; disable web entrypoint branch.
2. Remove `app/web/production/`; revert compose port mapping.
3. Recipe data on disk and in SQLite unaffected — web is read-only except import trigger.
