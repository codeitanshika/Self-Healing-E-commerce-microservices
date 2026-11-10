import { useState } from "react";
import { injectFault } from "../lib/api";
import { FAULT_INFO } from "../lib/format";

// Multi-fault scenarios: several incidents running concurrently.
const SCENARIOS = [
  {
    id: "flash-sale",
    title: "Flash-sale surge",
    blurb: "Payment crashes while cart slows and auth throws errors",
    steps: [["payment", "crash"], ["cart", "slow"], ["auth", "error"]],
  },
  {
    id: "leak-and-crash",
    title: "Slow burn",
    blurb: "Inventory leaks memory as notification dies",
    steps: [["inventory", "memory"], ["notification", "crash"]],
  },
];

export function FaultLab({ services }) {
  const names = Object.keys(services?.services ?? {});
  const [service, setService] = useState("payment");
  const [fault, setFault] = useState("crash");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState(null);

  // The real Nginx container only has an honest equivalent for "crash".
  const faults = service === "nginx" ? ["crash"] : Object.keys(FAULT_INFO);
  const pickService = (n) => {
    setService(n);
    if (n === "nginx") setFault("crash");
  };

  const run = async (pairs, label) => {
    setBusy(true);
    setNote(null);
    try {
      await Promise.all(pairs.map(([s, f]) => injectFault(s, f)));
      setNote({ ok: true, text: `${label} injected. Watch the pipeline →` });
    } catch (err) {
      setNote({ ok: false, text: err.message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card">
      <div className="card-head">
        <div>
          <h3 className="card-title">Fault lab</h3>
          <p className="card-sub">Break something on purpose and watch it heal</p>
        </div>
      </div>

      <span className="label">Target service</span>
      <div className="chips" role="radiogroup" aria-label="Target service">
        {(names.length ? names : ["auth", "cart", "payment", "inventory", "notification"]).map((n) => (
          <button key={n} role="radio" aria-checked={service === n}
            className={`chip ${service === n ? "on" : ""}`} onClick={() => pickService(n)}>
            {n}
          </button>
        ))}
      </div>

      <span className="label">Fault type</span>
      <div className="fault-opts" role="radiogroup" aria-label="Fault type">
        {faults.map((f) => (
          <button key={f} role="radio" aria-checked={fault === f}
            className={`fault-opt ${fault === f ? "on" : ""}`} onClick={() => setFault(f)}>
            <b>{FAULT_INFO[f].label}</b>
            <span>{FAULT_INFO[f].hint}</span>
          </button>
        ))}
      </div>

      <div style={{ marginTop: 14 }}>
        <button className="btn danger full" disabled={busy}
          onClick={() => run([[service, fault]], `${fault} on ${service}`)}>
          {busy ? "Injecting…" : `Inject ${fault} into ${service}`}
        </button>
      </div>

      <span className="label">Multi-fault scenarios</span>
      <div style={{ display: "grid", gap: 8 }}>
        {SCENARIOS.map((s) => (
          <div className="scenario" key={s.id}>
            <div><b>{s.title}</b><span>{s.blurb}</span></div>
            <button className="btn ghost" disabled={busy}
              onClick={() => run(s.steps, s.title)}>Run</button>
          </div>
        ))}
      </div>

      {note && <div className={`notice ${note.ok ? "ok" : "err"}`} role="status">{note.text}</div>}
    </section>
  );
}
