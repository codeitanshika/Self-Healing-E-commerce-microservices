import { useEffect, useState } from "react";
import { getJson } from "../lib/api";
import { fmtDateTime, fmtInr, fmtSeconds, prettyCause } from "../lib/format";

export function IncidentDrawer({ id, onClose }) {
  const [inc, setInc] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    getJson(`/api/incidents/${id}`)
      .then((d) => alive && setInc(d))
      .catch((e) => alive && setError(e.message));
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => { alive = false; window.removeEventListener("keydown", onKey); };
  }, [id, onClose]);

  const t0 = inc?.timeline?.[0]?.ts;

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label="Incident detail">
        <button className="x" onClick={onClose} aria-label="Close">✕</button>
        {error && <div className="notice err">{error}</div>}
        {!inc && !error && <div className="skeleton" style={{ height: 160 }} />}
        {inc && (
          <>
            <h2>{inc.service} · {inc.fault_type}</h2>
            <p className="section-sub" style={{ marginTop: 4 }}>
              Incident #{inc.id} · {fmtDateTime(inc.timestamp)}
            </p>

            <div className="live-facts" style={{ marginTop: 16 }}>
              <div className="fact"><div className="fact-label">Outcome</div>
                <div className="fact-value"><span className={`tag ${inc.result}`}>{inc.result.toLowerCase()}</span></div></div>
              <div className="fact"><div className="fact-label">MTTR</div>
                <div className="fact-value num">{fmtSeconds(inc.mttr_seconds)}</div></div>
              <div className="fact"><div className="fact-label">Protected</div>
                <div className="fact-value num">{fmtInr(inc.revenue_protected)}</div></div>
              <div className="fact"><div className="fact-label">Root cause</div>
                <div className="fact-value">{prettyCause(inc.root_cause)}</div></div>
              <div className="fact"><div className="fact-label">Confidence</div>
                <div className="fact-value num">{inc.confidence}%</div></div>
              <div className="fact"><div className="fact-label">Retries</div>
                <div className="fact-value num">{inc.retry_count}</div></div>
            </div>

            {inc.explanation && (
              <>
                <span className="label">LLM reasoning</span>
                <div className="prose">{inc.explanation}</div>
              </>
            )}
            {inc.business_impact && (
              <>
                <span className="label">Business impact</span>
                <div className="prose">{inc.business_impact}</div>
              </>
            )}

            <span className="label">Timeline</span>
            {inc.timeline.length === 0 ? (
              <p className="section-sub">No stage timeline was recorded for this older incident.</p>
            ) : (
              <ol className="timeline">
                {inc.timeline.map((s, i) => (
                  <li key={i} className={s.stage}>
                    <div className="tl-stage">{s.stage.replace("_", " ").toLowerCase()}</div>
                    <div className="tl-meta num">+{(s.ts - t0).toFixed(2)}s</div>
                    {s.detail && <div className="tl-detail">{s.detail}</div>}
                  </li>
                ))}
              </ol>
            )}
          </>
        )}
      </aside>
    </>
  );
}
