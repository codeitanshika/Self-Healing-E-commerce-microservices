"""
run_experiments.py
==================
Automated experiment runner for the research paper.

Runs 20 fault scenarios through BOTH:
- Multiple LLMs (Llama 3.3, Llama 3.1, Mixtral) via Groq
- The rule-based baseline

Records for each:
- Was the diagnosis correct? (accuracy)
- What was the MTTR?
- What fix was applied?

Saves results to experiments/results_{model}.csv for each model.

HOW TO RUN:
    python -m experiments.run_experiments llama-3.3-70b-versatile
    python -m experiments.run_experiments llama-3.1-70b-versatile  
    python -m experiments.run_experiments mixtral-8x7b-32768
"""

import asyncio
import csv
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.service_manager import ServiceManager
from agents.diagnosis_agent import DiagnosisAgent
from agents.rule_based_diagnosis import rule_based_diagnose
from shared.config import MANUAL_BASELINE_SECONDS

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


async def run_single_experiment(manager, scenario, diagnosis_agent):
    service = scenario["service"]
    fault = scenario["fault"]
    expected = scenario["expected"]

    print(f"\n{'='*50}")
    print(f"Scenario: {service} / {fault} (expected: {expected})")

    manager.inject_fault(service, fault)
    detected_at = time.time()
    metrics = manager.get_service_metrics(service)

    llm_result = diagnosis_agent.diagnose(service, metrics)
    llm_correct = llm_result["root_cause"] == expected

    rule_result = rule_based_diagnose(service, metrics)
    rule_correct = rule_result["root_cause"] == expected

    print(f"LLM:   {llm_result['root_cause']} ({'✅' if llm_correct else '❌'})")
    print(f"Rules: {rule_result['root_cause']} ({'✅' if rule_correct else '❌'})")

    fix = llm_result["fix"]
    manager.heal_service(service, fix)

    await asyncio.sleep(2)
    is_healthy = manager.is_service_healthy(service)
    mttr = time.time() - detected_at
    result = "RECOVERED" if is_healthy else "STILL_BROKEN"

    print(f"Result: {result} | MTTR: {mttr:.2f}s")

    return {
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


async def main(model: str):
    print(f"\nSelf-Healing E-Commerce — Experiment Runner")
    print(f"Model: {model}")
    print(f"{'='*50}")
    print(f"Running {len(SCENARIOS)} scenarios...\n")

    # override the model in environment
    os.environ["GROQ_MODEL"] = model

    manager = ServiceManager()
    diagnosis_agent = DiagnosisAgent()

    results = []

    for i, scenario in enumerate(SCENARIOS):
        print(f"[{i+1}/{len(SCENARIOS)}]", end="")
        try:
            record = await run_single_experiment(
                manager, scenario, diagnosis_agent
            )
            results.append(record)
            await asyncio.sleep(1)
        except Exception as e:
            print(f"ERROR: {e}")
            continue

    # save to model-specific CSV
    os.makedirs("experiments", exist_ok=True)
    model_short = model.replace("-", "_").replace(".", "_")
    csv_path = f"experiments/results_{model_short}.csv"

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    # print summary
    total = len(results)
    llm_correct = sum(1 for r in results if r["llm_correct"])
    rule_correct = sum(1 for r in results if r["rule_correct"])
    recovered = sum(1 for r in results if r["result"] == "RECOVERED")
    avg_mttr = sum(r["mttr_seconds"] for r in results) / total

    print(f"\n{'='*50}")
    print(f"MODEL: {model}")
    print(f"{'='*50}")
    print(f"LLM accuracy:        {llm_correct}/{total} ({llm_correct/total*100:.0f}%)")
    print(f"Rule accuracy:       {rule_correct}/{total} ({rule_correct/total*100:.0f}%)")
    print(f"Recovery rate:       {recovered}/{total} ({recovered/total*100:.0f}%)")
    print(f"Average MTTR:        {avg_mttr:.2f}s")
    print(f"Results saved to:    {csv_path}")

    return {
        "model": model,
        "llm_accuracy": f"{llm_correct/total*100:.0f}%",
        "rule_accuracy": f"{rule_correct/total*100:.0f}%",
        "recovery_rate": f"{recovered/total*100:.0f}%",
        "avg_mttr": f"{avg_mttr:.2f}s",
    }


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "llama-3.3-70b-versatile"
    asyncio.run(main(model))