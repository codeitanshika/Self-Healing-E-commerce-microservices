export function TopBar({ connected, apiError, summary }) {
  const down = summary?.down ?? 0;
  const degraded = summary?.degraded ?? 0;

  let health = { cls: "ok", text: "All systems operational" };
  if (down) health = { cls: "down", text: `${down} service${down > 1 ? "s" : ""} down · agents responding` };
  else if (degraded) health = { cls: "warn", text: `${degraded} degraded · agents responding` };
  if (apiError) health = { cls: "down", text: "Backend unreachable" };

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 12h4l2-6 4 12 2-6h6" />
            </svg>
          </div>
          <div>
            <div className="brand-name">Self-Healing Control Plane</div>
            <div className="brand-tag">Autonomous detect → diagnose → fix → validate</div>
          </div>
        </div>
        <div className="spacer" />
        <span className={`pill ${health.cls}`}>
          <span className={`dot ${health.cls !== "ok" ? "pulse" : ""}`} />
          {health.text}
        </span>
        <span className={`pill ${connected ? "ok" : "warn"}`} title="Server-Sent Events connection">
          <span className="dot" />
          {connected ? "Live stream" : "Reconnecting…"}
        </span>
      </div>
    </header>
  );
}
