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

## Container Strategy

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
│  │  ─ Distilled recipe formatter (production)        │  │
│  │  ─ MVP: teacher-sized model until distill ready   │  │
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
| Unsloth (distillation) | Separate training env | **Separate `Dockerfile.train`** — export GGUF/Modelfile → `ollama create` |
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
4. Entrypoint: `scripts/docker-entrypoint.sh` — validate ffmpeg/yt-dlp, create volume dirs, then exec command

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
# MVP bootstrap model (replace after distillation)
docker compose exec ollama ollama pull qwen2.5:3b-instruct

# After distillation — import custom model
docker compose exec ollama ollama create cookbook-formatter -f /path/to/Modelfile
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

## Environment Variables (.env.example)

```bash
# Paths (inside container)
REPOSITORY_PATH=/data/recipes
WORKING_DIR=/data/working
DATABASE_PATH=/data/db/recipes.db

# Whisper
WHISPER_MODEL=large-v3
WHISPER_DEVICE=cuda          # cuda | cpu (cpu for test compose)

# Formatter (Ollama sidecar — decision locked)
FORMATTER_PROVIDER=ollama
OLLAMA_HOST=http://ollama:11434
FORMATTER_MODEL=cookbook-formatter    # custom after distillation; bootstrap: qwen2.5:3b-instruct

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

## Distillation Training (Later Phase)

**Not in the runtime image.** Separate workflow:

- `docker/Dockerfile.train` — Unsloth + CUDA devel image, large VRAM or cloud GPU
- Run manually: `docker build -f docker/Dockerfile.train -t cookbook-train .`
- Output: LoRA adapter or GGUF → `ollama create cookbook-formatter -f Modelfile`
- Set `FORMATTER_MODEL=cookbook-formatter` in `.env`; no app rebuild required

---

## Ollama Formatter Lifecycle

| Phase | Model in Ollama | How |
|---|---|---|
| MVP bootstrap | `qwen2.5:3b-instruct` (or similar small model) | `ollama pull` — temporary until enough training data |
| Data collection | Same — teacher-quality output reviewed/corrected in web UI | Transcript → recipe pairs saved for distillation |
| Distillation | `cookbook-formatter` (custom) | Train via Unsloth → export Modelfile → `ollama create` |
| Production | `cookbook-formatter` | Default formatter; bootstrap model removed |

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
| INC-01 | Add Dockerfile, compose files (+ ollama service), entrypoint, `.env.example` |
| INC-06 | Verify faster-whisper CUDA inside GPU compose |
| INC-10 | `FormatterProvider` calls Ollama HTTP API; structured JSON output |
| INC-10b | Import distilled model into Ollama; swap `FORMATTER_MODEL` |
| INC-13 | CLI invoked via `docker compose run` |
| INC-14 | Web port exposed via compose (ollama stays internal) |

---

## Open Decisions

- [ ] Base image: `nvidia/cuda` runtime vs `python:3.12-slim` + CUDA wheels (test on target server)
- [ ] Bind-mount `./recipes` vs named volume only (bind-mount preferred for easy backup)
- [x] **Ollama:** compose sidecar (`ollama/ollama` image) — **decided**
- [ ] Java web layer: separate container later, or defer Java entirely
- [ ] Bootstrap Ollama model: `qwen2.5:3b-instruct` vs another small model until distillation
