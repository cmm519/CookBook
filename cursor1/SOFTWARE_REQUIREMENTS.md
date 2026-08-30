# Software Requirements Specification

## Requirements

### 1. Project Overview

Develop a software system for **building and maintaining a local-first recipe repository from Instagram Reel URLs** using:

- Language: **Python** (import pipeline, CLI, web backend, data models); **Java** (TBD — likely web/API layer or separate service; boundary to be decided in Section 21)
- Architecture: **Modular pipeline + MVC web layer** with provider interfaces for transcription (Whisper), vision/OCR, and recipe formatting (teacher model → distilled local model); **Docker Compose** for deployment on personal server
- UI framework: **Web UI** (homescreen, recipe viewer/editor, shopping list, bug reporting); **CLI** for import and search (invoked via `docker compose run`)
- Testing framework: **pytest** (Python, run inside `docker-compose.test.yml` container); **JUnit** (Java, when introduced)
- Exception/error-handling mechanism: **Structured exceptions per pipeline stage**; user-dismissible errors in web UI; debug log capture for maintenance agent review
- Deployment: **Docker** — all runtime dependencies (Python, ffmpeg, yt-dlp, faster-whisper, CUDA libs) containerized; host requires only Docker Engine + NVIDIA Container Toolkit (GPU hosts)

### 2. Startup / Initialization

On startup, the system should:

1. **Container startup:** Docker entrypoint validates bundled tools (ffmpeg, yt-dlp, faster-whisper) are available inside the container; creates volume mount directories if missing (`/data/recipes`, `/data/working`, `/data/db`).
2. **CLI mode:** Parse command-line arguments; load configuration from environment variables and `.env` file (injected by Docker Compose).
3. Load **configuration and repository state** from **environment variables, `.env`, and mounted volumes** (`recipes/`, `recipes.db`, `working/` — bind-mounted or named Docker volumes).
4. **Web mode:** Present **homescreen** containing:
   - **Import URL field** — accept Instagram Reel share URL and trigger import pipeline
   - **Video processing toggle** — enable/disable OCR/vision frame analysis (on-screen text extraction)
   - **User comment field** — optional notes from user to attach to the import job
   - **Custom instruction field** — optional text passed to the recipe formatter model alongside transcript/OCR evidence
   - **Recipe search/browse** — navigate to existing recipes in the repository

Additional startup behavior:

- Deploy on a **personal server** via `docker compose up` (not cloud SaaS).
- GPU workloads use `docker-compose.gpu.yml` override with NVIDIA Container Toolkit; CI/tests use `docker-compose.test.yml` (CPU only, mocked providers).
- See [`DOCKER.md`](DOCKER.md) for full container layout, volume mounts, and commands.
- Load the **recipe formatter** from the **Ollama sidecar** (`http://ollama:11434`); model name configured via `FORMATTER_MODEL` (bootstrap: `qwen2.5:3b-instruct`, production: `cookbook-formatter` after distillation).
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

- Save data when **[SAVE CONDITION]**.
- Save data when **[EXIT / CLOSE CONDITION]**.
- Use **[FILE / DATABASE / API]** as the persistence mechanism.
- Use **[FORMAT]** for stored data.

### 5. Primary Operations

The system should provide:

#### Operation: [OPERATION NAME]

**Trigger:** [USER ACTION / SYSTEM EVENT]

**Input:** [INPUT]

**Validation:** [VALIDATION RULES]

**Behavior:**  
[DESCRIBE WHAT HAPPENS]

**Success result:**  
[EXPECTED RESULT]

**Failure behavior:**  
[EXPECTED ERROR / EXCEPTION]

#### Operation: [OPERATION NAME]

**Trigger:** [USER ACTION / SYSTEM EVENT]

**Input:** [INPUT]

**Validation:** [VALIDATION RULES]

**Behavior:**  
[DESCRIBE WHAT HAPPENS]

**Success result:**  
[EXPECTED RESULT]

**Failure behavior:**  
[EXPECTED ERROR / EXCEPTION]

### 6. Multiple Views / Windows

The application should support:

- **[VIEW / WINDOW 1]**
- **[VIEW / WINDOW 2]**
- **[VIEW / WINDOW 3]**

When multiple views display the same underlying data:

- All views must remain synchronized.
- Changes made through one view must be reflected in all relevant views.
- **[OTHER SYNCHRONIZATION REQUIREMENTS]**

### 7. Agents / Background Processes

If applicable, the system should support **[AGENT / WORKER / BACKGROUND PROCESS]**.

Each agent should have:

- **[IDENTIFIER]**
- **[INPUT / CONFIGURATION]**
- **[RATE / INTERVAL]**
- **[STATE]**
- **[METRICS / COUNTERS]**
- **[CONTROL ACTIONS]**

Valid states:

- **[STATE 1]**
- **[STATE 2]**
- **[STATE 3]**

Agent behavior:

- **[START CONDITION]**
- **[RUNNING BEHAVIOR]**
- **[BLOCKING CONDITION]**
- **[STOP CONDITION]**
- **[DISMISS / CLEANUP BEHAVIOR]**

Concurrency requirements:

