# Software Requirements Specification

**Product:** CookBook  
**Version:** 1.0  
**Status:** Standalone specification  
**Date:** 2026-09-25

This document is complete by itself. A reader does not need the user guide, Docker notes, increment plan, or the working requirements draft to understand what the system must do.

Words **shall** and **shall not** are requirements. Words **should** and **may** are recommendations.

---

## 1. Introduction

### 1.1 Purpose

This specification defines the required behavior of CookBook, a local-first system that turns Instagram Reel URLs into a searchable recipe repository.

### 1.2 Scope

CookBook shall:

- Accept an Instagram Reel URL and produce a stored recipe package plus a search-index entry.
- Keep the original video and raw evidence separate from the generated recipe.
- Let an end user browse, search, edit, rate, and shop from stored recipes, and submit a bug report.
- Let a tester run each pipeline stage by itself.
- Let a deployer inspect stack health, configuration, and model status.
- Run on a personal server using Docker Compose. Core operation shall not depend on a cloud service.

The following are outside this specification:

- Multi-user accounts, authentication for household guests, and remote SaaS hosting.
- Publishing recipes or comments back to Instagram.
- A scheduled maintenance agent that triages bug reports (recorded as a future extension in Section 7).
- A Java component. The system is Python only.

### 1.3 Definitions

| Term | Meaning |
|---|---|
| Reel | A short Instagram video, addressed by an `https://www.instagram.com/reel/…` URL or an equivalent URL yt-dlp can resolve to one |
| Recipe package | The directory `recipes/<slug>/` that holds one finished recipe and its evidence |
| Slug | A filesystem-safe identifier derived from the recipe title |
| Evidence | Downloaded video, transcript, vision/OCR output, caption, and comments. Evidence is input. It is not the recipe |
| Formatter | The local language model that proposes structured recipe JSON from consolidated evidence |
| Import job | One run of the pipeline for one URL, with a working directory and a status |
| Phase 0 | Batch download and transcription into `dataset/` without writing `recipes/` |
| Personal server | The single machine that runs the Docker stack for one household |

### 1.4 Audiences

| Audience | Surface | Shall not be given |
|---|---|---|
| End user | Production web UI, port 8080 | Setup scripts, compose files, testing GUI, deployment GUI |
| Tester | Testing GUI port 8081, and CLI batch modes | — |
| Deployer | Setup script, CLI menu, deployment GUI port 8082 | A requirement to use the shopping list for daily operations |
| Developer | Source, tests, this specification | — |

### 1.5 References

Normative behavior is stated in this document. These names identify external tools the system uses; they are not additional requirements documents:

- Docker Engine 24+ and Docker Compose v2
- yt-dlp, ffmpeg, faster-whisper, Ollama HTTP API
- Python 3.12, Pydantic 2, FastAPI, pytest, SQLite

---

## 2. Overall description

### 2.1 Product perspective

CookBook is a single-user application on a personal server. Two containers run together:

- **cookbook** — Python application: pipeline, CLI, and three web UIs.
- **ollama** — local model server for recipe formatting only. It is reachable on the Docker network at `http://ollama:11434` and shall not be published to the host network.

The host installs Docker. Python, ffmpeg, yt-dlp, faster-whisper, and Ollama live in the containers.

### 2.2 Product functions

1. Batch-download reels into a dataset.
2. Batch-transcribe dataset videos.
3. Import one reel through a nine-step pipeline.
4. Search and browse stored recipes.
5. Edit a stored recipe and refresh the index.
6. Rate a recipe and attach a user note.
7. Build a shopping list from selected recipes, ordered for an H-E-B-style aisle walk.
8. Submit a bug report that points at a debug log.
9. Run one pipeline step at a time from the testing UI.
10. Show stack health, model names, and environment status from the deployment UI.

### 2.3 Operating environment

- Linux or Windows host with Docker Engine 24+ and Compose v2.
- GPU hosts: NVIDIA driver and NVIDIA Container Toolkit. CPU operation shall remain possible for tests and for transcription when CUDA is unavailable.
- Target GPU memory: 8 GB. Whisper and the formatter shall not be loaded on the GPU at the same time.
- Browser access on the same machine or LAN. No account system.

### 2.4 Constraints

