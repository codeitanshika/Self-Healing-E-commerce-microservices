# Experiment Findings

## Run Date
June 23, 2026

## Summary Results

| Metric | Value |
|---|---|
| Total scenarios | 20 (5 services × 4 fault types) |
| LLM diagnosis accuracy | 19/20 (95%) |
| Rule-based accuracy | 19/20 (95%) |
| Recovery rate | 20/20 (100%) |
| Average MTTR | 2.66s |
| Manual baseline MTTR | 900s |
| MTTR reduction | 99.7% |
| Avg time saved per incident | 897.34s |

## Key Findings

### Finding 1 — MTTR reduction
The autonomous system reduced mean recovery time from 900s (manual
baseline) to 2.66s — a 99.7% reduction. Across 20 incidents this
represents 17,946 seconds (≈5 hours) of downtime avoided.

### Finding 2 — Perfect recovery rate
100% of injected faults were successfully remediated on the first
fix attempt, with no retries required across all 20 scenarios.
This validates the fault→fix mapping in config.py.

### Finding 3 — LLM vs rule-based accuracy parity
Both the LLM-based and rule-based diagnosis systems achieved 95%
accuracy (19/20). On well-defined single-signal faults with clear
metric signatures, LLM reasoning does not outperform explicit rules
in accuracy. However the LLM produces human-readable explanations
alongside its diagnosis — a capability rule-based systems lack and
which adds value for incident post-mortems.

### Finding 4 — The one misclassification (both systems)
Scenario: cart / memory fault
Expected: memory_leak
Both systems diagnosed: service_crash

Root cause: the memory leak simulation progressed to service
termination before the diagnosis was triggered. At the moment of
metric sampling, status='down' with error_rate=1.0 — both systems
correctly applied the highest-priority rule (status==down →
service_crash). This is a fault-progression timing edge case, not
a reasoning failure. In a real system, faster polling (1-2s instead
of 5s) would likely catch the memory_leak stage before termination.

### Finding 5 — Prompt engineering impact
Before adding decision-priority rules to the LLM prompt:
accuracy = 3/5 (60%) on test cases.
After adding explicit priority ordering:
accuracy = 5/5 (100%) on test cases, 19/20 (95%) on full experiments.
This demonstrates that prompt structure has measurable impact on
LLM classification accuracy for structured diagnostic tasks.

## Baseline Comparison Table

| Approach | Accuracy | MTTR | Recovery Rate |
|---|---|---|---|
| Manual (human) | ~100%* | 900s | 100% |
| Rule-based healer | 95% | ~2.66s | 100% |
| LLM-based healer (ours) | 95% | ~2.66s | 100% |

*Manual diagnosis is assumed correct; human MTTR is an industry estimate.

## Limitations
- Services are simulated, not real containers
- 20 scenarios on a single testbed — small sample
- Manual baseline is an estimate, not measured
- Memory leak timing edge case affects one result
- Single LLM tested (Llama 3.3 70B via Groq)