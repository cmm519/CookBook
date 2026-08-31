# Docker Deployment Plan

> Replaces manual host dependency installation. All runtime dependencies (ffmpeg, yt-dlp, Python packages, CUDA libs for Whisper) are baked into containers. The host only needs Docker Engine and (for GPU) the NVIDIA Container Toolkit.

## Host Requirements (Minimal)

| Host dependency | Purpose | Required |
|---|---|---|
| Docker Engine 24+ | Run containers | Yes |
| Docker Compose v2 | Orchestration | Yes |
| NVIDIA Container Toolkit | GPU passthrough to containers | Yes (transcription + local formatter) |
| NVIDIA driver (host) | CUDA support | Yes (GPU hosts) |

Everything else lives **inside** the container.

---

## One-Shot Setup (Windows)

**Deployers** (not end users) double-click **`CookBook-Setup.bat`** in this folder (`cursor1/`). No manual `docker compose` required for first run.

**User guide:** [`USER_GUIDE.md`](USER_GUIDE.md) — dependencies, deployer vs end-user tools, DebugLog interpretation.

**Prompts:**

| Prompt | `.env` variable | Default |
|---|---|---|
| SQLite database folder | `HOST_DB_DIR` | `%USERPROFILE%\CookBook\db` |
| Ollama / trained models folder | `HOST_OLLAMA_DIR` | `%USERPROFILE%\CookBook\models` |
| Dataset (videos, transcripts) | `HOST_DATASET_DIR` | `%USERPROFILE%\CookBook\dataset` |
| Recipe repository | `HOST_RECIPES_DIR` | `%USERPROFILE%\CookBook\recipes` |
| GPU choice | `WHISPER_DEVICE` | `cuda` (option 2 → `cpu`) |
| Formatter model to pull | `FORMATTER_MODEL` | `qwen2.5:7b-instruct` |

**Actions after prompts:**

1. Create host directories
2. Write `.env` with forward-slash paths (`C:/Users/...`) for Docker Desktop
3. `docker compose build` (+ `-f docker-compose.gpu.yml` if GPU)
4. Optionally `docker compose up -d` and `ollama pull`

**Post-setup menu:** `CookBook-CLI.bat` — download, transcribe, tests, stack status.

All compose files bind-mount `HOST_*_DIR` from `.env` instead of opaque named volumes for db and models.

---

**Two-service compose stack:** GPU-enabled `cookbook` app + **Ollama sidecar** for recipe formatting.

