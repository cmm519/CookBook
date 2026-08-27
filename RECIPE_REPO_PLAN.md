# Recipe Repository Agent — Cursor Implementation Plan

## Objective

Build a local-first agent that accepts an Instagram Reel share URL and produces a complete, searchable recipe repository entry containing:

- Original downloaded video
- Audio/transcript
- On-screen text/OCR data
- Structured recipe JSON
- Clean cookbook-formatted Markdown recipe
- Metadata
- Search index entry

The implementation should be modular so individual components can be replaced later.

---

## Target Pipeline

```text
Instagram Reel URL
      |
      v
[1] Download video + metadata
      |
      v
[2] Extract audio
      |
      v
[3] Transcribe audio
      |
      v
[4] Extract video frames
      |
      v
[5] OCR / vision analysis
      |
      v
[6] LLM recipe extraction -> validated JSON
      |
      v
[7] Recipe formatter -> Markdown
      |
      v
[8] Store complete recipe package
      |
      v
[9] Update searchable index
```

---

# Phase 0 — Repository Initialization

Create the project:

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
│   └── workflow/
├── recipes/
├── tests/
├── scripts/
├── working/
├── pyproject.toml
├── README.md
└── .gitignore
```

Use Python 3.12+.

Recommended dependencies:

- yt-dlp
- ffmpeg-python or subprocess-based ffmpeg integration
- faster-whisper
- pydantic
- pytest
- sqlite3 (stdlib)
- httpx/requests as needed

Keep model/provider-specific code behind interfaces.

---

# Phase 1 — Downloader

## Input

```json
{
  "url": "https://www.instagram.com/reel/..."
}
```

## Responsibilities

1. Validate that the URL is supported.
2. Download the highest practical quality available.
3. Save the original video unchanged.
4. Extract available metadata.
5. Preserve the original source URL.
6. Fail cleanly when authentication, rate limiting, private reels, or unavailable media prevents download.

Use `yt-dlp` first unless project constraints require another downloader.

## Output

```json
{
  "video_path": "...",
  "metadata": {
    "source_url": "...",
    "title": "...",
    "uploader": "...",
    "upload_date": "..."
  }
}
```

## Tests

- URL validation
- downloader command construction
- metadata parsing
- expected failure handling

Do not require live Instagram access for the unit test suite. Use fixtures/mocked downloader responses.

---

# Phase 2 — Media Processing

Extract audio with ffmpeg into a transcription-friendly WAV file:

- mono
- 16 kHz
- PCM WAV

Example output:

```text
working/<job_id>/audio.wav
```

Also determine video duration and basic media metadata.

Tests:

- audio extraction from fixture video
- invalid/corrupt input handling

---

# Phase 3 — Transcription

Implement a transcription interface so the model can be changed later.

Recommended initial backend:

- Faster-Whisper
- configurable model size, default `large-v3` where hardware permits

Output:

```json
{
  "language": "en",
  "text": "...",
  "segments": [
    {
      "start": 0.0,
      "end": 2.1,
      "text": "..."
    }
  ]
}
```

Persist:

```text
transcript.txt
transcript.json
```

Important:

- Keep timestamps.
- Keep raw transcription separate from cleaned recipe text.
- Do not let the LLM overwrite the raw transcript.

Tests:

- schema validation
- mock transcription provider
- fixture transcription parsing

---

# Phase 4 — Frame Extraction

Recipe reels often contain critical information that is never spoken aloud.

Extract frames at a configurable interval, initially:

```text
1 frame / second
```

Allow future adaptive extraction around detected text/cuts.

Store frames under:

```text
working/<job_id>/frames/
```

Generate a lightweight contact sheet for debugging when useful.

Tests:

- frame count approximately matches duration/interval
- output filenames deterministic

---

# Phase 5 — OCR / Vision Extraction

Analyze frames for:

- ingredient names
- quantities
- temperatures
- cooking times
- text overlays
- captions/instructions appearing on screen

Implement a provider interface rather than hard-coding one model.

Output:

```json
{
  "frames": [
    {
      "timestamp": 12.0,
      "text": "2 tbsp soy sauce"
    }
  ],
  "combined_text": "..."
}
```

Keep the raw frame-level evidence.

Important: OCR/vision output is evidence, not automatically authoritative. The recipe extraction stage must preserve uncertainty when sources disagree.

---

# Phase 6 — Source Consolidation

Build a normalized input object for the extraction LLM containing:

- raw transcript
- timestamped transcript segments
- OCR/vision findings
- Instagram metadata
- caption/description when available

Example:

```json
{
  "source": {
    "url": "...",
    "title": "...",
    "creator": "..."
  },
  "transcript": {...},
  "vision": {...},
  "caption": "..."
}
```

This stage should not invent recipe information.

---

# Phase 7 — Recipe Extraction LLM

Create strict Pydantic models.

Suggested schema:

```python
class Ingredient(BaseModel):
    item: str
    quantity: str | None = None
    preparation: str | None = None
    notes: str | None = None
    confidence: float | None = None

