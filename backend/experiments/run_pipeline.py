"""
run_pipeline.py
===============
End-to-end experiment harness: unlike run_experiments.py (which calls the
diagnosis agent directly), this drives the REAL production pipeline —
Monitor -> Orchestrator -> Diagnosis -> Fix -> Validation — over the event
bus, so it measures what a user would actually experience, including
detection latency and the retry/escalation loop.

Works on simulated services AND on the real Docker-managed Nginx container
(the evidence that the system is not "only simulated").

    # real container (needs Docker Desktop running + `docker compose up -d`)
    python -m experiments.run_pipeline --service nginx --fault crash --trials 10 --mode rule
    python -m experiments.run_pipeline --service nginx --fault crash --trials 10 --mode llm

    # simulated services, all four fault types
    python -m experiments.run_pipeline --service payment --fault all --trials 5 --mode rule

    # concurrent / cascading incidents (see fault_injector/scenarios.py)
    python -m experiments.run_pipeline --scenario everything-breaks --trials 5 --mode rule

--mode rule : rule-based diagnosis (no API key / network needed)
--mode llm  : the Groq-backed Diagnosis Agent (GROQ_API_KEY required)

Per-trial timing (all seconds, wall clock):
  detect_s    fault injected -> ANOMALY_DETECTED   (bounded by the poll interval)
  diagnose_s  anomaly        -> DIAGNOSIS_READY
  fix_s       diagnosis      -> FIX_APPLIED
  validate_s  fix            -> terminal VALIDATION_RESULT
  mttr_s      fault injected -> RECOVERED (the user-visible outage length)
"""
import argparse
import asyncio
import csv
import os
import sys
import time
from statistics import mean, stdev

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import monitor_agent as monitor_module  # noqa: E402
from agents.fix_agent import FixAgent  # noqa: E402
from agents.monitor_agent import MonitorAgent  # noqa: E402
from agents.rule_based_diagnosis import rule_based_diagnose  # noqa: E402
from agents.validation_agent import ValidationAgent  # noqa: E402
from orchestrator.event_bus import bus  # noqa: E402
from orchestrator.orchestrator import Orchestrator  # noqa: E402
from services.service_manager import ServiceManager  # noqa: E402
from shared.config import FAULT_TYPES, FIX_MAP  # noqa: E402
from shared.events import DIAGNOSE_REQUEST, DIAGNOSIS_READY  # noqa: E402
from experiments.analyze import bootstrap_ci  # noqa: E402

EXPECTED = {"crash": "service_crash", "slow": "cpu_overload",
            "memory": "memory_leak", "error": "error_spike"}
HERE = os.path.dirname(os.path.abspath(__file__))


class RuleDiagnosisAgent:
    """Drop-in for DiagnosisAgent that uses the rule table (no network)."""

    def __init__(self):
        bus.subscribe(DIAGNOSE_REQUEST, self.handle)

    async def handle(self, payload: dict):
        d = rule_based_diagnose(payload["service"], payload["metrics"])
        await bus.publish(DIAGNOSIS_READY, {
            "service": payload["service"], "incident_id": payload["incident_id"],
            "root_cause": d["root_cause"], "confidence": d["confidence"],
            "fix": FIX_MAP[d["root_cause"]]["primary"],
            "business_impact": d["business_impact"], "explanation": d["explanation"],
        })


class Recorder:
    """Wildcard observer that timestamps every pipeline event per service."""

    def __init__(self):
        self.events: list[tuple[float, str, dict]] = []

    async def __call__(self, topic: str, payload: dict):
        self.events.append((time.time(), topic, dict(payload)))

    def since(self, t0: float, service: str):
        return [(t, topic, p) for t, topic, p in self.events
                if t >= t0 and p.get("service") == service]


def build_stack(manager, mode: str, poll: float):
    """Wire the real agents onto a clean bus. Returns (monitor, recorder)."""
    bus._subscribers.clear()
    bus._wildcard.clear()
    monitor_module.MONITOR_POLL_INTERVAL = poll
    orchestrator = Orchestrator()
    if mode == "llm":
        from agents.diagnosis_agent import DiagnosisAgent
        DiagnosisAgent()
    else:
        RuleDiagnosisAgent()
    FixAgent(manager)
    ValidationAgent(manager)
    monitor = MonitorAgent(manager)
    recorder = Recorder()
    bus.subscribe_all(recorder)
    return monitor, recorder, orchestrator


