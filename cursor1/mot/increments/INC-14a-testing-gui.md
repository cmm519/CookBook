# INCREMENT 14a: Testing GUI — URL Queue + Step Runner

**Status:** Standard  
**Dependencies:** INC-13 (CLI import workflow / orchestrator + steps 1–9)

## Capability Specification

Implement the **Testing GUI** (`MODE=testing-gui`, port **8081**) using **FastAPI + Jinja2**. Operators can queue Instagram URLs, select a reel, and **run each pipeline step (1–9) individually** with artifact inspection and log streaming.

**What changes:** Step-by-step pipeline debugging via browser — same `PipelineStep` classes as CLI import.

**What must remain unchanged:**

- Full pipeline orchestrator behavior (INC-13) — Testing GUI defaults to **single-step** dispatch only.
- Production Web UI (INC-14) — separate port and package (`web/testing/` vs `web/production/`).
- Step output artifacts must match CLI/batch modes for the same step inputs.

## Implementation Instructions

1. Add `app/web/testing/app.py` — FastAPI factory `create_testing_app()`.
2. Controllers (SRD §12):
   - **`TestingQueueController`** — `GET/POST /testing/queue`; textarea for URLs; persist to `dataset/urls.txt`; queue table (URL, reel_id, download status, last step run)
   - **`TestingStepController`** — `POST /testing/run-step/{step_number}` body `{ "url" | "reel_id" }`; build `StepContext`; call `orchestrator.run_step()`; return `StepResult` JSON + log tail
   - **`TestingArtifactController`** — `GET /testing/artifacts/{reel_id}/{artifact_type}` — serve metadata, transcript, vision.json, recipe JSON, markdown, video (range requests optional)
   - **`TestingLogController`** — `GET /testing/logs/{job_id}` SSE or short-poll for job log stream
3. Templates (SRD §13):
   - **URL queue** — textarea, add button, queue table, row select
   - **Step runner** — buttons 1–9 labeled (Download, Extract audio, Transcribe, Extract frames, Vision/OCR, Consolidate, Format recipe, Normalize+Markdown, Store+index)
   - **Prerequisites indicator** — green/red per step from `StepContext.artifacts`
   - **Output inspector** — tabs: Video, Metadata, Transcript, Vision, Recipe JSON, Markdown, Log
4. Step button wiring maps to step classes:
   - Step 5 uses Tesseract-backed `VisionProvider` from INC-08
   - Step 7 respects GPU lock (Ollama after Whisper completes)
   - Disable step button or show error when prerequisites missing
5. Entrypoint: `MODE=testing-gui` → uvicorn on port **8081**.
6. Auth: optional simple token via `TESTING_GUI_TOKEN` env (SRD §21 open question) — document LAN-trust default for personal server.
7. Tests:
   - `tests/test_testing_gui.py` — TestClient for queue + run-step with mocked steps
   - Assert `run_step(3)` does not invoke full `run_all()`

**Architectural constraints (SRD §10–13):**

- Testing GUI **never runs full pipeline unless explicitly requested** (optional "Run all" button may call `run_all` but not default).
- `web/testing/` must not import from `web/production/` or `web/deployment/`.

## Verification Protocol

**Quantitative success criteria:**

- [ ] Queue add persists URLs to session and optional `dataset/urls.txt`
- [ ] Each step button 1–9 invokes exactly one `PipelineStep` (mock assertion)
- [ ] Output inspector serves artifact files after successful step run
- [ ] Prerequisites indicator correctly red when prior artifact missing
- [ ] Step 3 output matches `MODE=transcribe` batch output for same reel (fixture comparison)
- [ ] Server starts on 8081 with `MODE=testing-gui`
- [ ] `pytest tests/test_testing_gui.py` passes

**Test cases:**

```bash
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_testing_gui.py -v
docker compose run --rm -e MODE=testing-gui -p 8081:8081 cookbook
# Browser: add URL → run Step 1 → inspect video artifact
```

**Expected output:** Per-step execution with artifact preview; logs visible in inspector.

## Rollback Procedure

1. Disable `MODE=testing-gui` in entrypoint; use CLI `recipe-import` and direct pytest for pipeline validation.
2. Remove `app/web/testing/`; no impact on production data.
3. `dataset/urls.txt` queue file remains valid for batch download mode.
