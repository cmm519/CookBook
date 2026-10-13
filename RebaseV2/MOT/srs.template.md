# Software requirements specification

You fill this file. It is stage 1 of the workflow in `README.md`.

This file is the only place that states what the system must do. Class names, prompt filenames, and the directory tree belong in `architecture.template.md` and `structure.template.md`.

The shape follows the software requirements topics in ISO/IEC/IEEE 29148:2018. Agents cite requirement IDs from the table below. They do not paste this whole file into every prompt.

## Required: Identity

**CookBook** (RebaseV2): a local-first recipe repository built from Instagram Reels.

Author: Corbin Copper (Net ID: CMM519). Rebuild of the `cursor1/` implementation. Behavior is carried over from `cursor1/SRS.md` v1.0, and the code is reorganized under Clean Architecture.

## Required: Purpose

This specification is for the developer and the coding agents that will rebuild CookBook from scratch in `RebaseV2/`. It records every behavior the rebuild must satisfy, so the rebuilt system can replace the `cursor1/` implementation with no user-visible regression. It is the acceptance record: a requirement is met only when its Verification column holds.

## Required: Scope

CookBook takes an Instagram Reel URL. It downloads the video, extracts and transcribes the audio, can read on-screen text with OCR, and turns that evidence into a validated, structured recipe. The result is stored as a self-contained recipe package on disk and indexed for search. One household uses it on a personal server. In the production web app they import, browse, search, view, edit, rate, and annotate recipes, build an aisle-ordered shopping list, and file bug reports. A tester can run each pipeline stage alone, and a deployer can inspect stack health. Speech-to-text and recipe formatting run on the household's own machine, so recipes, videos, and evidence stay private and work offline once model weights are present.

## Required: Product perspective

CookBook stands alone on one personal server, deployed as two Docker Compose containers: the CookBook application and an Ollama model server used only for recipe formatting. It talks to these external systems:

- **Instagram**, through yt-dlp, to download reel videos and metadata (caption, author, comments). This is the only required outbound network dependency.
- **Ollama** (sidecar container), over HTTP on the private Compose network only, to turn consolidated evidence into recipe JSON.
- **Host filesystem** (bind-mounted volumes) for recipe packages, the dataset, job scratch space, the search database, and model caches.
- **NVIDIA GPU** (optional), through the NVIDIA Container Toolkit, for Whisper transcription and Ollama inference.
- **A web browser** on the same machine or LAN, for the three web interfaces.

## Required: Users

- **End user** (household cook): uses the production web UI to import reels and to browse, search, view, edit, rate, annotate, and shop from recipes. They can use a browser. They do not install Docker or edit configuration.
- **Tester**: uses the testing web UI and the CLI batch modes to queue URLs, run one pipeline stage at a time, and inspect intermediate artifacts. They can read logs and JSON files.
- **Deployer**: installs the Docker stack with the setup script or Compose, chooses storage paths and GPU or CPU, manages models, and checks health on the deployment UI. They can use Docker and edit `.env`.
- **Developer**: maintains the source and the automated tests, and extends providers. They know Python and pytest.

## Required: Product functions

- Import one reel through a nine-stage pipeline: download, extract audio, transcribe, extract frames, OCR, consolidate evidence, format with a local LLM, normalize and render Markdown, then store and index.
- Batch-download reels into a dataset (Phase 0) and batch-transcribe them, without creating recipes.
- Search and browse stored recipes, and view one recipe with its original video.
- Edit a stored recipe, rate it 1–5, and attach notes.
- Build a merged shopping list from several recipes, ordered by an H-E-B-style aisle walk.
- Submit a bug report linked to a debug log.
- Run any single pipeline stage from a testing UI.
- Report stack health, model names, and tool availability on a deployment UI.
- Start exactly one mode (web, testing, deployment, import, download, transcribe, test) from one configuration setting.

## Required: Assumptions and dependencies

