# Strategy comparison under strict healing

Every fault below is one of the 20 (service, fault) scenarios, repeated 3 times per diagnoser, with `STRICT_HEALING=1` (a fix only cures a fault it is effective against). Recovery is reported for:

- **Blind restart**: always restart, no diagnosis, no verification (a Kubernetes liveness-probe analogue; analytic).
- **Open loop**: apply the diagnoser's first fix once and trust it (paired with the closed loop's diagnosis).
- **Closed loop**: the real pipeline: validate, retry an alternate fix, escalate after 2 retries (measured).

Cells: recovery rate (successes/n) with a 95% Wilson interval.

| Diagnoser | Diagnosis accuracy | Blind restart | Open loop | Closed loop | Needed a retry | Escalated | Closed vs open (McNemar) |
|---|---|---|---|---|---|---|---|
| rule-based | 100.0% (60/60) [94.0%, 100.0%] | 75.0% (45/60) [62.8%, 84.2%] | 100.0% (60/60) [94.0%, 100.0%] | 100.0% (60/60) [94.0%, 100.0%] | 0 | 0 | p = 1.000 (0 open-only, 0 closed-only) |
| gpt-oss-120b | 100.0% (60/60) [94.0%, 100.0%] | 75.0% (45/60) [62.8%, 84.2%] | 88.3% (53/60) [77.8%, 94.2%] | 100.0% (60/60) [94.0%, 100.0%] | 7 | 0 | p = 0.016 (0 open-only, 7 closed-only) |
| gpt-oss-20b | 80.0% (48/60) [68.2%, 88.2%] | 75.0% (45/60) [62.8%, 84.2%] | 91.7% (55/60) [81.9%, 96.4%] | 91.7% (55/60) [81.9%, 96.4%] | 5 | 5 | p = 1.000 (0 open-only, 0 closed-only) |
| qwen3-27b | 98.3% (59/60) [91.1%, 99.7%] | 75.0% (45/60) [62.8%, 84.2%] | 100.0% (60/60) [94.0%, 100.0%] | 100.0% (60/60) [94.0%, 100.0%] | 0 | 0 | p = 1.000 (0 open-only, 0 closed-only) |

## Pooled over all diagnosers

- Blind restart: 75.0% (180/240) [69.2%, 80.1%]
- Open loop: 95.0% (228/240) [91.5%, 97.1%]
- Closed loop: 97.9% (235/240) [95.2%, 99.1%]
- Closed vs blind restart: p < 0.001 (0 blind-only, 55 closed-only)
- Closed vs open loop: p = 0.016 (0 open-only, 7 closed-only)

## By fault type (closed loop / open loop / blind restart)

| Diagnoser | crash | error | memory | slow |
|---|---|---|---|---|
| rule-based | 15/15 / 15/15 / 15/15 | 15/15 / 15/15 / 15/15 | 15/15 / 15/15 / 15/15 | 15/15 / 15/15 / 0/15 |
| gpt-oss-120b | 15/15 / 15/15 / 15/15 | 15/15 / 8/15 / 15/15 | 15/15 / 15/15 / 15/15 | 15/15 / 15/15 / 0/15 |
| gpt-oss-20b | 15/15 / 15/15 / 15/15 | 15/15 / 15/15 / 15/15 | 15/15 / 15/15 / 15/15 | 10/15 / 10/15 / 0/15 |
| qwen3-27b | 15/15 / 15/15 / 15/15 | 15/15 / 15/15 / 15/15 | 15/15 / 15/15 / 15/15 | 15/15 / 15/15 / 0/15 |

## Reading this honestly

- Blind restart is modelled analytically from the simulator's `EFFECTIVE_FIXES` table (a restart does not cure a sustained overload, so it fails the *slow* class). This encodes plausible operations knowledge; it is not a measurement of a real Kubernetes cluster.
- Open and closed loop are scored on the same incidents, and open/closed on the same diagnosis, so the comparisons are paired.
- Where an LLM's *diagnosis* is right but its own chosen *fix* is not effective, the closed loop's retry is what recovers it; this table counts those cases.
- Validation wait is shortened to 0.5 s for these runs; it does not change which fixes are effective.
