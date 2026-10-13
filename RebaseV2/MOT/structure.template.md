# Structure

You fill this file. It is stage 3 of the workflow in `README.md`.

This file gives the directory tree, which architecture part owns each folder, and the commands that build and run that tree. Every part name below appears in `architecture.template.md`.

The project root is `RebaseV2/`. All paths below are relative to it. `MOT/` (these templates) and `prompts/` (generated increments) already exist and are not application code.

## Required: Directory tree

```text
RebaseV2/
├── MOT/                                   # workflow templates (not application code)
├── prompts/                               # generated MoT increments + tracking.md
├── pyproject.toml
├── README.md
├── USER_GUIDE.md
├── .gitignore
├── .env.example
├── docker/
│   ├── Dockerfile
│   └── ollama/
│       └── Modelfile
├── docker-compose.yml
├── docker-compose.gpu.yml
├── docker-compose.test.yml
├── scripts/
│   ├── docker-entrypoint.sh
│   └── ollama-bootstrap.sh
├── CookBook-Setup.bat
├── CookBook-CLI.bat
├── src/
│   └── cookbook/
│       ├── __init__.py                    # PIPELINE_VERSION
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── errors.py                  # DomainError, ValidationError(field), NotFound
│       │   ├── recipe.py                  # Recipe, Ingredient, Instruction
│       │   ├── slug.py                    # Slug derivation + suffixing
│       │   ├── evidence.py                # Transcript, TranscriptSegment, VisionEvidence, VideoMetadata, Comment, EvidenceBundle
│       │   ├── import_job.py              # ImportJob, JobStatus, ImportOptions, StageOutcome
│       │   ├── feedback.py                # Rating, UserNote
│       │   ├── shopping.py                # ShoppingList, ShoppingListItem, Aisle, AisleClassifier
│       │   ├── bug_report.py              # BugReport, BugReportStatus
│       │   ├── debug_log.py               # DebugLog, LogEntry, LogLevel
│       │   └── dataset.py                 # ManifestEntry, DownloadStatus, TranscriptStatus, SourceUrl rules
│       ├── application/
│       │   ├── __init__.py
│       │   ├── errors.py                  # StageFailed, PrerequisiteMissing, ProviderUnavailable, ConfigurationError
│       │   ├── ports/
│       │   │   ├── __init__.py
│       │   │   ├── media.py               # VideoDownloader, AudioExtractor, FrameExtractor
│       │   │   ├── recognition.py         # Transcriber, TextRecognizer
│       │   │   ├── formatting.py          # RecipeFormatter, RecipeRenderer
│       │   │   ├── persistence.py         # RecipeRepository, SearchIndex, DatasetStore, JobWorkspace, BugReportStore, DebugLogSink
│       │   │   ├── runtime.py             # GpuGate, Clock, IdGenerator
│       │   │   └── health.py              # HealthProbe
│       │   ├── import_recipe/
│       │   │   ├── __init__.py
│       │   │   ├── stage.py               # PipelineStage protocol, StageContext, StageResult, artifact keys
│       │   │   ├── stages/
│       │   │   │   ├── __init__.py        # ordered stage registry (1–9)
│       │   │   │   ├── s1_download.py
│       │   │   │   ├── s2_extract_audio.py
│       │   │   │   ├── s3_transcribe.py
│       │   │   │   ├── s4_extract_frames.py
│       │   │   │   ├── s5_recognize_text.py
│       │   │   │   ├── s6_consolidate.py
│       │   │   │   ├── s7_format.py
│       │   │   │   ├── s8_normalize_render.py
│       │   │   │   └── s9_store_index.py
│       │   │   ├── runner.py              # StageRunner: run_all, run_step, run_from
│       │   │   ├── publish.py             # write package → upsert index → restore on failure
│       │   │   └── import_recipe.py       # ImportRecipe use case + request/response
│       │   ├── library/
│       │   │   ├── __init__.py
│       │   │   ├── search_recipes.py
│       │   │   ├── view_recipe.py
│       │   │   ├── edit_recipe.py
│       │   │   ├── rate_recipe.py
│       │   │   ├── add_note.py
│       │   │   └── rebuild_index.py
│       │   ├── shopping/
│       │   │   ├── __init__.py
│       │   │   └── build_shopping_list.py
│       │   ├── dataset/
│       │   │   ├── __init__.py
│       │   │   ├── queue_urls.py
│       │   │   ├── batch_download.py
│       │   │   └── batch_transcribe.py
│       │   ├── bug_report/
│       │   │   ├── __init__.py
│       │   │   └── submit_bug_report.py
│       │   └── operations/
│       │       ├── __init__.py
│       │       └── check_health.py
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── media/
│       │   │   ├── __init__.py
│       │   │   ├── ytdlp_downloader.py
│       │   │   ├── ffmpeg_audio.py
│       │   │   └── ffmpeg_frames.py
│       │   ├── recognition/
│       │   │   ├── __init__.py
│       │   │   ├── whisper_transcriber.py
│       │   │   └── tesseract_recognizer.py
│       │   ├── formatting/
│       │   │   ├── __init__.py
│       │   │   ├── ollama_formatter.py
│       │   │   ├── mock_formatter.py
│       │   │   ├── formatter_prompt.py    # system prompt: JSON only, no invented quantities
│       │   │   ├── recipe_dto.py          # Pydantic DTO ↔ domain Recipe mapper
│       │   │   └── markdown_renderer.py
│       │   ├── persistence/
│       │   │   ├── __init__.py
│       │   │   ├── fs_recipe_repository.py
│       │   │   ├── package_mappers.py     # metadata/rating/notes JSON ↔ domain
│       │   │   ├── sqlite_search_index.py
│       │   │   ├── json_dataset_store.py
│       │   │   ├── fs_job_workspace.py
│       │   │   ├── file_debug_log.py
│       │   │   └── json_bug_report_store.py
│       │   ├── runtime/
│       │   │   ├── __init__.py
│       │   │   ├── lock_gpu_gate.py
│       │   │   ├── system_clock.py
│       │   │   └── uuid_ids.py
│       │   └── health/
│       │       ├── __init__.py
│       │       └── system_health_probe.py
│       ├── delivery/
│       │   ├── __init__.py
│       │   ├── web/
│       │   │   ├── __init__.py
│       │   │   ├── errors.py              # domain/application error → HTTP status + dismissible message
│       │   │   ├── production/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── app.py             # create_production_app(use_cases)
│       │   │   │   ├── routes.py
│       │   │   │   └── presenters.py
│       │   │   ├── testing/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── app.py
│       │   │   │   ├── routes.py
│       │   │   │   └── presenters.py
│       │   │   ├── deployment/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── app.py
│       │   │   │   ├── routes.py
│       │   │   │   └── presenters.py
│       │   │   ├── templates/
│       │   │   │   ├── base.html
│       │   │   │   ├── production/        # home, browse, recipe, edit, shopping, bugreport
│       │   │   │   ├── testing/           # queue, step runner
│       │   │   │   └── deployment/        # health
│       │   │   └── static/
│       │   │       └── style.css
│       │   └── cli/
│       │       ├── __init__.py
│       │       └── commands.py            # import, download, transcribe, run-step
│       └── main/
│           ├── __init__.py
│           ├── __main__.py                # `python -m cookbook.main` / `cookbook` → MODE dispatch
│           ├── settings.py                # pydantic-settings, DOWNLOAD_LIMIT cap
│           ├── bootstrap.py               # startup tool checks + folder creation
│           └── container.py               # builds adapters, injects into use cases
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── fakes/
    │   ├── __init__.py
    │   ├── media.py
    │   ├── recognition.py
    │   ├── formatting.py
    │   ├── persistence.py                 # in-memory repository, index, dataset, workspace, bug store, log sink
    │   ├── runtime.py                     # fixed clock, sequential ids, recording GPU gate
    │   └── health.py
    ├── fixtures/
    │   ├── recipe_valid.json
    │   ├── recipe_golden.md
    │   ├── formatter_outputs/
    │   └── media/                         # tiny sample.mp4 for adapter tests
    ├── test_architecture.py               # dependency rule (SRS-NFR-006/007)
    ├── domain/
    ├── application/
    ├── adapters/
    ├── delivery/
    ├── main/
    └── acceptance/                        # SRS end-to-end scenarios with fakes
```

