# CookBook User Guide

> Who this is for, what to install, how to set up, how to use the app, and how to read debug logs.
>
> **Related docs:** [SOFTWARE_REQUIREMENTS.md](SOFTWARE_REQUIREMENTS.md) (spec) · [DOCKER.md](DOCKER.md) (containers) · [README.md](README.md) (workspace quick start)

---

## 1. Three audiences — keep these separate

CookBook has **three operator surfaces** plus **one end-user surface**. Do not give end users deployment or testing tools.

| Audience | Who | Tools | Purpose |
|---|---|---|---|
| **Deployer / operator** | You (or whoever owns the server) | `CookBook-Setup.bat`, `CookBook-CLI.bat`, Deployment GUI (`MODE=deployment-gui`, port **8082**) | Install Docker stack, pick storage paths, GPU, pull models, start/stop services, health checks |
| **Developer / tester** | You during build-out | Testing GUI (`MODE=testing-gui`, port **8081**), `CookBook-CLI.bat`, CLI `MODE=download` / `transcribe` / `test` | Add reel URLs, run pipeline **steps 1–9 one at a time**, inspect intermediate files, build distillation dataset |
| **End user** | Household / guests using the recipe app | Production Web UI (`MODE=web`, port **8080**) | Import reels, browse/search recipes, edit, rate, shopping list, submit bug reports |
| **Maintenance agent** (future) | Scheduled background task | Reads `DebugLog` + `BugReport` files | Triage errors without operator watching logs live |

```text
 DEPLOYMENT (8082)          TESTING (8081)              END USER (8080)
 ─────────────────          ──────────────              ───────────────
 Setup.bat / CLI            Step-by-step pipeline       Import & browse recipes
 Start/stop stack           Dataset collection          Edit / rate / shop list
 Env + models + health      Debug individual steps      Bug report (captures DebugLog)
```

**Rule:** End users never need Docker, `.env`, or compose commands. Deployers never need the recipe shopping list UI for daily work.

---

## 2. Dependencies explained

### 2.1 What you install on the host (deployer only)

These are **not** inside CookBook — you install once on the machine that runs Docker.

| Dependency | Required? | Purpose |
|---|---|---|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows) or Docker Engine (Linux) | **Yes** | Runs all CookBook containers |
| Docker Compose v2 | **Yes** | Orchestrates `cookbook` + `ollama` services |
| NVIDIA GPU driver | If using GPU | Lets containers use your graphics card |
| NVIDIA Container Toolkit | If using GPU | Passes GPU into Docker (`docker-compose.gpu.yml`) |

**You do not install** Python, ffmpeg, yt-dlp, Whisper, or Ollama on the host — those live in containers.

### 2.2 What runs inside the `cookbook` container

Installed automatically when the Docker image builds (`pip install .` from [`pyproject.toml`](../pyproject.toml)).

| Dependency | Purpose |
|---|---|
| **Python 3.12** | Application runtime |
| **ffmpeg** | Extract audio from video; extract frames |
| **yt-dlp** | Download Instagram reels + post metadata (caption, comments) |
| **faster-whisper** | Local speech-to-text ( **not** `openai-whisper` — same models, faster on GPU via CTranslate2 ) |
| **pydantic** | Validate recipe JSON and config |
| **httpx** | Call Ollama HTTP API for recipe formatting |
| **pytest** | Automated tests (`MODE=test`) |

### 2.3 What runs in the `ollama` container (separate sidecar)

| Dependency | Purpose |
|---|---|
| **ollama/ollama** image | Serves the recipe **formatter** LLM locally |
| **Formatter model** | **`qwen2.5:7b-instruct`** (interim via Ollama) | Turns transcript + metadata into structured recipe JSON. Custom distilled `cookbook-formatter` is **on hold**. |

Whisper (transcription) and Ollama (formatting) are **different services**. They share the GPU **one at a time**, not concurrently (8GB VRAM limit).

### 2.4 Where large files are stored (your chosen paths)

Set during **`CookBook-Setup.bat`** → saved in **`.env`** as `HOST_*_DIR`.