- Filesystem recipe packages are the source of truth. The SQLite index is derived and must be rebuildable from those packages.
- The formatter shall not overwrite `transcript.txt` or `transcript.json`.
- The formatter shall not invent a quantity. Unknown quantity is null. Uncertain values may set `confidence` between 0 and 1.
- Steps 8 and 9 (normalize, Markdown, store, index) shall not call a language model.
- Only one GPU pipeline stage runs at a time.
- Secrets and machine-specific paths live in environment variables or `.env`. They shall not be committed.

### 2.5 Assumptions

- The operator can supply Instagram cookies when yt-dlp cannot download a reel anonymously.
- One household uses the production UI. Concurrent editors are not a design goal.
- Shopping-list aisle order follows a typical H-E-B walk: produce, meat, deli, bread, dairy, frozen, cooking, snacks, other.

---

## 3. Data requirements

### 3.1 Recipe

Stored as `recipe.json`. All recipe objects shall pass schema validation before they are written.

| Field | Rule |
|---|---|
| title | string, required, non-empty after trim |
| description | string, optional |
| servings, prep_time, cook_time, total_time | string, optional |
| ingredients | list, required, at least one Ingredient |
| instructions | list, required, at least one Instruction |
| notes | list of strings, optional |
| tags | list of strings, optional |
| source_url | string, required, valid URL |
| source_creator | string, optional |

**Ingredient:** `item` (required string); `quantity`, `preparation`, `notes` (optional strings); `confidence` (optional float, 0.0–1.0).

**Instruction:** `step` (required integer); `text` (required string); `duration`, `temperature` (optional strings). Step numbers shall be 1, 2, 3, … with no gaps and no duplicates.

### 3.2 Recipe package

Directory `recipes/<slug>/`:

| File | Required | Contents |
|---|---|---|
| video.mp4 | when download succeeded | original video, unmodified |
| transcript.txt | after transcription | plain-text transcript |
| transcript.json | after transcription | timestamped segments |
| vision.json | when video processing ran | frame-level OCR evidence |
| recipe.json | yes | validated Recipe |
| recipe.md | yes | deterministic Markdown of recipe.json |
| metadata.json | yes | source URL, creator, date added, pipeline version, slug |
| thumbnail.jpg | no | preview image |
| rating.json | no | latest 1–5 score |
| notes.json | no | user notes for this recipe |

**Uniqueness.** The slug comes from the title. If `metadata.json` in an existing folder has the same `source_url`, that folder is the same recipe and shall be reused. Otherwise a numeric suffix makes the slug unique (`title`, `title-2`, …).

**Consistency.** Every successful write of `recipe.json` shall upsert the SQLite index in the same operation. A failed index write shall not leave the package and the index describing different titles or ingredient text.

### 3.3 Import job

| Field | Rule |
|---|---|
| job_id | unique string |
| source_url | required |
| status | `pending`, `running`, `completed`, `failed` |
| current_stage | integer 0–9 |
| working_dir | path under `working/<job_id>/` |
| user_comment, custom_instruction | optional strings |
| video_processing_enabled | boolean |
| error_message | optional, set on failure |
| created_at | ISO 8601 |
| completed_at | ISO 8601, optional |

### 3.4 Dataset video metadata (Phase 0)

Sidecar `dataset/metadata/<reel_id>.json`:

- reel_id, source_url
- title, author, author_username, caption (optional)
- comments: list of `{author, text, timestamp}`
- comment_count, like_count, upload_date (optional)
- extracted_at (ISO 8601)

`dataset/manifest.json` records each attempted URL: url, reel_id, filename, status, downloaded_at, and error when failed. After transcription it also records transcript_status, transcript file names, and transcribed_at.

Caption and comments are evidence. They shall not replace the transcript.

### 3.5 User note

note_id, recipe_slug, text (required, non-empty), created_at, updated_at.

### 3.6 Rating

recipe_slug, score (integer 1–5), created_at, updated_at. One current rating per recipe.

### 3.7 Shopping list item

item_id, ingredient_name (required), quantity (optional), aisle_category, source_recipe_slugs, checked (default false).

Aisle values: `produce`, `meat`, `deli`, `bread`, `dairy`, `frozen`, `cooking`, `snacks`, `other`.

### 3.8 Bug report

report_id, description (required), debug_log_path, related_job_id (optional), related_recipe_slug (optional), created_at, status (`open`, `reviewed`, `resolved`).

### 3.9 Debug log

log_id, job_id (optional), entries, pipeline_version, model_versions (Whisper model and formatter model), created_at.