## Required: Ownership

| Path | Architecture part | What it holds |
| --- | --- | --- |
| `src/cookbook/__init__.py` | Domain | Package marker and `PIPELINE_VERSION` constant |
| `src/cookbook/domain/` | Domain | Entities, value objects, invariants, slug rules, shopping merge and aisle rules, domain errors. Standard library only |
| `src/cookbook/application/ports/` | Application | Abstract port protocols that use cases depend on |
| `src/cookbook/application/errors.py` | Application | Application-level errors (stage failure, missing prerequisite, provider unavailable, configuration) |
| `src/cookbook/application/import_recipe/` | Application | Pipeline stage protocol, the nine stages, `StageRunner`, publish policy, `ImportRecipe` use case |
| `src/cookbook/application/library/` | Application | Search, view, edit, rate, note, and rebuild-index use cases |
| `src/cookbook/application/shopping/` | Application | Build-shopping-list use case |
| `src/cookbook/application/dataset/` | Application | Queue URLs, batch download, batch transcribe use cases (Phase 0) |
| `src/cookbook/application/bug_report/` | Application | Submit-bug-report use case |
| `src/cookbook/application/operations/` | Application | Check-health use case for the deployment UI |
| `src/cookbook/adapters/media/` | Gateway Adapters | yt-dlp downloader, ffmpeg audio and frame extractors |
| `src/cookbook/adapters/recognition/` | Gateway Adapters | faster-whisper transcriber, Tesseract recognizer |
| `src/cookbook/adapters/formatting/` | Gateway Adapters | Ollama formatter, mock formatter, prompt text, Pydantic recipe DTO and mapper, Markdown renderer |
| `src/cookbook/adapters/persistence/` | Gateway Adapters | Filesystem recipe repository, SQLite index, dataset and manifest store, job workspace, debug log, bug-report store |
| `src/cookbook/adapters/runtime/` | Gateway Adapters | Process-wide GPU lock, system clock, UUID generator |
| `src/cookbook/adapters/health/` | Gateway Adapters | PATH, Ollama `/api/tags`, and CUDA probes |
| `src/cookbook/delivery/web/production/` | Web Delivery | Production FastAPI app (:8080): routes, presenters |
| `src/cookbook/delivery/web/testing/` | Web Delivery | Testing FastAPI app (:8081): URL queue, single-stage runner |
| `src/cookbook/delivery/web/deployment/` | Web Delivery | Deployment FastAPI app (:8082): health page |
| `src/cookbook/delivery/web/errors.py` | Web Delivery | Mapping of errors to HTTP status and dismissible messages |
| `src/cookbook/delivery/web/templates/`, `static/` | Web Delivery | Jinja2 templates and shared CSS |
| `src/cookbook/delivery/cli/` | CLI Delivery | `import`, `download`, `transcribe`, `run-step` command handlers |
| `src/cookbook/main/` | Composition Root | Settings, startup checks, folder creation, dependency wiring, MODE dispatch, console-script entry |
| `tests/fakes/` | Test Suite | In-memory implementations of every port |
| `tests/fixtures/` | Test Suite | Recipe JSON, golden Markdown, formatter outputs, tiny media sample |
| `tests/test_architecture.py` | Test Suite | Automated dependency-rule check |
| `tests/domain/`, `tests/application/` | Test Suite | Fast policy tests using fakes only |
| `tests/adapters/`, `tests/delivery/`, `tests/main/` | Test Suite | Seam tests for adapters, web/CLI controllers, settings and wiring |
| `tests/acceptance/` | Test Suite | SRS acceptance scenarios end-to-end with fakes |
| `pyproject.toml` | Deployment Packaging | Dependencies, `src/` package discovery, `cookbook` console script, pytest config |
| `docker/` | Deployment Packaging | App image Dockerfile, formatter Modelfile |
| `docker-compose.yml`, `docker-compose.gpu.yml`, `docker-compose.test.yml` | Deployment Packaging | Base stack (`cookbook` + unpublished `ollama`), GPU override, offline test run |
| `scripts/` | Deployment Packaging | Container entrypoint (calls Composition Root), Ollama model bootstrap |
| `CookBook-Setup.bat`, `CookBook-CLI.bat` | Deployment Packaging | Windows deployer launchers (writes `.env`, starts Compose, batch modes) |
| `.env.example`, `.gitignore` | Deployment Packaging | Placeholder configuration; ignores `.env`, data folders, caches |
| `README.md`, `USER_GUIDE.md` | Deployment Packaging | Setup commands, and the deployer/tester/end-user guide including debug logs |
| `ollama` service in `docker-compose.yml` | Ollama Sidecar | Unmodified `ollama/ollama` image, `OLLAMA_MAX_LOADED_MODELS=1`, no host port |

