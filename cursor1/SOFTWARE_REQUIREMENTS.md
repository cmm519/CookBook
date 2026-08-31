# Software Requirements Specification

## Requirements

### 1. Project Overview

Develop a software system for **building and maintaining a local-first recipe repository from Instagram Reel URLs** using:

- Language: **Python** (import pipeline, CLI, web backend, data models); **Java** (TBD — likely web/API layer or separate service; boundary to be decided in Section 21)
- Architecture: **Step-based pipeline** — one class/function per pipeline stage behind a common `PipelineStep` interface; **Modular pipeline + MVC web layer** with provider interfaces for transcription (Whisper), vision/OCR, and recipe formatting (**Ollama interim model now; custom distilled model on hold**); **Docker Compose** for deployment on personal server
- UI framework: **Three web GUIs** on the personal server:
  - **Testing GUI** (`MODE=testing-gui`) — add URLs, run each pipeline step individually, inspect intermediate outputs
  - **Deployment GUI** (`MODE=deployment-gui`) — manage Docker services, env, models, health, and stack lifecycle
  - **Production Web UI** (`MODE=web`) — recipe viewer/editor, shopping list, bug reporting (end-user facing)
- CLI for import and batch ops (invoked via `docker compose run`); GUIs call the same step classes as CLI
- Testing framework: **pytest** (Python, run inside `docker-compose.test.yml` container); **JUnit** (Java, when introduced)
- Exception/error-handling mechanism: **Structured exceptions per pipeline stage**; user-dismissible errors in web UI; debug log capture for maintenance agent review
- Deployment: **Docker** — all runtime dependencies (Python, ffmpeg, yt-dlp, faster-whisper, CUDA libs) containerized; host requires only Docker Engine + NVIDIA Container Toolkit (GPU hosts)

### 2. Startup / Initialization

On startup, the system should:

1. **Container startup:** Docker entrypoint validates bundled tools (ffmpeg, yt-dlp, faster-whisper) are available inside the container; creates volume mount directories if missing (`/data/recipes`, `/data/working`, `/data/db`, `/data/dataset/raw`, `/data/dataset/transcripts`).
2. **Modular Docker `MODE`:** The entrypoint reads the `MODE` environment variable (default: `web`) and dispatches to exactly one startup path. Valid values:

   | `MODE` | Purpose | GPU required | Notes |
   |---|---|---|---|
   | `download` | Batch-fetch videos via yt-dlp into `dataset/raw/` | No | Phase 0 — CLI batch |
   | `transcribe` | Batch-transcribe videos in `dataset/raw/` via faster-whisper | Yes (recommended) | Phase 0 — CLI batch |
   | `testing-gui` | Start **Testing GUI** web server (port 8081) | Per step run | Add links; run steps 1–9 individually |
   | `deployment-gui` | Start **Deployment GUI** web server (port 8082) | No | Manage compose, env, models, health |
   | `web` | Start **Production Web UI** (port 8080) | Yes (for import jobs) | End-user recipe app |
   | `import` | Run single-recipe import CLI (`recipe-import`) | Yes | Full pipeline — one URL |
   | `test` | Run `pytest` and exit | No | CI / local verification |

   - Set via `docker compose run -e MODE=<value> cookbook` or in `.env`.
   - Phase 0 uses only `download` and `transcribe`; `web`, `import`, and downstream pipeline stages are out of scope until Phase 1+.
   - See [`DOCKER.md`](DOCKER.md) for compose command examples per mode.
3. **CLI mode:** Parse command-line arguments; load configuration from environment variables and `.env` file (injected by Docker Compose).
4. Load **configuration and repository state** from **environment variables, `.env`, and mounted volumes** (`recipes/`, `recipes.db`, `working/`, `dataset/` — bind-mounted or named Docker volumes).
5. **Web mode (`MODE=web`):** Present **homescreen** containing:
   - **Import URL field** — accept Instagram Reel share URL and trigger import pipeline
   - **Video processing toggle** — enable/disable OCR/vision frame analysis (on-screen text extraction)
   - **User comment field** — optional notes from user to attach to the import job
   - **Custom instruction field** — optional text passed to the recipe formatter model alongside transcript/OCR evidence
   - **Recipe search/browse** — navigate to existing recipes in the repository

Additional startup behavior:

- Deploy on a **personal server** via `docker compose up` (not cloud SaaS).
- **Windows one-shot setup:** `CookBook-Setup.bat` in this workspace folder (`cursor1/`) — interactive prompts for database path, Ollama model storage path, dataset/recipes paths, GPU (CUDA vs CPU), then generates `.env` and runs `docker compose build` / `up -d`. Post-setup operations via `CookBook-CLI.bat` menu.
- GPU workloads use `docker-compose.gpu.yml` override with NVIDIA Container Toolkit; CI/tests use `docker-compose.test.yml` (CPU only, mocked providers).
- See [`DOCKER.md`](DOCKER.md) for full container layout, volume mounts, and commands.
- Load the **recipe formatter** from the **Ollama sidecar** (`http://ollama:11434`); model name configured via `FORMATTER_MODEL` (default interim: **`qwen2.5:7b-instruct`**). Custom distilled `cookbook-formatter` is **on hold** — see [`DISTALATION.MD`](DISTALATION.MD).
- Validate repository paths exist or create them on first run (`recipes/`, `working/`).
- Do not load Whisper and formatter models concurrently on GPU — sequential loading only (8GB VRAM constraint).

