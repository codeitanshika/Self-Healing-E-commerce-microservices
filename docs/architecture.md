# Architecture

> This supersedes the earlier SAM-based draft. The event-driven design is **identical**; only the transport changed (our own in-process event bus instead of Solace), and the LLM is Groq (free) instead of Anthropic (paid).

## High-Level Flow

```
[5 Simulated Services] --metrics--> [Monitor Agent]
                                         |
                                   ANOMALY_DETECTED
                                         v
                                  [Orchestrator]
                                         |
                                         v
                                 [Diagnosis Agent] --(Groq / Llama 3.3)
                                         |
                                  DIAGNOSIS_READY
                                         v
                                    [Fix Agent]
                                         |
                                    FIX_APPLIED
                                         v
                               [Validation Agent]
                                    /        \
                            RECOVERED      STILL_BROKEN
                                |               |
                                v               v
                          [Report Agent]   [Orchestrator: retry
                                            with next fix,
                                            max 2 retries -> ESCALATED]
                                |
                                v
                           [SQLite DB]
                                |
                                v
                       [React Dashboard]  (reads via REST, polls every 3-5s)
```

All arrows between agents are **events published/subscribed via our own in-process async event bus** (`orchestrator/event_bus.py`). Agents never call each other directly — they only know event topics.

## Communication Plane (Event Topics)

| Event Topic | Published By | Subscribed By | Payload |
|---|---|---|---|
| `ANOMALY_DETECTED` | Monitor Agent | Orchestrator | service, fault_type, metrics, timestamp |
| `DIAGNOSE_REQUEST` | Orchestrator | Diagnosis Agent | service, metrics |
| `DIAGNOSIS_READY` | Diagnosis Agent | Orchestrator | root_cause, confidence, fix, business_impact, explanation |
| `FIX_REQUEST` | Orchestrator | Fix Agent | service, fix |
| `FIX_APPLIED` | Fix Agent | Orchestrator | service, fix_applied, fix_time |
| `VALIDATE_REQUEST` | Orchestrator | Validation Agent | service, detected_at |
| `VALIDATION_RESULT` | Validation Agent | Orchestrator, Report Agent | result (RECOVERED/STILL_BROKEN), mttr |
| `INCIDENT_LOGGED` | Report Agent | (Dashboard reads DB via REST) | — |

## The Event Bus (our SAM replacement)

A minimal async publish/subscribe layer. Conceptually:

```python
# orchestrator/event_bus.py
import asyncio
from collections import defaultdict

class EventBus:
    def __init__(self):
        self._subscribers = defaultdict(list)   # topic -> [async fn]

    def subscribe(self, topic: str, handler):
        self._subscribers[topic].append(handler)

    async def publish(self, topic: str, payload: dict):
        # notify all handlers for this topic concurrently
        await asyncio.gather(*[h(payload) for h in self._subscribers[topic]])

bus = EventBus()   # single shared instance imported by all agents
```

Why this matters for the paper: it gives the system the decoupling and resilience properties of event-driven architecture (independent components, easy to add/remove agents) without any external broker or cost.

## Layers

### 1. Service Layer (Data/Execution Plane)
- 5 simulated services managed inside one FastAPI app, logical ports/names: auth(8001), cart(8002), payment(8003), inventory(8004), notification(8005).
- Each exposes the contract: `GET /health`, `POST /fault/{mode}`.
- Fault modes: `none`, `crash`, `slow`, `memory`, `error`.

> Solo/simple structure (chosen): services are Python objects inside the single FastAPI app, addressed by name, not 5 separate servers. The endpoint contract is still honored via routes like `/api/services/{name}/health`. This keeps it runnable with one command and easy to deploy on one free host.

### 2. Telemetry Layer
- Monitor Agent polls each service's health every 5s.
- Extracts: cpu%, memory%, response_time_ms, error_rate, status.
- Threshold rules flag anomalies (latency>2000ms, error_rate>0.3, memory>85%, status==down).

### 3. Agent / Orchestration Layer (Control Plane)
- Built on our own event bus.
- Orchestrator = central coordinator with retry logic.
- Each agent = an async task subscribing to its topics.

### 4. Intelligence Layer
- Diagnosis Agent calls **Groq (Llama 3.3 70B)** with a structured prompt.
- Returns JSON: root_cause, confidence, fix, business_impact, explanation.

### 5. Persistence Layer
- SQLite via SQLModel.
- Table `Incident`: id, service, root_cause, business_impact, fix_applied, result, mttr_seconds, revenue_protected, timestamp.

### 6. Presentation Layer
- React + Vite dashboard.
- Live health tiles (polls `GET /api/services`).
- Reads incidents/stats via REST for history, MTTR chart, revenue totals.

## Fault → Fix Mapping (used by Fix Agent)

| root_cause | primary fix | retry fix |
|---|---|---|
| service_crash | restart | reduce_load |
| memory_leak | clear_memory | restart |
| cpu_overload | reduce_load | restart |
| high_latency | reroute_traffic | reduce_load |
| error_spike | retry_with_backoff | restart |

## Retry Logic
- Validation = STILL_BROKEN → Orchestrator picks the next fix in the priority list for that root_cause, re-dispatches Fix Agent.
- After 2 failed retries → mark incident `ESCALATED` (would notify a human in production).

## Revenue Calculation (illustrative metric for dashboard)
```
revenue_protected = max(0, MANUAL_BASELINE_SECONDS - actual_mttr_seconds) * revenue_per_second[service]
```
Default `MANUAL_BASELINE_SECONDS = 900` (15 min). `revenue_per_second` is a configurable per-service constant (illustrative, not real data — state this clearly in the paper).
