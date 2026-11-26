import { useEffect, useRef } from "react";
import { describeEvent, fmtTime } from "../lib/format";

/** Render "**bold**" markers as <b> elements — never as raw HTML. */
function Rich({ text }) {
  return text.split("**").map((part, i) => (i % 2 ? <b key={i}>{part}</b> : part));
}

const SHORT = {
  ANOMALY_DETECTED: "ANOMALY",
  DIAGNOSE_REQUEST: "diagnose?",
  DIAGNOSIS_READY: "DIAGNOSIS",
  FIX_REQUEST: "fix?",
  FIX_APPLIED: "FIX",
  VALIDATE_REQUEST: "validate?",
  VALIDATION_RESULT: "VALIDATION",
  INCIDENT_LOGGED: "LOGGED",
};

export function EventFeed({ events, connected }) {
  const ref = useRef(null);
  const stick = useRef(true);

  // Auto-follow the newest event, but stop if the user scrolled up to read.
  useEffect(() => {
    const el = ref.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [events]);

  const onScroll = () => {
    const el = ref.current;
    stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
  };

  return (
    <section className="card">
      <div className="card-head">
        <div>
          <h3 className="card-title">Event bus</h3>
          <p className="card-sub">Every message agents exchange, as it happens</p>
        </div>
        <span className={`pill ${connected ? "ok" : "warn"}`}>
          <span className={`dot ${connected ? "pulse" : ""}`} />
          {connected ? "streaming" : "offline"}
        </span>
      </div>
      <div className="feed" ref={ref} onScroll={onScroll} role="log" aria-label="Pipeline events">
        {events.length === 0 && (
          <div className="chart-empty">Waiting for events. Inject a fault to see agents talk.</div>
        )}
        {events.map((e) => (
          <div className="feed-row" key={e.seq}>
            <span className="feed-time num">{fmtTime(e.ts)}</span>
            <span className={`feed-topic t-${e.topic}`}>{SHORT[e.topic] ?? e.topic}</span>
            <span className="feed-text"><Rich text={describeEvent(e)} /></span>
          </div>
        ))}
      </div>
    </section>
  );
}