### 3. Data Requirements

#### Entity: Recipe

Each **Recipe** (canonical structured representation, stored as `recipe.json`) should contain:

- **title** — string, required, non-empty
- **description** — string, optional
- **servings** — string, optional (e.g. "4 servings")
- **prep_time** — string, optional
- **cook_time** — string, optional
- **total_time** — string, optional
- **ingredients** — list of Ingredient objects, required, at least one
- **instructions** — list of Instruction objects, required, at least one, sequentially numbered
- **notes** — list of strings, optional
- **tags** — list of strings, optional
- **source_url** — string, required, valid URL
- **source_creator** — string, optional

Each **Ingredient** should contain:

- **item** — string, required
- **quantity** — string, optional (must not be silently invented when unknown)
- **preparation** — string, optional (e.g. "diced", "minced")
- **notes** — string, optional
- **confidence** — float 0.0–1.0, optional (marks uncertain/inferred values)

Each **Instruction** should contain:

- **step** — integer, required, sequential starting at 1
- **text** — string, required
- **duration** — string, optional
- **temperature** — string, optional

#### Entity: RecipePackage

Each **RecipePackage** (filesystem directory under `recipes/<slug>/`) should contain:

- **video.mp4** — original downloaded video, unchanged
- **transcript.txt** — plain-text raw transcript (never overwritten by formatter)
- **transcript.json** — timestamped transcript segments
- **vision.json** — OCR/vision frame-level evidence (when video processing enabled)
- **recipe.json** — validated structured Recipe (canonical)
- **recipe.md** — deterministic Markdown rendering of recipe.json
- **metadata.json** — import metadata (source URL, creator, date_added, pipeline_version)
- **thumbnail.jpg** — optional preview image

#### Entity: ImportJob

Each **ImportJob** should contain:

- **job_id** — string, unique identifier (UUID or similar)
- **source_url** — string, required
- **status** — enum: pending, running, completed, failed
- **current_stage** — integer 1–9 (pipeline stage)
- **working_dir** — filesystem path under `working/<job_id>/`
- **user_comment** — string, optional
- **custom_instruction** — string, optional
- **video_processing_enabled** — boolean
- **error_message** — string, optional (populated on failure)
- **created_at** — ISO 8601 timestamp
- **completed_at** — ISO 8601 timestamp, optional

#### Entity: DatasetVideoMetadata (Phase 0)

Each downloaded training video may have a metadata sidecar at `dataset/metadata/<reel_id>.json`:

- **reel_id** — string, Instagram shortcode
- **source_url** — string, original reel URL
- **title** — string, optional (yt-dlp title, often "Video by \<username\>")
- **author** — string, optional (display name)
- **author_username** — string, optional (Instagram handle)
- **caption** — string, optional (post description; often contains recipe text or links)
- **comments** — list of `{author, text, timestamp}` — top comments from yt-dlp (recipe sometimes posted in comments)
- **comment_count** — integer, total comments on post
- **like_count** — integer, optional
- **upload_date** — string, optional (YYYYMMDD)
- **extracted_at** — ISO 8601 timestamp

Manifest entries reference `metadata_path`. Caption and comments are preserved as evidence for distillation and must not overwrite raw transcripts.

#### Entity: UserNote

Each **UserNote** should contain:

- **note_id** — string, unique
- **recipe_slug** — string, required, references RecipePackage
- **text** — string, required, non-empty
- **created_at** — ISO 8601 timestamp
- **updated_at** — ISO 8601 timestamp

#### Entity: Rating

Each **Rating** should contain:

- **recipe_slug** — string, required, references RecipePackage
- **score** — integer, required, range 1–5
- **created_at** — ISO 8601 timestamp
- **updated_at** — ISO 8601 timestamp

#### Entity: ShoppingListItem

Each **ShoppingListItem** should contain:

- **item_id** — string, unique
- **ingredient_name** — string, required
- **quantity** — string, optional (combined quantity when merged from multiple recipes)
- **aisle_category** — enum: deli, produce, meat, bread, cooking, frozen, snacks, dairy, other (HEB store order)
- **source_recipe_slugs** — list of strings (recipes that contributed this item)
- **checked** — boolean, default false

#### Entity: BugReport

Each **BugReport** should contain:

- **report_id** — string, unique
- **description** — string, required (user-provided)
- **debug_log_path** — string, path to captured debug log snapshot
- **related_job_id** — string, optional
- **related_recipe_slug** — string, optional
- **created_at** — ISO 8601 timestamp
- **status** — enum: open, reviewed, resolved