## Required: Build and run

Run from `RebaseV2/`.

1. `python -m pip install -e ".[dev]" && python -m pytest -q`. This must succeed: every test passes, including `tests/test_architecture.py`, with no network and no GPU.
2. `docker compose up -d --build`, then open `http://localhost:8080`. Use `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build` on a GPU host.
3. Extra checks:
   - `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm cookbook` (MODE=test in the container) exits 0.
   - `MODE=deployment-gui python -m cookbook.main` serves `:8082` and shows both model names.
   - `MODE=foo python -m cookbook.main` exits non-zero and lists the valid modes.
   - `docker compose config` shows no `ports:` on the `ollama` service.

## Required: If the build fails

1. **Import errors / `ModuleNotFoundError: cookbook`**: confirm Python is 3.12 (`python --version`) and the editable install ran from `RebaseV2/`. Also check that `pyproject.toml` uses `[tool.setuptools.packages.find] where = ["src"]` and pytest `pythonpath = ["src"]`.
2. **`tests/test_architecture.py` fails**: read the reported module and the forbidden import. Move the translation or I/O outward into an adapter, or into the Composition Root, behind a port owned by Application. Do not add the module to an allow-list.
3. **Tests that touch Whisper, Tesseract, ffmpeg, yt-dlp, or Ollama fail on a dev machine**: those tests must use fakes or subprocess mocks. Mark true tool-dependent adapter tests to skip when the binary is absent (`shutil.which`). The policy tests must never need them.
4. **faster-whisper raises `TypeError` about `metadata_errors`**: PyAV ≥ 19 was installed. Keep the `av>=12,<19` pin.
5. **Docker GPU run fails** (`could not select device driver`, CUDA libs missing): verify the NVIDIA Container Toolkit (`docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi`). Check that the GPU override file is included and `nvidia-cublas-cu12` / `nvidia-cudnn-cu12` are installed in the image. Otherwise set `WHISPER_DEVICE=cpu`.
6. **Formatter stage fails with Ollama unreachable or the model not found**: check `docker compose logs ollama`, confirm `OLLAMA_HOST=http://ollama:11434`, and check that `cookbook-formatter.gguf` is mounted for the bootstrap. Otherwise set `FORMATTER_MODEL=qwen2.5:7b-instruct` and run `docker compose exec ollama ollama pull qwen2.5:7b-instruct`.
7. **Ollama sidecar crash-loops on start**: check that the bootstrap script waits for `ollama serve` to answer `/api/tags` before `ollama create`, and that the entrypoint does not exit after registration.
