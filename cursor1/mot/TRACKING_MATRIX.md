# Performance Tracking Matrix

> Record metrics after each increment. Color-code: **Green** = acceptable, **Yellow** = warning, **Red** = failure requiring intervention.

## Threshold Legend

| Zone | Meaning |
|---|---|
| Green | Acceptable — proceed to next increment |
| Yellow | Warning — investigate before proceeding |
| Red | Failure — execute isolation protocol, do not proceed |

## Variants

| Variant | Description |
|---|---|
| A | Whisper `large-v3`, vision on, teacher formatter (API) |
| B | Whisper `medium`, vision on, teacher formatter (API) |
| C | Whisper `large-v3`, vision off, teacher formatter (API) |
| D | Whisper `large-v3`, vision on, Ollama `qwen2.5:7b-instruct` (interim formatter) |
| D-distill | *(on hold)* Distilled `cookbook-formatter` local | INC-10b deferred |

## Metrics Matrix

| Increment | Metric | Green | Yellow | Red | Var A | Var B | Var C | Var D |
|---|---|---|---|---|---|---|---|---|
| 1 | Docker build succeeds | pass | — | fail | pass | | | pass |
| 1 | Project compiles / tests run (in test compose) | pass | — | fail | pass | | | pass |
| 2 | Pydantic model validation (fixtures) | 100% | — | < 100% | pass | | | pass |
| 3 | Storage round-trip (write/read package) | pass | — | fail | pass | | | pass |
| 4 | Download success (fixture URL) | pass | — | fail | pass | | | pass |
| 6 | Transcription segments / video minute | ≥ 8 | 4–7 | < 4 | | | | pass |
| 10 | Schema validation pass rate | 100% | 90–99% | < 90% | | | | pass |
| 11 | Markdown golden-file match | 100% | — | mismatch | pass | | | pass |
| 12 | Search query latency (ms) | < 200 | 200–500 | > 500 | pass | | | pass |
| 17 | Shopping list merge accuracy (fixture) | 100% | 90–99% | < 90% | pass | | | pass |

## Session Log

| Date | Increment | Variant | Key Metrics | Zone | Notes |
|---|---|---|---|---|---|
| 2026-08-30 | 1, 4, 6 | D | Phase 0: 6/6 transcripts; pytest pass | Green | CPU transcribe; package stubs added |
| 2026-08-30 | 2–18 | D | Full pipeline + 3 GUIs implemented | Green | INC-10b on hold; mock formatter in test compose |

## Notes

- Fill Variant columns as each variant is tested; leave blank until tested.
- For INC-10b, run Variants A and D on the same fixture set and compare.
- Record session log entry after every development session.
