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
| D | Whisper `large-v3`, vision on, distilled formatter (local) |

## Metrics Matrix

| Increment | Metric | Green | Yellow | Red | Var A | Var B | Var C | Var D |
|---|---|---|---|---|---|---|---|---|
| 1 | Docker build succeeds | pass | — | fail | | | | |
| 1 | Project compiles / tests run (in test compose) | pass | — | fail | | | | |
| 2 | Pydantic model validation (fixtures) | 100% | — | < 100% | | | | |
| 3 | Storage round-trip (write/read package) | pass | — | fail | | | | |
| 4 | Download success (fixture URL) | pass | — | fail | | | | |
| 5 | Audio extraction (fixture video) | WAV valid | — | corrupt/missing | | | | |
| 6 | Transcription segments / video minute | ≥ 8 | 4–7 | < 4 | | | | |
| 6 | Transcription latency (fixture, seconds) | < 60 | 60–120 | > 120 | | | | |
| 7 | Frame count ≈ duration × interval | ± 5% | ± 10% | > ± 10% | | | | |
| 8 | OCR text detected (fixture frames) | ≥ 80% | 50–79% | < 50% | | | | |
| 9 | Consolidation object schema valid | 100% | — | < 100% | | | | |
| 10 | Schema validation pass rate | 100% | 90–99% | < 90% | | | | |
| 10 | Formatter latency (fixture, seconds) | < 30 | 30–60 | > 60 | | | | |
| 10b | Distilled vs teacher JSON similarity | ≥ 90% | 80–89% | < 80% | | | | |
| 11 | Markdown golden-file match | 100% | — | mismatch | | | | |
| 12 | Search query latency (ms) | < 200 | 200–500 | > 500 | | | | |
| 13 | End-to-end import success | pass | — | fail | | | | |
| 14 | Recipe detail page load (seconds) | < 2 | 2–5 | > 5 | | | | |
| 17 | Shopping list merge accuracy (fixture) | 100% | 90–99% | < 90% | | | | |

## Session Log

| Date | Increment | Variant | Key Metrics | Zone | Notes |
|---|---|---|---|---|---|
| | | | | | |

## Notes

- Fill Variant columns as each variant is tested; leave blank until tested.
- For INC-10b, run Variants A and D on the same fixture set and compare.
- Record session log entry after every development session.
