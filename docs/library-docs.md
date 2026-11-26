# Library Notes

How this project uses its libraries. Versions are pinned in `backend/requirements.txt`, `backend/requirements-dev.txt` and `frontend/package.json`.

## FastAPI and Uvicorn
Routes are in `backend/main.py`. Run from `backend/`:
```bash
uvicorn main:app --reload --reload-exclude "*.db" --port 8000
```
The exclude stops database writes from restarting the server. Protected routes use dependencies:
```python
@app.post("/api/services/{name}/fault/{fault_type}",
          dependencies=[Depends(require_api_key), Depends(rate_limit)])
def inject_fault(name: str, fault_type: str):
    ...
```
Background work (the Monitor, delayed scenario steps) is started with `asyncio.create_task` or `BackgroundTasks`. Live updates use `StreamingResponse` with `text/event-stream`.

## Groq and python-dotenv
Used in `shared/llm.py` only.
```python
response = await asyncio.to_thread(
    client.chat.completions.create,
    model=current_model(),            # GROQ_MODEL, default openai/gpt-oss-120b
    messages=[{"role": "user", "content": prompt}],
    max_tokens=1500,
    temperature=0.2,
)
```
- The client is synchronous, so it runs in a worker thread.
- Reasoning models spend tokens before answering: a small limit cuts the JSON off.
- Parse with `parse_json_object`, which tolerates code fences and surrounding text.
- Groq retires model IDs from time to time. Change `GROQ_MODEL`, not the code.

## SQLModel (SQLite)
Tables are in `database/models.py`; the file is `backend/database/incidents.db`.
```python
with Session(engine) as session:
    rows = session.exec(select(Incident).order_by(Incident.timestamp.desc()).limit(50)).all()
```
`init_db()` creates missing tables and does not alter existing ones. Adding a column to a table needs a migration or a fresh database, which is why the timeline has its own table.

## Event bus (our own)
`orchestrator/event_bus.py`, one shared instance:
```python
from orchestrator.event_bus import bus
from shared.events import FIX_REQUEST

bus.subscribe(FIX_REQUEST, handler)          # async handler(payload)
bus.subscribe_all(observer)                  # async observer(topic, payload)
await bus.publish(FIX_REQUEST, {"service": "cart", "fix": "restart", "incident_id": "a1b2c3d4"})
```
`publish` returns after every subscribed handler has finished, so a chain of events runs to completion inside the first call.

## Docker SDK and httpx
`services/docker_service.py` stops and restarts the Nginx container, reads `docker stats`, and probes it with a 1.5 s HTTP timeout. Without a Docker daemon the service is not registered.

## Analysis: SciPy, NumPy, Matplotlib
Used by `backend/experiments/` only (development requirements). Statistics helpers are in `stats_utils.py`; figure styling is in `make_figures.py`.

## pytest
`python -m pytest -q` from `backend/`. `tests/conftest.py` clears the event bus between tests and disables Docker.

## React and Vite
React 19 function components. Scripts, from `frontend/`:

| Command | Does |
|---|---|
| `npm run dev` | development server on port 5173 |
| `npm run build` | production build in `dist/` |
| `npm run lint` | ESLint |
| `npm run preview` | serves the build |

Environment variables are read at build time through `import.meta.env`: `VITE_API_URL`, `VITE_API_KEY`.

## Recharts
Charts sit in `components/Charts.jsx` inside `ResponsiveContainer`, loaded with `React.lazy` so the library does not delay the first paint.

## Styling
Hand-written CSS in `src/index.css`; see [ui-tokens.md](ui-tokens.md). No CSS framework.