Each entry: timestamp, stage number, level (`INFO`, `WARNING`, `ERROR`), message.

---

## 4. Persistence

The system shall save:

- When pipeline step 9 completes: the recipe package and the SQLite index row.
- When the user saves an edit: `recipe.json`, regenerated `recipe.md`, and an index upsert.
- When the user submits a rating or note: a JSON sidecar in the recipe package.
- When the user submits a bug report: JSON under `working/bugreports/`.
- When a batch download or transcription finishes a URL: `dataset/manifest.json` and the video or transcript files.

Mechanisms:

| Store | Role | Format |
|---|---|---|
| `recipes/<slug>/` | source of truth | JSON, Markdown, plain text, mp4 |
| `recipes.db` | search index derived from recipe.json | SQLite |
| `dataset/` | Phase 0 videos, transcripts, metadata, manifest | mp4, txt, JSON |
| `working/<job_id>/` | scratch for one import, including `debug.log` | mixed |
| `working/bugreports/` | bug reports | JSON |

The system shall create these directories on startup when they are missing.

---

## 5. Startup

On container start the entrypoint shall:

1. Check that ffmpeg and yt-dlp are available inside the image.
2. Create data directories if missing: recipes, working, database directory, `dataset/raw`, `dataset/transcripts`, `dataset/metadata`.
3. Read `MODE` and start exactly one path.

| MODE | Behavior | GPU |
|---|---|---|
| `web` | Production UI. Default port 8080 | Needed when an import runs |
| `testing-gui` | Testing UI. Default port 8081 | Per step |
| `deployment-gui` | Deployment UI. Default port 8082 | No |
| `import` | One full import from a URL argument, then exit | Yes for transcribe and format |
| `download` | Phase 0 batch download, then exit | No |
| `transcribe` | Phase 0 batch transcription, then exit | Recommended |
| `test` | Run pytest and exit | No |

Configuration comes from environment variables and an optional `.env` file. The production home page shall offer:

- an import URL field
- a video-processing toggle (OCR on or off)
- an optional user comment
- an optional custom instruction passed to the formatter
- a way to search and browse existing recipes

Windows setup may be driven by `CookBook-Setup.bat`, which asks for storage paths and GPU versus CPU, writes `.env`, and starts Compose. `CookBook-CLI.bat` may expose the batch modes. Those scripts are deployer tools.

The formatter client shall use `OLLAMA_HOST` (default `http://ollama:11434`) and `FORMATTER_MODEL` (default `cookbook-formatter`).

---

## 6. Functional requirements

### 6.1 Import recipe

**ID:** FR-IMPORT  
**Trigger:** Production import form, `MODE=import`, or `cookbook import <url>`.  
**Input:** Reel URL. Optional user comment, custom instruction, and video-processing flag.

**Validation:** The URL shall be an HTTP(S) URL. A URL that is not an Instagram reel shall be rejected with a message that names the URL.

**Behavior:** Run steps 1–9 in order (Section 10). Write a debug log under `working/<job_id>/`. If video processing is off, skip steps 4 and 5 and record that they were skipped.

**Success:** Job status `completed`. Package under `recipes/<slug>/`. Index row present. Production UI opens that recipe.

**Failure:** Job status `failed`. Error message stored on the job and in the debug log. Partial files remain in the working directory. The production UI shows a dismissible error that includes the step number.

### 6.2 Pipeline steps

Each step is one class with `name`, `step_number` (1–9), `requires`, and `run(context) -> result`. A step shall not call another step. The orchestrator or the testing UI invokes steps.

| Step | Name | Output |
|---|---|---|
| 1 | Download | video file and metadata sidecar (caption, author, comments when yt-dlp provides them) |
| 2 | Extract audio | mono, 16 kHz, PCM WAV |
| 3 | Transcribe | `transcript.txt` and timestamped `transcript.json` via faster-whisper |
| 4 | Extract frames | frames at `FRAME_INTERVAL` seconds (default 2.0). Skipped when video processing is off |
| 5 | Vision / OCR | `vision.json` with frame text. Skipped when video processing is off |
| 6 | Consolidate | one evidence object: transcript, vision, metadata, user comment, custom instruction |
| 7 | Format | draft recipe JSON from the Ollama formatter |
| 8 | Normalize and Markdown | schema-valid `recipe.json` and deterministic `recipe.md`. No language model |
| 9 | Store and index | recipe package and SQLite upsert |