| Storage | `.env` variable | Typical host path | Contents |
|---|---|---|---|
| **Database** | `HOST_DB_DIR` | `%USERPROFILE%\CookBook\db` | SQLite `recipes.db` (search index) |
| **Trained / Ollama models** | `HOST_OLLAMA_DIR` | `%USERPROFILE%\CookBook\models` | Downloaded & fine-tuned LLM weights |
| **Whisper model cache** | `HOST_WHISPER_CACHE_DIR` | `%USERPROFILE%\CookBook\whisper-cache` | faster-whisper weights (e.g. `large-v3`) — downloaded on **first transcribe** |
| **Dataset (Phase 0)** | `HOST_DATASET_DIR` | `%USERPROFILE%\CookBook\dataset` | `raw/` videos, `transcripts/`, `metadata/`, `manifest.json` |
| **Recipe packages** | `HOST_RECIPES_DIR` | `%USERPROFILE%\CookBook\recipes` | Finished imports: video, recipe.json, recipe.md, etc. |
| **Working scratch** | `HOST_WORKING_DIR` | `%USERPROFILE%\CookBook\working` | Per-job temp files, **debug logs** |

Inside containers these mount as `/data/db`, `/data/dataset`, `/data/recipes`, `/data/working`, etc.

---

## 3. Setup instructions (deployer)

### 3.1 First-time setup (Windows — recommended)

1. Install and start **Docker Desktop**.
2. (GPU) Confirm `nvidia-smi` works in a terminal and Docker Desktop → Settings → Resources → GPU is enabled.
3. Double-click **`CookBook-Setup.bat`** in the repo folder.
4. Answer prompts:
   - Database folder
   - Models folder (Ollama)
   - Dataset folder
   - Recipes folder
   - GPU: **1** = NVIDIA, **2** = CPU only
   - Action: **1** = build + start stack (recommended first time)
5. Wait for build, `docker compose up`, and optional `ollama pull`.

Setup writes **`.env`** — do not commit it (contains paths; may contain secrets later).

### 3.2 Verify stack is running

```bat
docker compose -f docker-compose.yml -f docker-compose.gpu.yml ps
```

Both `cookbook` and `ollama` should be **running** (full stack).

Or open **Deployment GUI** at `http://localhost:8082` when implemented.

### 3.3 Phase 0 dataset path (developer — before full app)

If you only need download + transcribe (no Ollama yet):

- Use **`CookBook-CLI.bat`** menu, or
- `CookBook-Setup.bat` → choose action **3** (Phase 0 build only)

---

## 4. Usage instructions

### 4.1 Deployer / operator

| Task | How |
|---|---|
| Initial setup | `CookBook-Setup.bat` |
| Download videos, transcribe, tests | `CookBook-CLI.bat` |
| Start stack | `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d` |
| Stop stack | `docker compose -f docker-compose.yml -f docker-compose.gpu.yml down` |
| View service logs | `docker compose logs -f cookbook` or `docker compose logs -f ollama` |
| Pull new formatter model | `docker compose exec ollama ollama pull <model>` |
| Change storage paths | Re-run `CookBook-Setup.bat` or edit `.env` `HOST_*_DIR`, then restart stack |

**Deployment GUI (port 8082)** — when built — replaces most of the above with buttons: stack status, env editor, health checks, log tail.

### 4.2 Developer / tester

**Dataset collection (current Phase 0):**

1. Add Instagram reel URLs to `dataset/urls.example.txt` or `dataset/urls.txt` (one per line).
2. **Download:** `CookBook-CLI.bat` → option 1, or:
   ```bat
   docker compose -f docker-compose.phase0.yml run --rm -e MODE=download cookbook --urls-file /data/dataset/urls.txt
   ```
3. **Metadata** (caption, author, comments): CLI option 2 or `--metadata-only`.
4. **Transcribe:** CLI option 3 (GPU recommended; first run downloads Whisper model to `HOST_WHISPER_CACHE_DIR`):
   ```bat
   docker compose -f docker-compose.phase0.yml -f docker-compose.gpu.yml run --rm -e MODE=transcribe cookbook
   ```
