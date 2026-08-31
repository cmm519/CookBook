# INCREMENT 13: CLI Import Workflow

**Status:** Standard  
**Dependencies:** INC-12 (Store + SQLite index)

## Capability Specification

Implement `PipelineOrchestrator` and the `recipe-import` CLI (`MODE=import`) to run **all nine pipeline steps** sequentially for a single Instagram Reel URL. CLI invokes the same `app/steps/*` classes as the Testing GUI and Production import.

**What changes:** `docker compose run --rm cookbook recipe-import "<url>"` executes the full pipeline and produces a stored recipe package + index entry.

**What must remain unchanged:**

- Individual step implementations (Steps 1–9) — orchestrator coordinates only, no duplicated business logic.
- Phase 0 batch modes (`MODE=download`, `MODE=transcribe`) — separate code paths.
- GPU sequential lock: Steps 3 and 7 never overlap.

## Implementation Instructions

1. Add `app/workflow/orchestrator.py`:
   - `PipelineOrchestrator(steps: list[PipelineStep], gpu_lock: threading.Lock)`
   - `run_all(context: StepContext) -> ImportJob` — run steps 1–9 in order; stop on first failure
   - `run_step(step_number, context)`, `run_from(step_number, context)` — for Testing GUI (INC-14a)
   - `validate_prerequisites` per step before `run`
   - On failure: raise `OrchestrationError` wrapping `StepExecutionError`; preserve partial artifacts in `working/<job_id>/`
   - Worker lock: only one GPU import at a time inside container
2. Add `app/workflow/job.py`:
   - `ImportJob` model tracking `job_id`, `status`, `current_stage`, `working_dir`, timestamps, `error_message`
   - Persist job state JSON to `working/<job_id>/job.json` for resume/debug
3. Add `app/cli/import_cmd.py`:
   - Entry: `recipe-import <url> [--no-video] [--comment TEXT] [--instruction TEXT]`
   - Build `StepContext` from config + CLI flags
   - Call `orchestrator.run_all()`; exit 0 on success, non-zero on failure with stderr message
4. Register CLI in `pyproject.toml` scripts: `recipe-import = app.cli.import_cmd:main`
5. Update `scripts/docker-entrypoint.sh`: `MODE=import` → `recipe-import "$@"`
6. Add `app/bugreport/debuglog.py` stub — append timestamped entries per stage (full implementation INC-18); orchestrator writes stage start/end to debug log
7. Tests:
   - `tests/test_orchestrator.py` — mock steps, failure at step N, prerequisite validation, gpu_lock
   - `tests/test_import_cli.py` — integration with mocked providers (test compose)
   - Mark full GPU e2e test `@pytest.mark.gpu` optional

**Architectural constraints (SRD §10–12):**

- `workflow/` imports `steps/`; `steps/` must **not** import `workflow/` or `web/`.
- Controllers (future web) call `orchestrator.run_all()` — no inline step sequences in web layer.

## Verification Protocol

**Quantitative success criteria:**

- [ ] End-to-end import success on fixture/mock pipeline: **pass** (TRACKING_MATRIX INC-13)
- [ ] Failed step N does not run step N+1; `job.json` records `current_stage` and error
- [ ] `recipe-import --help` documents all flags
- [ ] `MODE=import` via docker entrypoint invokes same code path as CLI script
- [ ] Partial artifacts remain in `working/<job_id>/` after failure
- [ ] GPU lock prevents overlapping Step 3 and Step 7 (unit test)

**Test cases:**

```bash
# Mocked e2e
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_orchestrator.py tests/test_import_cli.py -v

# Docker CLI (fixture URL or mock)
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm cookbook recipe-import "https://www.instagram.com/reel/TEST_ID/"
```

**Expected output:** On success, `recipes/<slug>/` package exists and `recipes.db` has row; on failure, actionable error and debug log stub entries.

## Rollback Procedure

1. Disable `MODE=import` in entrypoint (log "not ready"); use Testing GUI single-step mode (INC-14a) for manual pipeline.
2. Revert `app/workflow/` and CLI registration; Steps 1–9 remain usable individually.
3. In-flight jobs in `working/` are safe to delete manually; no partial writes to `recipes/` if Step 9 did not complete.