#### Entity: DebugLog

Each **DebugLog** should contain:

- **log_id** — string, unique
- **job_id** — string, optional
- **entries** — list of timestamped log lines (stage, level, message)
- **pipeline_version** — string
- **model_versions** — object (Whisper model, formatter model/provider)
- **created_at** — ISO 8601 timestamp

Additional constraints:

- **Uniqueness:** Recipe slug derived from title must be unique within the repository; duplicate imports detected by source URL first, then title similarity.
- **Validation:** All Recipe objects must pass Pydantic schema validation before persistence; raw transcript must never be modified by the formatter.
- **Relationship / consistency:** RecipePackage filesystem is source of truth; SQLite index must stay in sync with recipe.json on every write; web UI edits must update both filesystem and index atomically.

### 4. Persistence

The system should:

- Save data when **a pipeline step completes successfully** (Step 9 writes recipe package + SQLite index).
- Save data when **the user edits a recipe** in the Production Web UI (atomic update to `recipe.json` + re-index).
- Save data when **the user submits a rating, note, or bug report** (JSON sidecar or `working/bugreports/`).
- Use **filesystem + SQLite** as the persistence mechanism:
  - **Filesystem:** `recipes/<slug>/` is source of truth for recipe packages.
  - **SQLite:** `recipes.db` search index (derived from recipe.json; rebuilt on upsert).
  - **Dataset (Phase 0):** `dataset/manifest.json`, `dataset/raw/`, `dataset/transcripts/`, `dataset/metadata/`.
  - **Working:** `working/<job_id>/` per-import scratch + `debug.log`.
- Use **JSON** for structured data (recipe.json, metadata.json, manifest, debug logs); **plain text** for transcripts and Markdown.

### 5. Primary Operations

The system should provide:

#### Operation: import-recipe (full pipeline)

**Trigger:** `MODE=import`, Production Web UI import form, or `python -m app.cli import <url>`.

**Input:** Instagram Reel URL; optional user comment, custom instruction, video processing toggle.

**Behavior:** Run `PipelineOrchestrator.run_all()` (Steps 1–9); write DebugLog to `working/<job_id>/debug.log`.

**Success:** Recipe package under `recipes/<slug>/`; SQLite index row; job status `completed`.

**Failure:** Job status `failed`; error in DebugLog; partial artifacts retained in `working/<job_id>/`.

#### Operation: search-recipes

**Trigger:** Production Web UI search field.

**Input:** Query string (title or ingredient substring).

**Behavior:** Query SQLite index; return matching slugs and titles.

#### Operation: edit-recipe

**Trigger:** Production Web UI editor.

**Behavior:** Update `recipe.json`; re-render optional; upsert SQLite index.

#### Operation: shopping-list

**Trigger:** Production Web UI shopping list page.

**Input:** One or more recipe slugs.

**Behavior:** Merge ingredients conservatively; sort by HEB aisle order (produce → meat → … → other).

#### Operation: bug-report

**Trigger:** Production Web UI bug report form.

**Behavior:** Save `BugReport` JSON under `working/bugreports/` with reference to DebugLog path.

#### Operation: batch-download / batch-transcribe

(See existing Phase 0 operations — unchanged; CLI batch modes for dataset collection.)

#### Operation: batch-download

**Trigger:** Operator runs `docker compose run -e MODE=download cookbook` (optionally with CLI args or env vars for input source).

**Input:**

- **Option A — URL list file:** Plain-text file mounted at `/data/dataset/urls.txt` (one Instagram Reel URL per line).
- **Option B — Instagram hub URL:** Single profile or collection URL passed via `DOWNLOAD_SOURCE_URL` env var or CLI `--source`; yt-dlp resolves reel URLs from the hub.
- **Limit:** Maximum **50** URLs per run (`DOWNLOAD_LIMIT=50`, configurable, hard cap 50).

**Validation:**

- At least one input source must be present (file or hub URL).
- Each URL must be a valid HTTP(S) URL; non-Instagram URLs are rejected with a logged warning and skipped.
- If resolved URL count exceeds limit, process only the first 50 and log the truncation.

**Behavior:**

- For each URL (up to limit): invoke yt-dlp to download the reel video into `dataset/raw/` using a deterministic filename derived from reel ID or URL hash (e.g. `{reel_id}.mp4`).
- Skip URLs whose target file already exists in `dataset/raw/` (idempotent re-runs).
- Append/update `dataset/manifest.json` with one entry per attempted URL: `{ url, reel_id, filename, status, downloaded_at, error? }`.
- Do **not** run ffmpeg extraction, transcription, formatting, or recipe persistence.

**Success result:**

- Video files present in `dataset/raw/` for all successfully downloaded URLs.
- Updated `dataset/manifest.json` reflecting per-URL status.

**Failure behavior:**

- Per-URL failures (rate limit, deleted reel, network error) are recorded in `manifest.json` with `status: failed` and `error` message; batch continues for remaining URLs.
- Fatal errors (yt-dlp missing, volume unwritable) exit non-zero after logging.