- The host runs Docker Engine 24+ and Docker Compose v2. GPU hosts also have an NVIDIA driver and the NVIDIA Container Toolkit.
- The target GPU has 8 GB of VRAM, so Whisper and the formatter model cannot be resident at the same time.
- The application container provides Python 3.12, ffmpeg, yt-dlp, faster-whisper, and Tesseract. The project does not build these tools.
- The Ollama image provides the model server. The formatter model is either the local `cookbook-formatter` GGUF registered at startup, or `qwen2.5:7b-instruct` pulled as a fallback.
- The operator can supply an Instagram cookie file when a reel cannot be downloaded anonymously.
- One household uses the production UI. Concurrent editing of the same recipe is not a design goal.
- Aisle order follows a typical H-E-B walk: produce, meat, deli, bread, dairy, frozen, cooking, snacks, other.
- The `cursor1/` implementation is reference behavior only. The rebuild does not import its code.

## Required: Out of scope

- User accounts, login, authentication, or per-user data.
- Cloud hosting, remote SaaS operation, or any cloud LLM or cloud transcription provider.
- Publishing recipes, comments, or anything else back to Instagram.
- Sources other than Instagram reels (TikTok, YouTube, web recipe pages).
- A scheduled maintenance agent that triages bug reports. File layouts must allow one later, but none is built.
- Background job queues, WebSocket progress, or a job status polling API. Imports run in the request or CLI process that started them.
- Preview or approval of a draft recipe before it is stored.
- Export to Mealie, Tandoor, or another recipe manager.
- Mobile apps, a PWA, or share-sheet targets.
- Training or distilling the formatter model (LoRA, Unsloth). The rebuild only consumes a model that already exists.
- Unit conversion or arithmetic when merging shopping-list quantities.
- Starting, stopping, or controlling Docker from the deployment UI.
- Any Java component.

## Required: Requirements