5. Check outputs:
   - `dataset/raw/*.mp4`
   - `dataset/metadata/*.json`
   - `dataset/transcripts/*.txt` and `*.json`
   - `dataset/manifest.json`

**Testing GUI (port 8081)** — when built — same steps via UI: paste URL → click step buttons 1–9 → inspect artifacts in the output panel.

### 4.3 End user (Production Web UI — port 8080)

When `MODE=web` is fully implemented:

1. Open **`http://localhost:8080`** (or your server hostname).
2. **Import a recipe:** paste Instagram Reel URL → optional toggles (video processing, your comment, custom instruction) → Import.
3. **Browse / search** saved recipes by title or ingredient.
4. **Open a recipe:** watch original video, read formatted recipe, edit if needed.
5. **Rate** and add **notes**.
6. **Shopping list:** select recipes → combined ingredient list (HEB aisle order).
7. **Report a problem:** Bug report dialog — describe what went wrong; system attaches a **DebugLog** snapshot automatically.

End users do **not** use `CookBook-Setup.bat`, compose, or Testing GUI.

---

## 5. DebugLog — where to find it and how to read it

### 5.1 What DebugLog is

A **DebugLog** is a structured record of one import job (or test run). It captures:

- Timestamped lines for each pipeline stage (1–9)
- Log level: `INFO`, `WARNING`, `ERROR`
- Which models ran (Whisper model, formatter model)
- Pipeline version
- Optional link to `job_id` and recipe slug

Defined in the SRD as entity **DebugLog** — fields: `log_id`, `job_id`, `entries[]`, `pipeline_version`, `model_versions`, `created_at`.

DebugLogs are **for operators and maintenance**, not shown to end users as raw JSON. End users submit a **BugReport**; the report stores a **copy** of the relevant DebugLog path.

### 5.2 Where DebugLogs are stored

| Location | When | Path |
|---|---|---|
| **Per-job working directory** | During/after import | `HOST_WORKING_DIR/<job_id>/debug.log` (host) · `/data/working/<job_id>/debug.log` (container) |
| **Bug report snapshot** | When user submits bug report | `HOST_WORKING_DIR/bugreports/<report_id>.json` |
| **Docker stdout** | Always (live) | `docker compose logs cookbook` |
| **Testing GUI log panel** | When using Testing GUI | Step result page shows last step output |

**Implemented:** `DebugLogWriter` appends structured JSON to `working/<job_id>/debug.log` on each pipeline step. Bug reports saved to `working/bugreports/`.

### 5.3 How to view DebugLogs today

**Live container output:**

```bat
docker compose -f docker-compose.yml -f docker-compose.gpu.yml logs -f cookbook
```

**After a CLI batch job** — check manifest and working dir:

```text
%USERPROFILE%\CookBook\working\     ← scratch + future debug.log per job
```

**When BugReport exists (Production UI):**

1. User submits bug from recipe page or homescreen.
2. Operator opens Deployment GUI → Bug reports, or reads file at `debug_log_path` on disk.
3. Maintenance agent (future) scans open reports on a schedule.

### 5.4 Example DebugLog entry (planned JSON shape)

```json
{
  "log_id": "dbg-a1b2c3",
  "job_id": "job-9f8e7d",
  "pipeline_version": "0.1.0",
  "model_versions": {
    "whisper": "large-v3",
    "formatter": "qwen2.5:7b-instruct",
    "formatter_provider": "ollama"
  },
  "created_at": "2026-08-30T21:15:00+00:00",
  "entries": [
    { "ts": "2026-08-30T21:15:01+00:00", "stage": 1, "level": "INFO", "message": "Download started" },
    { "ts": "2026-08-30T21:15:08+00:00", "stage": 1, "level": "INFO", "message": "Download complete: DaF766uDQ0C.mp4" },
    { "ts": "2026-08-30T21:15:09+00:00", "stage": 3, "level": "INFO", "message": "Whisper transcribe started" },
    { "ts": "2026-08-30T21:16:02+00:00", "stage": 3, "level": "ERROR", "message": "CUDA OOM — retry with WHISPER_DEVICE=cpu or smaller model" }
  ]
}
```