#### Operation: batch-transcribe

**Trigger:** Operator runs `docker compose -f docker-compose.yml -f docker-compose.gpu.yml run -e MODE=transcribe cookbook` after `batch-download` has populated `dataset/raw/`.

**Input:**

- All `*.mp4` (and supported video extensions) in `dataset/raw/`.
- Optional filter: `TRANSCRIBE_ONLY=<reel_id>` env var to process a single file.
- Whisper config from env: `WHISPER_MODEL`, `WHISPER_DEVICE` (default `cuda` on GPU compose).

**Validation:**

- `dataset/raw/` must exist and contain at least one video file; otherwise exit with clear message.
- Skip files that already have a matching transcript in `dataset/transcripts/` unless `TRANSCRIBE_FORCE=true`.

**Behavior:**

- For each video in `dataset/raw/` (respecting filter and skip rules): run faster-whisper transcription.
- Write outputs per video to `dataset/transcripts/`:
  - `{reel_id}.txt` — plain-text transcript
  - `{reel_id}.json` — timestamped segments
- Update `dataset/manifest.json` entries with `transcript_status`, `transcript_files`, and `transcribed_at`.
- Do **not** run vision/OCR, recipe formatting, or write to `recipes/`.

**Success result:**

- Transcript files in `dataset/transcripts/` for all successfully processed videos.
- Updated `dataset/manifest.json` with transcription status per entry.

**Failure behavior:**

- Per-video failures (corrupt file, Whisper OOM) recorded in manifest; batch continues.
- GPU unavailable when `WHISPER_DEVICE=cuda` exits with actionable error suggesting CPU fallback or GPU compose override.

#### 5.1 Audience tracking — deployment vs end user

Use this table to classify **every feature, script, and doc** as deployer, tester, or end-user facing. Full setup and DebugLog help: **[`USER_GUIDE.md`](USER_GUIDE.md)**.

| Deliverable | Audience | Status (Phase 0) | Port / entry |
|---|---|---|---|
| `CookBook-Setup.bat` | **Deployer** | Implemented | Host — first-time install |
| `CookBook-CLI.bat` | **Deployer / tester** | Implemented | Host — batch ops menu |
| `docker compose` + `.env` | **Deployer** | Implemented | Host — stack lifecycle |
| `MODE=download`, `MODE=transcribe` | **Tester** (dataset) | Implemented | CLI via compose |
| `MODE=test` | **Developer** | Implemented | CI / local pytest |
| Deployment GUI | **Deployer** | Spec only | **8082** |
| Testing GUI | **Tester** | Spec only | **8081** |
| Production Web UI | **End user** | Spec only | **8080** |
| Bug report + DebugLog snapshot | **End user** submits → **Deployer** reads | Spec only | Production UI |
| Maintenance agent (DebugLog triage) | **Deployer** (background) | Future | N/A |
| `USER_GUIDE.md` | **All** (plain language) | Implemented | Docs |
| `SOFTWARE_REQUIREMENTS.md` | **Developer** | In progress | Docs |
| `DOCKER.md` | **Deployer / developer** | Implemented | Docs |

**Rules:**

- End users never receive setup scripts, compose files, or Testing/Deployment GUIs.
- Deployers never need Production UI for daily stack maintenance (optional for smoke tests).
- Testers use CLI + Testing GUI; same step outputs must match Production import pipeline.

### 6. Multiple Views / Windows

The application exposes **three separate web GUIs** (distinct `MODE` values and default ports). Each GUI is a separate view/controller bundle; they share the same step-based pipeline core but serve different operators.

#### GUI 1: Testing GUI (`MODE=testing-gui`, port 8081)

**Purpose:** Developer/operator workbench — add Instagram links and **run each pipeline step independently** to validate behavior before running the full import workflow.

**Views:**

- **URL queue** — paste or upload links (`urls.txt`); add/remove entries; persist to `dataset/urls.txt` or in-memory session queue
- **Job / reel selector** — pick a reel ID or URL from queue or `dataset/manifest.json`
- **Step runner panel** — one button per pipeline step (Steps 1–9); show step status, duration, and last error
- **Step output inspector** — read-only view of artifacts produced by the selected step (video path, metadata JSON, transcript, vision JSON, consolidated input, recipe JSON, etc.)
- **Run log** — timestamped log for the current job (stage, level, message)

**Step runner actions (each invokes exactly one `PipelineStep`):**

| Button | Step | Produces |
|---|---|---|
| Download | Step 1 | `dataset/raw/{id}.mp4`, `dataset/metadata/{id}.json` |
| Extract audio | Step 2 | `working/{job_id}/audio.wav` |
| Transcribe | Step 3 | `dataset/transcripts/{id}.txt`, `.json` |
| Extract frames | Step 4 | `working/{job_id}/frames/` |
| Vision / OCR | Step 5 | `working/{job_id}/vision.json` |
| Consolidate sources | Step 6 | consolidated input object (preview JSON) |
| Format recipe | Step 7 | `recipe.json` (draft in working dir) |
| Normalize + Markdown | Step 8 | normalized JSON + `recipe.md` |
| Store + index | Step 9 | `recipes/<slug>/` package + SQLite index entry |

