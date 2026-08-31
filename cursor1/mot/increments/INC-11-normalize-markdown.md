# INCREMENT 11: Normalization + Markdown Formatter (Deterministic)

**Status:** Standard  
**Dependencies:** INC-10 (Ollama formatter / draft recipe.json)

## Capability Specification

Implement `NormalizeMarkdownStep` (Step 8) and the `app/formatting/` module to **deterministically** normalize draft `Recipe` JSON and render `recipe.md`. No LLM calls in this step.

**What changes:** Draft `recipe.json` from Step 7 → final validated `recipe.json` + `recipe.md` in the job working directory.

**What must remain unchanged:**

- Raw evidence files (transcript, vision) — still immutable.
- Step 7 draft semantics; normalization **refines** (slug-safe titles, ordered instructions, trimmed strings) but does not invent new ingredients or quantities.
- SRD §10 rule: **No LLM in Steps 8–9.**

## Implementation Instructions

1. Add `app/formatting/normalize.py`:
   - `normalize_recipe(draft: Recipe) -> Recipe` — deterministic transforms:
     - Strip whitespace; collapse duplicate ingredients (same `item` + `preparation`, case-insensitive)
     - Renumber `instructions` sequentially starting at 1
     - Ensure `source_url` preserved from context if missing in draft
     - Reject empty `ingredients` or `instructions` with `NormalizationError`
   - No quantity inference — if draft has empty quantity, leave empty
2. Add `app/formatting/markdown.py`:
   - `render_markdown(recipe: Recipe) -> str` — stable, deterministic template:
     - Title H1, optional description, metadata block (servings, times)
     - Ingredients bullet list (`- {quantity} {item} ({preparation})`)
     - Numbered instructions
     - Notes and tags sections when present
   - Same input → same output (snapshot-test friendly)
3. Implement `app/steps/step08_normalize_markdown.py`:
   - Class `NormalizeMarkdownStep` (`step_number=8`, `requires=[7]`)
   - Read draft from `StepContext.artifacts["recipe_json_path"]`
   - Write `recipe.json` (final) and `recipe.md` to working dir
   - Artifacts: `recipe_json_final_path`, `recipe_md_path`
4. Add tests:
   - `tests/test_normalize.py` — boundary cases (duplicate ingredients, gap in step numbers)
   - `tests/test_markdown.py` — golden-file comparison against fixture recipes
   - `tests/test_step08_normalize_markdown.py` — step integration with fixture draft JSON
5. Wire into `PipelineOrchestrator` step list (ordering after Step 7).

**Architectural constraints (SRD §10–11):**

- `formatting/` has no imports from `extraction/` or Ollama client code.
- Testing GUI Step 8 button invokes the same `NormalizeMarkdownStep` class as full import.

## Verification Protocol

**Quantitative success criteria:**

- [ ] Schema validation pass rate after normalization: **100%**
- [ ] `render_markdown()` is deterministic — repeated calls produce identical bytes
- [ ] Instruction steps always sequential 1..N with no gaps
- [ ] No new ingredients or quantities added that were absent in draft (diff audit test)
- [ ] `pytest tests/test_normalize.py tests/test_markdown.py tests/test_step08_normalize_markdown.py` passes in test compose

**Test cases:**

```bash
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_normalize.py tests/test_markdown.py tests/test_step08_normalize_markdown.py -v
```

**Expected output:** Final `recipe.json` and `recipe.md` in working dir; golden markdown matches committed fixture.

## Rollback Procedure

1. Remove Step 8 from orchestrator step list — pipeline stops after Step 7 draft (manual markdown acceptable temporarily).
2. Delete `app/formatting/` and `app/steps/step08_normalize_markdown.py`; revert orchestrator registration.
3. Downstream INC-12 can index draft JSON if needed for unblock (not recommended for production).
