# Progress Tracker

Update checkboxes as you go. Each phase ends with a runnable result + a git commit. Self-paced — no dates.

> Checkboxes below were verified against the actual repo state (code, commit history, deployment configs, and experiment outputs) on 2026-09-14, not just self-reported.

---

## Phase 0 — Setup
- [x] Python 3.11+, Node 18+, VS Code, Git installed
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
- [x] Any service can be broken on demand — via the `POST /api/services/{name}/fault/{fault_type}` route (there's no separate `inject.py` script; `backend/fault_injector/` is currently just a placeholder package)
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
- [x] All agents run in one app on startup — Monitor runs as an explicit background `asyncio` task; Diagnosis/Fix/Validation/Report are event-driven (subscribed to the bus) rather than separate polling tasks, which is the intended pub/sub design
- [x] End-to-end: inject fault → auto-heal → DB row, no human action
- [x] Commit: `added The Orchestrator`

**Notes / blockers:**

---

## Phase 5 — React Dashboard
- [x] React + Vite + Recharts scaffolded (React-Bootstrap used for layout/components instead of Tailwind)
- [x] Backend API endpoints (`/api/services`, `/api/incidents`, `/api/stats`, `/api/mttr-chart`, `/api/active-incident`, fault-inject) live
- [x] Health tiles (×5) live
- [x] Summary metric cards (avg MTTR, baseline, revenue protected, incidents resolved)
- [ ] Active incident banner (stage updates) — `GET /api/active-incident` exists on the backend but isn't wired into `App.jsx` yet
- [x] Incident history table (includes per-incident revenue protected)
- [x] MTTR chart (Recharts bar chart by fault type)
- [ ] Cumulative revenue chart — revenue is currently shown as a stats-card total and a table column only, not a standalone chart
- [x] Fault-injection demo controls (inline panel with service/fault-type selectors — not a sidebar)
- [x] Polling auto-refresh works (`usePolling` hook, 3–5s intervals)
- [x] Commit: `React dashboard with live health tiles, incident table, MTTR chart`

**Notes / blockers:** Active-incident banner and a dedicated revenue chart are the two dashboard items from the original plan that never got built.

---

## Phase 6 — Deploy + Experiments + Paper
- [x] Backend deployed to Render (`render.yaml`, `Procfile`, `runtime.txt` present; CORS reads `ALLOWED_ORIGINS` env var)
- [x] Frontend deployed to Vercel (`vercel.json` present)
- [x] Live URL works end to end (see README Live Demo section and its noted free-tier caveats)
- [x] Experiments run (×3 each) — exceeded original scope: 20 scenarios × 3 trials × **3 models** = 180 trials, not just one model. Results in `backend/experiments/*.csv` and `docs/results/`
- [x] MTTR table + diagnosis accuracy computed (`backend/experiments/findings.md`, `docs/results/model-comparison.md`); revenue total shown live on the dashboard
- [ ] Charts generated for the paper — the dashboard has a live MTTR chart, but no chart images were found under `docs/results/`; the written findings are tabular only
- [x] Paper sections drafted, Abstract → Conclusion → References (`docs/paper.md`, 601 lines, kept out of version control until publication — see `.gitignore`)
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
