# CookBook

A local-first recipe repository. CookBook turns shared cooking videos into a
searchable, cookbook-formatted recipe library. The long-term pipeline
(described in [`RECIPE_REPO_PLAN.md`](RECIPE_REPO_PLAN.md)) downloads a video,
transcribes it, reads on-screen text, extracts a structured recipe, and stores
a complete package on disk plus a search index.

This repository currently implements the deterministic, dependency-light core
of that pipeline:

- **Validated data models** (`app/models.py`) — Pydantic `Recipe`, `Ingredient`,
  `Instruction`, and metadata.
- **Deterministic Markdown formatter** (`app/formatting/`) — renders a recipe to
  a consistent cookbook layout (no LLM).
- **Filesystem storage** (`app/storage/`) — one directory per recipe with
  `recipe.json`, `recipe.md`, and `metadata.json`, plus slug generation and
  duplicate-by-source-URL detection.
- **SQLite search index** (`app/search/`) — search by title, ingredient, or tag.
- **CLI** (`app/cli.py`) — `import-json`, `search`, `show`, `demo`, `version`.

Networked / model-heavy stages (video download, transcription, vision/OCR, LLM
extraction) are kept behind interfaces (`app/downloader/`,
`app/transcription/`) so they can be implemented or mocked without touching the
core.

## Requirements

- Python 3.12+
- `ffmpeg` (for future media-processing stages)

## Setup

The one-step setup installs system prerequisites, creates a virtual
environment in `.venv`, and installs the project (editable) with dev
dependencies. It is idempotent:

```bash
bash scripts/setup.sh
source .venv/bin/activate
```

To install manually instead:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Optional pipeline extras (not required for the core or tests):

```bash
pip install -e ".[media,transcription]"
```

## Usage

Run an offline, end-to-end demo (builds a recipe, stores the package, indexes
it, searches, and prints the rendered Markdown):

```bash
cookbook demo
```

Import a validated recipe JSON file, then search and view it:

```bash
cookbook import-json path/to/recipe.json
cookbook search chicken
cookbook show chicken-teriyaki
```

Stored recipes live under `recipes/<slug>/` and the search index is
`recipes.db` (both are git-ignored).

## Testing

```bash
source .venv/bin/activate
pytest        # run the unit test suite
ruff check .  # lint
```

## Project layout

```text
app/
├── models.py          # Pydantic recipe models (canonical schema)
├── downloader/        # video download interface + URL validation
├── transcription/     # transcription interface + mock backend
├── formatting/        # deterministic recipe -> Markdown
├── storage/           # slug generation + filesystem recipe packages
├── search/            # SQLite search index
├── workflow/          # store-and-index orchestration
└── cli.py             # command-line interface
tests/                 # pytest suite
scripts/setup.sh       # idempotent dev environment setup
recipes/               # generated recipe packages (git-ignored)
```

## Cloud Agent environment

The Cursor Cloud Agent environment is configured in
[`.cursor/environment.json`](.cursor/environment.json); it runs
`scripts/setup.sh` on install so a fresh agent has the toolchain and
dependencies ready.