Step 7 shall send the consolidated evidence and require JSON only. On invalid JSON the step may retry a bounded number of times. If validation still fails, the step fails and does not write a package.

Re-import of a URL already stored shall update that package rather than create a second slug.

### 6.3 Search and browse

**ID:** FR-SEARCH  
**Trigger:** Production browse page, with an optional query.  
**Behavior:** Empty query lists recipes from the repository. A non-empty query searches the SQLite index for a case-insensitive substring of title, ingredient text, or instruction text, and returns slug, title, source URL, and creator.  
**Success:** Matching recipes, ordered by title, limited to 50.  
**Failure:** A missing database file is created empty; the page shows an empty list rather than a stack trace.

### 6.4 Edit recipe

**ID:** FR-EDIT  
**Trigger:** Production editor save.  
**Behavior:** Update allowed recipe fields, re-validate, rewrite `recipe.json` and `recipe.md`, upsert the index.  
**Failure:** Invalid title, empty ingredient list, or non-sequential steps are rejected and the previous package remains.

### 6.5 Rating and notes

**ID:** FR-RATE  
**Trigger:** Production recipe page.  
**Behavior:** A score outside 1–5 is rejected. A valid score replaces `rating.json`. A non-empty note is appended to the recipe’s notes with timestamps. Empty note text is rejected.

### 6.6 Shopping list

**ID:** FR-SHOP  
**Trigger:** Production shopping page with one or more selected slugs.  
**Behavior:**

- Load each recipe from its package.
- Merge ingredients by case-insensitive item name.
- If two quantities differ, concatenate them with ` + ` rather than parsing units.
- Record every contributing slug.
- Assign an aisle with keyword rules; unknown items are `other`.
- Sort by aisle walk order, then by ingredient name.

**Failure:** An unknown slug is reported and omitted. The list for the remaining slugs is still shown.

### 6.7 Bug report

**ID:** FR-BUG  
**Trigger:** Production bug-report form.  
**Input:** Required description. Optional related recipe slug and job id.  
**Behavior:** Write a bug report JSON under `working/bugreports/` with status `open` and a debug log path.  
**Failure:** Empty description is rejected.

### 6.8 Batch download

**ID:** FR-DOWNLOAD  
**Trigger:** `MODE=download`.  
**Input:** Either `dataset/urls.txt` (one URL per line) or `DOWNLOAD_SOURCE_URL` (a profile or collection page). Limit `DOWNLOAD_LIMIT`, default 50, maximum 50.

**Behavior:**

- Reject a run that has neither input.
- Skip blank lines. Log and skip non-HTTP(S) URLs.
- If more than the limit would be processed, take the first 50 and log the truncation.
- Download with yt-dlp to `dataset/raw/{reel_id}.mp4`.
- Skip a URL whose video file already exists.
- Write or update metadata and `manifest.json`.
- Do not transcribe, format, or write `recipes/`.

Per-URL failures (rate limit, deleted reel, network) set that manifest entry to `failed` and the batch continues. A missing yt-dlp binary or an unwritable volume exits non-zero.

### 6.9 Batch transcribe

**ID:** FR-TRANSCRIBE  
**Trigger:** `MODE=transcribe` after videos exist in `dataset/raw/`.  
**Input:** Video files in `dataset/raw/`. Optional `TRANSCRIBE_ONLY` for one reel id. Model and device from `WHISPER_MODEL` and `WHISPER_DEVICE`.

**Behavior:**

- If no video exists, exit with a message that names the directory.
- Skip a video that already has a transcript unless `TRANSCRIBE_FORCE=true`.
- Write `{reel_id}.txt` and `{reel_id}.json` under `dataset/transcripts/`.
- Update the manifest. Do not run OCR, formatting, or recipe storage.

Per-video failures are recorded and the batch continues. If `WHISPER_DEVICE=cuda` and the GPU is unavailable, exit with a message that names CPU fallback.

### 6.10 Testing GUI

**ID:** FR-TESTGUI  
**Port:** 8081.

The tester shall be able to:

- Paste reel URLs and save them to `dataset/urls.txt`.
- Choose a URL and run exactly one step.
- See success or failure, duration, and the error string.
- See prerequisite failures when earlier artifacts are missing.

The testing GUI shall call the same step classes as the CLI and the full import.

### 6.11 Deployment GUI

**ID:** FR-DEPLOYGUI  
**Port:** 8082.

