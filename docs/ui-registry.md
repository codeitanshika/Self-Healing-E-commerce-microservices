# UI Registry — Dashboard Components

Where each part of the dashboard lives (`frontend/src/`) and where its data comes from. `App.jsx` fetches the data and passes it down.

| Part | Component | Data source | Poll interval |
|---|---|---|---|
| Status pills | `components/TopBar.jsx` | `GET /api/services` (summary), stream state | 3 s + every event |
| Key figures | `components/KpiStrip.jsx` | `GET /api/stats` | 5 s + on results |
| Service cards | `components/ServiceGrid.jsx` | `GET /api/services`, `/api/history`, active incidents | 3 s / 5 s |
| Healing pipeline | `components/PipelineBoard.jsx` | `GET /api/active-incidents` | 1.5 s + every event |
| Event bus feed | `components/EventFeed.jsx` | `GET /api/stream` | pushed |
| Fault lab | `components/FaultLab.jsx` | `GET /api/scenarios`; `POST` fault, scenario, reset | 60 s |
| Charts | `components/Performance.jsx` → `components/Charts.jsx` (loaded lazily) | `GET /api/mttr-chart`, `/api/revenue-series`, `/api/breakdown`, `/api/incidents` | 8 s / 6 s + on results |
| Incident table | `components/IncidentTable.jsx` | `GET /api/incidents?limit=100` | 6 s + on results |
| Incident drawer | `components/IncidentDrawer.jsx` | `GET /api/incidents/{id}` | on open |

"On results" means an immediate re-fetch when the newest event is `VALIDATION_RESULT` or `INCIDENT_LOGGED`.

## Charts
| Chart | Type | Content |
|---|---|---|
| `MttrByCause` | horizontal bar | average recovery time per root cause |
| `RevenueArea` | area | cumulative illustrative revenue protected |
| `MttrTrend` | line with average line | recovery time per recovered incident |
| `ServiceBreakdown` | bar | incidents per service |

## Shared code
| File | Provides |
|---|---|
| `lib/api.js` | `getJson`, `post` (adds `X-API-Key` when configured), `injectFault` |
| `lib/hooks.js` | `usePolling(path, intervalMs, refreshKey)`, `useEventStream(limit)`, `useNow(ms)` |
| `lib/format.js` | number and time formatting, `STAGES`, `stageIndex`, `FAULT_INFO`, `describeEvent` |

## Endpoint shapes
```
GET /api/services          -> { services: { name: {status, cpu, memory, response_time_ms, error_rate, active_fault, ...} },
                                summary: {ok, degraded, down}, total, timestamp }
GET /api/history           -> { history: { name: [ {t, rt, err, mem, cpu, status} ] }, poll_interval }
GET /api/active-incidents  -> { incidents: [ {incident_id, service, fault_type, stage, retry_count, detected_at, timeline, ...} ] }
GET /api/incidents         -> { incidents: [ {id, timestamp, service, root_cause, confidence, fix_applied,
                                retry_count, result, mttr_seconds, revenue_protected, ...} ] }
GET /api/incidents/{id}    -> one incident + { explanation, timeline: [ {stage, ts, detail} ] }
GET /api/stats             -> totals, average / p50 / p95 recovery time, recovery rate, first-try rate,
                              diagnosis accuracy, average confidence, revenue, baseline
```
Interactive documentation for every endpoint is at `/docs` on the backend.