```text
┌─────────────────────────────────────────────────────────┐
│  Host (personal server)                                 │
│  Docker Engine + NVIDIA Container Toolkit               │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │  cookbook  (GPU for Whisper transcription)        │  │
│  │  ─ Python 3.12, ffmpeg, yt-dlp                    │  │
│  │  ─ faster-whisper + CUDA                          │  │
│  │  ─ CLI + web server                               │  │
│  │  ─ Calls Ollama HTTP API for recipe formatting    │  │
│  │  Volumes: recipes/, working/, data/, whisper-cache│
│  └───────────────────────┬───────────────────────────┘  │
│                          │ http://ollama:11434          │
│  ┌───────────────────────▼───────────────────────────┐  │
│  │  ollama  (GPU for formatter model)                │  │
│  │  ─ Interim formatter: qwen2.5:7b-instruct         │  │
│  │  ─ Distilled cookbook-formatter: ON HOLD          │  │
│  │  Volume: ollama-models/                           │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Why Ollama as a compose sidecar (decision locked):**

- Formatter models swap without rebuilding the app image (`ollama pull`, Modelfile import)
- Distillation output (GGUF/LoRA → Ollama Modelfile) deploys by updating the sidecar, not the app
- App container stays lean — only Whisper + pipeline code
- Official `ollama/ollama` image; no host Ollama install required
- Network isolated on internal Docker network; only `cookbook` web port exposed to host

**GPU sharing on 8GB VRAM:**

- Both services reserve the same GPU via compose overrides
- Pipeline enforces **sequential** usage: Whisper runs in `cookbook` → completes → HTTP POST to `ollama` for formatting
- Ollama config: `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_NUM_PARALLEL=1`
- Only one import job runs GPU stages at a time (worker lock in `cookbook`)

---

## Dependency Map: Host vs Container

| Dependency | Old plan (manual) | Docker plan |
|---|---|---|
| Python 3.12+ | Install on host | `python:3.12-slim` base + app deps in image |
| ffmpeg | apt/brew on host | `apt-get install ffmpeg` in Dockerfile |
| yt-dlp | pip on host | `pip install yt-dlp` in Dockerfile |
| faster-whisper | pip + CUDA on host | pip in Dockerfile; `nvidia/cuda` runtime base or ctranslate2 CUDA wheel |
| pydantic, pytest, httpx | pip on host | pip in Dockerfile; dev deps in `Dockerfile.dev` or compose profile |
| sqlite3 | stdlib | included |
| Whisper model weights | Downloaded to host cache | Volume `whisper-cache` on `cookbook` service |
| Recipe formatter model | API or local | **Ollama sidecar** — `ollama-models` volume; HTTP API from `cookbook` |
| API keys (formatter MVP fallback) | `.env` on host | `.env` via compose; use only if `FORMATTER_PROVIDER=api` during bootstrap |
| Unsloth (distillation) | Separate training env | **ON HOLD** — `Dockerfile.train` / INC-10b deferred; see [`DISTALATION.MD`](DISTALATION.MD) |
| Ollama runtime | Host install | **`ollama/ollama` compose service** (decision locked) |

---

## File Layout (added to project skeleton)

```text
recipe-repo/
├── docker/
│   ├── Dockerfile              # Production/runtime image (GPU-capable)
│   ├── Dockerfile.dev          # Dev image (+ pytest, linters, editable install)
│   └── Dockerfile.train        # Distillation training (later — Unsloth, not MVP)
├── docker-compose.yml          # Base: app service, volumes, env
├── docker-compose.gpu.yml      # Override: deploy GPU resources
├── docker-compose.test.yml     # CI: no GPU, mocked providers
├── .env.example                # All configurable env vars
└── ... (existing app/ layout)
```

---

## Dockerfile (Runtime) — Key Decisions

**Base image:** `nvidia/cuda:12.4.1-runtime-ubuntu22.04` + Python 3.12 via deadsnakes PPA, OR `python:3.12-slim` with ctranslate2 CUDA wheels if compatible on target platform.

**Layers:**

1. System: `ffmpeg`, `curl`, minimal build tools (removed in final stage if multi-stage)
2. Python: `pip install` from `pyproject.toml` / `requirements.txt`
3. App: copy `app/` only (not recipes or working data)
4. Entrypoint: `scripts/docker-entrypoint.sh` — validate ffmpeg/yt-dlp, create volume dirs, read `MODE`, dispatch workflow, then exec command

**Non-root user:** Run app as `cookbook` user (uid 1000) for personal server security.

**Image size target:** < 4GB excluding model cache (models live on volume).

---

## docker-compose.yml

```yaml
services:
  cookbook:
    build:
      context: .
      dockerfile: docker/Dockerfile
    env_file: .env
    ports:
      - "${WEB_PORT:-8080}:8080"
    volumes:
      - ./recipes:/data/recipes
      - ./working:/data/working
      - ./dataset:/data/dataset
      - cookbook-db:/data/db
      - whisper-cache:/root/.cache
    depends_on:
      - ollama
    restart: unless-stopped
    # GPU added via docker-compose.gpu.yml override

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama-models:/root/.ollama
    environment:
      - OLLAMA_MAX_LOADED_MODELS=1
      - OLLAMA_NUM_PARALLEL=1
    restart: unless-stopped
    # GPU added via docker-compose.gpu.yml override
    # Not exposed to host — internal network only

volumes:
  cookbook-db:
  whisper-cache:
  ollama-models:
```

**Persistent data:**

| Mount | Service | Contents |
|---|---|---|
| `./recipes` | cookbook | Recipe packages (source of truth) |
| `./working` | cookbook | Import job scratch space |
| `./dataset` | cookbook | Phase 0 batch data (`raw/`, `transcripts/`, `manifest.json`) |
| `cookbook-db` | cookbook | SQLite `recipes.db` |
| `whisper-cache` | cookbook | faster-whisper model weights |
| `ollama-models` | ollama | Formatter LLM weights (distilled or bootstrap) |

---

## docker-compose.gpu.yml (override)

```yaml
services:
  cookbook:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Both services share the host GPU. Sequential pipeline usage prevents concurrent VRAM pressure.

**Usage:**

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm cookbook recipe-import "<url>"
```

**Pull formatter model (first-time setup):**

```bash
# Interim formatter (default until distilled model is trained)
docker compose exec ollama ollama pull qwen2.5:7b-instruct

# CPU-only or very tight VRAM fallback
# docker compose exec ollama ollama pull qwen2.5:3b-instruct

