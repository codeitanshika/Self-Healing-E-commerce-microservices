# End-to-end pipeline latency

125 incidents through the real event-bus pipeline (rule-based diagnosis, 1s monitor poll). Unlike the diagnosis-only benchmark, MTTR here starts at fault injection and therefore includes detection latency.

## Single faults (all simulated services x all fault types)

- Incidents: 60, recovered: 60
- MTTR: 2.83s (SD 0.26), 95% CI [2.77, 2.89]

Where the time goes (mean per stage):

| Stage | Mean (s) | Share |
|---|---|---|
| Detect | 0.82 | 29% |
| Diagnose | 0.00 | 0% |
| Fix | 0.00 | 0% |
| Validate | 2.01 | 71% |

Detection is bounded by the monitor poll interval (expected ≈ poll/2 plus scheduling) and validation by a fixed 2s settle wait, so these two stages dominate. With the production default of a 5s poll, expected detection rises to ≈ 2.5s; the LLM adds its own network latency on top in `--mode llm`.

| Fault | MTTR |
|---|---|
| crash | 2.63s (SD 0.45), 95% CI [2.39, 2.83] (n=15) |
| error | 2.89s (SD 0.07), 95% CI [2.85, 2.92] (n=15) |
| memory | 2.90s (SD 0.08), 95% CI [2.86, 2.94] (n=15) |
| slow | 2.92s (SD 0.06), 95% CI [2.89, 2.95] (n=15) |

## Concurrent and cascading incidents

Each incident is timed from its own injection (staggered cascades are listed separately, not counted as simultaneous). If the pipeline serialised work, MTTR would grow roughly linearly with the number of simultaneous incidents; here it rises only modestly.

| Simultaneous incidents | MTTR per incident |
|---|---|
| 2 | 2.74s (SD 0.38), 95% CI [2.47, 2.93] (n=10) |
| 3 | 2.89s (SD 0.67), 95% CI [2.63, 3.26] (n=15) |
| 5 | 3.10s (SD 0.77), 95% CI [2.84, 3.43] (n=25) |

| Scenario | MTTR per incident |
|---|---|
| checkout-cascade | 2.75s (SD 0.38), 95% CI [2.55, 2.92] (n=15) |
| everything-breaks | 3.10s (SD 0.77), 95% CI [2.84, 3.43] (n=25) |
| flash-sale | 2.89s (SD 0.67), 95% CI [2.63, 3.26] (n=15) |
| slow-burn | 2.74s (SD 0.38), 95% CI [2.47, 2.93] (n=10) |

All incidents recovered: **True**; maximum retries used: **0**.

## Caveat

The simulated services always heal when asked, so first-try success is 100% by construction. Retry/escalation behaviour is covered by the forced-failure test in `retry-loop-test.md`, and the real Nginx container (see `run_pipeline.py --service nginx`) is where a genuinely failing fix can occur.