| ID | Statement | Priority | Verification |
| --- | --- | --- | --- |
| SRS-FR-001 | Import accepts an HTTP(S) Instagram reel URL. It rejects a missing, non-HTTP(S), or non-reel URL with a message that includes the offending value, and runs no pipeline stage. | must | A test submits `ftp://x`, a blank string, and `https://example.com/video`. Each returns a rejection containing the value, and no job working directory is created. |
| SRS-FR-002 | A successful import runs stages 1–9 in order. It ends with job status `completed`, a recipe package, and a matching search-index row. | must | An acceptance test with fake download, transcription, OCR, and formatter adapters imports one URL. The package holds video, transcript (`.txt`, `.json`), `recipe.json`, `recipe.md`, and `metadata.json`. The index returns the slug, and the job status is `completed`. |
| SRS-FR-003 | When video processing is off, the import skips stages 4 and 5 and records each skip in the job's debug log. | must | Importing with the toggle off writes no `vision.json`, and the debug log has a "skipped" entry for stages 4 and 5. |
| SRS-FR-004 | When any stage fails, the job status becomes `failed`. The error message, including the stage number, is stored on the job and in the debug log. Partial artifacts stay in the job working directory, and an existing package for the same URL is not deleted or changed. | must | A test injects a failure into stage 7 after a prior successful import of the same URL. The job is `failed`, the error names stage 7, working files remain, and the old package bytes are unchanged. |
| SRS-FR-005 | Re-importing a source URL that already has a package updates that package and keeps its slug. | must | Importing the same URL twice yields one package directory and one index row. |
| SRS-FR-006 | A new recipe's slug is derived from its title and is filesystem-safe. When a different source URL already holds that slug, a numeric suffix is added (`title`, `title-2`, `title-3`, …). | must | Two imports with the same title and different URLs produce `<slug>` and `<slug>-2`. A title with `/`, `:`, and spaces produces a slug with only lowercase letters, digits, and hyphens. |
| SRS-FR-007 | The formatting stage sends the consolidated evidence to the formatter and requires JSON-only output. Consolidated evidence is the transcript, OCR text, caption, comments, user comment, and custom instruction. On unparseable or schema-invalid output it retries at most 2 times. If output is still invalid, the stage fails and no package is written. | must | A fake formatter returning invalid JSON three times causes the stage to fail after 3 calls, with no new package. A fake returning valid JSON on the second call succeeds. The evidence sent to the fake contains each of the six inputs. |
| SRS-FR-008 | The pipeline never invents a quantity. An ingredient with unknown quantity is stored with a null quantity. A confidence value, when present, is between 0.0 and 1.0. The formatter instruction forbids invented quantities. | must | A fake formatter returns an ingredient with `quantity: null`. The stored `recipe.json` keeps `null`. A confidence of 1.5 is rejected. The formatter prompt text contains the no-invented-quantities rule. |
| SRS-FR-009 | A recipe is accepted only when its title is non-blank after trimming, it has at least one ingredient and at least one instruction, step numbers run 1, 2, 3, … with no gaps or duplicates, every ingredient has a non-blank item, and the source URL is a valid URL. A rejection names the failing field. | must | Unit tests build a recipe that violates each rule, one rule per test. Each is rejected with the field name, and a valid fixture is accepted. |
| SRS-FR-010 | Markdown rendering of a recipe is deterministic and uses no language model. The same recipe always renders to byte-identical Markdown. | must | Rendering a fixture recipe twice produces identical bytes, and the output matches a stored golden file. |
| SRS-FR-011 | No stage after transcription modifies the transcript files. | must | The acceptance test hashes `transcript.txt` and `transcript.json` after stage 3 and again after stage 9. The hashes match. |
| SRS-FR-012 | Every successful write of a recipe also upserts its index row. If the index write fails, the package is restored to its previous content, so the package and the index never disagree on title or ingredient text. | must | A test makes the index fail during an edit. The previous `recipe.json` is restored byte-for-byte and the index still returns the previous title. |
| SRS-FR-013 | The search index can be rebuilt entirely from the recipe packages on disk. | must | Deleting the database and running the rebuild produces search results identical to those before the deletion. |
| SRS-FR-014 | Browse with an empty query lists stored recipes. A non-empty query returns recipes whose title, ingredient text, or instruction text contains the query (case-insensitive). Each result gives slug, title, source URL, and creator, ordered by title, at most 50. | must | With two indexed recipes, a substring of one recipe's ingredient returns only that recipe. An uppercase query matches lowercase text. 60 indexed recipes return 50. |
| SRS-FR-015 | If the search database file is missing, it is created empty, and browse shows an empty list instead of an error. | must | Starting with no database file, `GET /recipes` returns HTTP 200 with an empty list, and the file now exists. |
| SRS-FR-016 | The recipe page shows title, description, ingredients, ordered instructions, and source URL. It embeds the original video when one exists. An unknown slug returns HTTP 404. | must | `GET /recipes/<slug>` for a stored fixture contains the title and every ingredient item. The video element is present when `video.mp4` exists. `GET /recipes/nope` returns 404. |
| SRS-FR-017 | Saving an edited recipe re-validates it, rewrites `recipe.json` and `recipe.md`, and upserts the index. An invalid edit is rejected with the failing field named, and the previous package stays unchanged. | must | Saving a new title updates the file, the Markdown heading, and search results. Saving a blank title is rejected and the package bytes are unchanged. |
| SRS-FR-018 | A recipe rating is an integer from 1 to 5. A valid rating replaces the recipe's current rating, and a rating outside 1–5 is rejected. | must | Rating 4, then 2, leaves one current rating of 2. Ratings 0 and 6 are rejected and leave the stored rating unchanged. |
| SRS-FR-019 | A non-empty note is appended to the recipe's notes with created and updated timestamps. An empty or whitespace-only note is rejected. | must | Adding two notes yields two timestamped entries in order. Adding `"   "` is rejected. |
| SRS-FR-020 | The shopping list loads each selected recipe and merges ingredients by case-insensitive item name. Different quantities for the same item are joined with ` + ` without unit arithmetic. Every contributing recipe slug is recorded on the merged line. | must | Two recipes with `Garlic` "2 cloves" and `garlic` "1 head" produce one line, quantity `2 cloves + 1 head`, listing both slugs. |
| SRS-FR-021 | Each shopping-list item gets an aisle from keyword rules (`produce`, `meat`, `deli`, `bread`, `dairy`, `frozen`, `cooking`, `snacks`, `other`). Unknown items are `other`. The list is sorted by aisle walk order, then by item name. | must | A list with "onion", "chicken thigh", and "mystery sauce" orders produce, meat, other. Items in the same aisle are alphabetical. |
| SRS-FR-022 | An unknown slug in a shopping-list request is reported and omitted, and the list is still built from the remaining slugs. | must | A request for one valid and one unknown slug shows the valid recipe's items and a message naming the unknown slug. |
| SRS-FR-023 | A bug report needs a non-blank description, and may name a recipe slug and a job id. It is saved as JSON with status `open`, a creation timestamp, and the path of the related debug log. A blank description is rejected. | must | Submitting "Video missing" creates one bug-report JSON file with status `open`. Submitting `""` creates no file and returns a message naming the description field. |
| SRS-FR-024 | Each import job writes a debug log in its working directory. Every entry has a timestamp, stage number, level (`INFO`, `WARNING`, `ERROR`), and message. The log also records the pipeline version and the Whisper and formatter model names. | must | After the acceptance import, the job's debug log parses, holds at least one entry per executed stage, and names both models. |
| SRS-FR-025 | Batch download reads URLs from the dataset URL list file, or from a configured source page URL. With neither, it exits non-zero with a message naming both inputs. | must | With no list file and no source URL, the download mode exits non-zero and the message names both. |
| SRS-FR-026 | Batch download skips blank lines, and skips non-HTTP(S) URLs with a log entry. It processes at most the configured limit (default 50, hard maximum 50) and logs any truncation. | must | A list with 55 valid URLs, one blank line, and one `ftp://` line processes 50 URLs. It logs the truncation and the skipped `ftp://` line. |
| SRS-FR-027 | Batch download saves each video to the dataset raw folder, keyed by reel id, with a metadata sidecar (caption, author, comments, counts, upload date). It skips a URL whose video already exists. It records each URL's outcome in the dataset manifest, and a per-URL failure marks that entry `failed` and continues. It never transcribes, formats, or writes recipe packages. | must | With a fake downloader, a three-URL list (one existing, one failing, one new) produces manifest entries `skipped`, `failed`, `downloaded`. No recipe package directory appears. |
| SRS-FR-028 | Batch download exits non-zero with the path or tool named when yt-dlp is missing or a dataset folder is unwritable. | must | A test with an unwritable raw folder exits non-zero and the message contains the folder path. |
| SRS-FR-029 | Batch transcribe processes the videos in the dataset raw folder. With no videos it exits with a message naming the folder. It skips a video that already has a transcript unless force is set, and can be limited to one reel id. | must | A second run skips the transcribed video. A forced run re-transcribes it. Limiting to one id touches only that id. With an empty folder the message names the folder. |
| SRS-FR-030 | Batch transcribe writes a plain-text and a timestamped-segment transcript per video and updates the manifest. Per-video failures are recorded and the batch continues. It never runs OCR, formatting, or recipe storage. | must | With a fake transcriber that fails on one of two videos, one `.txt`/`.json` pair is written, the manifest marks one `failed`, and no recipe package appears. |
| SRS-FR-031 | When CUDA is requested for transcription and no GPU is available, the run stops with a message that names the CPU fallback setting. | must | A fake device probe reporting no GPU makes transcribe mode exit non-zero, with a message containing `WHISPER_DEVICE=cpu`. |
| SRS-FR-032 | The testing UI lets the tester paste reel URLs and save them to the dataset URL list file. | must | Posting two URLs to the testing UI appends both to the list file, and the page then lists them. |
| SRS-FR-033 | The testing UI runs exactly one chosen stage for a chosen URL and shows success or failure, duration, and the error text. | must | Posting stage 2 for a URL with stage 1 artifacts present invokes only stage 2, as recorded by a fake runner. The response shows status and duration. |
| SRS-FR-034 | Running a stage whose prerequisite artifacts are missing fails without side effects, with a message naming the missing earlier stage output. | must | Running stage 3 with no audio file reports that stage 2's audio output is missing and creates no transcript. |
| SRS-FR-035 | The deployment UI shows whether `docker` and `ffmpeg` are available in the app container, whether Ollama answers its model-list endpoint, and the configured Whisper and formatter model names. It runs no pipeline stage and puts no secret values in the page. | must | With fake probes, the deployment home page shows each status and both model names. A configured cookie-file path and any token value do not appear in the HTML. |
| SRS-FR-036 | The production home page offers an import URL field, a video-processing toggle defaulting to the configured default, an optional user comment, an optional custom instruction, and a link to browse and search. | must | `GET /` contains all five controls, and the toggle state matches the configured default. |
| SRS-FR-037 | A failed import from the production UI shows a dismissible error message that includes the failing stage number. | must | A web import with a fake formatter failure returns a page whose error element contains "stage 7" and a dismiss control. |
| SRS-FR-038 | The CLI import command and the import mode run the same import as the production UI and exit non-zero on failure. | must | A CLI import with fakes produces the same package as FR-002. A failing import exits non-zero. |
| SRS-FR-039 | On start, the application checks that ffmpeg and yt-dlp are available. It creates any missing data folders (recipes, working, database folder, dataset raw, transcripts, metadata) and starts exactly the mode named by configuration. An unknown mode exits non-zero and lists the valid modes. | must | Starting against empty temp folders creates every folder. An unknown mode `foo` exits non-zero, and the message lists `web, testing-gui, deployment-gui, import, download, transcribe, test`. |
| SRS-FR-040 | Configuration comes from environment variables and an optional `.env` file, using the defaults in the External interfaces section. The download limit is capped at 50. | must | With no environment set, defaults match the table. Setting `DOWNLOAD_LIMIT=500` yields 50, and setting `FRAME_INTERVAL=1.5` yields 1.5. |
| SRS-FR-041 | Error messages name the failing stage, field, or file when one exists, and suggest a fix when one is known. Unreachable Ollama names the `OLLAMA_HOST` value. A GPU out-of-memory error suggests CPU or a smaller model. A download refusal suggests a cookie file. | must | Tests trigger each of the three conditions with fakes and assert the message contains the host value, "cpu", and "cookie" respectively. |
| SRS-FR-042 | Stage 2 extracts mono 16 kHz PCM WAV audio. Stage 4 extracts frames every configured interval (default 2.0 s). Stage 5 writes per-frame OCR text with each frame's timestamp. | must | Adapter tests on a short fixture video confirm the WAV header (1 channel, 16000 Hz, PCM). The frame count equals ⌈duration / interval⌉ ± 1, and the vision output has one entry per frame. |
| SRS-NFR-001 | Transcription and formatting need no cloud service. The Ollama API is reachable only on the private Compose network and is not published to the host. | must | The Compose file has no `ports:` entry for the Ollama service. A full fake-free import on a host with networking disabled after model download succeeds (manual check). |
| SRS-NFR-002 | Whisper and the formatter model are never resident on the GPU at the same time, and at most one GPU-using stage runs at once across all jobs in the process. | must | A concurrency test runs two imports at once with fakes that record enter/exit times. GPU stage intervals never overlap. Ollama is configured with at most one loaded model. |
| SRS-NFR-003 | A search query returns in under 200 ms with 5,000 indexed recipes. | must | A benchmark test indexes 5,000 synthetic recipes and times 20 queries. The 95th percentile is under 200 ms. |
| SRS-NFR-004 | The recipe page renders in under 2 seconds on the server, excluding video buffering. | should | A test-client timing of `GET /recipes/<slug>` over 20 requests averages under 2 s. |
| SRS-NFR-005 | The automated test suite passes with no network access, no GPU, no display, and no Whisper weights or Ollama server. | must | `pytest` exits 0 in the test container with networking disabled. |
| SRS-NFR-006 | Business rules and use cases import no framework, database driver, HTTP client, subprocess call, media tool, model library, or environment reader. | must | An automated architecture test scans the domain and application source and fails on any forbidden import. It passes. |
| SRS-NFR-007 | Every external dependency the use cases rely on can be replaced by an in-memory fake, so domain and use-case tests run with no adapter. | must | The domain and application test packages import no adapter module and complete in under 10 seconds. |
| SRS-NFR-008 | No secret or machine-specific path is committed. `.env` is git-ignored, and only `.env.example` with placeholders is versioned. | must | `git ls-files` shows no `.env`, and `.env.example` contains no real cookie path or token. |
| SRS-NFR-009 | Normalization, Markdown rendering, storage, and indexing (stages 8 and 9) make no language-model call. | must | During the acceptance import, the fake formatter's call count does not change across stages 8 and 9. |
| SRS-NFR-010 | Each module that validates input has at least one accepting test and one rejecting test. | must | A review of the test suite finds paired accept/reject tests for each validated input listed in FR-001, FR-009, FR-018, FR-019, FR-023, FR-025, and FR-040. |
| SRS-NFR-011 | Public use cases, pipeline stages, the stage runner, and the recipe repository have docstrings stating their purpose and failure behavior. | should | A docstring check over those modules reports none missing. |
| SRS-NFR-012 | A whole stack can be installed on a Windows host by the setup launcher, which asks for storage paths and GPU or CPU, writes `.env`, and starts Compose. | should | Running the setup launcher on a clean Windows host produces a `.env` and a running production UI on port 8080 (manual check). |

