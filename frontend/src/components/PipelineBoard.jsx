import { STAGES, fmtSeconds, prettyCause, stageIndex } from "../lib/format";
import { useNow } from "../lib/hooks";

function Stepper({ stage }) {
  const done = stage === "idle" ? -1 : stageIndex(stage);
  const escalated = stage === "escalated";
  return (
    <div className="stepper" role="list">
      {STAGES.map((label, i) => {
        const cls = i < done ? "done" : i === done ? "active" : "";
        const fail = escalated && i === STAGES.length - 1;
        return (
          <div key={label} role="listitem" className={`step ${cls} ${fail ? "fail" : ""}`}>
            <div className="step-node">{i < done ? "✓" : i + 1}</div>
            <span>{label}</span>
          </div>
        );
      })}
    </div>
  );
}

function LiveIncident({ inc, now }) {
  const elapsed = Math.max(0, now - inc.detected_at);
  return (
    <div className="incident-live">
      <div className="live-head">
        <span className="dot pulse" style={{ color: "var(--accent)" }} />
        <b>{inc.service}</b>
        <span className="pill">{inc.fault_type}</span>
        {inc.retry_count > 0 && <span className="pill warn">retry #{inc.retry_count}</span>}
        <span className="live-timer num">{fmtSeconds(elapsed)}</span>
      </div>
      <Stepper stage={inc.stage} />
      <div className="live-facts">
        <div className="fact">
          <div className="fact-label">Root cause</div>
          <div className="fact-value">{inc.root_cause ? prettyCause(inc.root_cause) : "diagnosing…"}</div>
        </div>
        <div className="fact">
          <div className="fact-label">Confidence</div>
          <div className="fact-value num">{inc.confidence != null ? `${inc.confidence}%` : "—"}</div>
        </div>
        <div className="fact">
          <div className="fact-label">Current fix</div>
          <div className="fact-value">{inc.fix_applied ?? "pending"}</div>
        </div>
      </div>
    </div>
  );
}

export function PipelineBoard({ active }) {
  const now = useNow();
  const list = active ?? [];
  return (
    <section className="card" aria-live="polite">
      <div className="card-head">
        <div>
          <h3 className="card-title">Healing pipeline</h3>
          <p className="card-sub">Live state of every incident the agents are working on</p>
        </div>
        <span className={`pill ${list.length ? "warn" : ""}`}>
          {list.length ? `${list.length} active` : "idle"}
        </span>
      </div>
      {list.length === 0 ? (
        <div>
          <Stepper stage="idle" />
          <div className="pipe-empty">
            <b style={{ color: "var(--text-2)" }}>No active incidents</b>
            <span>Inject a fault from the Fault Lab and watch the agents close the loop.</span>
          </div>
        </div>
      ) : (
        list.map((inc) => <LiveIncident key={inc.incident_id} inc={inc} now={now} />)
      )}
    </section>
  );
}
