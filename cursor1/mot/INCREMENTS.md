# Module of Thought — Increment List

> ONE capability added per increment with explicit verification.
> See [`increments/`](increments/) for individual increment prompt files.

## Increment Overview

| # | Capability | Status | Critical? | Depends on |
|---|---|---|---|---|
| 1 | Project skeleton + config + Docker scaffold (+ Phase 0 `MODE=download` / `MODE=transcribe`) | **done** | | — |
| 2 | Pydantic data models | **done** | | 1 |
| 3 | Recipe package storage | **done** | | 2 |
| 4 | Downloader interface + yt-dlp (aligns with Phase 0 batch-download / `dataset/raw/`) | **done** | | 3 |
| 5 | Media/audio extraction (ffmpeg) | **done** | | 4 |
| 6 | Transcription interface + Whisper (local) (aligns with Phase 0 batch-transcribe / `dataset/transcripts/`) | **done** | | 5 |
| 7 | Frame extraction | **done** | | 5 |
| 8 | Vision/OCR interface | **done** | **CRITICAL** | 7 |
| 9 | Source consolidation | **done** | | 6, 8 |
| 10 | Recipe formatter via Ollama API + validation | **done** | **CRITICAL** | 9 |
| 10b | Distilled `cookbook-formatter` model — LoRA train + `ollama create` | **done** | — | 10 + sufficient training data |
| 11 | Normalization + Markdown formatter (deterministic, no LLM) | **done** | | 10 |
| 12 | SQLite search index | **done** | | 11 |
| 13 | CLI import workflow | **done** | | 12 |
| 14 | Web server skeleton + recipe viewer | **done** | | 13 |
| 14a | **Testing GUI** — URL queue + step runner (steps 1–9) | **done** | | 13 |
| 14b | **Deployment GUI** — stack, env, models, health | **done** | | 13 |
| 15 | Recipe editor (manual override) | **done** | | 14 |
| 16 | Rating + user notes/comments | **done** | | 15 |
| 17 | Shopping list (multi-recipe, HEB order) | **done** | **CRITICAL** | 16 |
| 18 | Bug reporting + debug log + maintenance hook | **done** | | 13 |

## Phase 0 vs Full Pipeline

**INC-01** now includes Docker **`MODE`** dispatch so Phase 0 can run before the full app:

- `MODE=download` — yt-dlp batch fetch into `dataset/raw/` (stub in INC-01; production logic in INC-04)
- `MODE=transcribe` — faster-whisper on `dataset/raw/` → `dataset/transcripts/` (stub in INC-01; production logic in INC-06)

Phase 0 acceptance uses INC-01 entrypoint + volume layout only. **INC-04** and **INC-06** implement the reusable downloader and transcription interfaces that back both batch dataset collection and the later single-recipe import pipeline.

## Critical Checkpoints

### INC-08: Vision/OCR Interface

- **Risk:** On-screen recipe text is often the only source for quantities; OCR quality varies widely across video styles.
- **Failure mode:** Missing or garbled ingredient quantities; formatter invents values to fill gaps.
- **Mitigation:** Preserve raw frame-level evidence; pass confidence scores; formatter must mark uncertain values; test with fixture frames containing known text overlays.

### INC-10: Recipe Formatter (Ollama — `qwen2.5:7b-instruct` interim)

- **Risk:** LLM returns invalid JSON, hallucinates quantities, or fails to reconcile transcript vs OCR conflicts.
- **Failure mode:** Schema validation failures; silently invented ingredients; instructions out of cooking order.
- **Mitigation:** Strict Pydantic validation; retry/repair logic for malformed JSON; confidence fields on uncertain ingredients; use `qwen2.5:7b-instruct` (fallback `qwen2.5:3b-instruct` if VRAM tight).
- **Rollback:** Fall back to raw transcript + manual edit in web UI; retain working directory artifacts.

### INC-10b: Distilled Formatter Model — **ON HOLD**

> Deferred to future development. Interim formatter is `qwen2.5:7b-instruct` via Ollama pull. See [`DISTALATION.MD`](../DISTALATION.MD).

- **Risk:** Distilled model underperforms interim model on edge cases (unusual recipes, heavy OCR noise).
- **Failure mode:** Lower schema validation pass rate; degraded ingredient accuracy vs interim baseline.
- **Mitigation:** Compare distilled vs interim on held-out test set before swap-in; keep interim as fallback; track formatting quality in tracking matrix.
- **Isolation test:** Run same fixture inputs through both; compare JSON diff.

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