class Instruction(BaseModel):
    step: int
    text: str
    duration: str | None = None
    temperature: str | None = None

class Recipe(BaseModel):
    title: str
    description: str | None = None
    servings: str | None = None
    prep_time: str | None = None
    cook_time: str | None = None
    total_time: str | None = None
    ingredients: list[Ingredient]
    instructions: list[Instruction]
    notes: list[str] = []
    tags: list[str] = []
    source_url: str
    source_creator: str | None = None
```

LLM requirements:

1. Return structured JSON only.
2. Validate against the Pydantic schema.
3. Never silently invent missing quantities.
4. Mark uncertain/inferred values.
5. Reconcile transcript and visual evidence.
6. Preserve source wording where it matters.
7. Normalize obvious speech-to-text errors.
8. Keep instructions in chronological cooking order.

Use structured-output/API schema support when the selected LLM supports it.

Add retry/repair logic for invalid JSON.

Tests:

- fixture transcript + OCR -> expected schema
- malformed model response -> repair/failure path
- missing quantities remain missing/uncertain

---

# Phase 8 — Recipe Quality / Normalization

Implement deterministic cleanup after extraction:

- normalize units
- normalize whitespace
- normalize ingredient naming where safe
- ensure instruction numbering is sequential
- remove duplicated ingredients caused by repeated frames
- deduplicate repeated OCR text

Do not make aggressive culinary assumptions.

Keep `recipe.json` as the canonical structured representation.

---

# Phase 9 — Cookbook Markdown Formatter

Render the validated recipe JSON into a consistent Markdown template.

Template:

```markdown
# <Title>

<Description>

## Yield
<Servings>

## Time
- Prep: <...>
- Cook: <...>
- Total: <...>

## Ingredients
- <quantity> <ingredient>

## Instructions
1. <instruction>
2. <instruction>

## Notes
- <note>

## Source
[Original Reel](<source_url>)
```

The formatter should be deterministic. Do not use an LLM for the final Markdown unless there is a demonstrated need.

Tests:

- snapshot/golden-file output
- escaping/special characters
- missing optional fields

---

# Phase 10 — Recipe Package Storage

Generate a stable slug from the canonical recipe title.

Store one recipe per directory:

```text
recipes/
└── chicken-teriyaki/
    ├── video.mp4
    ├── transcript.txt
    ├── transcript.json
    ├── vision.json
    ├── recipe.json
    ├── recipe.md
    ├── metadata.json
    └── thumbnail.jpg