**Synchronization:** Output inspector refreshes after each step completes. Running step N requires outputs from prerequisite steps (disable button or show clear error if missing).

#### GUI 2: Deployment GUI (`MODE=deployment-gui`, port 8082)

**Purpose:** Operate the personal-server stack without using the command line — start/stop services, verify health, manage configuration and models.

**Views:**

- **Stack status** — `cookbook`, `ollama` service state (running/stopped/unhealthy)
- **Compose controls** — start/stop/restart stack; apply `docker-compose.gpu.yml` override toggle
- **Environment editor** — view/edit non-secret env vars (`.env`); mask secrets; validate before save
- **Model management** — list Ollama models; pull formatter model; show Whisper model config
- **Volume / disk** — usage summary for `recipes/`, `dataset/`, `working/`, model caches
- **Health checks** — ffmpeg, yt-dlp, GPU visibility, Ollama reachable, disk writable
- **Logs tail** — recent container logs (cookbook, ollama)

**Actions:**

- Start stack → `docker compose up -d`
- Stop stack → `docker compose down`
- Pull Ollama model → `ollama pull <model>`
- Run health check suite → pass/fail per dependency

**Constraints:** Deployment GUI must not expose raw API keys in the browser after save; restart may be required for env changes.

#### GUI 3: Production Web UI (`MODE=web`, port 8080)

**Purpose:** End-user recipe repository (homescreen, import, viewer, editor, shopping list, bug reports) — see Section 2 and Section 13.

**Synchronization (all GUIs):**

- Filesystem is source of truth; Testing GUI step outputs must match what CLI/batch modes produce for the same step.
- Production Web UI edits to `recipe.json` must re-index SQLite and refresh open views.
- Deployment GUI restarts must not corrupt in-flight import jobs (warn if jobs running).

### 7. Agents / Background Processes

**Maintenance agent (future):** Scheduled task scanning `working/bugreports/` and DebugLogs. Not implemented in MVP — file layout and entities exist (INC-18).

**No other background workers.** Import jobs run synchronously; GPU steps sequential within one job.

### 8. Constants / Configuration

| Name | Value / default | Purpose |
|---|---|---|
| `WHISPER_MODEL` | `large-v3` | faster-whisper model |
| `WHISPER_DEVICE` | `cuda` / `cpu` | Transcription device |
| `FORMATTER_MODEL` | `qwen2.5:7b-instruct` | Ollama interim formatter |
| `FORMATTER_PROVIDER` | `ollama` / `mock` | Formatter backend |
| `FRAME_INTERVAL` | `2.0` | Seconds between OCR frames |
| `DOWNLOAD_LIMIT` | `50` | Max URLs per batch download |
| `WEB_PORT` | `8080` | Production Web UI |
| `TESTING_GUI_PORT` | `8081` | Testing GUI |
| `DEPLOYMENT_GUI_PORT` | `8082` | Deployment GUI |

### 9. Error Handling

The system should provide appropriate errors for:

- Invalid input
- Missing input
- Invalid data format
- Corrupted data
- Inconsistent data
- GPU OOM during transcription or formatting
- Ollama unreachable (formatter step)

Error messages should:

- Clearly identify the problem.
- Identify the affected data where applicable.
- Identify the location of the problem where applicable.
- Provide a suggested correction where appropriate.
- Be dismissible by the user.

For unrecoverable errors:

- Production Web UI shows dismissible error with step number.
- Partial artifacts remain in `working/<job_id>/`.
- User may submit BugReport; DebugLog path recorded in `working/bugreports/`.

### 10. Architecture

Organize the implementation into **step modules** (one responsibility per pipeline stage), **provider interfaces** (swappable backends), **orchestration** (workflow only — no business logic), and **three GUI bundles**.

#### Package layout

```text
app/
├── steps/                  # One module per pipeline step (core requirement)
│   ├── base.py             # PipelineStep ABC, StepContext, StepResult
│   ├── step01_download.py
│   ├── step02_extract_audio.py
│   ├── step03_transcribe.py
│   ├── step04_extract_frames.py
│   ├── step05_vision.py
│   ├── step06_consolidate.py
│   ├── step07_format_recipe.py
│   ├── step08_normalize_markdown.py
│   └── step09_store_index.py
├── downloader/             # yt-dlp provider (used by Step 1)
├── media/                  # ffmpeg audio/frame ops (Steps 2, 4)
├── transcription/          # Whisper provider (Step 3)
├── vision/                 # OCR provider (Step 5)
├── extraction/             # consolidation + Ollama formatter (Steps 6–7)
├── formatting/             # deterministic Markdown (Step 8)
├── storage/                # recipe package layout (Step 9)
├── search/                 # SQLite index (Step 9)
├── workflow/               # PipelineOrchestrator — runs steps in order; no step logic
├── web/
│   ├── testing/            # Testing GUI controllers + templates
│   ├── deployment/         # Deployment GUI controllers + templates
│   └── production/         # Production Web UI (viewer, editor, shopping, bug)
├── config/
└── cli/                    # CLI invokes same steps as Testing GUI
```

