"""
run_experiments.py
==================
Automated experiment runner for the research paper.

Runs 20 fault scenarios, REPEATS times each (to average out LLM
variability), through BOTH:
- One or more LLMs via Groq
- The rule-based baseline

Records for each trial:
- Was the diagnosis correct? (accuracy)
- What was the MTTR?
- What fix was applied?

Saves per-trial raw rows to experiments/results_{model}.csv and an
aggregated per-scenario summary (mean/std MTTR, accuracy fraction) to
experiments/results_{model}_summary.csv for each model.

HOW TO RUN:
    python -m experiments.run_experiments openai/gpt-oss-120b
    python -m experiments.run_experiments openai/gpt-oss-20b
    python -m experiments.run_experiments qwen/qwen3.8-27b
"""

import asyncio
import csv
import statistics
import time
import os
import sys

# See main.py for why this is needed — agents print emoji that crash on
# Windows' default cp1252 console encoding.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.service_manager import ServiceManager
from agents.diagnosis_agent import DiagnosisAgent
from agents.rule_based_diagnosis import rule_based_diagnose
from shared.config import MANUAL_BASELINE_SECONDS

REPEATS = 3   # trials per scenario, to average out LLM non-determinism

SCENARIOS = [
    # crash faults → expected: service_crash
    {"service": "auth",         "fault": "crash",  "expected": "service_crash"},
    {"service": "cart",         "fault": "crash",  "expected": "service_crash"},
    {"service": "payment",      "fault": "crash",  "expected": "service_crash"},
    {"service": "inventory",    "fault": "crash",  "expected": "service_crash"},
    {"service": "notification", "fault": "crash",  "expected": "service_crash"},

    # memory faults → expected: memory_leak
    {"service": "auth",         "fault": "memory", "expected": "memory_leak"},
    {"service": "cart",         "fault": "memory", "expected": "memory_leak"},
    {"service": "payment",      "fault": "memory", "expected": "memory_leak"},
    {"service": "inventory",    "fault": "memory", "expected": "memory_leak"},
    {"service": "notification", "fault": "memory", "expected": "memory_leak"},

    # slow faults → expected: cpu_overload
    {"service": "auth",         "fault": "slow",   "expected": "cpu_overload"},
    {"service": "cart",         "fault": "slow",   "expected": "cpu_overload"},
    {"service": "payment",      "fault": "slow",   "expected": "cpu_overload"},
    {"service": "inventory",    "fault": "slow",   "expected": "cpu_overload"},
    {"service": "notification", "fault": "slow",   "expected": "cpu_overload"},

    # error faults → expected: error_spike
    {"service": "auth",         "fault": "error",  "expected": "error_spike"},
    {"service": "cart",         "fault": "error",  "expected": "error_spike"},
    {"service": "payment",      "fault": "error",  "expected": "error_spike"},
    {"service": "inventory",    "fault": "error",  "expected": "error_spike"},
    {"service": "notification", "fault": "error",  "expected": "error_spike"},
]


async def run_single_experiment(manager, scenario, diagnosis_agent, trial: int):
    service = scenario["service"]
    fault = scenario["fault"]
    expected = scenario["expected"]

    print(f"\n{'='*50}")
    print(f"Scenario: {service} / {fault} (expected: {expected}) — trial {trial}")

    manager.inject_fault(service, fault)
    detected_at = time.time()
    metrics = manager.get_service_metrics(service)

    llm_result = diagnosis_agent.diagnose(service, metrics)
    llm_correct = llm_result["root_cause"] == expected

    rule_result = rule_based_diagnose(service, metrics)
    rule_correct = rule_result["root_cause"] == expected

    print(f"LLM:   {llm_result['root_cause']} ({'correct' if llm_correct else 'WRONG'})")
    print(f"Rules: {rule_result['root_cause']} ({'correct' if rule_correct else 'WRONG'})")

    fix = llm_result["fix"]
    manager.heal_service(service, fix)

    await asyncio.sleep(2)
    is_healthy = manager.is_service_healthy(service)
    mttr = time.time() - detected_at
    result = "RECOVERED" if is_healthy else "STILL_BROKEN"

    print(f"Result: {result} | MTTR: {mttr:.2f}s")

    return {
        "trial":               trial,
        "service":             service,
        "fault_type":          fault,
        "expected_root_cause": expected,
        "llm_root_cause":      llm_result["root_cause"],
        "llm_correct":         llm_correct,
        "llm_confidence":      llm_result["confidence"],
        "rule_root_cause":     rule_result["root_cause"],
        "rule_correct":        rule_correct,
        "fix_applied":         fix,
        "result":              result,
        "mttr_seconds":        round(mttr, 2),
        "manual_baseline":     MANUAL_BASELINE_SECONDS,
        "time_saved":          round(MANUAL_BASELINE_SECONDS - mttr, 2),
    }


