import { useMemo, useState } from "react";
import { fmtInr, fmtSeconds, fmtTime, prettyCause } from "../lib/format";

const RESULTS = ["ALL", "RECOVERED", "ESCALATED"];

export function IncidentTable({ incidentsData, onOpen }) {
  const [result, setResult] = useState("ALL");
  const [service, setService] = useState("all");
  const [limit, setLimit] = useState(12);
  const rows = useMemo(() => incidentsData?.incidents ?? [], [incidentsData]);

  const services = useMemo(() => [...new Set(rows.map((r) => r.service))].sort(), [rows]);
  const shown = rows.filter(
    (r) => (result === "ALL" || r.result === result) && (service === "all" || r.service === service)
  );

  return (
    <section className="card">
      <div className="card-head">
        <div>
          <h3 className="card-title">Incident history</h3>
          <p className="card-sub">Click a row for the full stage-by-stage timeline and the LLM's reasoning</p>
        </div>
        <span className="pill num">{shown.length} shown</span>
      </div>

      <div className="toolbar">
        <div className="chips">
          {RESULTS.map((r) => (
            <button key={r} className={`chip ${result === r ? "on" : ""}`} onClick={() => setResult(r)}>
              {r === "ALL" ? "All" : r.toLowerCase()}
            </button>
          ))}
        </div>
        <select className="select" value={service} onChange={(e) => setService(e.target.value)} aria-label="Filter by service">
          <option value="all">All services</option>
          {services.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {rows.length === 0 ? (
        <div className="chart-empty" style={{ padding: 36 }}>
          No incidents yet — inject a fault to see the system respond.
        </div>
      ) : (
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>Time</th><th>Service</th><th>Root cause</th><th>Confidence</th>
                <th>Fix</th><th className="r">Retries</th><th className="r">MTTR</th>
                <th className="r">Protected</th><th>Outcome</th>
              </tr>
            </thead>
            <tbody>
              {shown.slice(0, limit).map((r) => (
                <tr key={r.id} onClick={() => onOpen(r.id)} tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && onOpen(r.id)}>
                  <td className="num" style={{ color: "var(--text-3)" }}>{fmtTime(r.timestamp)}</td>
                  <td style={{ textTransform: "capitalize", fontWeight: 600 }}>{r.service}</td>
                  <td className="cause">{prettyCause(r.root_cause)}</td>
                  <td>
                    <span className="conf num">
                      <span className="conf-bar"><i style={{ width: `${r.confidence}%` }} /></span>
                      {r.confidence}%
                    </span>
                  </td>
                  <td className="cause">{r.fix_applied}</td>
                  <td className="r num">{r.retry_count}</td>
                  <td className="r num">{fmtSeconds(r.mttr_seconds)}</td>
                  <td className="r num">{fmtInr(r.revenue_protected)}</td>
                  <td><span className={`tag ${r.result}`}>{r.result.toLowerCase()}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          {shown.length > limit && (
            <button className="btn ghost full" style={{ marginTop: 12 }} onClick={() => setLimit((l) => l + 25)}>
              Show more ({shown.length - limit} remaining)
            </button>
          )}
        </div>
      )}
    </section>
  );
}
