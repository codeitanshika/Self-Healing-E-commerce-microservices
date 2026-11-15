# How the system works (mapped to the code)

One sentence: **when a service breaks, five small agents talk over an event bus to detect it, ask an LLM why, apply a fix, check the fix actually worked, retry a different fix if it didn't, and record everything.**

## 1. The big picture

```
 services ──poll──> MONITOR ──ANOMALY_DETECTED──> ORCHESTRATOR
                                                      │ DIAGNOSE_REQUEST
                                                      ▼
                                              DIAGNOSIS (LLM)
                                                      │ DIAGNOSIS_READY
                                                      ▼
                       ┌──────────────────────── ORCHESTRATOR ──FIX_REQUEST──> FIX
                       │                              ▲                         │ FIX_APPLIED
                       │                              │                         ▼
                       │                         VALIDATION_RESULT <──────── VALIDATION
                       │                              │
              RECOVERED / ESCALATED                   └── STILL_BROKEN: retry next fix
                       ▼
                    REPORT ──> SQLite ──> REST + live stream ──> React dashboard
```

Agents never call each other. They publish and subscribe to named events. That is the whole architecture.

## 2. Walking one incident through the code

Say you click **Inject crash into payment**.

| Step | What happens | Where |
|---|---|---|
| 0 | The dashboard POSTs `/api/services/payment/fault/crash`. The route checks the API key and the rate limit. | `backend/main.py` (`inject_fault`), `backend/shared/security.py` |
| 1 | The service object flips to `status="down"`, 100% errors. | `SimulatedService.inject_fault`, `backend/services/simulated_service.py` |
| 2 | The Monitor wakes up on its timer (default 5 s), reads every service's health and compares it with the thresholds. It sees a crash and publishes `ANOMALY_DETECTED`. It remembers the service, so it does not report the same fault again. | `MonitorAgent._check_all_services`, `_detect_anomaly`, `_publish_anomaly` in `agents/monitor_agent.py`; thresholds in `shared/config.py` (`THRESHOLDS`) |
| 3 | The Orchestrator creates an incident record (id, timestamp, stage `diagnosing`) and publishes `DIAGNOSE_REQUEST`. | `Orchestrator.on_anomaly_detected`, `orchestrator/orchestrator.py` |
| 4 | The Diagnosis Agent builds a prompt (metrics, decision priority, allowed answers) and calls Groq. The reply is parsed as JSON: `root_cause`, `confidence`, `fix`, `explanation`, `business_impact`. A truncated or broken reply is retried once, then falls back to a safe default (`unknown` -> restart). It publishes `DIAGNOSIS_READY`. | `DiagnosisAgent._build_prompt` in `agents/diagnosis_agent.py`; `ask_llm`, `parse_json_object` in `shared/llm.py` |
| 5 | The Orchestrator stores the diagnosis and publishes `FIX_REQUEST`. | `Orchestrator.on_diagnosis_ready` |
| 6 | The Fix Agent calls `heal()` on the service. | `FixAgent.apply_fix`, `agents/fix_agent.py` -> `SimulatedService.heal` |
| 7 | The Orchestrator asks for validation. The Validation Agent waits 2 s, then re-reads the **real** health. It never trusts the fix. | `ValidationAgent.validate`, `agents/validation_agent.py` |
| 8a | Healthy -> `RECOVERED`. | `Orchestrator.on_validation_result` |
| 8b | Still broken -> the Orchestrator picks the next fix from `FIX_MAP[root_cause]["retry"]` and loops. After `MAX_RETRIES = 2` it marks the incident `ESCALATED`, the point where a human would be paged. | same function; `FIX_MAP`, `MAX_RETRIES` in `shared/config.py` |
| 9 | The Report Agent writes one row (MTTR, revenue protected, retries) and the stage timeline. Only this agent writes to the database. | `ReportAgent.log_incident`, `log_timeline` in `agents/report_agent.py`; tables in `database/models.py` |
| 10 | Every event above was also broadcast to the browser, so the pipeline view and event feed moved in real time. | `EventBus.publish` + `StreamHub` in `orchestrator/event_bus.py`, `shared/stream.py`; `/api/stream` in `main.py` |