```

`metadata.json` should include at least:

```json
{
  "source_url": "...",
  "creator": "...",
  "title_original": "...",
  "date_added": "...",
  "pipeline_version": "..."
}
```

Do not overwrite an existing recipe blindly.

Implement duplicate detection using source URL first, then reasonable content/title matching.

---

# Phase 11 — SQLite Search Index

Create a SQLite database, e.g.:

```text
recipes.db
```

Tables should cover at least:

- recipes
- ingredients
- tags

Index fields:

- title
- ingredient names
- tags
- source URL
- filesystem path

Support queries such as:

```text
find recipes containing miso
find chicken recipes
find recipes tagged asian
```

Keep the filesystem package as the source of truth. SQLite is the index.

---

# Phase 12 — CLI

Implement:

```bash
recipe-import "https://www.instagram.com/reel/..."
```

Suggested commands:

```bash
recipe-import <url>
recipe-search <query>
recipe-show <slug>
```

Import should execute:

```text
validate URL
 -> download
 -> media extraction
 -> transcription
 -> frame extraction
 -> vision/OCR
 -> recipe extraction
 -> schema validation
 -> normalization
 -> markdown rendering
 -> repository storage
 -> search indexing
```

Provide clear progress/status messages and actionable errors.

Support a `--keep-working` or equivalent debug option so intermediate artifacts can be retained.

---

# Phase 13 — Configuration

Use environment variables/configuration for:

- downloader settings
- transcription model
- transcription device
- vision provider
- LLM provider/model
- repository path
- working directory
- frame interval

Never hard-code API keys.

Provide `.env.example` if external providers are used.

---

# Phase 14 — Testing Strategy

Create three levels of tests.

## Unit tests

Mock external services.

Cover:

- URL validation
- downloader parsing
- media processing
- transcript parsing
- schema validation
- deduplication
- slug generation
- Markdown formatting
- SQLite indexing

## Integration tests

Use local fixtures to run:

```text
fixture video
 -> audio extraction
 -> mocked transcription
 -> mocked vision
 -> mocked extraction response
 -> recipe package
```

## End-to-end test

Provide a clearly documented optional live test requiring a valid accessible Reel URL and configured models.

Do not make live-network/model access mandatory for normal CI.

---

# Phase 15 — Observability / Debugging

Every import should have a job ID.

Log major stages:

```text
JOB abc123
[1/9] Download
[2/9] Audio extraction
[3/9] Transcription
...
[9/9] Indexing
```

On failure, retain the working directory when debugging is enabled.

Record pipeline/model versions in metadata.

---

# Definition of Done

The MVP is complete when this works:

```bash
recipe-import "<instagram-reel-url>"
```

and creates:

```text
recipes/<recipe-slug>/
├── video.mp4
├── transcript.txt
├── transcript.json
├── vision.json
├── recipe.json
├── recipe.md
├── metadata.json
└── thumbnail.jpg
```

The recipe must:

- pass schema validation
- have ingredients and ordered instructions
- preserve source URL
- distinguish extracted facts from uncertain/inferred values
- be searchable via SQLite

---

# Implementation Order

Codex should implement in this exact order and keep the project runnable after each phase:

1. Repository/project skeleton
2. Pydantic data models
3. Storage layer
4. Downloader interface + implementation
5. Media processing
6. Transcription interface + implementation
7. Frame extraction
8. Vision/OCR interface
9. Source consolidation
10. LLM extraction + validation
11. Normalization
12. Markdown formatter
13. SQLite index/search
14. CLI workflow
15. Tests/integration fixtures
16. Documentation

At each phase:

- run the relevant tests
- fix failures before proceeding
- update README when user-facing behavior changes
- avoid unnecessary architecture changes

---

# Engineering Constraints

- Prefer small modules with explicit interfaces.
- Keep raw evidence separate from generated recipe data.
- Make imports idempotent where practical.
- Do not silently discard failed intermediate outputs.
- Avoid hard dependencies on a single cloud LLM provider.
- Keep the canonical recipe format stable and versioned.
- Do not store secrets in the repository.
- Do not make the formatter dependent on a generative model.

---

# Initial Cursor Task

Start by implementing Phase 0 through Phase 3 only.

Before moving past Phase 3:

1. Run the full test suite.
2. Demonstrate a local fixture video can be downloaded/copied into the workflow, converted to audio, and passed through the transcription interface.
3. Confirm all generated data models validate.
4. Update README with exact setup and execution commands.

Do not implement later phases until the Phase 0–3 tests pass.
