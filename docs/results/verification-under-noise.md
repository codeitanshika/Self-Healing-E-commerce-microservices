# Does verify-and-retry help when diagnosis is wrong?

Strict healing mode (only effective fixes cure a fault). A diagnoser is forced wrong on a fraction of incidents; the **closed loop** (real pipeline: validate, retry an alternate fix, escalate after 2 retries) is compared with an **open loop** that applies the first fix once and trusts it. Both are scored on the *same* sampled diagnoses (paired). Cells show recovery rate (successes/n) with a 95% Wilson interval.

| Injected diagnosis error | Realised diagnosis accuracy | Open-loop recovery | Closed-loop recovery | Escalated | Mean fix attempts | Paired McNemar |
|---|---|---|---|---|---|---|
| 0% | 100% | 100% (40/40) [91%, 100%] | 100% (40/40) [91%, 100%] | 0 | 1.00 | p = 1.000 (0 vs 0) |
| 25% | 68% | 68% (27/40) [52%, 80%] | 90% (36/40) [77%, 96%] | 4 | 1.43 | p = 0.004 (0 vs 9) |
| 50% | 50% | 57% (23/40) [42%, 71%] | 95% (38/40) [83%, 99%] | 2 | 1.48 | p < 0.001 (0 vs 15) |
| 75% | 28% | 38% (15/40) [24%, 53%] | 85% (34/40) [71%, 93%] | 6 | 1.77 | p < 0.001 (0 vs 19) |

## Headline

- Pooled: closed loop 92% (148/160) [87%, 96%] vs open loop 66% (105/160) [58%, 73%]; paired exact McNemar p < 0.001 (open-only-correct 0, closed-only-correct 43).
- Restricted to the 62 incidents that were *misdiagnosed*: closed loop recovered 81% (50/62) [69%, 89%], open loop 11% (7/62) [6%, 22%].

## Reading this honestly

- The diagnoser's errors are synthetic and uniform over wrong root causes; real LLM errors are correlated with metric patterns, so this shows the *mechanism's* value, not a forecast of production accuracy.
- Retry picks the alternate fix for the (wrong) diagnosed cause, it does not re-diagnose. Some wrong diagnoses therefore remain unrecoverable within the retry budget and escalate; that residual is the honest cost of this simple retry policy and motivates re-diagnosis on failure as future work.
- Whether a fix is 'effective' is defined by the simulator's table (`EFFECTIVE_FIXES`). It encodes plausible operational knowledge, not measured production behaviour.
