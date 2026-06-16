# Build Plan (Phase-Based, Self-Paced)

No fixed calendar. Each phase ends with **(a) something that runs** and **(b) a git commit**. Don't start a phase until the previous one runs. If you're in a team, suggested splits are noted, but the plan works solo.

> Golden rule: **every file must run or import without errors before you commit.** A broken `main` branch wastes everyone's time (including future-you).

---

## Phase 0 — Setup (do this once)

**Goal:** an empty but correctly structured repo, tools installed, first commit pushed.

1. Install Python 3.11+, Node.js 18+, VS Code, Git.
2. Create the repo (see `setup-guide.md` for exact VS Code + GitHub steps).
3. Create the folder structure (also in `setup-guide.md`).
4. Set up the Python virtualenv and install backend requirements.
5. Get a free Groq API key from console.groq.com → put it in `backend/.env`.
6. Verify a single Groq call works (the test script in `setup-guide.md`).
7. **Commit:** `chore: initial project structure and tooling`

**Done when:** `uvicorn main:app --reload` starts an empty FastAPI app and a Groq test call prints a reply.

---

## Phase 1 — The 5 Services + Fault Injection

**Goal:** five simulated services that can be broken on demand.

1. Build the `SimulatedService` class (tracks status, cpu, memory, latency, error rate).
2. Build the `ServiceManager` holding all 5: auth(8001), cart(8002), payment(8003), inventory(8004), notification(8005).
3. Expose the endpoint contract on each (see `code-standards.md`):
   - `GET /health` → status + metrics
   - `POST /fault/{mode}` → mode ∈ {none, crash, slow, memory, error}
4. Write `fault_injector/inject.py` so you can break a service from a script too.
5. Test via `/docs`: inject each fault into each service, confirm `/health` reflects it.
6. **Commit:** `feat: 5 simulated services with fault injection`

**Done when:** you can crash/slow/leak/error any service and see it in its health response.
*(Team: Person A → auth+cart, Person B → payment+inventory+injector, Person C → notification.)*

---

## Phase 2 — Event Bus + Monitor Agent

**Goal:** anomaly detection flowing over your own event bus.

1. Write the event bus (`orchestrator/event_bus.py`) — async pub/sub, ~40 lines.
2. Define all event topic names as constants in `shared/events.py` (matches `architecture.md`).
3. Build the Monitor Agent: polls all services every 5s (async httpx), applies threshold rules (latency>2000ms, error_rate>0.3, memory>85%, status==down), publishes `ANOMALY_DETECTED`.
4. Temporarily subscribe a print-function to `ANOMALY_DETECTED` to see detections in the console.
5. Test: inject a fault, watch the anomaly event fire.
6. **Commit:** `feat: event bus and monitor agent with anomaly detection`

**Done when:** breaking a service prints `ANOMALY_DETECTED payment crash` via the event bus.
*(Team: Person C owns this.)*

---

## Phase 3 — The Four Reactive Agents

**Goal:** each agent works, triggered by its event. Build and test them one at a time.

1. **Diagnosis Agent** (the AI one): subscribes `DIAGNOSE_REQUEST`, builds prompt, calls Groq, parses JSON (with the safe-default fallback from `code-standards.md`), publishes `DIAGNOSIS_READY`. Test with 5 hardcoded metric sets first.
2. **Fix Agent:** subscribes `FIX_REQUEST`, maps fix name → remediation function (restart/reduce_load/clear_memory/reroute/retry), publishes `FIX_APPLIED`.
3. **Validation Agent:** subscribes `VALIDATE_REQUEST`, waits ~3s, re-polls, publishes `VALIDATION_RESULT` (RECOVERED/STILL_BROKEN) with MTTR.
4. **Report Agent:** subscribes `VALIDATION_RESULT`, writes the `Incident` row to SQLite.
5. **Commit after each agent:** e.g. `feat: diagnosis agent with groq integration`

**Done when:** each agent, given a hardcoded sample event, does its job correctly in isolation.
*(Team: A→Diagnosis, B→Fix+Validation, D→Report.)*

---

## Phase 4 — Orchestrator + Full Loop + Retry

**Goal:** the whole cycle runs autonomously, including retries.

1. Build the Orchestrator: subscribes `ANOMALY_DETECTED`; sequences DIAGNOSE → FIX → VALIDATE by publishing the request events and reacting to the result events; tracks incident timing.
2. Implement the retry loop: on STILL_BROKEN, pick the next fix in the priority list for that root cause; after 2 failed retries → mark `ESCALATED`.
3. Wire all agents as startup async tasks inside the single FastAPI app.
4. End-to-end test: inject a fault, do nothing, watch the full detect→diagnose→fix→validate→log cycle complete; check the DB row.
5. Force a failure (make first fix a no-op) to confirm retry works.
6. **Commit:** `feat: orchestrator with full closed-loop healing and retry`

**Done when:** breaking any service auto-heals and logs an incident with no human action.
*(Team: A→orchestrator skeleton, B→retry loop, C→wiring.)*

---

## Phase 5 — React Dashboard

**Goal:** the real frontend (replaces the old Streamlit plan).

1. Scaffold React + Vite + Tailwind; add Recharts. (Steps in `setup-guide.md`.)
2. Add backend API endpoints the frontend needs:
   - `GET /api/services` (all health) · `GET /api/incidents` · `GET /api/stats` (avg MTTR, totals) · `GET /api/active-incident` · `POST /api/services/{name}/inject-fault`
3. Build components (design system in `ui-tokens.md`/`ui-rules.md`, mapped to React in `ui-registry.md`):
   - 5 `HealthTile`s · summary `MetricCard` row · `ActiveIncidentBanner` · `IncidentTable` · `MttrChart` · `RevenueChart` · sidebar fault-injection controls
4. Poll the backend every 3–5s (a `usePolling` hook) so it updates live.
5. Empty-state and DOWN-state handling per `ui-rules.md`.
6. **Commit:** `feat: react dashboard with live health, incidents, and charts`

**Done when:** you run backend + frontend, inject a fault from the UI, and watch the whole heal cycle animate in the browser.
*(Team: D leads frontend; others add their agent's data to the relevant API endpoint.)*

---

## Phase 6 — Deploy + Experiments + Paper

**Goal:** live URL, real results, written paper.

1. **Deploy:** backend to Render (free), frontend to Vercel (free). Set `GROQ_API_KEY` and CORS for the deployed frontend origin. (Steps in `setup-guide.md`.)
2. **Experiments:** run 15–20 fault scenarios (mix of 5 services × 5 fault types). For each, record: detection time, whether the LLM named the actually-injected fault (diagnosis accuracy), first-try vs retry, total MTTR.
3. **Analysis:** build the MTTR-vs-baseline table, diagnosis-accuracy %, total revenue protected; generate charts.
4. **Paper:** fill in the outline in `research-paper.md` with your numbers.
5. **Final commit + tag:** `release: v1.0 — full system, deployed, evaluated`

**Done when:** there's a public URL, a results table, and a paper draft.

---

## Commit discipline (applies to every phase)

- Commit in small, working chunks with clear messages (`feat:`, `fix:`, `docs:`, `chore:`).
- Never commit `.env` or `*.db` (the `.gitignore` handles this).
- Push at the end of every working session.
- Tag milestones: `v0.1-services`, `v0.2-agents`, `v1.0-release`.
