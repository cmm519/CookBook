# CookBook workspace (`cursor1/`)

This folder is the **full CookBook project**: application code, Docker stack, dataset/recipes volumes, and requirements / MoT docs.

## Application layout

| Path | Purpose |
|---|---|
| `app/` | Python package (pipeline, CLI, web GUIs) |
| `scripts/` | Entrypoint + seed helpers |
| `tests/` | pytest |
| `docker/` | Dockerfile |
| `docker-compose*.yml` | Stack definitions |
| `CookBook-Setup.bat` / `CookBook-CLI.bat` | Windows deployer tools |
| `dataset/` / `recipes/` / `data/` / `working/` | Local volumes (mostly gitignored) |

## Docs

| File / Folder | Purpose | Primary audience |
|---|---|---|
| [`USER_GUIDE.md`](USER_GUIDE.md) | **Setup, usage, dependencies, DebugLog** — deployer vs end user | Deployer, end user, tester |
| [`SOFTWARE_REQUIREMENTS.md`](SOFTWARE_REQUIREMENTS.md) | Software Requirements Specification — filled incrementally | Developers |
| [`DOCKER.md`](DOCKER.md) | Container deployment, MODE reference, volumes | Deployer, developers |
| [`mot/MASTER_CONTEXT.md`](mot/MASTER_CONTEXT.md) | MoT Prompt 0 — persistent context loaded at every dev session |
| [`mot/INCREMENTS.md`](mot/INCREMENTS.md) | Ordered capability list with critical checkpoints |
| [`mot/TRACKING_MATRIX.md`](mot/TRACKING_MATRIX.md) | Performance metrics across increments and variants |
| [`mot/increments/`](mot/increments/) | Individual increment prompt files |

## Source Documents

- [`Module of Thought_instr.md`](Module%20of%20Thought_instr.md) — MoT methodology
- [`Gutted Software Requirements Document Template.md`](Gutted%20Software%20Requirements%20Document%20Template.md) — original SRD template (unchanged)
- [`RECIPE_REPO_PLAN.md`](RECIPE_REPO_PLAN.md) — pipeline phases and implementation order
- [`DISTALATION.MD`](DISTALATION.MD) — model distillation strategy (teacher → distilled formatter)
- [`Planning scratchpad`](Planning%20scratchpad) — full product vision notes (do not edit)

## Deployment: Docker-First

All runtime dependencies are **inside the container**. The host only needs:

- Docker Engine 24+
- Docker Compose v2
- NVIDIA Container Toolkit + driver (GPU hosts)

Run all `docker compose` commands **from this folder** (`cursor1/`).

See [`DOCKER.md`](DOCKER.md) for the full dependency map, compose file layout, volume mounts, and common commands.

**Quick reference:**

```bash
# Start web UI (GPU) — Phase 1+ full app
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

# Import a recipe — Phase 1+ full app
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm cookbook recipe-import "<url>"

# Run tests (no GPU)
docker compose -f docker-compose.test.yml run --rm -e MODE=test cookbook
```

### Phase 0 quick start (download + transcribe only)

Phase 0 builds a local dataset **before** the full recipe app. No web UI, formatting, or `recipes/` writes — only videos and transcripts under `./dataset/`.

```bash
# 1. Create dataset layout on host
mkdir -p dataset/raw dataset/transcripts
# Optional: add reel URLs (one per line)
# echo "https://www.instagram.com/reel/..." >> dataset/urls.txt

# 2. Batch download (up to 50 URLs) — CPU only
docker compose run --rm \
  -e MODE=download \
  -e DOWNLOAD_LIMIT=50 \
  -v ./dataset:/data/dataset \
  cookbook

# Or download from an Instagram hub URL:
# docker compose run --rm -e MODE=download \
#   -e DOWNLOAD_SOURCE_URL="https://www.instagram.com/<profile>/reels/" \
#   -e DOWNLOAD_LIMIT=50 -v ./dataset:/data/dataset cookbook

# 3. Batch transcribe downloaded videos — GPU recommended
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm \
  -e MODE=transcribe \
  -e WHISPER_MODEL=large-v3 \
  -v ./dataset:/data/dataset \
  cookbook

# 4. Verify outputs
ls dataset/raw/ dataset/transcripts/ dataset/manifest.json
```

See [`DOCKER.md`](DOCKER.md) for full `MODE` reference and volume layout.

## SRD Fill-Out Workflow

The SRD is filled collaboratively in **5 sessions**. Confirm or correct each block before moving to the next.

| Session | Sections | Topics | Status |
|---|---|---|---|
| **A** | 1–3 | Project overview, startup/initialization, data requirements | **Done** (Docker notes added) |
| **B** | 4–5 | Persistence, primary operations (import, search, web CRUD, shopping list, bug report) | **Done** |
| **C** | 6–8 | Three GUIs (testing, deployment, production), agents, config | **Done** |
| **D** | 9–13 | Error handling, step-based architecture, model/controller/view | **Done** |
| **E** | 14–21 | Documentation, testing, dev process, acceptance tests, constraints, deliverables, open questions | **Done** (UML deferred) |

## Model Strategy (Key Decision)

Two separate local-model roles, two containers:

- **Transcription:** faster-whisper in `cookbook` container — always local, MVP
- **Recipe formatting:** **Ollama sidecar** — interim **`qwen2.5:7b-instruct`**. Custom distilled `cookbook-formatter` is **on hold** (INC-10b).

Whisper and Ollama share the GPU **sequentially** (transcribe first, then format). Ollama is not exposed to the host — internal Docker network only.

```bash
# First-time: pull interim formatter model
docker compose exec ollama ollama pull qwen2.5:7b-instruct
```

## Three Web GUIs

| GUI | MODE | Port | Purpose |
|---|---|---|---|
| **Testing** | `testing-gui` | 8081 | Add links; run pipeline steps 1–9 one at a time |
| **Deployment** | `deployment-gui` | 8082 | Manage Docker stack, env, models, health |
| **Production** | `web` | 8080 | Recipe viewer, import, shopping list |

Architecture: one **`PipelineStep` class per stage** under `app/steps/` — shared by CLI, Testing GUI, and full import.

## Next Steps

1. Review [`DOCKER.md`](DOCKER.md) — confirm base image and volume strategy
2. Begin **Session B** — fill SRD Sections 4–5 (persistence and primary operations)
3. When SRD is complete, begin MoT Increment 1 per [`mot/increments/INC-01-project-skeleton.md`](mot/increments/INC-01-project-skeleton.md)
