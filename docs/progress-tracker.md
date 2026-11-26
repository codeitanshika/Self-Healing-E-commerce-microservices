# Progress Tracker

Each phase ends with a runnable result and a commit.

> Checkboxes were verified against the repository (code, commit history, deployment configs and experiment outputs) on 2026-11-26.

---

## Phase 0 — Setup
- [x] Python 3.12+, Node 20.19+, VS Code, Git installed
- [x] Repo created, folder structure in place, `.gitignore` added
- [x] Backend virtualenv + requirements installed
- [x] Groq API key in `.env`; `test_groq.py` printed a reply
- [x] First commit pushed to GitHub

## Phase 1 — Services + Fault Injection
- [x] `SimulatedService` class
- [x] `ServiceManager` with all 5 services
- [x] Endpoints `/api/services/{name}` and `/api/services/{name}/fault/{type}` working for all 5
- [x] Any service can be broken on demand; multi-fault and cascade scenarios in `backend/fault_injector/scenarios.py`
- [x] All 4 fault types (`crash`, `slow`, `memory`, `error`) exercised by the experiment suite
- [x] Optional real Nginx container as a sixth service

## Phase 2 — Event Bus + Monitor
- [x] Async publish/subscribe event bus, with wildcard observers
- [x] Event topic constants in `shared/events.py`
- [x] Monitor Agent polls all services and applies thresholds
- [x] `ANOMALY_DETECTED` fires on the bus

## Phase 3 — The Four Reactive Agents
- [x] Diagnosis Agent returns JSON, exercised in the experiment suite
- [x] Fix Agent implements all 5 fix types
- [x] Validation Agent returns RECOVERED / STILL_BROKEN
- [x] Report Agent writes incidents and timelines to SQLite

## Phase 4 — Orchestrator + Full Loop
- [x] Orchestrator sequences diagnose → fix → validate
- [x] Retry loop and escalation after 2 retries (see [retry-loop-test.md](results/retry-loop-test.md), including a feedback-loop bug found and fixed)
- [x] Each retry uses a fix not yet tried; only effective fixes cure a fault (both configurable)
- [x] End to end: inject a fault, auto-heal, database row, no human action

## Phase 5 — React Dashboard
- [x] React + Vite + Recharts, hand-written CSS
- [x] Dashboard API endpoints
- [x] Service cards, key figures, healing pipeline, event-bus feed
- [x] Charts with table views, incident table and detail panel
- [x] Fault lab (single faults, scenarios, demo reset)
- [x] Live updates (Server-Sent Events with polling fallback)

## Phase 6 — Deploy + Experiments
- [x] Backend deployed to Render
- [x] Dashboard deployed to Vercel
- [x] Redesigned version merged into `main`; the live dashboard and API serve it
- [ ] Confirm `API_KEY` on Render and `VITE_API_KEY` on Vercel are set
- [x] Diagnosis benchmark: 20 scenarios × 3 trials × 3 models = 180 trials
- [x] Pipeline latency, noisy-diagnosis, strategy-comparison and sensitivity experiments
- [x] Real Nginx container run
- [x] Figures and statistics in [`docs/results/`](results/)
- [x] [Demo guide](demo-guide.md)
- [ ] Slides and backup demo video
- [ ] Tag `v1.0-release`

---

## Known limitations and next fixes
- [ ] The Monitor pauses polling while incidents are being healed, so a new fault is detected late
- [ ] LLM replies are not checked for missing or invalid fields
- [ ] Strategy and noise experiments used `RETRY_POLICY=repeat`; re-run them with the current `distinct` policy
- [ ] Escalation does not notify anyone
