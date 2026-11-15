# Strategy comparison, run 1 (before the LLM-client and fallback fixes)

Kept for provenance. This run exposed two defects that run 2 fixes:

1. `shared/llm.py` used `max_tokens=400`, which truncated reasoning-model answers mid-JSON
   (12 of 60 gpt-oss-20b diagnoses fell back to `unknown`).
2. `FIX_MAP["unknown"]` retried `restart` after `restart`, so a failed diagnosis could never
   recover from a slow fault (5 incidents escalated).

It also measured a real, separate effect: gpt-oss-120b diagnosed every fault correctly but chose
`reduce_load` for error spikes, which does not cure them; the closed loop's retry recovered all 7.
