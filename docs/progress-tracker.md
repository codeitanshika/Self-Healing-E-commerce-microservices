# Progress Tracker

Update checkboxes as you go. Each phase ends with a runnable result + a git commit. Self-paced — no dates.

> Checkboxes below were verified against the actual repo state (code, commit history, deployment configs, and experiment outputs) on 2026-11-26, not just self-reported.

---

## Phase 0 — Setup
- [x] Python 3.12+, Node 20.19+, VS Code, Git installed
- [x] Repo created, folder structure in place, `.gitignore` added
- [x] Backend virtualenv + requirements installed
- [x] Groq API key in `.env`; `test_groq.py` printed a reply
- [x] First commit pushed to GitHub

**Notes / blockers:**

---

## Phase 1 — Services + Fault Injection
- [x] `SimulatedService` class done
- [x] `ServiceManager` with all 5 services
- [x] Endpoint contract (`/api/services/{name}`, `/api/services/{name}/fault/{type}`) working for all 5
- [x] Any service can be broken on demand — via the `POST /api/services/{name}/fault/{fault_type}` route (multi-fault and cascade scenarios live in `backend/fault_injector/scenarios.py`)
- [x] Verified each fault type — all 4 (`crash`, `slow`, `memory`, `error`) exercised repeatedly via the experiment suite (`backend/experiments/findings.md`)
- [x] Commit: `created services & config`

**Notes / blockers:**

---

## Phase 2 — Event Bus + Monitor
- [x] `event_bus.py` (async pub/sub) done
- [x] Event topic constants in `shared/events.py`
- [x] Monitor Agent polls all services, applies thresholds
- [x] `ANOMALY_DETECTED` fires on the bus (seen in console)
- [x] Commit: `event bus and monitor agent with anomaly detection`

**Notes / blockers:**

---

## Phase 3 — The Four Reactive Agents
- [x] Diagnosis Agent returns valid JSON — verified far beyond 5 scenarios (180 trials across the experiment suite)
- [x] Fix Agent — all 5 fix types implemented (`restart`, `clear_memory`, `reduce_load`, `reroute_traffic`, `retry_with_backoff`) and exercised
- [x] Validation Agent returns RECOVERED/STILL_BROKEN correctly (confirmed in `docs/results/retry-loop-test.md`)
- [x] Report Agent writes to SQLite correctly
- [x] Commit after each agent

**Notes / blockers:**

---

## Phase 4 — Orchestrator + Full Loop
- [x] Orchestrator sequences DIAGNOSE → FIX → VALIDATE
- [x] Retry loop works (forced-failure test confirms retry — see `docs/results/retry-loop-test.md`, including a self-triggered feedback-loop bug that was found and fixed)
- [x] ESCALATED path works after 2 retries
- [x] Each retry uses a fix not yet tried; only effective fixes cure a fault (both configurable)
- [x] All agents run in one app on startup — Monitor runs as an explicit background `asyncio` task; Diagnosis/Fix/Validation/Report are event-driven (subscribed to the bus) rather than separate polling tasks, which is the intended pub/sub design
- [x] End-to-end: inject fault → auto-heal → DB row, no human action
- [x] Commit: `added The Orchestrator`

**Notes / blockers:**

---

## Phase 5 — React Dashboard
- [x] React + Vite + Recharts scaffolded (hand-written CSS design system)
- [x] Backend API endpoints (`/api/services`, `/api/incidents`, `/api/stats`, `/api/mttr-chart`, `/api/active-incident`, fault-inject) live
- [x] Health tiles (×5) live
- [x] Summary metric cards (avg MTTR, baseline, revenue protected, incidents resolved)
- [x] Live incident pipeline with stage updates (`PipelineBoard`, `/api/active-incidents`) and event-bus feed
- [x] Incident history table (includes per-incident revenue protected)
- [x] MTTR chart (Recharts bar chart by fault type)
- [x] Cumulative revenue chart
- [x] Fault lab (single faults, scenarios, demo reset)
- [x] Live updates (Server-Sent Events with polling fallback)
- [x] Commit: `React dashboard with live health tiles, incident table, MTTR chart`

**Notes / blockers:** The dashboard redesign is on `v2-overhaul`; the live site runs `main` until it is merged.

---

## Phase 6 — Deploy + Experiments + Paper
- [x] Backend deployed to Render (`render.yaml`, `Procfile`, `runtime.txt` present; CORS reads `ALLOWED_ORIGINS` env var)
- [x] Frontend deployed to Vercel (`vercel.json` present)
- [ ] Live URL runs the current version (merge `v2-overhaul` into `main`, then set `API_KEY` on Render and `VITE_API_KEY` on Vercel)
- [x] Experiments run (×3 each) — exceeded original scope: 20 scenarios × 3 trials × **3 models** = 180 trials, not just one model. Results in `backend/experiments/*.csv` and `docs/results/`
- [x] MTTR table + diagnosis accuracy computed (`backend/experiments/findings.md`, `docs/results/model-comparison.md`); revenue total shown live on the dashboard
- [x] Charts generated (`docs/results/figures/`, PNG and PDF)
- [x] Pipeline latency, noisy-diagnosis, strategy-comparison and sensitivity experiments; real Nginx container run
- [ ] Research paper: to be drafted after the project is complete (kept off GitHub)
- [ ] Slides + demo script + backup video
- [ ] Final commit + tag `v1.0-release` (no tag exists yet — `git tag` is currently empty)

**Notes / blockers:**

---

## Viva questions to prep (answers in research-paper.md)
1. Why an event bus instead of direct calls?
2. Why not Solace Agent Mesh?
3. How is this different from Kubernetes self-healing?
4. How is it different from RCAgent / OpenRCA?
5. What happens if the LLM diagnosis is wrong?
6. Retry limit and escalation?
7. Is the 900s manual baseline realistic?
8. Production-ready? What's missing?
9. What does it cost to run?
10. How does it scale?
