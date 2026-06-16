# Code Standards

> Supersedes the earlier draft. Changes: Groq replaces Anthropic; our own event bus replaces SAM; React replaces Streamlit; single FastAPI app structure.

## General
- Python 3.11+, follow PEP8 (use `black` if available).
- All agent I/O (HTTP calls, event handlers) uses `async def` + `await` — no blocking calls inside agents.
- No hardcoded secrets — load from `.env` via `python-dotenv`.
- Every file must import/run without errors before you commit.

## Naming Conventions
- Files: `snake_case.py` (Python), `PascalCase.jsx` (React components).
- Classes: `PascalCase` (`DiagnosisAgent`, `Incident`).
- Functions/variables: `snake_case` (Python), `camelCase` (JS).
- Event topic names: `UPPER_SNAKE_CASE` constants in `shared/events.py`.
- Service names/logical ports: auth=8001, cart=8002, payment=8003, inventory=8004, notification=8005.

## Folder Structure
```
self-healing-ecommerce/
├── backend/
│   ├── services/        # simulated_service.py, service_manager.py
│   ├── agents/          # monitor, diagnosis, fix, validation, report
│   ├── orchestrator/    # event_bus.py, orchestrator.py
│   ├── shared/          # config.py, models.py, events.py, llm.py
│   ├── database/        # db.py  (incidents.db auto-created, NOT committed)
│   ├── fault_injector/  # inject.py
│   ├── main.py
│   ├── requirements.txt
│   └── .env / .env.example
├── frontend/            # React + Vite
│   └── src/{components,hooks,App.jsx}
├── docs/
└── README.md
```

## Service Endpoint Contract
Exposed via the FastAPI app (single-app structure, addressed by name):
```
GET  /api/services/{name}/health
  -> { "status": "ok"|"degraded"|"down", "service": str,
       "cpu": float, "memory": float,
       "response_time_ms": int, "error_rate": float }

POST /api/services/{name}/fault/{mode}
  mode in {none, crash, slow, memory, error}
  -> { "fault_set": mode }
```
Any new service MUST honor this shape or the Monitor Agent breaks.

## Event Payload Contract
Every event payload is a JSON-serializable dict and MUST include:
- `service`: str
- `timestamp`: float (unix time)

Diagnosis Agent output MUST be valid JSON:
```json
{
  "root_cause": "service_crash|memory_leak|cpu_overload|high_latency|error_spike",
  "confidence": 0-100,
  "fix": "restart|reduce_load|clear_memory|reroute_traffic|retry_with_backoff",
  "business_impact": "string",
  "explanation": "string"
}
```
If the LLM returns invalid JSON, the Diagnosis Agent catches it, logs it, and defaults to `{"root_cause": "unknown", "fix": "restart", "confidence": 0, ...}`.

## LLM Access (Groq, free)
- All LLM calls go through one helper in `shared/llm.py` (the `ask_llm` function from setup-guide.md).
- Model from env (`GROQ_MODEL`), `temperature=0.2` for consistent JSON.
- Never call the LLM from anywhere except the Diagnosis Agent.

## Database Rule
Only the Report Agent writes to `incidents.db`. The dashboard (via REST) only reads. Avoids write conflicts.

## Logging
Every agent prints one line per event handled:
```
[AGENT_NAME] <event received> -> <action taken>
```
Example: `[FIX_AGENT] payment:memory_leak -> applying clear_memory`

## Testing Before Integration
Each agent must run in isolation with a hardcoded sample event before wiring to the event bus. Include an `if __name__ == "__main__":` block with a sample payload.

## Git Workflow
- Solo: commit per working chunk on `main`, push every session.
- Team: branch per person (`feat/diagnosis-agent`), merge to `main` only when it runs standalone.
- Never commit `.env` or `*.db`.
- Tag milestones (`v0.1-services`, `v1.0-release`).