## Optional: External interfaces

**Web interfaces** (server-rendered HTML, one mode per process):

| Interface | Default port | Audience |
| --- | --- | --- |
| Production | 8080 | End user |
| Testing | 8081 | Tester |
| Deployment | 8082 | Deployer |

Production routes: `GET /` (import form), `POST /import`, `GET /recipes` (browse/search, `q` parameter), `GET /recipes/{slug}`, `GET /recipes/{slug}/video`, `GET|POST /recipes/{slug}/edit`, `POST /recipes/{slug}/rating`, `POST /recipes/{slug}/notes`, `GET /shopping` (selected slugs), `GET|POST /bugreport`.

**Modes** (selected by `MODE`):

| MODE | Behavior |
| --- | --- |
| `web` | Production UI |
| `testing-gui` | Testing UI |
| `deployment-gui` | Deployment UI |
| `import` | One full import from a URL argument, then exit |
| `download` | Phase 0 batch download, then exit |
| `transcribe` | Phase 0 batch transcription, then exit |
| `test` | Run the automated suite and exit |

**Configuration** (environment or `.env`):

| Name | Default | Purpose |
| --- | --- | --- |
| `MODE` | `web` in Compose, `test` when unset | Startup path |
| `REPOSITORY_PATH` | `/data/recipes` | Recipe packages |
| `WORKING_DIR` | `/data/working` | Job scratch and bug reports |
| `DATABASE_PATH` | `/data/db/recipes.db` | Search index |
| `DATASET_DIR` | `/data/dataset` | Phase 0 root (raw, transcripts, metadata, manifest, URL list) |
| `DOWNLOAD_LIMIT` | 50 (hard max 50) | Batch size |
| `DOWNLOAD_SOURCE_URL` | empty | Profile or collection page for batch download |
| `TRANSCRIBE_ONLY` | empty | Restrict batch transcribe to one reel id |
| `TRANSCRIBE_FORCE` | false | Re-transcribe existing transcripts |
| `WHISPER_MODEL` | `large-v3` | Transcription model |
| `WHISPER_DEVICE` | `cuda` | `cuda` or `cpu` |
| `FORMATTER_PROVIDER` | `ollama` | `ollama` or `mock` |
| `OLLAMA_HOST` | `http://ollama:11434` | Formatter API |
| `FORMATTER_MODEL` | `cookbook-formatter` | Ollama model name (fallback `qwen2.5:7b-instruct`) |
| `FRAME_INTERVAL` | 2.0 | Seconds between OCR frames |
| `VIDEO_PROCESSING_DEFAULT` | true | OCR on when the caller omits the flag |
| `WEB_PORT` / `TESTING_GUI_PORT` / `DEPLOYMENT_GUI_PORT` | 8080 / 8081 / 8082 | Ports |
| `YTDLP_COOKIES_FILE` | empty | Optional Instagram cookie file |
| `KEEP_WORKING` | false | Keep job scratch after success |

