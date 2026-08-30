# cursor1 — Requirements Workspace

This folder contains the working requirements and Module of Thought (MoT) development docs for the CookBook recipe repository project.

## Contents

| File / Folder | Purpose |
|---|---|
| [`SOFTWARE_REQUIREMENTS.md`](SOFTWARE_REQUIREMENTS.md) | Software Requirements Specification — filled incrementally across 5 sessions |
| [`DOCKER.md`](DOCKER.md) | **Container deployment plan** — dependency map, compose files, GPU rules |
| [`mot/MASTER_CONTEXT.md`](mot/MASTER_CONTEXT.md) | MoT Prompt 0 — persistent context loaded at every dev session |
| [`mot/INCREMENTS.md`](mot/INCREMENTS.md) | Ordered capability list with critical checkpoints |
| [`mot/TRACKING_MATRIX.md`](mot/TRACKING_MATRIX.md) | Performance metrics across increments and variants |
| [`mot/increments/`](mot/increments/) | Individual increment prompt files |

## Source Documents (repo root)

- [`Module of Thought_instr.md`](../Module%20of%20Thought_instr.md) — MoT methodology
- [`Gutted Software Requirements Document Template.md`](../Gutted%20Software%20Requirements%20Document%20Template.md) — original SRD template (unchanged)
- [`RECIPE_REPO_PLAN.md`](../RECIPE_REPO_PLAN.md) — pipeline phases and implementation order
- [`DISTALATION.MD`](../DISTALATION.MD) — model distillation strategy (teacher → distilled formatter)
- [`Planning scratchpad`](../Planning%20scratchpad) — full product vision notes (do not edit)

## Deployment: Docker-First

All runtime dependencies are **inside the container**. The host only needs:

- Docker Engine 24+
- Docker Compose v2
- NVIDIA Container Toolkit + driver (GPU hosts)

See [`DOCKER.md`](DOCKER.md) for the full dependency map, compose file layout, volume mounts, and common commands.

**Quick reference:**

```bash
# Start web UI (GPU)
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

# Import a recipe
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm cookbook recipe-import "<url>"

# Run tests (no GPU)
docker compose -f docker-compose.test.yml run --rm cookbook pytest
```

## SRD Fill-Out Workflow

The SRD is filled collaboratively in **5 sessions**. Confirm or correct each block before moving to the next.

| Session | Sections | Topics | Status |
|---|---|---|---|
| **A** | 1–3 | Project overview, startup/initialization, data requirements | **Done** (Docker notes added) |
| **B** | 4–5 | Persistence, primary operations (import, search, web CRUD, shopping list, bug report) | Pending |
| **C** | 6–8 | Views/windows, agents (Whisper + formatter + maintenance), constants/config | Pending |
| **D** | 9–13 | Error handling, architecture, model/controller/view specs | Pending |
| **E** | 14–21 | Documentation, testing, dev process, acceptance tests, constraints, deliverables, open questions | Pending |

## Model Strategy (Key Decision)

Two separate local-model roles, two containers:

- **Transcription:** faster-whisper in `cookbook` container — always local, MVP
- **Recipe formatting:** **Ollama sidecar** — bootstrap small model → custom `cookbook-formatter` after distillation

Whisper and Ollama share the GPU **sequentially** (transcribe first, then format). Ollama is not exposed to the host — internal Docker network only.

```bash
# First-time: pull bootstrap formatter model
docker compose exec ollama ollama pull qwen2.5:3b-instruct
```

## Next Steps

1. Review [`DOCKER.md`](DOCKER.md) — confirm base image and volume strategy
2. Begin **Session B** — fill SRD Sections 4–5 (persistence and primary operations)
3. When SRD is complete, begin MoT Increment 1 per [`mot/increments/INC-01-project-skeleton.md`](mot/increments/INC-01-project-skeleton.md)
