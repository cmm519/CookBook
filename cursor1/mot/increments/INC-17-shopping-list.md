# INCREMENT 17: Shopping List (Multi-Recipe, HEB Aisle Order)

**Status:** CRITICAL  
**Dependencies:** INC-16 (Ratings + user notes — recipe detail UX complete)

## Capability Specification

Implement `app/shopping/` and **Shopping List** UI in the Production Web UI. Users select multiple recipes and generate a combined ingredient list sorted by **HEB store aisle order** (deli → produce → meat → bread → cooking → frozen → snacks → dairy → other).

**What changes:** Multi-recipe shopping list with merge rules, check-off, manual edit, and source recipe references.

**What must remain unchanged:**

- Canonical `recipe.json` per package — shopping list is derived data, not written back to recipes.
- Ingredient quantities from recipes — merge must not invent combined quantities when ambiguous.

## Implementation Instructions

1. Add `app/shopping/aisle.py`:
   - `HEB_AISLE_ORDER` enum matching SRD §3: `deli, produce, meat, bread, cooking, frozen, snacks, dairy, other`
   - `categorize_ingredient(item: str) -> aisle_category` — keyword/heuristic map (e.g. "chicken" → meat, "milk" → dairy); default `other`
   - Document heuristic file for operator tuning (`app/shopping/aisle_keywords.json`)
2. Add `app/shopping/merge.py`:
   - `build_shopping_list(recipes: list[Recipe], slugs: list[str]) -> list[ShoppingListItem]`
   - **Conservative merge rules:**
     - Merge only when normalized `item` + `preparation` match AND quantities are combinable (same unit or both numeric-compatible)
     - Ambiguous pairs (e.g. "2 cloves garlic" + "1 head garlic") → **separate lines** with both `source_recipe_slugs`
     - Never sum unlike units; leave `quantity` as combined string only when explicit rule matches
   - Assign `aisle_category` per item; sort by HEB order then alphabetically within aisle
3. Add `app/shopping/session.py` (or SQLite table `shopping_list_items`):
   - Persist session list: `item_id`, `ingredient_name`, `quantity`, `aisle_category`, `source_recipe_slugs`, `checked`
   - Support check-off and manual add/remove/edit
4. **`ShoppingListController`** in `app/web/production/`:
   - `GET /shopping` — recipe multi-select + current list view grouped by aisle
   - `POST /shopping/build` — body `{ "slugs": ["...", "..."] }` — regenerate from selected recipes
   - `POST /shopping/items/{item_id}/check`, `PATCH /shopping/items/{item_id}` — check-off and manual edit
5. Templates:
   - `shopping.html` — recipe checkboxes, "Build list" button, aisle-grouped list with checkboxes, source recipe links
6. Tests with **fixture merge accuracy** (TRACKING_MATRIX metric):
   - `tests/fixtures/shopping_merge/` — known inputs and expected line counts
   - `tests/test_shopping_list.py` — merge accuracy, aisle ordering, ambiguous non-merge cases

**Architectural constraints (SRD §3, §10):**

- `shopping/` reads `Recipe` objects via storage/search — does not import web layer.
- Shopping list is end-user facing (Production UI only).

## Verification Protocol

**Quantitative success criteria:**

- [ ] Shopping list merge accuracy on fixture set: **100%** green, 90–99% yellow, < 90% red (TRACKING_MATRIX)
- [ ] Items sorted by HEB aisle order enum
- [ ] Ambiguous garlic-style fixtures produce **separate lines** (not incorrect sum)
- [ ] Each line lists `source_recipe_slugs` when merged from multiple recipes
- [ ] Check-off state persists in session/DB across page reload
- [ ] `pytest tests/test_shopping_list.py` passes

**Test cases:**

```bash
docker compose -f docker-compose.test.yml run --rm cookbook pytest tests/test_shopping_list.py -v
# Manual: select 2+ fixture recipes → build list → verify aisle grouping
```

**Expected output:** Aisle-grouped list; fixture expectations match exactly; no phantom merged quantities.

## CRITICAL Isolation Protocol

Execute if merge accuracy drops below 90% or aisle misclassification exceeds 5% on fixtures. **Do not mark increment complete** until green zone.

### 1. Isolate

- Run `build_shopping_list()` unit tests only — no web layer, no import pipeline
- Use frozen fixture recipes in `tests/fixtures/shopping_merge/`

### 2. Test variants

| Variant | Merge strategy | Notes |
|---|---|---|
| S1 | Conservative (default) | Separate lines when quantity ambiguous |
| S2 | Stricter item normalization | Lowercase + strip only |
| S3 | Aisle keyword tuning | Edit `aisle_keywords.json` |

Record merge_accuracy per variant in [`TRACKING_MATRIX.md`](../TRACKING_MATRIX.md).

### 3. Analyze component outputs

- For each failing fixture, dump input recipes and actual vs expected `ShoppingListItem` lists side-by-side
- Bucket failures: merge rule error, aisle keyword miss, normalization mismatch

### 4. Verify computational correctness

- HEB aisle sort order matches enum: deli → produce → meat → bread → cooking → frozen → snacks → dairy → other
- Every line has `source_recipe_slugs` when derived from recipes
- No writes to canonical `recipe.json` files

### 5. Apply mitigation

- When in doubt, prefer **duplicate lines** over wrong combined quantity (SRD mitigation)
- Add failing case as permanent fixture before fixing heuristic
- Allow manual edit/check-off in UI for operator overrides

### 6. Proceed gate

- Do **not** sign off INC-17 until fixture merge accuracy is **100%** (TRACKING_MATRIX green zone)

## Rollback Procedure

1. Hide `/shopping` routes and navigation — recipes remain browsable without shopping feature.
2. Remove `app/shopping/` — no impact on recipe packages or index.
3. Clear shopping session table if schema was added — user checklist data only.