#### Step-based design rules

- Each step is **exactly one class** implementing `PipelineStep`:
  - `name: str` — e.g. `"download"`, `"transcribe"`
  - `step_number: int` — 1–9
  - `requires: list[int]` — prerequisite step numbers
  - `run(context: StepContext) -> StepResult`
- **No step calls another step directly** — only `PipelineOrchestrator` (or Testing GUI) invokes steps.
- **StepContext** carries: `job_id`, `source_url`, paths, toggles (video processing on/off), user comment, custom instruction, prior step artifacts.
- **StepResult** carries: `success`, `artifacts` (paths/JSON), `metrics` (duration, counts), `error` (optional).
- Existing packages (`downloader/`, `transcription/`, etc.) are **dependencies of steps**, not replacements — steps are thin orchestration wrappers with validation and artifact paths.

#### GUI architecture

| GUI | Package | Controller responsibility |
|---|---|---|
| Testing | `web/testing/` | Queue URLs; dispatch single step; stream logs; serve artifact previews |
| Deployment | `web/deployment/` | Proxy compose/health/model commands; never embed secrets in responses |
| Production | `web/production/` | Recipe CRUD, import trigger (full orchestrator), shopping list, bug reports |

Required architectural constraints:

- **Single step implementation** — CLI, Testing GUI, and full import all call the same `app/steps/*` classes.
- **Provider interfaces** — transcription, vision, formatter swappable via config; steps depend on interfaces, not concrete models.
- **No LLM in Steps 8–9** — normalization and Markdown are deterministic.
- **Sequential GPU** — Steps 3 and 7 never load GPU models concurrently; orchestrator enforces lock.
- **Dependency direction** — `web/*` → `workflow/` → `steps/` → providers; steps must not import from `web/`.

### 11. Model / Core Logic

Implement step classes and shared models. Each step module exposes one primary class.

#### `PipelineStep` (abstract)

- Attributes: `name`, `step_number`, `requires`
- Operations: `run(context) -> StepResult`, `validate_prerequisites(context) -> bool`
- Exceptions: `StepPrerequisiteError`, `StepExecutionError`

#### `StepContext`

- Attributes: `job_id`, `source_url`, `working_dir`, `dataset_raw_dir`, `repository_path`, `video_processing_enabled`, `user_comment`, `custom_instruction`, `artifacts: dict[str, Any]`
- Operations: `artifact(key)`, `set_artifact(key, value)`

#### `StepResult`

- Attributes: `step_number`, `success`, `artifacts`, `metrics`, `error`, `duration_ms`

#### Step classes (1:1 with pipeline stages)

| Class | Module | Uses | Key outputs |
|---|---|---|---|
| `DownloadStep` | `step01_download.py` | `YtDlpDownloader` | video, metadata sidecar |
| `ExtractAudioStep` | `step02_extract_audio.py` | ffmpeg | mono 16 kHz WAV |
| `TranscribeStep` | `step03_transcribe.py` | `FasterWhisperTranscription` | transcript txt/json |
| `ExtractFramesStep` | `step04_extract_frames.py` | ffmpeg | frames directory |
| `VisionStep` | `step05_vision.py` | `VisionProvider` | vision.json |
| `ConsolidateStep` | `step06_consolidate.py` | — | consolidated input JSON |
| `FormatRecipeStep` | `step07_format_recipe.py` | Ollama `FormatterProvider` | recipe.json draft |
| `NormalizeMarkdownStep` | `step08_normalize_markdown.py` | deterministic formatter | recipe.json final, recipe.md |
| `StoreIndexStep` | `step09_store_index.py` | storage, search | recipes package, SQLite row |

#### `PipelineOrchestrator`

- Attributes: `steps: list[PipelineStep]`, `gpu_lock`
- Operations: `run_all(context)`, `run_step(step_number, context)`, `run_from(step_number, context)`
- Exceptions: `OrchestrationError` — wraps failed step; preserves partial artifacts

#### Domain models (unchanged from Section 3)

- `Recipe`, `Ingredient`, `Instruction`, `RecipePackage`, `ImportJob`, `VideoMetadata`, `TranscriptResult`, etc. live in `app/models/` (Pydantic).

### 12. Controller / Application Logic

Controllers dispatch to **step classes** or **orchestrator** — no pipeline logic in controllers.

#### Testing GUI controllers (`web/testing/`)

- **`TestingQueueController`** — add/remove URLs; load/save `dataset/urls.txt`
- **`TestingStepController`** — `POST /testing/run-step/{step_number}` with `{ url | reel_id }`; returns `StepResult` JSON + log tail
- **`TestingArtifactController`** — `GET /testing/artifacts/{reel_id}/{artifact_type}` — serve metadata, transcript, vision preview, etc.
- **`TestingLogController`** — SSE or poll for job log stream

