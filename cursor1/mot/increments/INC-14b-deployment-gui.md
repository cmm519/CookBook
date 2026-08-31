# INCREMENT 14b: Deployment GUI — Stack, Env, Models, Health

**Status:** Standard  
**Dependencies:** INC-13 (CLI import workflow — shared config/orchestrator context)

## Capability Specification

Implement the **Deployment GUI** (`MODE=deployment-gui`, port **8082**) using **FastAPI + Jinja2**. Deployers manage Docker stack lifecycle, `.env` configuration, Ollama models, health checks, and volume usage — **no pipeline step execution**.

**What changes:** Browser-based stack operations replace daily compose CLI for deployers.

**What must remain unchanged:**

- Pipeline steps — Deployment GUI must **not** run import, transcribe, or format steps.
- Secrets handling — never return raw API keys to browser after save (SRD §12).
- Ollama interim model `qwen2.5:7b-instruct` (INC-10b distillation on hold).

## Implementation Instructions

1. Add `app/web/deployment/app.py` — FastAPI factory `create_deployment_app()`.
2. Controllers (SRD §12):
   - **`StackController`** — `POST /deployment/stack/{action}` where action ∈ `start|stop|restart`; subprocess `docker compose` (or Docker API if socket mounted — document security tradeoff per SRD §21)
   - **`EnvController`** — `GET /deployment/env` (secrets redacted/masked), `POST /deployment/env` validate + write `.env`; prompt restart on change
   - **`ModelController`** — `GET /deployment/models` list Ollama models via `http://ollama:11434/api/tags`; `POST /deployment/models/pull` body `{ "name": "qwen2.5:7b-instruct" }`
   - **`HealthController`** — `GET /deployment/health` structured pass/fail: ffmpeg, yt-dlp, GPU visibility (`nvidia-smi` or torch CUDA check), Ollama reachable, disk writable on volume mounts
   - **`VolumeController`** — `GET /deployment/volumes` disk usage for `recipes/`, `dataset/`, `working/`, db, model caches
3. Templates (SRD §13 — Deployment GUI windows):
   - **Stack dashboard** — service cards (cookbook, ollama), status/uptime, restart buttons, GPU indicator
   - **Env editor** — key/value form with masked secrets
   - **Model panel** — installed models list, pull new model field
   - **Health check** — run suite button, pass/fail list
   - **Log viewer** — tail last N lines per service (`docker compose logs --tail`)
4. Entrypoint: `MODE=deployment-gui` → uvicorn on port **8082**.
5. Constraints:
   - Warn before restart if import jobs running (check `working/*/job.json` for `status=running`)
   - GPU compose override toggle documented (link to `docker-compose.gpu.yml`)
6. Tests:
   - `tests/test_deployment_gui.py` — mock subprocess and Ollama HTTP; verify secrets redacted in GET env
   - Verify no route under `/deployment/` calls `PipelineOrchestrator.run_all`

**Architectural constraints (SRD §10–13):**

- Deployment GUI is **infrastructure only** — no `steps/` imports except optional health probes.
- Default stack control: subprocess `docker compose` from container (may require Docker socket mount — document in DOCKER.md).

## Verification Protocol

**Quantitative success criteria:**

- [ ] Health suite returns pass/fail for ffmpeg, yt-dlp, Ollama, disk writable
- [ ] `GET /deployment/env` masks `FORMATTER_API_KEY` and similar secrets
- [ ] Model list returns installed Ollama models when sidecar running
- [ ] Stack start/stop invokes compose subprocess (mocked in unit tests)
- [ ] No deployment route triggers pipeline steps
- [ ] Server starts on 8082 with `MODE=deployment-gui`
- [ ] `pytest tests/test_deployment_gui.py` passes

**Test cases:**

```bash
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_deployment_gui.py -v
docker compose run --rm -e MODE=deployment-gui -p 8082:8082 cookbook
curl -s http://localhost:8082/deployment/health | jq .
```

**Expected output:** JSON health report; env keys visible with secrets masked; model pull returns success when Ollama up.

## Rollback Procedure

1. Disable `MODE=deployment-gui`; deployers use host `docker compose` and `CookBook-CLI.bat` per USER_GUIDE.
2. Remove `app/web/deployment/` — no data loss; `.env` on host unchanged.
3. If env write corrupted `.env`, restore from `.env.example` + Setup.bat prompts.
