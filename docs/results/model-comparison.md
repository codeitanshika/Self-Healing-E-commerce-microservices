# Multi-LLM Comparison Study (corrected re-run, September 2026)

## Why this replaces the June study
The three models compared in June (`llama-3.3-70b-versatile`,
`llama-3.1-70b-versatile`, `mixtral-8x7b-32768`) have all since been
decommissioned by Groq and can no longer be queried — see
`archive_2026-06_dead_models/` for the original (now-irreproducible) data.
This re-run also benefits from two bug fixes made before running (see
`backend/experiments/findings.md`) and uses 3 trials per scenario instead
of 1.

## Setup
Same 20 fault scenarios (5 services × 4 fault types), run 3× each (60 trials
per model, 180 total), through three free open-weight models via Groq, plus
the rule-based baseline.

## Results

| Model | LLM accuracy | Rule accuracy (same inputs) | Recovery rate* | Mean MTTR |
|---|---|---|---|---|
| gpt-oss-120b | 98.3% (59/60) | 100% (60/60) | 100% | 2.88s (σ=0.22s) |
| gpt-oss-20b  | 100% (60/60) | 100% (60/60) | 100% | 3.21s (σ=0.56s) |
| qwen3.8-27b  | 100% (60/60) | 100% (60/60) | 100% | 3.51s (σ=0.64s) |
| **Pooled** | **99.4% (179/180)** | **100% (180/180)** | **100%** | **3.20s (σ=0.57s)** |

The manual baseline used for comparison is an assumed 900s; it was not measured.

*This run used any-fix-heals (`STRICT_HEALING=0`), so recovery rate does not depend on the fix chosen. Strict healing is now the default; see [strategy-comparison.md](strategy-comparison.md) for fix-sensitive results.

Confidence intervals and significance tests: [statistics.md](statistics.md).

## Key Findings

### Model-agnostic accuracy, with one exception
Two of three models (gpt-oss-20b, qwen3.8-27b) scored 100%. gpt-oss-120b scored 98.3%; its single miss was a failed or unparseable reply caught by the safe-default fallback, not a reasoning error (see [findings.md](../../backend/experiments/findings.md), Finding 3). On these four well-separated fault types, model choice did not limit accuracy.

### LLM vs. rule-based
The rules scored 100%, marginally above the pooled LLM figure of 99.4% (difference not significant, McNemar p = 1.000). On clean, single-signal faults the LLM adds no measured accuracy advantage over a correctly specified rule set. What it adds is a readable explanation with each diagnosis.

### Speed differs between models
Mean MTTR rose from gpt-oss-120b (2.88s) to gpt-oss-20b (3.21s) to qwen3.8-27b (3.51s). The largest model was the fastest, so the spread does not follow model size; it most likely reflects how quickly each model's API answered. All values include a fixed 2s validation wait.

### Free-tier models are not a stable reference
Every model used in June had been retired by this run. Three current models were swapped in by changing `GROQ_MODEL` only, but specific model IDs should not be treated as a long-term reference.
