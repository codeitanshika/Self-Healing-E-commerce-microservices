# UI Registry — Dashboard Components (React)

Maps each dashboard element to its React component and data source. Replaces the Streamlit registry.

| Component | React component | Data source (backend REST) | Refresh |
|---|---|---|---|
| Page title | `<Header/>` | static | — |
| Service health tile (×5) | `<HealthTile/>` in a grid | `GET /api/services` | 4s poll |
| Summary metrics row | `<MetricCard/>` ×4 | `GET /api/stats` | 4s poll |
| Active incident banner | `<ActiveIncidentBanner/>` | `GET /api/active-incident` | 4s poll |
| Incident history table | `<IncidentTable/>` | `GET /api/incidents` | 4s poll |
| MTTR comparison chart | `<MttrChart/>` (Recharts BarChart) | `GET /api/incidents` (group client-side) | 4s poll |
| Revenue protected chart | `<RevenueChart/>` (Recharts LineChart) | `GET /api/incidents` (cumsum client-side) | 4s poll |
| Fault injection controls | `<DemoControls/>` (sidebar) | `POST /api/services/{name}/inject-fault` | on click |
| Debug event log (optional) | `<DebugPanel/>` (collapsible) | `GET /api/events?limit=20` | 4s poll |

## Backend endpoints the frontend needs (build in Phase 5)
```
GET  /api/services                       -> { services: {name: {status,cpu,memory,response_time_ms,error_rate}}, summary }
GET  /api/incidents                      -> [ {timestamp, service, root_cause, fix_applied, result, mttr_seconds, revenue_protected} ]
GET  /api/stats                          -> { avg_mttr, baseline_mttr: 900, total_revenue_protected, incidents_resolved }
GET  /api/active-incident                -> { active: bool, service?, stage?: "diagnosing|fixing|validating" }
POST /api/services/{name}/inject-fault?fault_type=crash
```

## Polling hook (shared)
```jsx
// src/hooks/usePolling.js
import { useEffect, useState } from "react";
const API = import.meta.env.VITE_API_URL;

export function usePolling(path, intervalMs = 4000) {
  const [data, setData] = useState(null);
  useEffect(() => {
    let alive = true;
    const tick = () =>
      fetch(`${API}${path}`).then(r => r.json()).then(d => alive && setData(d)).catch(() => {});
    tick();
    const id = setInterval(tick, intervalMs);
    return () => { alive = false; clearInterval(id); };
  }, [path, intervalMs]);
  return data;
}
```

## App composition
```jsx
// src/App.jsx (shape)
function App() {
  const services = usePolling("/api/services");
  const incidents = usePolling("/api/incidents");
  const stats = usePolling("/api/stats");
  const active = usePolling("/api/active-incident");
  return (
    <div className="min-h-screen bg-bgPrimary text-textPrimary p-6">
      <Header />
      <HealthGrid services={services} />
      <MetricRow stats={stats} />
      <ActiveIncidentBanner active={active} />
      <IncidentTable incidents={incidents} />
      <MttrChart incidents={incidents} />
      <RevenueChart incidents={incidents} />
      <DemoControls />
    </div>
  );
}
```

## HealthTile example (uses ui-tokens colors)
```jsx
const COLOR = { ok: "bg-healthy", degraded: "bg-degraded", down: "bg-down" };
export function HealthTile({ name, s }) {
  const key = s?.status === "ok" ? "ok" : s?.status === "degraded" ? "degraded" : "down";
  return (
    <div className={`rounded-xl p-4 ${COLOR[key]} text-white`}>
      <div className="font-bold">{name}</div>
      <div className="text-sm">{key === "ok" ? "HEALTHY" : key.toUpperCase()}</div>
      <div className="text-xs opacity-80">CPU {s?.cpu ?? "—"}% | Mem {s?.memory ?? "—"}%</div>
    </div>
  );
}
```