def _model_short_name(model: str) -> str:
    return model.replace("/", "_").replace("-", "_").replace(".", "_")


def _write_summary(results: list, csv_path: str):
    """
    Aggregates per-scenario across trials: accuracy fraction, recovery
    fraction, mean + stdev MTTR (stdev is 0.0 / blank when REPEATS < 2
    trials recovered, since stdev needs at least 2 data points).
    """
    grouped: dict[tuple, list] = {}
    for r in results:
        key = (r["service"], r["fault_type"])
        grouped.setdefault(key, []).append(r)

    rows = []
    for (service, fault_type), trials in grouped.items():
        n = len(trials)
        llm_correct_n = sum(1 for t in trials if t["llm_correct"])
        rule_correct_n = sum(1 for t in trials if t["rule_correct"])
        recovered_n = sum(1 for t in trials if t["result"] == "RECOVERED")
        mttrs = [t["mttr_seconds"] for t in trials if t["result"] == "RECOVERED"]

        rows.append({
            "service":            service,
            "fault_type":         fault_type,
            "expected_root_cause": trials[0]["expected_root_cause"],
            "trials":             n,
            "llm_accuracy":       round(llm_correct_n / n, 3),
            "rule_accuracy":      round(rule_correct_n / n, 3),
            "recovery_rate":      round(recovered_n / n, 3),
            "mean_mttr_seconds":  round(statistics.mean(mttrs), 2) if mttrs else "",
            "stdev_mttr_seconds": round(statistics.stdev(mttrs), 2) if len(mttrs) > 1 else 0.0,
        })

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


async def main(model: str):
    print(f"\nSelf-Healing E-Commerce — Experiment Runner")
    print(f"Model: {model}")
    print(f"{'='*50}")
    print(f"Running {len(SCENARIOS)} scenarios x {REPEATS} trials = "
          f"{len(SCENARIOS) * REPEATS} total runs...\n")

    # override the model in environment
    os.environ["GROQ_MODEL"] = model

    manager = ServiceManager()
    diagnosis_agent = DiagnosisAgent()

    results = []
    total_runs = len(SCENARIOS) * REPEATS
    run_i = 0

    for trial in range(1, REPEATS + 1):
        for scenario in SCENARIOS:
            run_i += 1
            print(f"[{run_i}/{total_runs}]", end="")
            try:
                record = await run_single_experiment(
                    manager, scenario, diagnosis_agent, trial
                )
                results.append(record)
                await asyncio.sleep(1)
            except Exception as e:
                print(f"ERROR: {e}")
                continue

    # save raw per-trial rows
    os.makedirs("experiments", exist_ok=True)
    model_short = _model_short_name(model)
    csv_path = f"experiments/results_{model_short}.csv"
    summary_path = f"experiments/results_{model_short}_summary.csv"

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    _write_summary(results, summary_path)

    # print summary
    total = len(results)
    llm_correct = sum(1 for r in results if r["llm_correct"])
    rule_correct = sum(1 for r in results if r["rule_correct"])
    recovered = sum(1 for r in results if r["result"] == "RECOVERED")
    mttrs = [r["mttr_seconds"] for r in results if r["result"] == "RECOVERED"]
    avg_mttr = statistics.mean(mttrs) if mttrs else 0.0
    std_mttr = statistics.stdev(mttrs) if len(mttrs) > 1 else 0.0

    print(f"\n{'='*50}")
    print(f"MODEL: {model}  ({REPEATS} trials x {len(SCENARIOS)} scenarios = {total} runs)")
    print(f"{'='*50}")
    print(f"LLM accuracy:        {llm_correct}/{total} ({llm_correct/total*100:.0f}%)")
    print(f"Rule accuracy:       {rule_correct}/{total} ({rule_correct/total*100:.0f}%)")
    print(f"Recovery rate:       {recovered}/{total} ({recovered/total*100:.0f}%)")
    print(f"Average MTTR:        {avg_mttr:.2f}s (stdev {std_mttr:.2f}s)")
    print(f"Raw results saved to:     {csv_path}")
    print(f"Per-scenario summary to:  {summary_path}")

    return {
        "model": model,
        "llm_accuracy": f"{llm_correct/total*100:.0f}%",
        "rule_accuracy": f"{rule_correct/total*100:.0f}%",
        "recovery_rate": f"{recovered/total*100:.0f}%",
        "avg_mttr": f"{avg_mttr:.2f}s",
        "stdev_mttr": f"{std_mttr:.2f}s",
    }


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "openai/gpt-oss-120b"
    asyncio.run(main(model))