# Future (ON HOLD): custom distilled model
# docker compose exec ollama ollama create cookbook-formatter -f /path/to/Modelfile
```

---

## Common Commands

| Task | Command |
|---|---|
| Start web UI | `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d` |
| Import recipe (CLI) | `docker compose run --rm cookbook recipe-import "<url>"` |
| Search | `docker compose run --rm cookbook recipe-search "miso"` |
| Run tests (no GPU) | `docker compose -f docker-compose.test.yml run --rm cookbook pytest` |
| Shell inside container | `docker compose run --rm cookbook bash` |
| Rebuild after code change | `docker compose build cookbook` |
| Pull formatter model | `docker compose exec ollama ollama pull <model>` |
| List Ollama models | `docker compose exec ollama ollama list` |
| Ollama logs | `docker compose logs -f ollama` |

---

## Modular Startup Modes

The container entrypoint reads **`MODE`** (default `web`) and runs exactly one workflow before exiting (batch modes) or staying up (web).

| `MODE` | Behavior | GPU | Port | Typical use |
|---|---|---|---|---|
| `download` | Batch yt-dlp fetch → `dataset/raw/` | No | — | Phase 0 CLI |
| `transcribe` | Batch Whisper → `dataset/transcripts/` | Yes | — | Phase 0 CLI |
| `testing-gui` | **Testing GUI** — add URLs, run steps 1–9 individually | Per step | 8081 | Dev/operator workbench |
| `deployment-gui` | **Deployment GUI** — stack, env, models, health | No | 8082 | Personal server ops |
| `web` | **Production Web UI** — recipes, import, shopping | Yes | 8080 | End users |
| `import` | Single full pipeline CLI | Yes | — | Phase 1+ |
| `test` | Run pytest and exit | No | — | CI |

Set mode via environment: `-e MODE=download` or in `.env`.

### Compose examples

**Phase 0 — batch download (CPU only, no GPU override required):**

```bash
# Option A: URL list file at ./dataset/urls.txt (one reel URL per line)
docker compose run --rm \
  -e MODE=download \
  -e DOWNLOAD_LIMIT=50 \
  -v ./dataset:/data/dataset \
  cookbook

# Option B: Instagram hub/profile URL
docker compose run --rm \
  -e MODE=download \
  -e DOWNLOAD_SOURCE_URL="https://www.instagram.com/<profile>/reels/" \
  -e DOWNLOAD_LIMIT=50 \
  -v ./dataset:/data/dataset \
  cookbook
```

**Phase 0 — batch transcribe (GPU recommended):**

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm \
  -e MODE=transcribe \
  -e WHISPER_MODEL=large-v3 \
  -e WHISPER_DEVICE=cuda \
  -v ./dataset:/data/dataset \
  -v whisper-cache:/root/.cache \
  cookbook
```

**Run tests:**

```bash
docker compose -f docker-compose.test.yml run --rm \
  -e MODE=test \
  cookbook
```

**Full app (Phase 1+) — web UI:**

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
# equivalent: -e MODE=web (default)
```

### `dataset/` volume layout

Bind-mount `./dataset` → `/data/dataset` inside the container. Phase 0 reads and writes only under this tree.

```text
dataset/
├── urls.txt              # optional input for MODE=download (one URL per line)
├── manifest.json         # batch job ledger: url, reel_id, filenames, status, timestamps
├── raw/                  # downloaded videos (*.mp4) — MODE=download output
│   └── {reel_id}.mp4
└── transcripts/          # MODE=transcribe output
    ├── {reel_id}.txt     # plain-text transcript
    └── {reel_id}.json    # timestamped segments
```

**Add to `docker-compose.yml` volumes (cookbook service):**

```yaml
volumes:
  - ./dataset:/data/dataset
```

Entrypoint creates `raw/` and `transcripts/` on first run if missing. `manifest.json` is created or updated by batch modes.

---

## Environment Variables (.env.example)

```bash
# Startup mode (entrypoint dispatch)
MODE=web                       # web | download | transcribe | import | test

# Paths (inside container)
REPOSITORY_PATH=/data/recipes
WORKING_DIR=/data/working
DATABASE_PATH=/data/db/recipes.db
DATASET_PATH=/data/dataset

# Phase 0 batch download
DOWNLOAD_LIMIT=50              # hard cap 50 URLs per run
DOWNLOAD_SOURCE_URL=           # optional Instagram hub/profile URL
# Batch input file: /data/dataset/urls.txt (one URL per line)

# Whisper
WHISPER_MODEL=large-v3
WHISPER_DEVICE=cuda          # cuda | cpu (cpu for test compose)

# Formatter (Ollama sidecar — decision locked)
FORMATTER_PROVIDER=ollama
OLLAMA_HOST=http://ollama:11434
FORMATTER_MODEL=qwen2.5:7b-instruct  # interim default; distilled cookbook-formatter ON HOLD