## 3. The pieces

**Event bus** (`orchestrator/event_bus.py`). About 100 lines: a dict of topic -> handlers. `publish` calls every handler concurrently. `subscribe_all` lets *observers* (the live stream) watch every event without being able to break the pipeline. Topic names are constants in `shared/events.py`.

**Simulated services** (`services/`). Each one is an object with response time, error rate, memory and CPU, plus `get_health`, `inject_fault` and `heal`. `ServiceManager` holds them all. If Docker is running, a real Nginx container (`docker_service.py`, `docker-compose.yml`) joins as a sixth service with the same interface, so no agent knows the difference.

**Why one LLM agent.** Four agents are plain deterministic code. Only diagnosis needs reasoning, so only it calls a model.

**Strict healing** (`shared/config.py`: `EFFECTIVE_FIXES`, `strict_healing()`). Off by default: any fix cures any fault (the original behavior). With `STRICT_HEALING=1`, only an effective fix cures a given fault (a restart does not cure an overload). This makes "recovered" depend on the fix chosen, so verify-and-retry can be measured.

**Scenarios** (`fault_injector/scenarios.py`). Scripted multi-fault and cascade incidents, launched with `POST /api/scenarios/{id}/run`.

**Security** (`shared/security.py`). If `API_KEY` is set, mutating endpoints need an `X-API-Key` header. A per-IP rate limit protects public demos.

## 4. The API the dashboard uses (`backend/main.py`)

| Endpoint | Powers |
|---|---|
| `GET /api/services`, `/api/history` | Service cards and sparklines |
| `GET /api/stream` | The live event feed and instant refresh |
| `GET /api/active-incidents` | The healing pipeline stepper |
| `GET /api/incidents`, `/api/incidents/{id}` | Incident table and drawer (with timeline) |
| `GET /api/stats`, `/mttr-chart`, `/revenue-series`, `/breakdown` | KPI strip and charts (`database/queries.py`) |
| `POST /api/services/{n}/fault/{type}`, `/api/scenarios/{id}/run`, `/api/admin/reset?confirm=true` | Fault lab (key + rate-limited) |

## 5. The dashboard (`frontend/src`)

`App.jsx` wires everything. `lib/hooks.js` has `usePolling` (fetch on an interval, and immediately when the stream reports an event) and `useEventStream` (Server-Sent Events). Components: `KpiStrip`, `ServiceGrid`, `PipelineBoard`, `EventFeed`, `FaultLab`, `Charts`, `IncidentTable`, `IncidentDrawer`. All styling is in `index.css`.

## 6. How the research claims are tested (`backend/experiments/`)

| Question | Script | Output |
|---|---|---|
| Is LLM diagnosis accurate, and how fast is recovery? | `run_experiments.py`, `analyze.py` | `docs/results/statistics.md` |
| Where does recovery time go? Does concurrency slow it? | `run_pipeline.py`, `analyze_pipeline.py` | `pipeline-latency.md` |
| Does verify-and-retry help when diagnosis is wrong? | `run_noise.py`, `analyze_noise.py` | `verification-under-noise.md` |
| Closed loop vs blind restart vs open loop, with real LLMs | `run_strategies.py`, `analyze_strategies.py` | `strategy-comparison.md` |
| Figures | `make_figures.py` (+ the analyze scripts) | `docs/results/figures/` |

## 7. Tests

`backend/tests/` (66 tests): event bus, orchestrator retry and escalation, fix map, monitor, API auth and reset, strict healing, LLM client parsing and retry, statistics, and the experiment harness. Run `python -m pytest -q` from `backend/`.