#### Deployment GUI controllers (`web/deployment/`)

- **`StackController`** — start/stop/restart compose stack (subprocess or Docker API)
- **`EnvController`** — read/write `.env` (secrets redacted on read)
- **`ModelController`** — list/pull Ollama models; show Whisper config
- **`HealthController`** — run dependency checks; return structured pass/fail
- **`VolumeController`** — disk usage per mount

#### Production Web controllers (`web/production/`)

- **`ImportController`** — trigger full `PipelineOrchestrator.run_all()` from homescreen
- **`RecipeController`** — CRUD, search, viewer data
- **`ShoppingListController`**, **`BugReportController`** — per Section 5 (when filled)

Controller requirements:

- **One controller per GUI concern** — no monolithic god controller
- **Testing GUI never runs full pipeline unless explicitly requested** — default is single-step dispatch
- **Deployment GUI never runs pipeline steps** — infrastructure only
- **Exception handling** — map `StepExecutionError` to HTTP 422 with step number, message, and artifact paths

### 13. View / UI

Three web GUIs plus shared styling optional. Recommended: server-rendered HTML + minimal JS for Testing/Deployment; Production UI may use richer frontend later.

---

**Window: Testing GUI — URL Queue**

**Purpose:** Add and manage Instagram links for step-by-step testing.

**Components:**

- URL textarea — paste one URL per line
- Add to queue button — append to session + optional save to `dataset/urls.txt`
- Queue table — URL, reel ID, download status, last step run

**Actions:**

- Add URLs → updates queue table
- Select row → enables step runner for that reel

---

**Window: Testing GUI — Step Runner**

**Purpose:** Run individual pipeline steps and inspect results.

**Components:**

- Step buttons 1–9 — labeled Download, Extract audio, Transcribe, … Store+index
- Prerequisites indicator — green/red per step based on `StepContext.artifacts`
- Output inspector — tabs: Video, Metadata, Transcript, Vision, Recipe JSON, Markdown, Log
- Run selected step → invokes `TestingStepController`

**Actions:**

- Click step N → runs only that step; refreshes inspector on success
- View artifact → read-only preview of files from `StepResult.artifacts`

---

**Window: Deployment GUI — Stack Dashboard**

**Purpose:** Operate Docker stack on personal server.

**Components:**

- Service cards — cookbook, ollama (status, uptime, restart button)
- GPU indicator — CUDA available yes/no
- Env editor — key/value form (secrets masked)
- Model panel — installed Ollama models, pull new model field
- Health check button — runs full suite, shows pass/fail list
- Log viewer — tail last N lines per service

**Actions:**

- Start / Stop stack → compose up/down
- Pull model → ollama pull
- Save env → write `.env`, prompt restart

---

**Window: Production Web UI — Homescreen** *(Phase 1+)*

**Purpose:** End-user import and browse (see Section 2).

**Components:**

- Import URL field, video processing toggle, user comment, custom instruction
- Recipe search/browse link

**Actions:**

- Submit import → full orchestrator (all 9 steps)

### 14. Documentation

Provide documentation for:

- Every class
- Important methods
- Important implementation sections
- Public APIs
- **[USER_GUIDE.md](USER_GUIDE.md)** — deployer vs end-user vs tester audiences; dependencies; setup; usage; DebugLog interpretation (required deliverable for operators and end users)

Documentation format:

- **User-facing:** Markdown ([`USER_GUIDE.md`](USER_GUIDE.md))
- **Developer-facing:** Markdown docstrings + [`SOFTWARE_REQUIREMENTS.md`](SOFTWARE_REQUIREMENTS.md)

Generated documentation:

- Architecture diagram in [`mot/MASTER_CONTEXT.md`](mot/MASTER_CONTEXT.md)
- Optional API docs from FastAPI/OpenAPI when web layer is implemented

### 15. Testing

Unit tests should cover:

- Every method in **[TARGET COMPONENTS]**
- Normal operation
- Boundary conditions
- Invalid input
- Exception conditions
- State transitions
- Concurrency where applicable
- **[OTHER TEST REQUIREMENTS]**

Required test organization:

**[TEST PACKAGE / DIRECTORY STRUCTURE]**

Required test classes:

- **[TEST CLASS]**
- **[TEST CLASS]**
- **[TEST CLASS]**

### 16. Development Process

Implement incrementally:

1. Create the project structure and class/interface skeleton.
2. Define attributes, operations, interfaces, and exceptions.
3. Ensure the project compiles.
4. Generate initial documentation.
5. Implement and test the core/model layer.
6. Implement the controller/application layer.
7. Implement the view/UI layer.
8. Implement concurrency/background processing if required.
9. Perform integration testing.
10. Perform acceptance testing.
11. Fix discovered faults.
12. Generate final documentation.
13. Generate **[UML / ARCHITECTURE / OTHER REQUIRED ARTIFACTS]**.