**External tools**: yt-dlp (video + metadata; failures are per URL), ffmpeg (WAV and frame extraction), faster-whisper (audio in, timestamped segments out), Tesseract (image in, text out), Ollama `POST /api/chat` with JSON output (prompt in, JSON text out) and `GET /api/tags` (health), a SQLite file (search index), Docker Compose (starts `cookbook` and `ollama`; a GPU override file enables NVIDIA devices).

**Formatter model contract**: temperature 0.1, and the system prompt requires JSON only and forbids invented quantities. When the GGUF file is mounted, the Ollama bootstrap registers `cookbook-formatter` from it.

## Optional: Logical data

- **Recipe**: title (required), description, servings, prep time, cook time, total time, ingredients (≥ 1), instructions (≥ 1), notes, tags, source URL (required), source creator.
  - **Ingredient**: item (required), quantity, preparation, notes (all optional), confidence (optional, 0.0–1.0).
  - **Instruction**: step number (required, sequential from 1), text (required), duration, temperature (optional).
- **Recipe package** (one folder per recipe, the source of truth): original video; plain-text transcript; timestamped transcript; OCR evidence when video processing ran; validated recipe JSON; deterministic Markdown; import metadata (source URL, creator, date added, pipeline version, slug); optional thumbnail, current rating, and notes.
- **Search index**: a derived, rebuildable copy of slug, title, source URL, creator, ingredient text, and instruction text.
- **Import job**: job id, source URL, status (`pending`, `running`, `completed`, `failed`), current stage (0–9), working folder, user comment, custom instruction, video-processing flag, error message, created and completed timestamps.
- **Evidence bundle**: transcript text and segments, OCR text per frame, caption, author, comments, user comment, custom instruction. Evidence is input, never the recipe.
- **Dataset video metadata**: reel id, source URL, title, author, author username, caption, comments (author, text, timestamp), comment count, like count, upload date, extracted-at timestamp.
- **Dataset manifest**: per URL, the URL, reel id, file name, download status, download time, and error. After transcription it also has transcript status, transcript file names, and transcribed-at time.
- **User note**: note id, recipe slug, text (non-empty), created and updated timestamps.
- **Rating**: recipe slug, score (1–5), created and updated timestamps. One current rating per recipe.
- **Shopping-list item**: item id, ingredient name, quantity (optional), aisle, source recipe slugs, checked (default false).
- **Bug report**: report id, description (required), debug-log path, related job id, related recipe slug, created timestamp, status (`open`, `reviewed`, `resolved`).
- **Debug log**: log id, job id, pipeline version, Whisper model, formatter model, created timestamp, entries (timestamp, stage number, level, message).

