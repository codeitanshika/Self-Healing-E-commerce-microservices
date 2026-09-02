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

| Model | LLM Accuracy | Rule Accuracy | Recovery Rate* | Mean MTTR |
|---|---|---|---|---|
| gpt-oss-120b | 98.3% (59/60) | 100% | 100% | 2.88s (σ=0.22s) |
| gpt-oss-20b  | 100% (60/60) | 100% | 100% | 3.21s (σ=0.56s) |
| qwen3.8-27b  | 100% (60/60) | 100% | 100% | 3.51s (σ=0.64s) |
| Rule-based (pooled) | — | 100% (180/180) | 100%* | ~3.2s |
| Manual baseline (illustrative) | ~100%† | — | 100% | 900s |
| Manual baseline (PagerDuty-measured [11]) | ~100%† | — | — | ~7,560s |

*See caveat below — recovery rate is not currently fix-sensitive in this
testbed.
†Manual diagnosis is assumed correct; MTTR figures are external estimates.

## Key Findings

### Model-agnostic robustness, with one honest exception
Two of three models (gpt-oss-20b, qwen3.8-27b) achieved 100% diagnosis
accuracy; the third (gpt-oss-120b) scored 98.3%, with its single miss being
a transient API/JSON-parsing failure caught by the system's safe-default
fallback, not a reasoning error (see `findings.md` Finding 3). Structured
fault classification over well-defined metric signatures remains robustly
solvable across current open-weight model families and sizes — model choice
is not a limiting factor for this fault taxonomy.

### LLM vs. rule-based
The rule-based baseline scored 100% on every trial, matching or
marginally exceeding the LLM's pooled 99.4%. On these clean, single-signal
faults the LLM adds no measurable accuracy advantage over an explicit,
correctly-specified rule set — its value here is the human-readable
explanation it produces alongside each diagnosis, not raw classification
accuracy. This is consistent with the June finding and is not an artifact of
the bug fixes.

### MTTR scales roughly with model size/latency, not reasoning quality
Mean MTTR increased mildly from gpt-oss-120b (2.88s) to gpt-oss-20b (3.21s)
to qwen3.8-27b (3.51s). Given all three reached comparable-to-identical
diagnosis accuracy, this spread is best read as API response latency
variation rather than reasoning speed — consistent with the June report's
same conclusion on a different model set.

### A cautionary note on "free-tier" reproducibility
Every model this project depended on in June is gone as of this run. The
practical accessibility argument this project makes (any of several free
models achieves strong accuracy, so the approach is not locked to one
vendor's specific model) held up — we swapped in three different current
models with no code changes beyond `GROQ_MODEL` — but the *specific* model
identifiers cannot be treated as a stable long-term reference. See
`docs/paper.md` §6.2 for the fuller discussion.
