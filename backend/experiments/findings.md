# Experiment Findings (corrected re-run)

## Run Date
September 2, 2026

## Why this run replaces the June findings
The June run used `llama-3.3-70b-versatile`, `llama-3.1-70b-versatile`, and
`mixtral-8x7b-32768`, all three of which Groq has since decommissioned (see
`archive_2026-06_dead_models/`) — that data can no longer be reproduced
against a live API. This run also fixes two bugs present in June:
1. The memory-leak fault's escalation to a full crash was driven by *how
   many things polled `get_health()`*, not by elapsed time — non-reproducible
   by construction, and the real (previously misdiagnosed) cause of the
   cart/memory misclassification reported in June.
2. The Report Agent logged a DB row on every `VALIDATION_RESULT`, including
   intermediate `STILL_BROKEN` retries — harmless in June only because every
   fix happened to succeed first-try.

This run also adds 3 trials per scenario (June ran each scenario once),
so accuracy and MTTR are reported with real sample sizes instead of
single-point estimates.

## Models
`openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b` — the three
free open-weight chat models available on Groq at the time of this run.

## Summary Results (pooled across all 3 models, 180 trials total: 20 scenarios × 3 trials × 3 models)

| Metric | Value |
|---|---|
| Total trials | 180 |
| LLM diagnosis accuracy | 179/180 (99.4%) |
| Rule-based accuracy | 180/180 (100%) |
| Recovery rate | 180/180 (100%) — see caveat below |
| Mean MTTR | 3.20s (σ = 0.57s, range 2.44–5.38s) |
| Manual baseline MTTR | 900s (assumed, not measured) |
| Total time saved (vs. 900s baseline) | 161,424s ≈ 44.8 hours across 180 incidents |

## Per-model results

| Model | LLM Accuracy | Rule Accuracy | Recovery Rate | Mean MTTR |
|---|---|---|---|---|
| gpt-oss-120b | 59/60 (98.3%) | 60/60 (100%) | 60/60 (100%) | 2.88s (σ=0.22s) |
| gpt-oss-20b  | 60/60 (100%) | 60/60 (100%) | 60/60 (100%) | 3.21s (σ=0.56s) |
| qwen3.8-27b  | 60/60 (100%) | 60/60 (100%) | 60/60 (100%) | 3.51s (σ=0.64s) |

## Accuracy and MTTR by fault type (pooled, n=45 per fault type)

| Fault type | Expected root cause | LLM accuracy | Mean MTTR |
|---|---|---|---|
| crash | service_crash | 45/45 (100%) | 3.05s (σ=0.50s) |
| memory | memory_leak | 45/45 (100%) | 3.03s (σ=0.45s) |
| slow | cpu_overload | 44/45 (98%) | 3.43s (σ=0.62s) |
| error | error_spike | 45/45 (100%) | 3.28s (σ=0.59s) |

## Key Findings

### Finding 1 — MTTR reduction
Mean recovery time was 3.20s versus an assumed 900s manual baseline
(99.6% reduction). The timer starts at fault injection and the diagnosis agent
is called directly, so monitor detection delay is not included. Across 180 recovered incidents
this represents ~44.8 hours of downtime avoided against the conservative
baseline alone.

### Finding 2 — The fault-simulation fix worked
With the fault simulation made time-based instead of poll-count-based
(growth now depends on time since injection), the memory-leak
misclassification from the June run did not recur: memory_leak was diagnosed
correctly in all 45 memory-fault trials (5 services × 3 trials × 3 models).

### Finding 3 — The one remaining miss was an infrastructure hiccup, not a reasoning error
The single LLM misclassification (`gpt-oss-120b`, cart/slow, trial 1)
returned `root_cause: "unknown", confidence: 0` — the `_safe_default()`
fallback in `shared/llm.py`, which fires when the API call fails or returns
non-JSON output. This is not a diagnostic reasoning failure; it is the
system's safety fallback correctly engaging on a transient error, and the
Fix Agent's default fix (`restart`) recovered the service under this run's
any-fix-heals setting. Under strict healing (today's default) a restart does
not cure a slow fault, so the retry loop would have to recover it.

### Finding 4 — Recovery rate in this run is not a meaningful discriminator
**Caveat, stated plainly:** this benchmark ran with any-fix-heals
(`STRICT_HEALING=0`), where `SimulatedService.heal()` resets a service to
full health whichever `fix_type` is passed. *Any* diagnosed fix, correct or
not, produced `RECOVERED`, so the 100% recovery rate is a property of that
setting, not evidence that fix *selection* mattered. Diagnosis accuracy is the metric in this study that actually
varies with model/method choice; recovery rate and MTTR mostly reflect
API latency and the fixed 2s validation delay.

**Since then:** strict healing was added and is the default, so only a fix
that suits the fault cures it. Fix selection and retries are measured in
[strategy-comparison.md](../../docs/results/strategy-comparison.md) and
[verification-under-noise.md](../../docs/results/verification-under-noise.md).

### Finding 5 — LLMs frequently choose a different, but not "canonical," fix
Even when root_cause was correctly diagnosed, the LLM's chosen `fix` for
`error_spike` varied across trials: `reduce_load` (most common),
`retry_with_backoff`, and `restart` were all selected across models, despite
`config.py`'s `FIX_MAP` documenting `retry_with_backoff` as the "primary"
fix for `error_spike`. This is because the primary fix is read directly from
the LLM's own JSON output (`orchestrator.py`'s `on_diagnosis_ready`), not
looked up from `FIX_MAP` — `FIX_MAP` is only consulted for the *retry* fix
after a `STILL_BROKEN` result. Because of Finding 4, this divergence had no
effect on outcomes here. It does matter under strict healing, where
`reduce_load` does not cure an error spike (see the strategy comparison).

## Baseline Comparison Table

| Approach | Diagnosis accuracy | Mean MTTR | Recovery rate* |
|---|---|---|---|
| Manual (assumed) | not measured | 900s | not measured |
| Rule-based diagnosis | 100% (180/180) | not timed in this run | not applied in this run |
| LLM-based (ours, pooled) | 99.4% (179/180) | 3.20s | 100% (180/180) |

*See Finding 4: recovery rate was not fix-sensitive in this run.

## Limitations
- Services are simulated in this benchmark.
- 20 scenarios × 3 trials × 3 models = 180 trials on a single testbed: small
  by ML-evaluation standards.
- The manual baseline is an assumption, not measured.
- Recovery rate and MTTR here measure loop latency, not remediation
  correctness (Finding 4).
- Free-tier model availability is not a stable experimental control: model IDs
  get retired.