- **[THREADING MODEL]**
- **[SYNCHRONIZATION REQUIREMENTS]**
- **[RACE-CONDITION REQUIREMENTS]**

### 8. Constants / Configuration

The following values should be defined as constants or configuration:

| Name | Value | Purpose |
|---|---|---|
| [CONSTANT] | [VALUE] | [PURPOSE] |
| [CONSTANT] | [VALUE] | [PURPOSE] |
| [CONSTANT] | [VALUE] | [PURPOSE] |

### 9. Error Handling

The system should provide appropriate errors for:

- Invalid input
- Missing input
- Invalid data format
- Corrupted data
- Inconsistent data
- Insufficient resources
- **[OTHER ERROR CONDITIONS]**

Error messages should:

- Clearly identify the problem.
- Identify the affected data where applicable.
- Identify the location of the problem where applicable.
- Provide a suggested correction where appropriate.
- Be dismissible by the user.

For unrecoverable errors:

**[DESCRIBE REQUIRED APPLICATION BEHAVIOR]**

### 10. Architecture

Organize the implementation into:

- **[PACKAGE / MODULE 1]** — [RESPONSIBILITY]
- **[PACKAGE / MODULE 2]** — [RESPONSIBILITY]
- **[PACKAGE / MODULE 3]** — [RESPONSIBILITY]
- **[OPTIONAL PACKAGE / MODULE]** — [RESPONSIBILITY]

Required architectural constraints:

- **[ARCHITECTURAL REQUIREMENT]**
- **[INHERITANCE REQUIREMENT]**
- **[INTERFACE REQUIREMENT]**
- **[DEPENDENCY REQUIREMENT]**

### 11. Model / Core Logic

Implement:

1. **[CLASS / COMPONENT]**
   - Attributes: **[ATTRIBUTES]**
   - Operations: **[OPERATIONS]**
   - Exceptions: **[EXCEPTIONS]**

2. **[CLASS / COMPONENT]**
   - Attributes: **[ATTRIBUTES]**
   - Operations: **[OPERATIONS]**
   - Exceptions: **[EXCEPTIONS]**

3. **[ADDITIONAL COMPONENTS]**

### 12. Controller / Application Logic

Controllers should:

- **[RESPONSIBILITY]**
- **[INPUT HANDLING]**
- **[MODEL INTERACTION]**
- **[VIEW UPDATES]**
- **[EXCEPTION HANDLING]**

Controller requirements:

- **[ONE CONTROLLER PER VIEW / OTHER RULE]**
- **[EVENT DISPATCHING RULE]**
- **[LIFECYCLE RULE]**

### 13. View / UI

Views should:

- **[VIEW ARCHITECTURE REQUIREMENT]**
- **[LIST REQUIRED WINDOWS]**
- **[LIST REQUIRED COMPONENTS]**
- **[LIST USER INTERACTIONS]**

For each window, specify:

**Window:** [WINDOW NAME]

**Purpose:** [PURPOSE]

**Components:**

- [COMPONENT] — [BEHAVIOR]
- [COMPONENT] — [BEHAVIOR]
- [COMPONENT] — [BEHAVIOR]

**Actions:**

- [ACTION] → [RESULT]
- [ACTION] → [RESULT]

### 14. Documentation

Provide documentation for:

- Every class
- Important methods
- Important implementation sections
- Public APIs
- **[OTHER DOCUMENTATION REQUIREMENTS]**

Documentation format:

**[JAVADOC / MARKDOWN / OTHER]**

Generated documentation:

**[REQUIRED OUTPUT]**

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

- **[LANGUAGE VERSION]**
- **[FRAMEWORK VERSION]**
- **[LIBRARY REQUIREMENTS]**
- **[BUILD SYSTEM]**
- **[OPERATING SYSTEM / PLATFORM]**
- **[PERFORMANCE REQUIREMENTS]**
- **[RESOURCE LIMITATIONS]**
- **[OTHER CONSTRAINTS]**

### 19. Deliverables

The final submission must contain:

- [ ] Source code
- [ ] Unit tests
- [ ] Integration/acceptance tests
- [ ] Generated documentation
- [ ] UML/class diagram
- [ ] Configuration files
- [ ] Build/run instructions
- [ ] **[OTHER DELIVERABLE]**

### 20. Explicit Requirements / Grading Criteria

The implementation will be evaluated against the following:

| ID | Requirement | Priority | Verification |
|---|---|---|---|
| REQ-[001] | [REQUIREMENT] | [HIGH/MEDIUM/LOW] | [TEST/INSPECTION] |
| REQ-[002] | [REQUIREMENT] | [HIGH/MEDIUM/LOW] | [TEST/INSPECTION] |
| REQ-[003] | [REQUIREMENT] | [HIGH/MEDIUM/LOW] | [TEST/INSPECTION] |

### 21. Open Questions / Decisions

- [ ] **[QUESTION / UNKNOWN]**
- [ ] **[QUESTION / UNKNOWN]**
- [ ] **[QUESTION / UNKNOWN]**

Decisions:

- **[DECISION]** — [RATIONALE]
- **[DECISION]** — [RATIONALE]
