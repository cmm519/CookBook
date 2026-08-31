# INCREMENT 1: Project Skeleton + Config + Docker

**Status:** Standard  
**Dependencies:** None

## Capability Specification

Create the project repository structure, dependency management, configuration loading, baseline test harness, and **Docker deployment scaffold**. After this increment the project builds into a container, tests run (even if empty), configuration is loadable from environment variables and `.env`, and `docker compose` starts the app shell.

**What changes:** Empty repository → runnable project skeleton with config module and Docker files.

**What must remain unchanged:** N/A (first increment).

## Implementation Instructions

1. Create project layout:

```text
recipe-repo/
├── app/
│   ├── downloader/
│   ├── media/
│   ├── transcription/
│   ├── vision/
│   ├── extraction/
│   ├── formatting/
│   ├── storage/
│   ├── search/
│   ├── workflow/
│   ├── web/
│   ├── shopping/
│   ├── bugreport/
│   └── config/
├── docker/
│   ├── Dockerfile              # Runtime image (GPU-capable)
│   ├── Dockerfile.dev          # Dev image (+ editable install)
│   └── Dockerfile.train        # Stub only — distillation later
├── dataset/                    # Phase 0 bind-mount (host-side layout)
│   ├── raw/                    # MODE=download output (*.mp4)
│   ├── transcripts/            # MODE=transcribe output (*.txt, *.json)
│   ├── urls.txt                # optional batch input
│   └── manifest.json           # batch job ledger (created on first run)
├── recipes/
├── tests/
├── scripts/
│   └── docker-entrypoint.sh    # reads MODE env var and dispatches
├── working/
├── docker-compose.yml
├── docker-compose.gpu.yml
├── docker-compose.test.yml
├── .env.example
├── pyproject.toml
├── README.md
└── .gitignore
```

2. Add `pyproject.toml` with Python 3.12+, pydantic, pytest, faster-whisper, yt-dlp dependencies.
3. Implement `app/config/` module:
   - Load from environment variables with sensible defaults
   - Support `.env` file (provide `.env.example`)
   - Config keys: `REPOSITORY_PATH`, `WORKING_DIR`, `DATABASE_PATH`, `DATASET_PATH`, `WHISPER_MODEL`, `WHISPER_DEVICE`, `FORMATTER_PROVIDER`, `FRAME_INTERVAL`, `MODE`, `DOWNLOAD_LIMIT`, `DOWNLOAD_SOURCE_URL`, etc.
   - Container paths default to `/data/recipes`, `/data/working`, `/data/db/recipes.db`, `/data/dataset`
4. Add `docker/Dockerfile`:
   - Base: CUDA runtime or python:3.12-slim with ctranslate2 CUDA wheels
   - Install ffmpeg, yt-dlp via apt/pip
   - Non-root `cookbook` user
   - Entrypoint: `scripts/docker-entrypoint.sh` — reads `MODE` and dispatches:
     - `download` → batch yt-dlp fetch to `/data/dataset/raw/` (stub OK in INC-01)
     - `transcribe` → faster-whisper on `/data/dataset/raw/` → `/data/dataset/transcripts/` (stub OK)
     - `web` → start web server (stub/no-op OK until INC-14)
     - `import` → `recipe-import` CLI (stub OK until INC-13)
     - `test` → `pytest` (default test compose)
5. Add compose files per [`DOCKER.md`](../../DOCKER.md):
   - `docker-compose.yml` — `cookbook` + `ollama` services, volume mounts (`./dataset:/data/dataset`), port 8080
   - `docker-compose.gpu.yml` — NVIDIA device reservation for both services
   - `docker-compose.test.yml` — CPU only, mock Ollama formatter, run pytest
6. Add `__init__.py` to all packages.
7. Add smoke tests: config load, docker build succeeds.
8. Update README with Docker setup and run commands.

## Verification Protocol

**Quantitative success criteria:**

- [ ] `docker compose -f docker-compose.test.yml run --rm cookbook pytest` passes
- [ ] `docker compose build cookbook` succeeds
- [ ] Config module loads without error when `.env` is absent (uses defaults)
- [ ] Config module loads custom values when env vars are set
- [ ] All package directories exist with `__init__.py`
- [ ] Entrypoint creates `/data/recipes`, `/data/working`, `/data/db`, `/data/dataset/raw`, `/data/dataset/transcripts` if missing
- [ ] `MODE=download` exits 0 (stub logs "not implemented" OK; full logic in INC-04)
- [ ] `MODE=transcribe` exits 0 (stub OK; full logic in INC-06)
- [ ] `MODE=test` runs pytest via test compose

**Test cases:**

```bash
docker compose build cookbook
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/ -v
docker compose run --rm cookbook python -c "from app.config import load_config; c = load_config(); print(c.repository_path)"
docker compose run --rm -e MODE=download -v ./dataset:/data/dataset cookbook
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm -e MODE=transcribe -v ./dataset:/data/dataset cookbook
```

**Expected output:** Image builds; test suite passes; config prints `/data/recipes`; Phase 0 mode stubs run without crash.

## Rollback Procedure

N/A — first increment. If structure is wrong, delete and recreate before proceeding to Increment 2.
