# Library Docs — Quick Reference

> Updated for the free + React stack. Anthropic → Groq. Streamlit → React/Recharts. Solace → our own event bus.

---

## FastAPI + Uvicorn
**Install:** `pip install fastapi "uvicorn[standard]"`
**Run:** `uvicorn main:app --reload --port 8000`
```python
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/services/{name}/health")
async def health(name: str):
    return {"status": "ok", "service": name}
```

---

## httpx (async HTTP — used by Monitor/Validation agents)
**Install:** `pip install httpx`
```python
import httpx, asyncio

async def check(url):
    async with httpx.AsyncClient(timeout=3.0) as client:
        r = await client.get(url)
        return r.json()

async def check_all(urls):
    return await asyncio.gather(*[check(u) for u in urls])
```

---

## psutil (real CPU/memory readings, optional realism)
**Install:** `pip install psutil`
```python
import psutil
cpu = psutil.cpu_percent(interval=0.1)   # 0-100
mem = psutil.virtual_memory().percent    # 0-100
```

---

## Groq (free LLM — replaces paid Anthropic)
**Install:** `pip install groq python-dotenv`
**.env:** `GROQ_API_KEY=...` and `GROQ_MODEL=llama-3.3-70b-versatile`
```python
import os, json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

resp = client.chat.completions.create(
    model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    max_tokens=400, temperature=0.2,
    messages=[{"role": "user", "content": 'Reply ONLY with JSON: {"ok": true}'}],
)
text = resp.choices[0].message.content
result = json.loads(text.replace("```json","").replace("```","").strip())
```
**Tip:** always wrap `json.loads()` in try/except — LLMs occasionally add stray text.

---

## SQLModel (SQLite)
**Install:** `pip install sqlmodel`
```python
from sqlmodel import SQLModel, Field, Session, create_engine, select
from typing import Optional

class Incident(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    service: str
    root_cause: str
    fix_applied: str
    result: str
    mttr_seconds: float
    revenue_protected: float
    timestamp: float

engine = create_engine("sqlite:///database/incidents.db")
SQLModel.metadata.create_all(engine)

with Session(engine) as s:
    s.add(Incident(service="payment", root_cause="error_spike",
                   fix_applied="retry_with_backoff", result="RECOVERED",
                   mttr_seconds=47.0, revenue_protected=8400.0, timestamp=1234567890))
    s.commit()
```

---

## Our Event Bus (replaces Solace Agent Mesh)
No install — it's our own file `orchestrator/event_bus.py`.
```python
import asyncio
from collections import defaultdict

class EventBus:
    def __init__(self):
        self._subs = defaultdict(list)
    def subscribe(self, topic, handler):
        self._subs[topic].append(handler)
    async def publish(self, topic, payload):
        await asyncio.gather(*[h(payload) for h in self._subs[topic]])

bus = EventBus()
```
Usage in an agent:
```python
from orchestrator.event_bus import bus
from shared.events import ANOMALY_DETECTED, DIAGNOSE_REQUEST

async def on_anomaly(payload):
    await bus.publish(DIAGNOSE_REQUEST, {"service": payload["service"], ...})

bus.subscribe(ANOMALY_DETECTED, on_anomaly)
```

---

## React + Vite (frontend — replaces Streamlit)
**Scaffold:** `npm create vite@latest frontend -- --template react`
**Run:** `npm run dev` (http://localhost:5173)
Fetch + poll pattern:
```jsx
import { useEffect, useState } from "react";
const API = import.meta.env.VITE_API_URL;

function useServices() {
  const [data, setData] = useState(null);
  useEffect(() => {
    const tick = () =>
      fetch(`${API}/api/services`).then(r => r.json()).then(setData);
    tick();
    const id = setInterval(tick, 4000);   // poll every 4s
    return () => clearInterval(id);
  }, []);
  return data;
}
```

---

## Recharts (charts in React — replaces Plotly/Streamlit)
**Install:** `npm install recharts`
```jsx
import { BarChart, Bar, XAxis, YAxis, ReferenceLine, Tooltip } from "recharts";

<BarChart width={600} height={300} data={mttrData}>
  <XAxis dataKey="root_cause" /><YAxis />
  <Tooltip />
  <Bar dataKey="mttr_seconds" />
  <ReferenceLine y={900} strokeDasharray="4 4" label="Manual baseline" />
</BarChart>
```

---

## Tailwind CSS (styling)
**Install:** `npm install -D tailwindcss postcss autoprefixer && npx tailwindcss init -p`
Set `content: ["./src/**/*.{js,jsx}"]` and add the three `@tailwind` directives to `src/index.css`. Use the color tokens from `ui-tokens.md` as your Tailwind theme colors.
