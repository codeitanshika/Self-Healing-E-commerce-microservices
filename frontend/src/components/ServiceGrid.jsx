import { memo } from "react";

const STATE = { ok: "HEALTHY", degraded: "DEGRADED", down: "DOWN" };

function Sparkline({ points, color }) {
  if (!points || points.length < 2) return <div className="svc-spark" />;
  const w = 180, h = 34, pad = 3;
  const max = Math.max(...points, 1);
  const min = Math.min(...points, 0);
  const span = max - min || 1;
  const xy = points.map((v, i) => [
    (i / (points.length - 1)) * w,
    h - pad - ((v - min) / span) * (h - pad * 2),
  ]);
  const line = xy.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${line} L${w},${h} L0,${h} Z`;
  const [lx, ly] = xy[xy.length - 1];
  return (
    <svg className="svc-spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" width="100%" height="34" aria-hidden="true">
      <path d={area} fill={color} opacity="0.12" />
      <path d={line} fill="none" stroke={color} strokeWidth="1.6" vectorEffect="non-scaling-stroke" />
      <circle cx={lx} cy={ly} r="2.4" fill={color} />
    </svg>
  );
}

function Meter({ label, value, max = 100, warnAt = 70, downAt = 85, text }) {
  const pct = Math.min((value / max) * 100, 100);
  const color = value >= downAt ? "var(--down)" : value >= warnAt ? "var(--warn)" : "var(--series-1)";
  return (
    <div className="meter">
      <span>{label}</span>
      <div className="meter-track"><div className="meter-fill" style={{ width: `${pct}%`, background: color }} /></div>
      <span className="num" style={{ textAlign: "right" }}>{text}</span>
    </div>
  );
}

const ServiceCard = memo(function ServiceCard({ name, h, history, healingStage }) {
  const color = h.status === "ok" ? "#2fbf8f" : h.status === "degraded" ? "#e0a030" : "#ec5b5b";
  const rt = (history ?? []).map((s) => s.rt);
  return (
    <article className={`card svc ${h.status} ${healingStage ? "healing" : ""}`} aria-label={`${name} service ${STATE[h.status]}`}>
      <div className="svc-top">
        <span className="svc-name">
          {name}
          {name === "nginx" && <span className="svc-tag">real container</span>}
        </span>
        <span className={`svc-state ${h.status}`}>{STATE[h.status]}</span>
      </div>
      <div className="svc-rt num">
        <b>{h.status === "down" ? "—" : h.response_time_ms}</b>
        <span>ms</span>
      </div>
      <Sparkline points={rt} color={color} />
      <div className="svc-meters">
        <Meter label="CPU" value={h.cpu} text={`${Math.round(h.cpu)}%`} />
        <Meter label="MEM" value={h.memory} warnAt={70} downAt={85} text={`${Math.round(h.memory)}%`} />
        <Meter label="ERR" value={h.error_rate * 100} warnAt={15} downAt={30} text={`${Math.round(h.error_rate * 100)}%`} />
      </div>
      {healingStage && (
        <div className="healing-badge">
          <span className="dot pulse" /> Agents {healingStage}…
        </div>
      )}
      {!healingStage && h.active_fault && (
        <div className="healing-badge" style={{ color: "var(--warn)" }}>
          <span className="dot" /> {h.active_fault} fault active
        </div>
      )}
    </article>
  );
});

export function ServiceGrid({ servicesData, historyData, active }) {
  if (!servicesData?.services) {
    return (
      <div className="services">
        {Array.from({ length: 6 }).map((_, i) => <div key={i} className="skeleton" style={{ height: 190 }} />)}
      </div>
    );
  }
  const stageByService = {};
  (active ?? []).forEach((i) => { stageByService[i.service] = i.stage; });

  return (
    <div className="services">
      {Object.entries(servicesData.services).map(([name, h]) => (
        <ServiceCard
          key={name} name={name} h={h}
          history={historyData?.history?.[name]}
          healingStage={stageByService[name]}
        />
      ))}
    </div>
  );
}