The deployer shall see:

- Whether `docker` and `ffmpeg` are on `PATH` inside the app container.
- Whether Ollama answers `GET /api/tags`.
- The configured Whisper model name and formatter model name.

The deployment GUI shall not run pipeline steps and shall not return secret values in page HTML.

### 6.12 Production recipe view

**ID:** FR-VIEW  
The recipe page shall show title, description, ingredients, ordered instructions, source URL, and the original video when `video.mp4` exists. A missing slug returns HTTP 404.

---

## 7. Background processes

No background worker is required for the current product. Import jobs run in the request or CLI process that started them. GPU steps inside one job are sequential.

**Deferred:** a maintenance agent may later scan `working/bugreports/` and debug logs on a schedule. It is not required for acceptance of this specification. File layouts in Section 3 shall already support it.

---

## 8. Configuration

| Name | Default | Purpose |
|---|---|---|
| `MODE` | `web` in Compose; `test` in the settings class when unset | Startup path |
| `REPOSITORY_PATH` | `/data/recipes` | Recipe packages |
| `WORKING_DIR` | `/data/working` | Job scratch and bug reports |
| `DATABASE_PATH` | `/data/db/recipes.db` | Search index |
| `DATASET_DIR` | `/data/dataset` | Phase 0 root |
| `DOWNLOAD_LIMIT` | 50 (hard max 50) | Batch size |
| `DOWNLOAD_SOURCE_URL` | empty | Hub URL for batch download |
| `WHISPER_MODEL` | `large-v3` | Transcription model |
| `WHISPER_DEVICE` | `cuda` | `cuda` or `cpu` |
| `FORMATTER_PROVIDER` | `ollama` | `ollama` or `mock` |
| `OLLAMA_HOST` | `http://ollama:11434` | Formatter API |
| `FORMATTER_MODEL` | `cookbook-formatter` | Ollama model name |
| `FRAME_INTERVAL` | 2.0 | Seconds between OCR frames |
| `VIDEO_PROCESSING_DEFAULT` | true | OCR on when the caller omits the flag |
| `WEB_PORT` | 8080 | Production |
| `TESTING_GUI_PORT` | 8081 | Testing |
| `DEPLOYMENT_GUI_PORT` | 8082 | Deployment |
| `YTDLP_COOKIES_FILE` | empty | Optional cookie file for Instagram |
| `KEEP_WORKING` | false | Retain scratch after success when true |

Ollama shall load at most one model (`OLLAMA_MAX_LOADED_MODELS=1`). The bootstrap script shall register `cookbook-formatter` from `cookbook-formatter.gguf` and the Modelfile when that file is mounted. If the GGUF is absent, the operator may set `FORMATTER_MODEL=qwen2.5:7b-instruct` and pull that model instead. Temperature for the distilled model shall be 0.1. The system prompt shall require JSON only and shall forbid invented quantities.

---

## 9. External interfaces

### 9.1 User interfaces

Server-rendered HTML. Three apps, one process mode each, as in Section 6. Shared static files may be used. The production UI is the only interface an end user needs.

### 9.2 Software interfaces

| Interface | Contract |
|---|---|
| yt-dlp | Download video and metadata. Failures are per URL |
| ffmpeg | WAV extraction and frame extraction |
| faster-whisper | Audio file in, segments out |
| Tesseract (via pytesseract) | Image in, text out, for vision step |
| Ollama `POST /api/chat` or generate API | Prompt in, JSON text out |
| SQLite file | Index as specified in Section 3 |
| Docker Compose | Starts `cookbook` and `ollama`; GPU override file enables NVIDIA devices |

### 9.3 Communications

Browser to production UI: HTTP on port 8080. Application to Ollama: HTTP on the Compose network only. No outbound requirement for formatting or transcription after model weights are present. Download mode needs network access to Instagram (and to yt-dlp’s own update endpoints only if the image allows them).

---

## 10. Architecture constraints

Package layout:

```text
app/
  steps/            one module per pipeline step, plus PipelineStep base
  downloader/       yt-dlp provider
  media/            ffmpeg audio and frames
  transcription/    Whisper provider
  vision/           OCR provider
  extraction/       consolidation and Ollama formatter
  formatting/       deterministic Markdown
  storage/          recipe packages
  search/           SQLite index
  workflow/         orchestrator only
  web/              production, testing, and deployment apps
  config/           environment settings
  cli/              same steps as the testing UI
  models/           Pydantic entities
  shopping/
  bugreport/
```

