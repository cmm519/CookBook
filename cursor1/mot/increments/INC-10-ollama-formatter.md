# INCREMENT 10: Recipe Formatter via Ollama API + Validation

**Status:** CRITICAL  
**Dependencies:** INC-09 (Source consolidation)

> **Interim model:** `qwen2.5:7b-instruct` via Ollama sidecar (`FORMATTER_MODEL` default).  
> **INC-10b (distilled `cookbook-formatter`) is ON HOLD** — do not implement LoRA training or `ollama create` in this increment. See [`DISTALATION.MD`](../../DISTALATION.MD).

## Capability Specification

Implement `FormatterProvider` and `FormatRecipeStep` (Step 7) to call the **Ollama HTTP API** (`http://ollama:11434`) and produce a **Pydantic-validated draft `Recipe` JSON** from consolidated evidence (transcript, vision/OCR, metadata, user comment, custom instruction).

**What changes:** Consolidated input JSON → draft `recipe.json` in the job working directory, with strict schema validation, retry/repair for malformed JSON, and confidence fields on uncertain ingredients.

**What must remain unchanged:**

- Raw transcript files (`transcript.txt`, `transcript.json`) — never modified by the formatter.
- Steps 1–6 behavior and artifact paths.
- Vision provider from INC-08 (Tesseract-backed `VisionProvider`); formatter consumes `vision.json` as read-only evidence.
- GPU sequencing: Whisper (Step 3) must complete and release GPU before Ollama formatting runs (orchestrator `gpu_lock`).

## Implementation Instructions

1. Add `app/extraction/formatter.py`:
   - `FormatterProvider` ABC: `format(consolidated_input: dict, *, user_comment: str | None, custom_instruction: str | None) -> Recipe`
   - `OllamaFormatterProvider` — calls `POST {OLLAMA_HOST}/api/generate` (or `/api/chat` if structured) with `model=FORMATTER_MODEL`
   - Config: `FORMATTER_PROVIDER=ollama`, `OLLAMA_HOST`, `FORMATTER_MODEL` (default `qwen2.5:7b-instruct`; fallback `qwen2.5:3b-instruct` documented for VRAM OOM)
   - `MockFormatterProvider` for `docker-compose.test.yml` (returns fixture Recipe JSON, no network)
2. Prompt design:
   - System prompt: output **only** valid JSON matching `Recipe` schema; never invent quantities; use `confidence < 0.5` when uncertain; reconcile transcript vs OCR conflicts explicitly in `notes` when ambiguous.
   - Include consolidated evidence sections: transcript segments, vision frame text + confidence, caption/comments from metadata, `user_comment`, `custom_instruction`.
3. Validation and repair:
   - Parse response; strip markdown fences if present.
   - `Recipe.model_validate()` — on failure, retry once with repair prompt including validation errors.
   - Raise `FormatterValidationError` after max retries; preserve raw LLM response in `working/<job_id>/formatter_raw.txt` for debugging.
4. Implement `app/steps/step07_format_recipe.py`:
   - Class `FormatRecipeStep` (`step_number=7`, `requires=[6]`)
   - Read consolidated input from `StepContext.artifacts["consolidated_input"]` or path artifact
   - Write `recipe.json` (draft) to working dir; set artifacts: `recipe_json_path`, `formatter_model`, `formatter_latency_ms`
   - Acquire `gpu_lock` before Ollama call; release after response (Whisper must not be loaded concurrently)
5. Wire config in `app/config/settings.py`: `FORMATTER_PROVIDER`, `OLLAMA_HOST`, `FORMATTER_MODEL`, optional `FORMATTER_TIMEOUT_SECONDS`.
6. Add unit tests with `MockFormatterProvider`; integration test (optional, marked `@pytest.mark.gpu`) with live Ollama against fixture consolidated input.
7. Document first-time model pull in README/DOCKER: `docker compose exec ollama ollama pull qwen2.5:7b-instruct`.

