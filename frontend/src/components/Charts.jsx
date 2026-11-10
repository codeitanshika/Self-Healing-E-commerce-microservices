import { useState } from "react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart,
  ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { fmtInr, fmtSeconds, fmtTime, prettyCause } from "../lib/format";

const AXIS = { stroke: "#6f7787", fontSize: 11, tickLine: false, axisLine: false };
const GRID = <CartesianGrid stroke="#242933" strokeDasharray="3 4" vertical={false} />;

/** Card with a title, optional legend, and a chart/table view toggle (a11y). */
function ChartCard({ title, subtitle, rows, columns, empty, children }) {
  const [asTable, setAsTable] = useState(false);
  const hasData = rows && rows.length > 0;
  return (
    <section className="card" aria-label={title}>
      <div className="card-head">
        <div>
          <h3 className="card-title">{title}</h3>
          <p className="card-sub">{subtitle}</p>
        </div>
        {hasData && (
          <button className="view-toggle" onClick={() => setAsTable((v) => !v)}>
            {asTable ? "Chart" : "Table"}
          </button>
        )}
      </div>
      {!hasData ? (
        <div className="chart-box"><div className="chart-empty">{empty}</div></div>
      ) : asTable ? (
        <div className="chart-box" style={{ overflowY: "auto" }}>
          <table className="mini-table">
            <thead><tr>{columns.map((c) => <th key={c.key}>{c.label}</th>)}</tr></thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>{columns.map((c) => <td key={c.key} className="num">{c.render ? c.render(r) : r[c.key]}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="chart-box">{children}</div>
      )}
    </section>
  );
}

function Tip({ active, payload, label, format }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="tt">
      <b>{label}</b>
      {payload.map((p) => (
        <div className="tt-row" key={p.dataKey}>
          <span>{p.name}</span>
          <span className="num" style={{ color: "#eceef2" }}>{format(p.value, p)}</span>
        </div>
      ))}
    </div>
  );
}

export function MttrByCause({ data, baseline }) {
  const rows = (data?.data ?? []).map((d) => ({ ...d, label: prettyCause(d.root_cause) }));
  const worst = rows.length ? Math.max(...rows.map((r) => r.avg_mttr)) : 0;
  return (
    <ChartCard
      title="Recovery time by root cause"
      subtitle={`Average seconds from detection to verified recovery · manual baseline is ${baseline}s`}
      rows={rows}
      empty="No recovered incidents yet — inject a fault to see this fill in."
      columns={[
        { key: "label", label: "Root cause" },
        { key: "avg_mttr", label: "Avg MTTR", render: (r) => fmtSeconds(r.avg_mttr) },
        { key: "count", label: "Incidents" },
      ]}
    >
      <ResponsiveContainer>
        <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 36, top: 4, bottom: 4 }} barCategoryGap={14}>
          {GRID}
          <XAxis type="number" {...AXIS} domain={[0, Math.ceil(worst * 1.15) || 10]} unit="s" />
          <YAxis type="category" dataKey="label" {...AXIS} width={96} />
          <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }}
            content={<Tip format={(v) => fmtSeconds(v)} />} />
          <Bar dataKey="avg_mttr" name="Avg MTTR" fill="var(--series-1)" radius={[0, 4, 4, 0]} maxBarSize={22} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function RevenueArea({ data }) {
  const rows = (data?.data ?? []).map((d, i) => ({ ...d, n: i + 1, time: fmtTime(d.timestamp) }));
  return (
    <ChartCard
      title="Cumulative revenue protected"
      subtitle="Illustrative ₹ saved versus a 15-minute manual response, summed over incidents"
      rows={rows}
      empty="Revenue appears here after the first auto-healed incident."
      columns={[
        { key: "n", label: "#" },
        { key: "service", label: "Service" },
        { key: "increment", label: "Added", render: (r) => fmtInr(r.increment) },
        { key: "cumulative", label: "Total", render: (r) => fmtInr(r.cumulative) },
      ]}
    >
      <ResponsiveContainer>
        <AreaChart data={rows} margin={{ left: 0, right: 12, top: 8, bottom: 0 }}>
          <defs>
            <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#199e70" stopOpacity={0.45} />
              <stop offset="100%" stopColor="#199e70" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          {GRID}
          <XAxis dataKey="n" {...AXIS} label={{ value: "incident #", position: "insideBottomRight", offset: -2, fill: "#6f7787", fontSize: 11 }} />
          <YAxis {...AXIS} width={64} tickFormatter={(v) => (v >= 1000 ? `${Math.round(v / 1000)}k` : v)} />
          <Tooltip cursor={{ stroke: "#6f7787", strokeDasharray: "3 3" }}
            content={<Tip format={(v) => fmtInr(v)} />} labelFormatter={(n) => `Incident ${n}`} />
          <Area type="monotone" dataKey="cumulative" name="Total protected" stroke="#199e70" strokeWidth={2} fill="url(#rev)" dot={false} activeDot={{ r: 5, stroke: "#14171d", strokeWidth: 2 }} />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function MttrTrend({ incidents }) {
  const rows = [...(incidents?.incidents ?? [])]
    .reverse()
    .filter((i) => i.result === "RECOVERED")
    .map((i, n) => ({ n: n + 1, mttr: i.mttr_seconds, service: i.service, id: i.id }));
  const avg = rows.length ? rows.reduce((a, r) => a + r.mttr, 0) / rows.length : 0;
  return (
    <ChartCard
      title="Recovery time per incident"
      subtitle="Each point is one auto-healed incident, oldest to newest"
      rows={rows}
      empty="Waiting for incidents."
      columns={[
        { key: "n", label: "#" },
        { key: "service", label: "Service" },
        { key: "mttr", label: "MTTR", render: (r) => fmtSeconds(r.mttr) },
      ]}
    >
      <ResponsiveContainer>
        <LineChart data={rows} margin={{ left: 0, right: 16, top: 8, bottom: 0 }}>
          {GRID}
          <XAxis dataKey="n" {...AXIS} />
          <YAxis {...AXIS} width={44} unit="s" />
          <ReferenceLine y={avg} stroke="#6f7787" strokeDasharray="4 4"
            label={{ value: `avg ${avg.toFixed(1)}s`, fill: "#a4abb8", fontSize: 11, position: "insideTopRight" }} />
          <Tooltip cursor={{ stroke: "#6f7787", strokeDasharray: "3 3" }}
            content={<Tip format={(v) => fmtSeconds(v)} />} />
          <Line type="monotone" dataKey="mttr" name="MTTR" stroke="#3987e5" strokeWidth={2}
            dot={{ r: 3, fill: "#3987e5", stroke: "#14171d", strokeWidth: 2 }} activeDot={{ r: 6, stroke: "#14171d", strokeWidth: 2 }} />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function ServiceBreakdown({ data }) {
  const rows = data?.by_service ?? [];
  return (
    <ChartCard
      title="Incidents by service"
      subtitle="Where faults landed, and how many each service recovered from"
      rows={rows}
      empty="No incidents recorded yet."
      columns={[
        { key: "name", label: "Service" },
        { key: "count", label: "Incidents" },
        { key: "recovered", label: "Recovered" },
        { key: "avg_mttr", label: "Avg MTTR", render: (r) => fmtSeconds(r.avg_mttr) },
      ]}
    >
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ left: 0, right: 12, top: 8, bottom: 0 }} barCategoryGap={22}>
          {GRID}
          <XAxis dataKey="name" {...AXIS} />
          <YAxis {...AXIS} width={30} allowDecimals={false} />
          <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }}
            content={<Tip format={(v, p) => `${v} incidents · ${p.payload.recovered} recovered`} />} />
          <Bar dataKey="count" name="Incidents" radius={[4, 4, 0, 0]} maxBarSize={44}>
            {rows.map((r) => <Cell key={r.name} fill="var(--series-1)" />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
