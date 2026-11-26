"""
run_strategies.py
=================
Three remediation strategies, one set of real incidents, strict healing.

Under STRICT_HEALING a fix only cures a fault if it is actually effective, so
"did it recover?" finally depends on the fix chosen. For every injected fault
we record what each strategy would achieve:

  BLIND RESTART (Kubernetes liveness-probe style): always restart, no
      diagnosis, no verification. Outcome is analytic: restart is in
      EFFECTIVE_FIXES[fault] or it is not (restarting repeatedly changes
      nothing, so repeats are not modelled separately).
  OPEN LOOP: use the diagnoser's first fix once and trust it (diagnose, act,
      hope). Computed from the SAME diagnosis the closed loop received.
  CLOSED LOOP: the real production pipeline over the event bus
      (validate -> retry an alternate fix -> escalate). Measured, not modelled.

Because all three are scored on the same injected faults (and open/closed on
the same diagnosis), comparisons are paired.

    python -m experiments.run_strategies --mode llm  --model openai/gpt-oss-120b --trials 3
    python -m experiments.run_strategies --mode rule --trials 3
      -> experiments/strategies_<name>.csv

Runs with RETRY_POLICY=repeat, the policy behind the published results. Export
RETRY_POLICY=distinct to measure the application's default policy instead.
"""
import argparse
import asyncio
import csv
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import monitor_agent as monitor_module  # noqa: E402
from agents.validation_agent import ValidationAgent  # noqa: E402
from experiments.run_noise import reset_service  # noqa: E402
from experiments.run_pipeline import EXPECTED, build_stack  # noqa: E402
from services.service_manager import ServiceManager  # noqa: E402
from shared.config import EFFECTIVE_FIXES, FAULT_TYPES  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SERVICES = ["auth", "cart", "payment", "inventory", "notification"]
FIELDS = ["name", "trial", "service", "fault", "diagnosed", "diagnosis_correct", "first_fix", "fixes",
          "attempts", "result", "mttr_s", "closed_recovered", "open_recovered", "blind_restart_recovered"]


async def run(name: str, mode: str, trials: int, poll: float, settle: float, timeout: float = 90.0):
    manager = ServiceManager()
    monitor_module.MONITOR_POLL_INTERVAL = poll
    ValidationAgent.VALIDATION_DELAY_SECONDS = settle
    monitor, rec, _ = build_stack(manager, mode, poll)
    ValidationAgent.VALIDATION_DELAY_SECONDS = settle
    task = asyncio.create_task(monitor.run())
    rows = []
    scenarios = [(s, f) for s in SERVICES for f in FAULT_TYPES]
    try:
        for trial in range(1, trials + 1):
            for service, fault in scenarios:
                reset_service(manager, service)
                for _ in range(400):
                    if manager.is_service_healthy(service) and service not in monitor.active_anomalies:
                        break
                    await asyncio.sleep(0.05)
                t0 = time.time()
                manager.inject_fault(service, fault)
                done = []
                deadline = t0 + timeout
                while time.time() < deadline:
                    ev = rec.since(t0, service)
                    done = [(t, p) for t, tp, p in ev
                            if tp == "VALIDATION_RESULT" and p["result"] in ("RECOVERED", "ESCALATED")]
                    if done:
                        break
                    await asyncio.sleep(0.1)
                ev = rec.since(t0, service)
                fixes = [p["fix"] for _, tp, p in ev if tp == "FIX_REQUEST"]
                diag = next((p for _, tp, p in ev if tp == "DIAGNOSIS_READY"), {})
                result = done[0][1]["result"] if done else "TIMEOUT"
                mttr = round(done[0][0] - t0, 2) if done else ""
                reset_service(manager, service)
                first = fixes[0] if fixes else ""
                rows.append({
                    "name": name, "trial": trial, "service": service, "fault": fault,
                    "diagnosed": diag.get("root_cause", ""),
                    "diagnosis_correct": diag.get("root_cause") == EXPECTED[fault],
                    "first_fix": first, "fixes": "|".join(fixes), "attempts": len(fixes),
                    "result": result, "mttr_s": mttr,
                    "closed_recovered": result == "RECOVERED",
                    "open_recovered": first in EFFECTIVE_FIXES[fault],
                    "blind_restart_recovered": "restart" in EFFECTIVE_FIXES[fault],
                })
                r = rows[-1]
                print(f"  [{trial}] {service}/{fault}: diag={r['diagnosed']} fixes={r['fixes']} -> {result}")
                await asyncio.sleep(0.2)
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    return rows


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["rule", "llm"], default="rule")
    ap.add_argument("--model", default=None, help="Groq model id (llm mode)")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--poll", type=float, default=0.3)
    ap.add_argument("--settle", type=float, default=0.5,
                    help="validation wait in s (shortened from 2 s; does not affect correctness)")
    args = ap.parse_args()
    os.environ["STRICT_HEALING"] = "1"
    os.environ.setdefault("RETRY_POLICY", "repeat")

    if args.mode == "llm":
        if not args.model:
            raise SystemExit("--model is required in llm mode")
        os.environ["GROQ_MODEL"] = args.model
        name = args.model.replace("/", "_").replace("-", "_").replace(".", "_")
    else:
        name = "rule_based"

    print(f"Strategies: mode={args.mode} model={args.model} trials={args.trials} (strict healing)")
    rows = await run(name, args.mode, args.trials, args.poll, args.settle)
    path = os.path.join(HERE, f"strategies_{name}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    n = len(rows)
    print(f"\nsaved {path}\n  blind restart {sum(r['blind_restart_recovered'] for r in rows)}/{n}  "
          f"open loop {sum(r['open_recovered'] for r in rows)}/{n}  "
          f"closed loop {sum(r['closed_recovered'] for r in rows)}/{n}")


if __name__ == "__main__":
    asyncio.run(main())