**Architectural constraints (SRD §10–11):**

- Step 7 is the **only** step that invokes the formatter LLM.
- `web/*` and `cli/*` call `FormatRecipeStep` — no duplicate formatting logic.
- Formatter depends on `FormatterProvider` interface, not Ollama directly, in step code.

## Verification Protocol

**Quantitative success criteria:**

- [ ] Schema validation pass rate on fixture set: **100%** (TRACKING_MATRIX metric)
- [ ] Formatter latency on fixture consolidated input: **< 30s** green, 30–60s yellow, > 60s red
- [ ] No invented quantities when fixture input omits them — `confidence` field present and `< 0.5` or quantity empty
- [ ] Raw transcript files unchanged after Step 7 (checksum or mtime assertion)
- [ ] `MockFormatterProvider` tests pass in `docker-compose.test.yml` without Ollama
- [ ] GPU lock: concurrent Whisper + Ollama calls prevented (unit test on orchestrator lock)
- [ ] `formatter_raw.txt` written on validation failure

**Test cases:**

```bash
# Unit tests (mocked formatter)
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_formatter.py tests/test_step07_format_recipe.py -v

# Integration (GPU host, Ollama running)
docker compose exec ollama ollama pull qwen2.5:7b-instruct
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm cookbook pytest tests/test_formatter_integration.py -v -m gpu

# Single-step via Testing GUI stub (after INC-14a) or direct step invocation:
docker compose run --rm cookbook python -c "
from app.steps.step07_format_recipe import FormatRecipeStep
from app.steps.base import StepContext
# ... load fixture context with consolidated_input artifact
"
```

**Expected output:** Valid `recipe.json` matching `Recipe` schema; metrics logged; no transcript mutation.

## CRITICAL Isolation Protocol

Execute if schema validation pass rate < 100% or formatter latency enters red zone. **Do not proceed to INC-11** until resolved.

### 1. Isolate

- Run Step 7 only against frozen fixture `consolidated_input.json` in `tests/fixtures/` — bypass Steps 1–6 and web layer
- Disable all other pipeline stages in test compose

### 2. Test variants

| Variant | Model | Notes |
|---|---|---|
| D | `qwen2.5:7b-instruct` | Interim default (Ollama pull) |
| D-small | `qwen2.5:3b-instruct` | VRAM fallback |
| API | Teacher formatter (`FORMATTER_PROVIDER=api`) | Bootstrap only — separate model vs prompt issues |

Record pass_rate and latency per variant in [`TRACKING_MATRIX.md`](../TRACKING_MATRIX.md).

### 3. Analyze component outputs

- Compare `formatter_raw.txt` vs parsed JSON; check fence stripping, truncated JSON, hallucinated ingredients
- Process all formatter fixtures; log per-fixture validation errors

### 4. Verify computational correctness

- `Recipe.model_validate()` passes 100% on passing fixtures
- Raw transcript checksums unchanged after Step 7
- GPU lock held during Ollama call only

### 5. Apply mitigation

- Tune prompt; add repair retry; mark uncertain fields with `confidence < 0.5`
- Preserve `working/<job_id>/` artifacts for manual review (INC-15 editor)
- **Rollback option:** set `FORMATTER_PROVIDER=mock` to unblock INC-11 deterministic work

### 6. Proceed gate

- Do **not** start INC-11 until schema validation pass rate is **100%** on fixture set **or** mock provider documented as temporary bypass in session log

## Rollback Procedure

1. Set `FORMATTER_PROVIDER=mock` in test/dev to unblock downstream increments (INC-11+ deterministic steps).
2. Retain `working/<job_id>/` artifacts (consolidated input, raw formatter response) — downstream can use last good draft or manual edit (INC-15).
3. Revert `app/extraction/formatter.py` and `app/steps/step07_format_recipe.py` if interface contract breaks Steps 6 or 8.
4. Do **not** enable INC-10b distillation as rollback — interim Ollama model remains the production path until explicitly resumed.