### 17. Acceptance Tests

The completed system must demonstrate:

1. **[ACCEPTANCE TEST 1]**
   - Expected result: **[RESULT]**

2. **[ACCEPTANCE TEST 2]**
   - Expected result: **[RESULT]**

3. **[ACCEPTANCE TEST 3]**
   - Expected result: **[RESULT]**

4. **[ACCEPTANCE TEST 4]**
   - Expected result: **[RESULT]**

5. **[ADDITIONAL ACCEPTANCE TESTS]**

### 18. Technical Constraints

- **Python 3.12+** — application runtime inside Docker
- **FastAPI + Jinja2** — three web GUIs
- **Docker Compose v2** — deployment
- **8GB VRAM** — Whisper and Ollama formatter run sequentially
- **Personal server** — local-first
- **INC-10b distilled model on hold** — interim `qwen2.5:7b-instruct`

#### Phase 0 scope (download + transcribe only)

Phase 0 is a **dataset-collection milestone** that runs before the full recipe repository app. It validates the Docker scaffold, yt-dlp download path, and faster-whisper transcription path in isolation.

**In scope (Phase 0):**

- Docker entrypoint with `MODE=download` and `MODE=transcribe`
- Bind-mounted `dataset/` volume with `raw/`, `transcripts/`, and `manifest.json`
- Batch download of up to 50 Instagram Reel URLs per run
- Batch transcription of downloaded videos to plain text + JSON segments
- `MODE=test` for pytest smoke tests

**Out of scope (Phase 0 — deferred to Phase 1+ / later increments):**

- Web UI (`MODE=web`), single-recipe import CLI (`MODE=import`), recipe formatting, vision/OCR, SQLite index, shopping list, bug reporting
- Writing to `recipes/` or `recipes.db`
- Ollama sidecar usage (not required for transcribe-only runs; may start idle in compose but is unused)

Phase 0 acceptance: operator can download a batch of reels and produce matching transcripts on disk using Docker commands only, with no application code beyond the entrypoint dispatch and batch scripts.

### 19. Deliverables

The final submission must contain:

- [x] Source code (`app/`, `docker/`, `scripts/`)
- [x] Unit tests (`tests/` — 41+ pytest cases)
- [ ] Integration/acceptance tests (E2E import against live reel — manual)
- [x] Generated documentation (`cursor1/USER_GUIDE.md`, MoT increment prompts)
- [ ] UML/class diagram (deferred)
- [x] Configuration files (`.env.example`, compose files)
- [x] Build/run instructions (`README.md`, `CookBook-Setup.bat`, `CookBook-CLI.bat`)

### 20. Explicit Requirements / Grading Criteria

| ID | Requirement | Priority | Verification |
|---|---|---|---|
| REQ-001 | Batch download Instagram reels to dataset/raw | HIGH | pytest + manual Phase 0 |
| REQ-002 | Batch transcribe via faster-whisper | HIGH | pytest + 6/6 dataset transcripts |
| REQ-003 | Full import pipeline Steps 1–9 | HIGH | `MODE=import` + mock formatter tests |
| REQ-004 | Production Web UI browse/search/import | HIGH | `MODE=web` port 8080 |
| REQ-005 | Testing GUI single-step runner | MEDIUM | `MODE=testing-gui` port 8081 |
| REQ-006 | Deployment GUI health dashboard | MEDIUM | `MODE=deployment-gui` port 8082 |
| REQ-007 | DebugLog per import job | MEDIUM | `working/<job_id>/debug.log` |
| REQ-008 | Shopping list HEB aisle order | MEDIUM | pytest shopping merge |

### 21. Open Questions / Decisions

- [ ] **Testing vs Deployment GUI framework** — FastAPI + Jinja vs separate lightweight SPA; default FastAPI to match Python stack
- [ ] **Deployment GUI Docker control** — subprocess `docker compose` vs Docker socket mount (security tradeoff on personal server)
- [ ] **Java module boundary** — defer until Production Web UI needs Java component
- [ ] **Testing GUI auth** — open on LAN vs simple token for personal server

Decisions:

- **Three GUIs, three MODE values** — `testing-gui` (8081), `deployment-gui` (8082), `web` (8080) — keeps dev tooling separate from end-user app
- **Step-based architecture** — one class per pipeline stage under `app/steps/`; CLI and Testing GUI share same step classes
- **Whisper for transcription; Ollama for formatting** — separate model concerns; sequential GPU loading
- **Interim formatter: `qwen2.5:7b-instruct`** — strong instruction following and JSON output; ~5GB Q4 fits 8GB VRAM after Whisper unloads. Smaller fallback: `qwen2.5:3b-instruct` (CPU or tight VRAM).
- **Distilled `cookbook-formatter` on hold** — INC-10b deferred; use Ollama pull model until enough training data and bandwidth for Unsloth workflow ([`DISTALATION.MD`](DISTALATION.MD))
- **Docker-first deployment** — all runtime deps containerized; Deployment GUI manages compose lifecycle