# Formatter fallback (bootstrap only — optional API teacher before distill)
# FORMATTER_PROVIDER=api
# FORMATTER_API_KEY=
# FORMATTER_MODEL=

# Pipeline
FRAME_INTERVAL=1
KEEP_WORKING=false
VIDEO_PROCESSING_DEFAULT=true

# Web
WEB_PORT=8080
```

---

## GPU / VRAM Rules (enforced across cookbook + ollama)

- Whisper (in `cookbook`) and formatter (in `ollama`) run **sequentially**, never concurrently
- `cookbook` calls `http://ollama:11434/api/generate` only after transcription completes
- Ollama: `OLLAMA_MAX_LOADED_MODELS=1` limits loaded formatter to one model
- Only one import job runs GPU stages at a time (pipeline worker lock in `cookbook`)
- `WHISPER_DEVICE=cpu` fallback in test/CI compose (Ollama mocked, no NVIDIA required)

---

## CI / Testing Compose

`docker-compose.test.yml`:

- No GPU reservation
- `WHISPER_DEVICE=cpu`
- Mock formatter provider
- Mount `tests/fixtures/` read-only
- Run `pytest` on container start

---

## Distillation Training (ON HOLD — future development)

> **Status:** Deferred. Use `qwen2.5:7b-instruct` via Ollama for recipe formatting until INC-10b is resumed. See [`DISTALATION.MD`](DISTALATION.MD).

**Not in the runtime image.** Separate workflow when resumed:

- `docker/Dockerfile.train` — Unsloth + CUDA devel image, large VRAM or cloud GPU
- Run manually: `docker build -f docker/Dockerfile.train -t cookbook-train .`
- Output: LoRA adapter or GGUF → `ollama create cookbook-formatter -f Modelfile`
- Set `FORMATTER_MODEL=cookbook-formatter` in `.env`; no app rebuild required

---

## Ollama Formatter Lifecycle

| Phase | Model in Ollama | How | Status |
|---|---|---|---|
| **Now (interim)** | **`qwen2.5:7b-instruct`** | `ollama pull` — structured JSON, fits 8GB VRAM after Whisper | **Active** |
| Tight VRAM / CPU | `qwen2.5:3b-instruct` | Smaller fallback if 7B OOMs | Optional |
| Data collection | Same interim model; user edits in web UI | Save transcript→recipe pairs for future training | When web UI exists |
| Distillation | `cookbook-formatter` (custom) | Unsloth → Modelfile → `ollama create` | **ON HOLD (INC-10b)** |
| Future production | `cookbook-formatter` or keep 7B if good enough | Swap `FORMATTER_MODEL` in `.env` | Deferred |

**Why `qwen2.5:7b-instruct`:** Qwen 2.5 handles instruction-following and JSON reliably; 7B is a clear step up from 3B for messy spoken transcripts. At Q4 quantization (~4.7GB) it loads comfortably on an 8GB GPU once Whisper has finished and unloaded.

**Modelfile example (after distillation):**

```dockerfile
FROM ./cookbook-formatter.gguf
PARAMETER temperature 0.1
SYSTEM You are a specialized recipe extractor. Convert transcript and OCR evidence into structured JSON recipes. Never invent missing quantities.
```

---

## MoT Increment Impact

| Increment | Docker change |
|---|---|
| INC-01 | Add Dockerfile, compose files (+ ollama service), `MODE` entrypoint dispatch, `dataset/` volume, `.env.example` |
| INC-06 | Verify faster-whisper CUDA inside GPU compose |
| INC-10 | `FormatterProvider` calls Ollama HTTP API; structured JSON output |
| INC-10b | Import distilled model into Ollama; swap `FORMATTER_MODEL` — **ON HOLD** |
| INC-13 | CLI invoked via `docker compose run` |
| INC-14 | Web port exposed via compose (ollama stays internal) |

---

## Open Decisions

- [ ] Base image: `nvidia/cuda` runtime vs `python:3.12-slim` + CUDA wheels (test on target server)
- [ ] Bind-mount `./recipes` vs named volume only (bind-mount preferred for easy backup)
- [x] **Ollama:** compose sidecar (`ollama/ollama` image) — **decided**
- [ ] Java web layer: separate container later, or defer Java entirely
- [x] **Interim Ollama formatter:** `qwen2.5:7b-instruct` (fallback: `qwen2.5:3b-instruct`) — **decided**
- [ ] **Distilled model (INC-10b):** on hold until future development
