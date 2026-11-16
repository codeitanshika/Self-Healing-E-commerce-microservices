# Sensitivity of the strategy comparison to the fix-effectiveness table

The strategy results use a hand-written table saying which fix cures which fault (`EFFECTIVE_FIXES`). Because the closed loop's fix sequence is deterministic given its diagnosis, the recorded incidents can be replayed under other tables without re-querying the LLMs. Replayed incidents: 600 (the three real LLMs; the rule baseline is excluded because it never errs).

## 0. Replay validation

Replaying the original table reproduces the measured closed-loop outcome on **660/660** recorded incidents (all three LLMs and the rule baseline).

## 1. Hand-built alternative tables

| Table | Blind restart | Open loop | Closed loop | Closed - open | Closed - blind |
|---|---|---|---|---|---|
| original (used in all experiments) | 75.0% | 95.0% | 99.8% | +4.8 pp | +24.8 pp |
| strict: exactly one cure per fault | 25.0% | 93.8% | 93.8% | +0.0 pp | +68.8 pp |
| wider: restart also cures slow load | 100.0% | 95.0% | 99.8% | +4.8 pp | -0.2 pp |
| adversarial: restart cures everything | 100.0% | 51.2% | 99.8% | +48.7 pp | -0.2 pp |
| no overlap: restart cures crash only | 25.0% | 93.8% | 93.8% | +0.0 pp | +68.8 pp |

## 2. Random tables

2000 random tables (seed 20260517). For each fault, every one of the 5 fixes is independently effective with probability 0.4 (at least one cure is guaranteed). Same 600 LLM incidents replayed under each table.

| Question | Share of tables |
|---|---|
| Closed loop at least as good as open loop | 100.0% |
| Closed loop strictly better than open loop | 73.0% |
| Closed loop at least as good as blind restart | 82.2% |
| Closed loop strictly better than blind restart | 76.3% |

Closed minus open (percentage points): median +25.0, 5th-95th percentile [+0.0, +68.8].  
Closed minus blind restart: median +24.8, 5th-95th percentile [-0.2, +54.8].

## Reading this honestly

- Closed loop >= open loop holds by construction on every table: the closed loop applies the same first fix, then more. So that comparison cannot flip sign; only its *size* depends on the table.
- Closed loop vs blind restart is the table-dependent claim. If restart cures every fault (the adversarial row), a blind restart is perfect and the closed loop has no advantage over it on recovery rate; the closed loop's remaining value there is diagnosis and an audit trail.
- The replay assumes retries repeat `FIX_MAP[diagnosis]['retry']`, which is how the orchestrator behaves, and ignores timing (MTTR is not re-estimated).