def summarize_trial(events, t0: float, fault: str):
    """Turn the recorded events for one incident into timing + outcome."""
    first = lambda topic: next((t for t, tp, _ in events if tp == topic), None)  # noqa: E731
    t_anom = first("ANOMALY_DETECTED")
    t_diag = first("DIAGNOSIS_READY")
    t_fix = first("FIX_APPLIED")
    terminal = next(((t, p) for t, tp, p in events
                     if tp == "VALIDATION_RESULT" and p["result"] in ("RECOVERED", "ESCALATED")), None)
    diag = next((p for t, tp, p in events if tp == "DIAGNOSIS_READY"), {})
    retries = sum(1 for _, tp, p in events if tp == "FIX_REQUEST") - 1
    row = {
        "detect_s": round(t_anom - t0, 3) if t_anom else "",
        "diagnose_s": round(t_diag - t_anom, 3) if t_anom and t_diag else "",
        "fix_s": round(t_fix - t_diag, 3) if t_diag and t_fix else "",
        "validate_s": round(terminal[0] - t_fix, 3) if terminal and t_fix else "",
        "mttr_s": round(terminal[0] - t0, 3) if terminal else "",
        "result": terminal[1]["result"] if terminal else "TIMEOUT",
        "retries": max(retries, 0),
        "root_cause": diag.get("root_cause", ""),
        "diagnosis_correct": diag.get("root_cause") == EXPECTED.get(fault),
    }
    return row


async def run_pipeline_experiment(manager, service: str, faults: list[str], trials: int,
                                  mode: str = "rule", poll: float = 1.0, timeout: float = 90.0):
    monitor, recorder, _ = build_stack(manager, mode, poll)
    monitor_task = asyncio.create_task(monitor.run())
    rows = []
    try:
        for trial in range(1, trials + 1):
            for fault in faults:
                # settle: service healthy and monitor has forgotten any old anomaly
                for _ in range(int(timeout / 0.25)):
                    if manager.is_service_healthy(service) and service not in monitor.active_anomalies:
                        break
                    await asyncio.sleep(0.25)
                t0 = time.time()
                res = await asyncio.to_thread(manager.inject_fault, service, fault)
                if "error" in res:
                    print(f"  skip {service}/{fault}: {res['error']}")
                    continue

                deadline = t0 + timeout
                while time.time() < deadline:
                    done = [p for _, tp, p in recorder.since(t0, service)
                            if tp == "VALIDATION_RESULT" and p["result"] in ("RECOVERED", "ESCALATED")]
                    if done:
                        break
                    await asyncio.sleep(0.2)

                row = summarize_trial(recorder.since(t0, service), t0, fault)
                row.update({"trial": trial, "service": service, "fault_type": fault, "mode": mode})
                rows.append(row)
                print(f"  [{trial}] {service}/{fault}: {row['result']} mttr={row['mttr_s']}s "
                      f"detect={row['detect_s']}s retries={row['retries']}")
                await asyncio.sleep(0.5)
    finally:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
    return rows