## Optional: Performance

- Search: under 200 ms at the 95th percentile with 5,000 indexed recipes (SRS-NFR-003).
- Recipe page: under 2 s on the server, excluding video buffering (SRS-NFR-004).
- Batch download: at most 50 URLs per run (SRS-FR-026).
- Domain and use-case tests: under 10 s total (SRS-NFR-007).

## Optional: Design constraints

- The target GPU has 8 GB of VRAM, so the GPU work must run one stage at a time (SRS-NFR-002).
- Formatting and transcription must work offline (SRS-NFR-001).
- The recipe package on disk is authoritative, and the index must be derivable from it (SRS-FR-012, SRS-FR-013).
- Raw evidence is immutable once written (SRS-FR-011).
- The system is Python only (no Java).

## Optional: Software attributes

- **Reliability**: an import failure never damages an existing package (SRS-FR-004), and a failed index write never leaves the package and the index disagreeing (SRS-FR-012).
- **Maintainability**: any model or tool provider (downloader, transcriber, OCR, formatter, index, storage) can be swapped by adding one adapter and changing composition, with no change to business rules or use cases (SRS-NFR-006, SRS-NFR-007).
- **Security**: the deployment and testing UIs are for the operator's LAN only, with no authentication, and no page renders a secret value (SRS-FR-035, SRS-NFR-008).
