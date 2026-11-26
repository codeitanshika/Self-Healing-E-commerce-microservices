# Code Standards

## General
- Python: follow PEP 8. CI runs Python 3.13; `requirements-dev.txt` needs 3.12 or newer.
- Event handlers are `async def`. Run blocking work (the Groq client, Docker calls) in a worker thread with `asyncio.to_thread`.
- No hard-coded secrets: use environment variables, loaded from `backend/.env`.
- Constants (limits, fix tables, rates, service list) belong in `shared/config.py`.

## Naming
- Files: `snake_case.py`, React components `PascalCase.jsx`.
- Classes `PascalCase`; Python functions and variables `snake_case`; JavaScript `camelCase`.
- Event topics: `UPPER_SNAKE_CASE` constants in `shared/events.py`. Never type a topic as a bare string.

## Folder structure
```
backend/
  agents/          monitor, diagnosis, fix, validation, report, rule_based_diagnosis
  orchestrator/    event_bus.py, orchestrator.py
  services/        simulated_service, docker_service, service_manager
  shared/          config, events, llm, stream, security
  database/        models, queries (read only), admin (reset)
  fault_injector/  scenarios.py
  experiments/     runners, analysis, figures, raw CSV results
  tests/           pytest suite
  main.py          FastAPI app and routes
frontend/src/      App.jsx, components/, lib/
docs/
```

## Service interface
Every service, simulated or real, provides:
```
get_health()            -> {status: "ok"|"degraded"|"down", service, cpu, memory, response_time_ms, error_rate, active_fault, ...}
inject_fault(fault)     fault in {crash, slow, memory, error}; an "error" key reports refusal
heal(fix_type)          applies a fix
```
Agents go through `ServiceManager` and never depend on the concrete class.

## Events
- Agents communicate through the bus only; they do not call each other.
- Incident events carry `service` and `incident_id`. The topic list and payloads are in [architecture.md](architecture.md).
- The one shared object is the Orchestrator's `incident_cache`, read by the Report Agent.
- Observers (`subscribe_all`) must never affect the pipeline.
- A handler that listens to a topic it also publishes must guard against reacting to itself.

## LLM access
- All calls go through `ask_llm` in `shared/llm.py`: model from `GROQ_MODEL`, temperature 0.2, up to 1500 tokens, one retry, then a safe default.
- Only the Diagnosis Agent calls the model.
- The model chooses a fix name; it never runs commands. Unknown fix names are executed as `restart`.

## Database
- Only the Report Agent inserts rows. `database/queries.py` reads; `database/admin.py` deletes for the demo reset.
- Only final results (`RECOVERED`, `ESCALATED`) are stored.

## Logging
Agents print with a class prefix:
```
[FixAgent] payment: applying fix 'restart'
```

## Tests and checks
```bash
cd backend && python -m pytest -q
cd frontend && npm run lint && npm run build
```
- Tests must run without a network, an API key or Docker (`tests/conftest.py` enforces the last).
- Add a test with each behaviour change.
- Some agent files have an `if __name__ == "__main__":` demo. The diagnosis demo calls Groq, and the report demo writes sample rows into your local database.

## Experiments
Runners overwrite the CSV files that the published results come from. Commit or restore them deliberately.

## Git workflow
- Work on a branch, open a pull request, merge into `main` when CI passes. `main` is what gets deployed.
- Commit messages start with `feat:`, `fix:`, `docs:`, `chore:`, `test:` or `ci:`.
- Never commit `.env` or `*.db`.
