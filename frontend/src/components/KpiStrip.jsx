import { fmtInr, fmtPct, fmtSeconds } from "../lib/format";

function Kpi({ label, value, unit, note }) {
  return (
    <div className="card kpi">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value num">
        {value}
        {unit && <span className="kpi-unit">{unit}</span>}
      </div>
      <div className="kpi-note">{note}</div>
    </div>
  );
}

export function KpiStrip({ stats }) {
  const s = stats;
  const has = s && s.total_incidents > 0;
  const base = s?.baseline_mttr_seconds ?? 900;
  const ours = s?.avg_mttr_seconds ?? 0;
  // Visual comparison scaled so the baseline fills the track.
  const pct = has ? Math.max((ours / base) * 100, 0.8) : 0;

  return (
    <div className="kpis">
      <div className="card kpi hero">
        <div className="kpi-label">Mean time to recovery</div>
        <div className="kpi-value num">
          {has ? fmtSeconds(ours) : "—"}
          {has && s.speedup_vs_baseline > 0 && (
            <span className="kpi-unit">· {s.speedup_vs_baseline}× faster than manual</span>
          )}
        </div>
        <div className="bar-compare" aria-hidden={!has}>
          <div className="bar-row">
            <span>This system</span>
            <div className="bar-track"><div className="bar-fill" style={{ width: `${pct}%`, background: "var(--ok)" }} /></div>
            <span className="num">{has ? fmtSeconds(ours) : "—"}</span>
          </div>
          <div className="bar-row">
            <span>Manual on-call</span>
            <div className="bar-track"><div className="bar-fill" style={{ width: "100%", background: "var(--text-3)" }} /></div>
            <span className="num">{fmtSeconds(base)}</span>
          </div>
        </div>
      </div>
      <Kpi label="Recovery rate" value={has ? fmtPct(s.recovery_rate) : "—"}
        note={has ? `${s.incidents_resolved} of ${s.total_incidents} incidents${s.incidents_escalated ? ` · ${s.incidents_escalated} escalated` : ""}` : "No incidents yet"} />
      <Kpi label="Diagnosis accuracy" value={has ? fmtPct(s.diagnosis_accuracy) : "—"}
        note={has ? `avg confidence ${s.avg_confidence}%` : "LLM root-cause vs. injected fault"} />
      <Kpi label="Fixed first try" value={has ? fmtPct(s.first_try_rate) : "—"}
        note={has ? `p50 ${fmtSeconds(s.p50_mttr_seconds)} · p95 ${fmtSeconds(s.p95_mttr_seconds)}` : "No retry needed"} />
      <Kpi label="Revenue protected" value={has ? fmtInr(s.total_revenue_protected) : "—"}
        note="Illustrative, vs. 15-min manual response" />
    </div>
  );
}