Rules:

- CLI, testing UI, and full import shall share `app/steps` implementations.
- Transcription, vision, and formatter shall sit behind provider interfaces so tests can substitute mocks.
- Dependency direction: web → workflow → steps → providers. Steps shall not import web modules.
- `PipelineOrchestrator` exposes `run_all`, `run_step`, and `run_from`. It holds the GPU lock for steps 3 and 7.
- Domain types `Recipe`, `Ingredient`, `Instruction`, `ImportJob`, `UserNote`, `Rating`, `ShoppingListItem`, `BugReport`, and `DebugLog` live in `app/models` and match Section 3.

Step context carries job id, source URL, working directory, dataset and repository paths, video-processing flag, user comment, custom instruction, and artifacts from earlier steps. Step result carries step number, success, artifacts, metrics, error, and duration.

---

## 11. Error handling

The system shall report:

| Condition | Behavior |
|---|---|
| Missing or blank URL, title, description-of-bug | Reject with a message that names the field |
| Non-reel or non-HTTP URL | Reject and include the value |
| Schema failure on recipe JSON | Do not persist; name the field |
| Missing prerequisite artifact | Name the missing step output |
| yt-dlp failure (private, removed, rate limit) | Per-item failure; batch continues |
| Corrupt media or Whisper failure | Per-item failure; working files kept |
| GPU out of memory | Fail the step; message says to retry on CPU or a smaller model |
| Ollama unreachable | Fail step 7; message includes `OLLAMA_HOST` |
| Unwritable volume | Non-zero exit or HTTP 500 with the path |

Messages shall identify the failing step or file when one exists, and shall suggest a correction when one is known (CPU device, cookie file, model pull). Web errors shall be dismissible. Unrecoverable import failures shall leave partial artifacts in `working/<job_id>/` and shall not delete an older successful package for the same URL.

---

## 12. Quality attributes

| Metric | Target |
|---|---|
| Schema validation of stored recipes | 100% of writes pass before persist |
| Search query | under 200 ms for a household-sized library (thousands of recipes, not millions) |
| Recipe page | under 2 seconds on the local server, excluding video buffering |
| Import idempotence | same source URL updates one slug |
| Evidence immutability | formatter never changes transcript files |
| Test isolation | unit tests shall not call Instagram, Whisper weights, or a live Ollama server |

OCR coverage and import success rate depend on the reel and the model. They are operational metrics, not acceptance gates for a single fixture.

---

## 13. Testing requirements

Tests live in `tests/` and run with pytest (`MODE=test` or a local `pytest`). They shall not require a GPU, a display, or network access to Instagram.

Required coverage:

| Area | Cases |
|---|---|
| Models | Required fields, empty title, confidence bounds, sequential steps, rating range |
| Storage | Package write/read, slug reuse when source URL matches, suffix when it does not |
| Downloader | URL checks, command construction, metadata parsing, failure objects. Live downloads mocked |
| Transcription | Provider mapping of segments. Model load mocked |
| Formatter | Mock provider returns JSON; invalid JSON does not persist; null quantity preserved |
| Markdown | Deterministic rendering of a fixture recipe |
| Search | Upsert and substring search on title and ingredient text |
| Shopping | Merge of the same item, distinct quantities joined with ` + `, aisle order |
| Steps | Orchestrator runs one step; prerequisite failure; mock providers through steps 1–9 |
| Bug report | Report file written with description and status `open` |
| Config | Defaults and environment overrides, including download limit cap |

Each test class or module shall include at least one success path and one rejection path where the unit validates input.

Integration against a live reel is manual and is not part of the automated suite.

---

## 14. Documentation requirements

The repository shall include:

- This specification.
- A short project description a new reader can finish in a few minutes.
- A user guide that separates deployer, tester, and end user, and explains debug logs.
- Setup commands for Compose, including GPU and test files.
- Docstrings on public step classes, storage, and the orchestrator.

Generated UML is not required.

---

## 15. Development process

Work proceeds in increments: skeleton and configuration, models, storage, each pipeline provider, orchestrator, then web UIs, editor, ratings, shopping list, and bug reports. Each increment shall keep the automated suite passing before the next increment starts. Provider interfaces land before the concrete Whisper, OCR, and Ollama implementations so tests stay offline.

---

## 16. Acceptance tests

