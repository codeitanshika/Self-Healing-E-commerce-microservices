import { lazy, Suspense, useCallback, useMemo, useState } from "react";
import { usePolling, useEventStream } from "./lib/hooks";
import { TopBar } from "./components/TopBar";
import { KpiStrip } from "./components/KpiStrip";
import { ServiceGrid } from "./components/ServiceGrid";
import { PipelineBoard } from "./components/PipelineBoard";
import { EventFeed } from "./components/EventFeed";
import { FaultLab } from "./components/FaultLab";
import { IncidentTable } from "./components/IncidentTable";
import { IncidentDrawer } from "./components/IncidentDrawer";

// If the chunk fails to load (offline, or replaced by a newer deploy), keep the
// rest of the console working instead of blanking the page.
const Performance = lazy(() =>
  import("./components/Performance").catch(() => ({
    default: () => <div className="notice err">Charts could not load. Reload the page to retry.</div>,
  })),
);

export default function App() {
  const { events, connected } = useEventStream();

  // Whenever the stream reports a state change, refetch immediately instead
  // of waiting for the next poll tick: the UI reacts in milliseconds.
  const last = events[events.length - 1];
  const bump = last?.seq ?? 0;
  const settled = last && ["INCIDENT_LOGGED", "VALIDATION_RESULT"].includes(last.topic) ? bump : 0;

  const services = usePolling("/api/services", 3000, bump);
  const history = usePolling("/api/history", 5000);
  const active = usePolling("/api/active-incidents", 1500, bump);
  const stats = usePolling("/api/stats", 5000, settled);
  const incidents = usePolling("/api/incidents?limit=100", 6000, settled);
  const mttr = usePolling("/api/mttr-chart", 8000, settled);
  const revenue = usePolling("/api/revenue-series", 8000, settled);
  const breakdown = usePolling("/api/breakdown", 8000, settled);

  const [openId, setOpenId] = useState(null);
  const close = useCallback(() => setOpenId(null), []);
  const activeList = useMemo(() => active.data?.incidents ?? [], [active.data]);

  const apiError = services.error && !services.data;

  return (
    <>
      <TopBar connected={connected} apiError={apiError} summary={services.data?.summary} />
      <main className="shell">
        <KpiStrip stats={stats.data} />

        <div className="section">
          <div className="section-head">
            <h2 className="section-title">Service health</h2>
            <span className="section-sub">Polled every 3 s · sparklines show recent response time</span>
          </div>
          <ServiceGrid servicesData={services.data} historyData={history.data} active={activeList} />
        </div>

        <div className="section grid cols-main">
          <div className="grid" style={{ alignContent: "start" }}>
            <PipelineBoard active={activeList} />
            <EventFeed events={events} connected={connected} />
          </div>
          <FaultLab services={services.data} />
        </div>

        <div className="section">
          <div className="section-head">
            <h2 className="section-title">Performance</h2>
            <span className="section-sub">Every chart has a table view</span>
          </div>
          <Suspense fallback={<div className="skeleton" style={{ height: 320 }} />}>
            <Performance
              mttr={mttr.data}
              baseline={stats.data?.baseline_mttr_seconds ?? 900}
              revenue={revenue.data}
              incidents={incidents.data}
              breakdown={breakdown.data}
            />
          </Suspense>
        </div>

        <div className="section">
          <IncidentTable incidentsData={incidents.data} onOpen={setOpenId} />
        </div>

        <p className="footer">
          Event-driven multi-agent self-healing · LLM diagnosis · zero-cost, reproducible testbed
        </p>
      </main>
      {openId != null && <IncidentDrawer id={openId} onClose={close} />}
    </>
  );
}
