# INCREMENT 18: Bug Report + Debug Log + Maintenance Hook

**Status:** Standard  
**Dependencies:** INC-13 (CLI import workflow — debug log stub from orchestrator)

## Capability Specification

Implement `app/bugreport/` and Production Web UI **bug reporting** with automatic **DebugLog** snapshot attachment. Deployers review reports and per-job `debug.log` files for maintenance triage.

**What changes:** End users submit bug descriptions from Production UI; system captures structured debug log (pipeline stages, model versions, errors) linked to optional `job_id` or `recipe_slug`.

**What must remain unchanged:**

- Import pipeline behavior — logging is observability only, must not alter step outcomes.
- Debug log content from USER_GUIDE format (stage, level, message, model_versions).

## Implementation Instructions

1. Extend `app/bugreport/debuglog.py` (stub from INC-13):
   - `DebugLog` model: `log_id`, `job_id`, `entries[]` (timestamp, stage, level, message), `pipeline_version`, `model_versions` (Whisper, formatter provider/model), `created_at`
   - `DebugLogWriter` — context manager per import job; write to `working/<job_id>/debug.log` (JSON lines or structured JSON)
   - Orchestrator hooks: log step start/end, duration, errors, model config at job start
2. Add `app/bugreport/reports.py`:
   - `BugReport` model per SRD §3: `report_id`, `description`, `debug_log_path`, `related_job_id`, `related_recipe_slug`, `created_at`, `status` (open/reviewed/resolved)
   - Persist reports to `working/bugreports/<report_id>.json` or SQLite table `bug_reports`
   - On submit: copy/snapshot relevant `debug.log` to `working/bugreports/<report_id>_debug.json`
3. **`BugReportController`** in `app/web/production/`:
   - `GET /bug-report` — form (description, optional job_id/recipe_slug from query params)
   - `POST /bug-report` — create report; attach latest debug log for `related_job_id` if provided
   - User-dismissible success/error messages (SRD §9)
4. Deployer-facing (minimal in this increment):
   - `GET /bug-report/{report_id}` or list in Deployment GUI log panel (optional cross-link)
   - Document DebugLog interpretation in [`USER_GUIDE.md`](../../USER_GUIDE.md) — reference existing section
5. Maintenance hook stub:
   - `app/bugreport/maintenance.py` — `list_open_reports() -> list[BugReport]` for future scheduled agent; no autonomous action in this increment
6. Templates:
   - `bug_report.html` — description textarea, optional job/recipe fields pre-filled from import failure redirect
   - Link from import error page: "Report a bug"
7. Tests:
   - `tests/test_debuglog.py` — writer appends entries; model_versions captured
   - `tests/test_bugreport.py` — submit creates report file with debug snapshot

**Architectural constraints (SRD §5.1, §9):**

- End user submits → deployer reads (audience table).
- Never include secrets (API keys) in debug log entries — redact env values.

## Verification Protocol

**Quantitative success criteria:**

- [ ] Import job produces `working/<job_id>/debug.log` with entries for each completed stage
- [ ] `model_versions` records Whisper model and formatter model/provider
- [ ] Bug report submit stores `description` + debug snapshot path
- [ ] Reports without `job_id` still succeed (description only)
- [ ] No secrets in captured debug log (grep test for `API_KEY` patterns)
- [ ] `pytest tests/test_debuglog.py tests/test_bugreport.py` passes

**Test cases:**

```bash
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_debuglog.py tests/test_bugreport.py -v
# Run mock import → verify debug.log exists → submit bug report via TestClient
```

**Expected output:** Report JSON on disk; debug snapshot references orchestrator log entries; USER_GUIDE documents field meanings.

## Rollback Procedure

1. Remove bug report routes and form — import pipeline continues with file-only debug logs.
2. Disable `DebugLogWriter` hooks in orchestrator (optional); per-step logging to stdout remains.
3. Delete `working/bugreports/` if needed — does not affect recipe data.
