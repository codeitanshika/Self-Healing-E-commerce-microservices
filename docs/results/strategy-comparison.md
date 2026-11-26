# Strategy comparison under strict healing

Every fault below is one of the 20 (service, fault) scenarios, repeated per diagnoser (trials per diagnoser are in the table: n/20), with `STRICT_HEALING=1` (a fix only cures a fault it is effective against). Recovery is reported for:

- **Blind restart**: always restart, no diagnosis, no verification (a Kubernetes liveness-probe analogue; analytic).
- **Open loop**: apply the diagnoser's first fix once and trust it (paired with the closed loop's diagnosis).
- **Closed loop**: the real pipeline: validate, retry an alternate fix, escalate after 2 retries (measured with `RETRY_POLICY=repeat`: both retries use the same alternate).

Cells: recovery rate (successes/n) with a 95% Wilson interval.

| Diagnoser | Diagnosis accuracy | Blind restart | Open loop | Closed loop | Needed a retry | Escalated | Closed vs open (McNemar) |
|---|---|---|---|---|---|---|---|
| rule-based | 100.0% (60/60) [94.0%, 100.0%] | 75.0% (45/60) [62.8%, 84.2%] | 100.0% (60/60) [94.0%, 100.0%] | 100.0% (60/60) [94.0%, 100.0%] | 0 | 0 | p = 1.000 (0 open-only, 0 closed-only) |
| gpt-oss-120b | 100.0% (200/200) [98.1%, 100.0%] | 75.0% (150/200) [68.6%, 80.5%] | 86.0% (172/200) [80.5%, 90.1%] | 100.0% (200/200) [98.1%, 100.0%] | 28 | 0 | p < 0.001 (0 open-only, 28 closed-only) |
| gpt-oss-20b | 99.5% (199/200) [97.2%, 99.9%] | 75.0% (150/200) [68.6%, 80.5%] | 99.0% (198/200) [96.4%, 99.7%] | 99.5% (199/200) [97.2%, 99.9%] | 1 | 0 | p = 1.000 (0 open-only, 1 closed-only) |
| qwen3-27b | 99.5% (199/200) [97.2%, 99.9%] | 75.0% (150/200) [68.6%, 80.5%] | 100.0% (200/200) [98.1%, 100.0%] | 100.0% (200/200) [98.1%, 100.0%] | 0 | 0 | p = 1.000 (0 open-only, 0 closed-only) |

## Pooled over all diagnosers

- Blind restart: 75.0% (495/660) [71.6%, 78.2%]
- Open loop: 95.5% (630/660) [93.6%, 96.8%]
- Closed loop: 99.8% (659/660) [99.1%, 100.0%]
- Closed vs blind restart: p < 0.001 (1 blind-only, 165 closed-only)
- Closed vs open loop: p < 0.001 (0 open-only, 29 closed-only)

## By fault type (closed loop / open loop / blind restart)

| Diagnoser | crash | error | memory | slow |
|---|---|---|---|---|
| rule-based | 15/15 / 15/15 / 15/15 | 15/15 / 15/15 / 15/15 | 15/15 / 15/15 / 15/15 | 15/15 / 15/15 / 0/15 |
| gpt-oss-120b | 50/50 / 50/50 / 50/50 | 50/50 / 22/50 / 50/50 | 50/50 / 50/50 / 50/50 | 50/50 / 50/50 / 0/50 |
| gpt-oss-20b | 50/50 / 50/50 / 50/50 | 49/50 / 48/50 / 50/50 | 50/50 / 50/50 / 50/50 | 50/50 / 50/50 / 0/50 |
| qwen3-27b | 50/50 / 50/50 / 50/50 | 50/50 / 50/50 / 50/50 | 50/50 / 50/50 / 50/50 | 50/50 / 50/50 / 0/50 |

## Reading this honestly

- Blind restart is modelled analytically from the simulator's `EFFECTIVE_FIXES` table (a restart does not cure a sustained overload, so it fails the *slow* class). This encodes plausible operations knowledge; it is not a measurement of a real Kubernetes cluster.
- Open and closed loop are scored on the same incidents, and open/closed on the same diagnosis, so the comparisons are paired.
- Where an LLM's *diagnosis* is right but its own chosen *fix* is not effective (the paper's Section 6.1 observation), the closed loop's retry is what recovers it; this table counts those cases.
- Validation wait is shortened to 0.5 s for these runs; it does not change which fixes are effective.
