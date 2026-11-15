"""
run_noise.py
============
Does verify-and-retry actually earn its keep?

The paper's central architectural claim is that *verifying* a fix (and
retrying a different one) is what separates this system from "diagnose and
hope". Until STRICT_HEALING existed that claim was untestable, because every
fix cured every fault. This experiment tests it directly:

  * A diagnoser is made wrong on a fraction `p` of incidents (a stand-in for
    LLM error, sweeping from perfect to mostly wrong).
  * CLOSED LOOP  = the real pipeline (Validation -> retry alternate fix ->
    escalate). Run end-to-end over the event bus.
  * OPEN LOOP    = the same diagnosis, apply its first fix once, trust it.
    Computed from the SAME sampled diagnoses (paired design), so any
    difference is attributable to the verify/retry loop alone.

    python -m experiments.run_noise --trials 30
      -> experiments/noise_closed_loop.csv
"""
import argparse
import asyncio
import csv
import os
import random
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["STRICT_HEALING"] = "1"           # the whole point of this experiment

from agents import monitor_agent as monitor_module  # noqa: E402
from agents.fix_agent import FixAgent  # noqa: E402
from agents.monitor_agent import MonitorAgent  # noqa: E402
from agents.rule_based_diagnosis import rule_based_diagnose  # noqa: E402
from agents.validation_agent import ValidationAgent  # noqa: E402
from experiments.run_pipeline import EXPECTED, Recorder  # noqa: E402
from orchestrator.event_bus import bus  # noqa: E402
from orchestrator.orchestrator import Orchestrator  # noqa: E402
from services.service_manager import ServiceManager  # noqa: E402
from shared.config import EFFECTIVE_FIXES, FIX_MAP, FAULT_TYPES, MAX_RETRIES  # noqa: E402
from shared.events import DIAGNOSE_REQUEST, DIAGNOSIS_READY  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CAUSES = list(EXPECTED.values())             # the 4 diagnosable root causes
SERVICES = ["auth", "cart", "payment", "inventory", "notification"]


class NoisyDiagnosisAgent:
    """Correct (rule-based) diagnosis, replaced by a random WRONG cause with prob p."""

    def __init__(self, p: float, rng: random.Random):
        self.p, self.rng = p, rng
        self.log: dict[str, dict] = {}       # service -> last diagnosis made
        bus.subscribe(DIAGNOSE_REQUEST, self.handle)

    async def handle(self, payload: dict):
        right = rule_based_diagnose(payload["service"], payload["metrics"])["root_cause"]
        cause = right
        if self.rng.random() < self.p:
            cause = self.rng.choice([c for c in CAUSES if c != right])
        self.log[payload["service"]] = {"truth": right, "diagnosed": cause}
        await bus.publish(DIAGNOSIS_READY, {
            "service": payload["service"], "incident_id": payload["incident_id"],
            "root_cause": cause, "confidence": 80, "fix": FIX_MAP[cause]["primary"],
            "business_impact": "", "explanation": f"noisy diagnoser (p={self.p})",
        })


def reset_service(manager, service: str):
    """
    Return a service to health between trials. In strict mode an ESCALATED
    incident leaves the service genuinely broken (that is the point), so the
    harness must repair it itself or every later trial starts from a broken
    service and the run stalls.
    """
    for fix in ("restart", "clear_memory", "reduce_load", "retry_with_backoff"):
        if manager.is_service_healthy(service):
            return
        manager.heal_service(service, fix)


def open_loop_recovers(fault: str, diagnosed: str) -> bool:
    """Would applying only the diagnosed cause's primary fix cure this fault?"""
    return FIX_MAP[diagnosed]["primary"] in EFFECTIVE_FIXES[fault]


async def run_level(p: float, trials: int, seed: int, poll: float, settle: float):
    rng = random.Random(seed)
    manager = ServiceManager()
    bus._subscribers.clear()
    bus._wildcard.clear()
    monitor_module.MONITOR_POLL_INTERVAL = poll
    ValidationAgent.VALIDATION_DELAY_SECONDS = settle
    Orchestrator()
    diag = NoisyDiagnosisAgent(p, rng)
    FixAgent(manager)
    ValidationAgent(manager)
    monitor = MonitorAgent(manager)
    rec = Recorder()
    bus.subscribe_all(rec)
    task = asyncio.create_task(monitor.run())
    rows = []
    try:
        for t in range(1, trials + 1):
            service, fault = rng.choice(SERVICES), rng.choice(FAULT_TYPES)
            reset_service(manager, service)
            for _ in range(400):
                if manager.is_service_healthy(service) and service not in monitor.active_anomalies:
                    break
                await asyncio.sleep(0.05)
            t0 = time.time()
            manager.inject_fault(service, fault)
            for _ in range(int(120 / 0.1)):
                done = [pl for ts, tp, pl in rec.since(t0, service)
                        if tp == "VALIDATION_RESULT" and pl["result"] in ("RECOVERED", "ESCALATED")]
                if done:
                    break
                await asyncio.sleep(0.1)
            reset_service(manager, service)          # escalated => still broken; repair it
            d = diag.log.get(service, {})
            result = done[0]["result"] if done else "TIMEOUT"
            fixes = sum(1 for _, tp, _ in rec.since(t0, service) if tp == "FIX_REQUEST")
            diagnosed = d.get("diagnosed", "")
            rows.append({
                "p_wrong": p, "trial": t, "service": service, "fault": fault,
                "diagnosis_correct": d.get("truth") == d.get("diagnosed"),
                "diagnosed": diagnosed, "closed_result": result, "fix_attempts": fixes,
                "closed_recovered": result == "RECOVERED",
                "open_recovered": open_loop_recovers(fault, diagnosed) if diagnosed else False,
            })
            await asyncio.sleep(0.2)
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    return rows


FIELDS = ["p_wrong", "trial", "service", "fault", "diagnosis_correct", "diagnosed",
          "closed_result", "fix_attempts", "closed_recovered", "open_recovered"]


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=30, help="incidents per noise level")
    ap.add_argument("--levels", default="0,0.25,0.5,0.75")
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--poll", type=float, default=0.3)
    ap.add_argument("--settle", type=float, default=0.4,
                    help="validation wait (s); shortened from 2 s since it does not affect correctness")
    args = ap.parse_args()

    rows = []
    for p in [float(x) for x in args.levels.split(",")]:
        print(f"noise p={p} ...")
        level = await run_level(p, args.trials, args.seed, args.poll, args.settle)
        rows += level
        c = sum(r["closed_recovered"] for r in level)
        o = sum(r["open_recovered"] for r in level)
        print(f"  closed-loop recovered {c}/{len(level)}   open-loop {o}/{len(level)}")
    path = os.path.join(HERE, "noise_closed_loop.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print("saved", path, f"(retry budget = {MAX_RETRIES})")


if __name__ == "__main__":
    asyncio.run(main())
