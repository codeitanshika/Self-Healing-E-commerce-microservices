export const fmtSeconds = (s) => {
  if (s == null || Number.isNaN(s)) return "—";
  if (s < 1) return `${Math.round(s * 1000)} ms`;
  if (s < 60) return `${s.toFixed(1)} s`;
  const m = Math.floor(s / 60);
  return `${m}m ${Math.round(s - m * 60)}s`;
};

export const fmtPct = (x, digits = 0) => `${(x * 100).toFixed(digits)}%`;
export const fmtInr = (n) => `₹${Math.round(n || 0).toLocaleString("en-IN")}`;
export const fmtTime = (ts) =>
  new Date(ts * 1000).toLocaleTimeString([], { hour12: false });
export const fmtDateTime = (ts) =>
  new Date(ts * 1000).toLocaleString([], { dateStyle: "medium", timeStyle: "medium" });

export const prettyCause = (c) => (c || "unknown").replace(/_/g, " ");

export const FAULT_INFO = {
  crash:  { label: "Crash",   hint: "Process dies, 100% errors" },
  slow:   { label: "Slow",    hint: "3–8 s latency, CPU pegged" },
  memory: { label: "Memory",  hint: "Leak climbing toward OOM" },
  error:  { label: "Errors",  hint: "50% of requests failing" },
};

export const STAGES = ["Detect", "Diagnose", "Fix", "Validate", "Resolved"];

/** Map the orchestrator's stage string to how many pipeline steps are complete. */
export const stageIndex = (stage) =>
  ({ diagnosing: 1, fixing: 2, validating: 3, recovered: 5, escalated: 5 }[stage] ?? 0);

/** One-line summary of a bus event; **x** marks bold spans (rendered safely, never as HTML). */
export function describeEvent(evt) {
  const d = evt.data || {};
  switch (evt.topic) {
    case "ANOMALY_DETECTED":
      return `**${evt.service}** flagged as **${d.fault_type}** · ${d.metrics?.response_time_ms ?? "?"} ms, ${((d.metrics?.error_rate ?? 0) * 100).toFixed(0)}% errors`;
    case "DIAGNOSE_REQUEST":
      return `asking the LLM to diagnose **${evt.service}**`;
    case "DIAGNOSIS_READY":
      return `**${evt.service}** → ${prettyCause(d.root_cause)} (${d.confidence}%) · fix: **${d.fix}**`;
    case "FIX_REQUEST":
      return `executing **${d.fix}** on ${evt.service}`;
    case "FIX_APPLIED":
      return `**${d.fix_applied}** applied to ${evt.service} in ${d.fix_time}s`;
    case "VALIDATE_REQUEST":
      return `re-checking real health of ${evt.service}`;
    case "VALIDATION_RESULT":
      return `**${evt.service}** ${d.result}${d.mttr_seconds != null ? ` · MTTR ${d.mttr_seconds}s` : ""}`;
    case "INCIDENT_LOGGED":
      return `incident #${d.incident_db_id} stored · ${d.result}`;
    default:
      return evt.topic;
  }
}