1. **Batch download.** Given a fixture URL list and a mocked downloader, the run writes manifest entries, skips an existing file, and continues after one failed URL. No file appears under `recipes/`.
2. **Batch transcribe.** Given a fixture media file and a mocked Whisper provider, the run writes `.txt` and `.json` transcripts and updates the manifest. A second run skips the file unless force is set.
3. **Full import.** Given mocked download, transcription, vision, and formatter output that matches the recipe schema, steps 1–9 write a package with video path, transcript, `recipe.json`, `recipe.md`, metadata, and an index row. The transcript file bytes are unchanged by step 7.
4. **Formatter refusal.** Given formatter output that invents structure the schema rejects, import fails, no new package is published, and the debug log records the step number.
5. **Duplicate URL.** Importing the same source URL again resolves to the existing slug.
6. **Search.** After two packages are indexed, a query substring of an ingredient returns only the matching recipe.
7. **Edit.** Saving a new title updates `recipe.json` and the index. An empty title does not.
8. **Shopping list.** Two recipes that share an ingredient produce one line, both slugs, and aisle order produce before other.
9. **Bug report.** A description creates `working/bugreports/*.json` with status `open`. A blank description does not.
10. **Production page.** The recipe route returns the title and ingredient list for a stored slug and 404 for an unknown slug.
11. **Testing step.** `POST` of a single step number invokes that step only.
12. **Deployment page.** The deployment home renders Whisper and formatter model names and an Ollama reachability status without embedding secrets.
13. **Automated suite.** `pytest` exits 0 with network and GPU unavailable.

---

## 17. Deliverables

| Item | Location |
|---|---|
| Application source | `cursor1/app/` |
| Tests | `cursor1/tests/` |
| Container build and Compose files | `cursor1/docker/`, `cursor1/docker-compose*.yml` |
| Entrypoint and seed scripts | `cursor1/scripts/` |
| Example environment | `cursor1/.env.example` |
| Windows deployer launchers | `CookBook-Setup.bat`, `CookBook-CLI.bat` |
| Project description | `cursor1/PROJECT_DESCRIPTION.md` |
| This specification | `cursor1/SRS.md` |
| Operator guide | `cursor1/USER_GUIDE.md` |

A class diagram is not a required deliverable.

---

## 18. Requirement index

| ID | Requirement | Priority | Acceptance |
|---|---|---|---|
| FR-DOWNLOAD | Batch download to `dataset/raw` | High | Test 1 |
| FR-TRANSCRIBE | Batch transcribe with faster-whisper | High | Test 2 |
| FR-IMPORT | Steps 1–9 and package plus index | High | Tests 3, 4, 5 |
| FR-SEARCH | Browse and substring search | High | Test 6 |
| FR-EDIT | Edit package and re-index | High | Test 7 |
| FR-SHOP | Merged list in aisle order | Medium | Test 8 |
| FR-BUG | Bug report JSON and debug log path | Medium | Test 9 |
| FR-VIEW | Recipe page and video | High | Test 10 |
| FR-TESTGUI | Single-step runner on port 8081 | Medium | Test 11 |
| FR-DEPLOYGUI | Health page on port 8082 | Medium | Test 12 |
| FR-RATE | Rating 1–5 and user notes | Medium | Section 13 |
| NFR-LOCAL | No cloud dependency for transcribe or format | High | Section 2 |
| NFR-GPU | Whisper and formatter not concurrent | High | Section 2.4 |
| NFR-EVIDENCE | Transcripts immutable; quantities not invented | High | Tests 3, 4 |
| NFR-TEST | Offline pytest | High | Test 13 |

---

## 19. Decisions

| Topic | Decision |
|---|---|
| Language | Python 3.12. Java is out of scope |
| Web | FastAPI and Jinja2 templates |
| Three UIs | Separate `MODE` values and ports 8080, 8081, 8082 |
| Transcription | faster-whisper, local |
| Formatting | Ollama. Default model `cookbook-formatter`. Fallback `qwen2.5:7b-instruct` |
| GPU | Sequential loading. Ollama max loaded models = 1 |
| Truth | Recipe directory first, SQLite second |
| Shopping merge | Conservative string merge, no unit arithmetic |
| Deployment GUI control of the Docker socket | Not required. The page reports health. Stack start and stop remain Compose or the setup script |
| Testing GUI authentication | None. The port is for the operator’s LAN |
| Maintenance agent | Deferred |
