# Architecture

An event-driven control plane: five agents and an orchestrator exchange events over an in-process asynchronous bus. The LLM (Groq, free tier) is used by one agent only, for diagnosis.

## High-level flow

```
 [5 simulated services + optional real Nginx]
        ^ polls            ^ repairs         ^ rechecks
        |                  |                 |
   [Monitor] ──ANOMALY_DETECTED──> [Orchestrator]
                                        |  DIAGNOSE_REQUEST
                                        v
                                   [Diagnosis] ── Groq LLM
                                        |  DIAGNOSIS_READY
                                        v
                                   [Orchestrator] ──FIX_REQUEST──> [Fix]
                                        ^                            | FIX_APPLIED
                                        |                            v
                                        |                       [Orchestrator]
                                        |                            | VALIDATE_REQUEST
                                        |                            v
                                        └──── VALIDATION_RESULT ─ [Validation]
                                              STILL_BROKEN: next fix, at most 2 retries
                                              RECOVERED / ESCALATED
                                                     v
                                                 [Report] ──> SQLite ──> REST + SSE ──> React dashboard
```

Agents never call each other. They publish and subscribe to named events (`orchestrator/event_bus.py`). One piece of state is shared: the Orchestrator's `incident_cache`, which the Report Agent reads to assemble the stored row.

## Event topics

Topic names are constants in `shared/events.py`.

| Topic | Published by | Subscribed by | Payload |
|---|---|---|---|
| `ANOMALY_DETECTED` | Monitor | Orchestrator | service, fault_type, metrics, timestamp |
| `DIAGNOSE_REQUEST` | Orchestrator | Diagnosis | service, metrics, incident_id |
| `DIAGNOSIS_READY` | Diagnosis | Orchestrator | service, incident_id, root_cause, confidence, fix, business_impact, explanation |
| `FIX_REQUEST` | Orchestrator | Fix | service, fix, incident_id |
| `FIX_APPLIED` | Fix | Orchestrator | service, incident_id, fix_applied, fix_time, success |
| `VALIDATE_REQUEST` | Orchestrator | Validation | service, incident_id, detected_at |
| `VALIDATION_RESULT` | Validation (`ESCALATED`: Orchestrator) | Orchestrator, Report | service, incident_id, result, mttr_seconds |
| `INCIDENT_LOGGED` | Report | none (observed by the live stream) | incident_db_id, service, result, mttr_seconds |

## The event bus

The core of `publish`:

```python
async def publish(self, topic: str, payload: dict):
    for observer in list(self._wildcard):      # live-stream observers
        try:
            await observer(topic, payload)
        except Exception as exc:
            print(f"[EventBus] observer error ignored: {exc}")
    handlers = self._subscribers.get(topic, [])
    await asyncio.gather(*[handler(payload) for handler in handlers])
```

Wildcard observers see every event and cannot break the pipeline. The bus runs in one process and has no persistence or delivery guarantees, so it is not a substitute for a message broker at scale.

## Layers

### 1. Service layer
- Five simulated services in one FastAPI app: auth, cart, payment, inventory, notification. Each is a Python object (`services/simulated_service.py`) with `get_health`, `inject_fault` and `heal`.
- If a Docker daemon answers at startup, a real Nginx container joins as a sixth service with the same interface (`services/docker_service.py`). It supports the `crash` fault only, and every fix restarts the container.
- Fault types: `crash`, `slow`, `memory`, `error`.

### 2. Telemetry layer
- The Monitor polls every service every 5 s (`MONITOR_POLL_INTERVAL`) and keeps the last 120 samples per service.
- Anomaly rules, checked in this order: status is `down`; response time over 2000 ms; error rate over 0.3; memory over 85%.

### 3. Control layer
- The Orchestrator tracks each incident's stage and timeline, picks retry fixes and escalates.
- Incidents found in the same poll are handled concurrently.

### 4. Intelligence layer
- The Diagnosis Agent calls Groq (`openai/gpt-oss-120b` by default, set with `GROQ_MODEL`) with a structured prompt and expects JSON: `root_cause`, `confidence`, `fix`, `business_impact`, `explanation`.
- A failed call or unparseable reply is retried once, then replaced by a safe default (`unknown`, `restart`).
- `agents/rule_based_diagnosis.py` is the rule-based comparison used by the experiments.

### 5. Persistence layer
SQLite through SQLModel. Only the Report Agent inserts rows. The dashboard reads them, and the demo reset deletes them.

| Table | Columns |
|---|---|
| `Incident` | id, service, fault_type, root_cause, confidence, business_impact, explanation, fix_applied, retry_count, result, mttr_seconds, revenue_protected, timestamp |
| `IncidentStage` | id, incident_db_id, stage, ts, detail |

### 6. Presentation layer
- React + Vite dashboard: key figures, service cards, healing pipeline, event feed, fault lab, charts, incident table and detail panel.
- Data arrives by polling the REST API, plus Server-Sent Events from `/api/stream` for the feed and immediate refreshes.

### Access control
If `API_KEY` is set, the fault, scenario, heal and reset endpoints require an `X-API-Key` header. Those endpoints are rate limited per IP. There are no user accounts, and read endpoints are open.

## Faults and fixes

Under strict healing (the default), a fix cures a fault only if it is listed here (`EFFECTIVE_FIXES`). `STRICT_HEALING=0` lets any fix cure any fault.

| Fault | Effective fixes |
|---|---|
| crash | restart |
| memory | clear_memory, restart |
| slow | reduce_load, reroute_traffic |
| error | retry_with_backoff, restart |

The first fix is the one the diagnosis returns. `FIX_MAP` supplies the retry order:

| root_cause | primary fix | retry fix |
|---|---|---|
| service_crash | restart | reduce_load |
| memory_leak | clear_memory | restart |
| cpu_overload | reduce_load | restart |
| high_latency | reroute_traffic | reduce_load |
| error_spike | retry_with_backoff | restart |
| unknown | restart | reduce_load |

## Retry logic
- On `STILL_BROKEN` the Orchestrator picks a fix not yet tried on this incident: the table's retry fix first, then its primary, then any remaining fix. `RETRY_POLICY=repeat` reuses the retry fix every time.
- After 2 failed retries the incident is marked `ESCALATED`. No notification is sent.

## Revenue figure (illustrative)
```
revenue_protected = max(0, 900 - mttr_seconds) * revenue_per_second[service]    (recovered incidents only)
```
900 s is the assumed manual response time (`MANUAL_BASELINE_SECONDS`). The per-service rates are made-up constants.

## Known limitations
- The Monitor waits for the current batch of incidents to finish before polling again, so a fault that appears during healing is detected late.
- A reply that is valid JSON but lacks an expected field is not caught, and that incident stays open.
- Open incidents and metric history are held in memory and lost on restart.
