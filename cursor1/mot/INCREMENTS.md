# Module of Thought — Increment List

> ONE capability added per increment with explicit verification.
> See [`increments/`](increments/) for individual increment prompt files.

## Increment Overview

| # | Capability | Status | Critical? | Depends on |
|---|---|---|---|---|
| 1 | Project skeleton + config + Docker scaffold | pending | | — |
| 2 | Pydantic data models | pending | | 1 |
| 3 | Recipe package storage | pending | | 2 |
| 4 | Downloader interface + yt-dlp | pending | | 3 |
| 5 | Media/audio extraction (ffmpeg) | pending | | 4 |
| 6 | Transcription interface + Whisper (local) | pending | | 5 |
| 7 | Frame extraction | pending | | 5 |
| 8 | Vision/OCR interface | pending | **CRITICAL** | 7 |
| 9 | Source consolidation | pending | | 6, 8 |
| 10 | Recipe formatter via Ollama API + validation | pending | **CRITICAL** | 9 |
| 10b | Distilled `cookbook-formatter` model — LoRA train + `ollama create` | pending | **CRITICAL** | 10 + sufficient training data |
| 11 | Normalization + Markdown formatter (deterministic, no LLM) | pending | | 10 |
| 12 | SQLite search index | pending | | 11 |
| 13 | CLI import workflow | pending | | 12 |
| 14 | Web server skeleton + recipe viewer | pending | | 13 |
| 15 | Recipe editor (manual override) | pending | | 14 |
| 16 | Rating + user notes/comments | pending | | 15 |
| 17 | Shopping list (multi-recipe, HEB order) | pending | **CRITICAL** | 16 |
| 18 | Bug reporting + debug log + maintenance hook | pending | | 13 |

## Critical Checkpoints

### INC-08: Vision/OCR Interface

- **Risk:** On-screen recipe text is often the only source for quantities; OCR quality varies widely across video styles.
- **Failure mode:** Missing or garbled ingredient quantities; formatter invents values to fill gaps.
- **Mitigation:** Preserve raw frame-level evidence; pass confidence scores; formatter must mark uncertain values; test with fixture frames containing known text overlays.

### INC-10: Recipe Formatter (Teacher Model)

- **Risk:** LLM returns invalid JSON, hallucinates quantities, or fails to reconcile transcript vs OCR conflicts.
- **Failure mode:** Schema validation failures; silently invented ingredients; instructions out of cooking order.
- **Mitigation:** Strict Pydantic validation; retry/repair logic for malformed JSON; confidence fields on uncertain ingredients; collect transcript→recipe pairs for distillation dataset.
- **Rollback:** Fall back to raw transcript + manual edit in web UI; retain working directory artifacts.

### INC-10b: Distilled Formatter Model

- **Risk:** Distilled model underperforms teacher on edge cases (unusual recipes, heavy OCR noise).
- **Failure mode:** Lower schema validation pass rate; degraded ingredient accuracy vs teacher baseline.
- **Mitigation:** Compare distilled vs teacher on held-out test set before swap-in; keep teacher as fallback; track formatting quality in tracking matrix.
- **Isolation test:** Run same fixture inputs through both teacher and distilled; compare JSON diff.

### INC-17: Shopping List (HEB Aisle Order)

- **Risk:** Ingredient deduplication across recipes is ambiguous (e.g. "2 cloves garlic" + "1 head garlic").
- **Failure mode:** Duplicate items on list, wrong aisle assignment, quantities not combined.
- **Mitigation:** Conservative merge rules; keep source recipe references; allow manual edit/check-off in UI.

## Session Workflow

```
SESSION START
├── Load: MASTER_CONTEXT.md
├── Review: TRACKING_MATRIX.md (last session metrics)
├── Execute: Current increment
│   └── Verify: Quantitative metrics in green zone
├── If CRITICAL increment fails: Execute isolation protocol (see increment file)
└── SESSION END: Record metrics in TRACKING_MATRIX.md

NEXT SESSION START
├── Load: MASTER_CONTEXT.md
├── Review: Tracking matrix from previous session
└── Continue from last successful increment
```

## Degradation Analysis Protocol

When performance drops below threshold:

1. **Isolate:** Run current increment in isolation from rest of system
2. **Test variants:** Compare tracked variants (Whisper size, vision on/off, teacher vs distilled formatter)
3. **Analyze component outputs:** Check intermediate results (transcript segments, OCR frames, formatter JSON)
4. **Verify computational correctness:** Validate schema, segment timestamps, frame counts
5. **Apply mitigation:** Use pre-defined strategy from critical checkpoint documentation above
