# Progress Tracker

Update checkboxes as you go. Each phase ends with a runnable result + a git commit. Self-paced — no dates.

---

## Phase 0 — Setup
- [ ] Python 3.11+, Node 18+, VS Code, Git installed
- [ ] Repo created, folder structure in place, `.gitignore` added
- [ ] Backend virtualenv + requirements installed
- [ ] Groq API key in `.env`; `test_groq.py` printed a reply
- [ ] First commit pushed to GitHub

**Notes / blockers:**

---

## Phase 1 — Services + Fault Injection
- [ ] `SimulatedService` class done
- [ ] `ServiceManager` with all 5 services
- [ ] Endpoint contract (`/health`, `/fault/{mode}`) working for all 5
- [ ] `inject.py` can break any service
- [ ] Verified each fault type via `/docs`
- [ ] Commit: `feat: 5 simulated services with fault injection`

**Notes / blockers:**

---

## Phase 2 — Event Bus + Monitor
- [ ] `event_bus.py` (async pub/sub) done
- [ ] Event topic constants in `shared/events.py`
- [ ] Monitor Agent polls all services, applies thresholds
- [ ] `ANOMALY_DETECTED` fires on the bus (seen in console)
- [ ] Commit: `feat: event bus and monitor agent`

**Notes / blockers:**

---

## Phase 3 — The Four Reactive Agents
- [ ] Diagnosis Agent returns valid JSON for 5 test scenarios (Groq)
- [ ] Fix Agent — all 5 fix types implemented + tested
- [ ] Validation Agent returns RECOVERED/STILL_BROKEN correctly
- [ ] Report Agent writes to SQLite correctly
- [ ] Commit after each agent

**Notes / blockers:**

---

## Phase 4 — Orchestrator + Full Loop
- [ ] Orchestrator sequences DIAGNOSE → FIX → VALIDATE
- [ ] Retry loop works (forced-failure test confirms retry)
- [ ] ESCALATED path works after 2 retries
- [ ] All agents run as startup async tasks in one app
- [ ] End-to-end: inject fault → auto-heal → DB row, no human action
- [ ] Commit: `feat: orchestrator with closed-loop healing and retry`

**Notes / blockers:**

---

## Phase 5 — React Dashboard
- [ ] React + Vite + Tailwind + Recharts scaffolded
- [ ] Backend API endpoints (`/api/services`, `/api/incidents`, `/api/stats`, `/api/active-incident`, inject)
- [ ] Health tiles (×5) live
- [ ] Summary metric cards
- [ ] Active incident banner (stage updates)
- [ ] Incident history table
- [ ] MTTR chart + revenue chart
- [ ] Sidebar fault-injection controls
- [ ] Polling auto-refresh works
- [ ] Commit: `feat: react dashboard`

**Notes / blockers:**

---

## Phase 6 — Deploy + Experiments + Paper
- [ ] Backend deployed to Render (env vars + CORS set)
- [ ] Frontend deployed to Vercel (VITE_API_URL set)
- [ ] Live URL works end to end
- [ ] 15–20 experiments run (×3 each), results in CSV (`docs/results/`)
- [ ] MTTR table + diagnosis accuracy + revenue total computed
- [ ] Charts generated
- [ ] Paper sections drafted (Abstract → Conclusion)
- [ ] Slides + demo script + backup video
- [ ] Final commit + tag `v1.0-release`

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