async def run_scenario_experiment(manager, scenario_id: str, trials: int, mode: str = "rule",
                                   poll: float = 1.0, timeout: float = 120.0):
    """
    Fire a multi-fault scenario and time every incident it creates. Rows carry
    `concurrency` (how many incidents the scenario opened) so the analysis can show
    how MTTR scales when many things fail at once.
    """
    from fault_injector.scenarios import run_scenario, valid_steps

    steps = valid_steps(manager, scenario_id)
    monitor, recorder, _ = build_stack(manager, mode, poll)
    monitor_task = asyncio.create_task(monitor.run())
    rows = []
    try:
        for trial in range(1, trials + 1):
            for _ in range(int(timeout / 0.25)):
                if all(manager.is_service_healthy(sv) and sv not in monitor.active_anomalies
                       for sv, _, _ in steps):
                    break
                await asyncio.sleep(0.25)
            t0 = time.time()
            injections = await run_scenario(manager, scenario_id)
            inject_done = time.time()
            injected_at = {i["service"]: i["injected_at"] for i in injections}

            deadline = inject_done + timeout
            while time.time() < deadline:
                finished = {
                    p["service"] for t, tp, p in recorder.events
                    if t >= t0 and tp == "VALIDATION_RESULT" and p["result"] in ("RECOVERED", "ESCALATED")
                }
                if all(sv in finished for sv, _, _ in steps):
                    break
                await asyncio.sleep(0.2)

            for service, fault, delay in steps:
                t_own = injected_at.get(service, t0)
                row = summarize_trial(recorder.since(t_own, service), t_own, fault)
                row.update({"trial": trial, "service": service, "fault_type": fault, "mode": mode,
                            "scenario": scenario_id, "concurrency": len(steps)})
                rows.append(row)
            print(f"  [{trial}] {scenario_id}: " + ", ".join(
                f"{r['service']}={r['result']}@{r['mttr_s']}s" for r in rows[-len(steps):]))
            await asyncio.sleep(0.5)
    finally:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
    return rows


def summarize(rows: list[dict]) -> dict:
    ok = [float(r["mttr_s"]) for r in rows if r["result"] == "RECOVERED" and r["mttr_s"] != ""]
    out = {"n": len(rows), "recovered": len(ok),
           "recovery_rate": len(ok) / len(rows) if rows else 0.0}
    if ok:
        lo, hi = bootstrap_ci(ok)
        out.update(mean_mttr=mean(ok), sd_mttr=stdev(ok) if len(ok) > 1 else 0.0, ci=[lo, hi],
                   mean_detect=mean(float(r["detect_s"]) for r in rows if r["detect_s"] != ""),
                   first_try=sum(1 for r in rows if r["result"] == "RECOVERED" and r["retries"] == 0) / len(rows))
    return out


FIELDS = ["scenario", "concurrency", "trial", "service", "fault_type", "mode", "detect_s", "diagnose_s", "fix_s",
          "validate_s", "mttr_s", "result", "retries", "root_cause", "diagnosis_correct"]


def write_csv(rows: list[dict], path: str):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, restval="")
        w.writeheader()
        w.writerows(rows)


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--service")
    ap.add_argument("--scenario", help="multi-fault scenario id (see fault_injector/scenarios.py)")
    ap.add_argument("--fault", default="crash", help="crash|slow|memory|error|all")
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--mode", choices=["rule", "llm"], default="rule")
    ap.add_argument("--poll", type=float, default=1.0, help="monitor poll interval (s)")
    args = ap.parse_args()
    # published results used legacy healing; export STRICT_HEALING=1 to change
    os.environ.setdefault("STRICT_HEALING", "0")

    manager = ServiceManager()
    if args.scenario:
        print(f"Scenario experiment: {args.scenario} trials={args.trials} mode={args.mode}")
        rows = await run_scenario_experiment(manager, args.scenario, args.trials, args.mode, args.poll)
        path = os.path.join(HERE, f"pipeline_{args.mode}_scenario_{args.scenario}.csv")
        write_csv(rows, path)
        print(f"\nSaved {path}\nSummary: {summarize(rows)}")
        return
    if not args.service:
        raise SystemExit("provide --service or --scenario")
    if args.service not in manager.services:
        raise SystemExit(f"service '{args.service}' not available. "
                         f"Registered: {list(manager.services)} "
                         "(for nginx: start Docker Desktop and run `docker compose up -d`)")
    faults = FAULT_TYPES if args.fault == "all" else [args.fault]
    kind = type(manager.services[args.service]).__name__
    print(f"Pipeline experiment: {args.service} ({kind}) faults={faults} trials={args.trials} mode={args.mode}")

    rows = await run_pipeline_experiment(manager, args.service, faults, args.trials, args.mode, args.poll)
    path = os.path.join(HERE, f"pipeline_{args.mode}_{args.service}.csv")
    write_csv(rows, path)
    s = summarize(rows)
    print(f"\nSaved {path}\nSummary: {s}")


if __name__ == "__main__":
    asyncio.run(main())