### 5.5 How to interpret common messages

| Stage | Symptom in log | Likely cause | What to do |
|---|---|---|---|
| **1 Download** | `yt-dlp failed` / `Unsupported URL` | Bad URL, private reel, rate limit | Use direct reel URL; add cookies in `.env`; retry later |
| **1 Download** | `Hub page yielded 0 URLs` | Instagram hub needs login or URL list | Use `dataset/urls.txt` with one URL per line |
| **2 Extract audio** | `ffmpeg not found` | Broken container image | Rebuild: `docker compose build` |
| **3 Transcribe** | `CUDA OOM` / out of memory | GPU VRAM full (Whisper + Ollama) | Ensure sequential steps; use smaller `WHISPER_MODEL`; or `WHISPER_DEVICE=cpu` |
| **3 Transcribe** | Very slow, no error | CPU mode or first model download | First run downloads model to `whisper-cache`; wait |
| **5 Vision** | Empty `vision.json` | Video processing off or no on-screen text | Enable toggle; check frames in `working/` |
| **7 Format** | `connection refused` to Ollama | Ollama sidecar down | `docker compose up -d ollama`; check Deployment GUI health |
| **7 Format** | Invalid JSON from formatter | Model too small or bad prompt | Default is `qwen2.5:7b-instruct`; retry; try smaller `qwen2.5:3b-instruct` only if GPU OOM |
| **9 Store** | Duplicate recipe | Same `source_url` already imported | Expected — open existing recipe or delete old package |

**Log levels:**

- **INFO** — normal progress; safe to ignore when job completes.
- **WARNING** — skipped optional step, hub partial URL list, uncertain formatter field — job may still succeed.
- **ERROR** — step failed; later steps may be blocked; check `error_message` on ImportJob and BugReport.

### 5.6 End user vs operator when something breaks

| Who sees what | End user | Operator |
|---|---|---|
| Friendly error on screen | “Import failed — try again or report a bug” | Full stage name + suggestion |
| Raw DebugLog | No | Yes — file path or Deployment GUI |
| Bug report | Can submit description | Reads attached DebugLog + fixes/config |

---

## 6. Quick reference card

```text
┌─────────────────────────────────────────────────────────────────┐
│ DEPLOYER                         END USER                       │
├─────────────────────────────────────────────────────────────────┤
│ CookBook-Setup.bat               http://localhost:8080          │
│ CookBook-CLI.bat                 Import · Browse · Shop list    │
│ http://localhost:8082 (deploy)   Bug report → DebugLog snapshot │
│ http://localhost:8081 (testing)                                 │
│ .env + docker compose            (no Docker knowledge needed)   │
└─────────────────────────────────────────────────────────────────┘

Dependencies on host:     Docker (+ NVIDIA toolkit if GPU)
Dependencies in container:  ffmpeg, yt-dlp, faster-whisper, Python app
Models on disk:           HOST_OLLAMA_DIR (formatter), HOST_WHISPER_CACHE_DIR (Whisper)
Debug logs:               HOST_WORKING_DIR/<job_id>/debug.log (planned)
Live logs now:            docker compose logs -f cookbook
```

---

## 7. Document map (deployment vs requirements vs user)

| Document | Audience | Content |
|---|---|---|
| **USER_GUIDE.md** (this file) | Deployer + end user + tester | Plain-language setup, usage, dependencies, DebugLog |
| [SOFTWARE_REQUIREMENTS.md](SOFTWARE_REQUIREMENTS.md) | Developers | Full spec, step architecture, GUIs |
| [DOCKER.md](DOCKER.md) | Deployer / developers | Compose files, volumes, MODE reference |
| [README.md](README.md) | Everyone | Workspace entry point, links here |
| [mot/MASTER_CONTEXT.md](mot/MASTER_CONTEXT.md) | Developers (MoT sessions) | Architecture, metrics, increments |
