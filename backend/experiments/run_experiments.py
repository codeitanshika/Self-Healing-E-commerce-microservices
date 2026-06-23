"""
run_experiments.py
==================
Automated experiment runner for the research paper.

Runs 20 fault scenarios through BOTH:
- The LLM-based diagnosis (Groq / Llama 3.3)
- The rule-based baseline

Records for each:
- Was the diagnosis correct? (accuracy)
- What was the MTTR?
- Did it need retries?
- What fix was applied?

Saves results to experiments/results.csv for paper tables/charts.

HOW TO RUN:
    python -m experiments.run_experiments

Takes ~5-10 minutes (LLM calls + healing delays × 20 scenarios).
"""

import asyncio
import csv
import time
import os
import sys

# add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.service_manager import ServiceManager
from agents.diagnosis_agent import DiagnosisAgent
from agents.rule_based_diagnosis import rule_based_diagnose
from shared.config import MANUAL_BASELINE_SECONDS

# ── The 20 experiment scenarios ──────────────────────────────────
# 5 services × 4 fault types = 20 combinations
# Each defines: which service, which fault, and the EXPECTED root cause
# (so we can check if diagnosis was correct)

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

    # slow faults → expected: cpu_overload (high CPU is the sim's slow signal)
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
    """
    Runs ONE experiment scenario end to end:
    1. Inject fault
    2. Get metrics
    3. Run LLM diagnosis
    4. Run rule-based diagnosis
    5. Apply fix
    6. Validate recovery
    7. Record results
    """
    service = scenario["service"]
    fault = scenario["fault"]
    expected = scenario["expected"]

    print(f"\n{'='*60}")
    print(f"Scenario: {service} / {fault} (expected: {expected})")

    # Step 1: inject fault
    manager.inject_fault(service, fault)
    detected_at = time.time()

    # Step 2: get metrics (what the monitor would see)
    metrics = manager.get_service_metrics(service)

    # Step 3: LLM diagnosis
    llm_result = diagnosis_agent.diagnose(service, metrics)
    llm_correct = llm_result["root_cause"] == expected

    # Step 4: rule-based diagnosis
    rule_result = rule_based_diagnose(service, metrics)
    rule_correct = rule_result["root_cause"] == expected

    print(f"LLM:   {llm_result['root_cause']} ({'✅' if llm_correct else '❌'})")
    print(f"Rules: {rule_result['root_cause']} ({'✅' if rule_correct else '❌'})")

    # Step 5: apply the LLM's recommended fix
    fix = llm_result["fix"]
    manager.heal_service(service, fix)

    # Step 6: wait then validate
    await asyncio.sleep(2)
    is_healthy = manager.is_service_healthy(service)
    mttr = time.time() - detected_at
    result = "RECOVERED" if is_healthy else "STILL_BROKEN"

    print(f"Result: {result} | MTTR: {mttr:.2f}s")

    # Step 7: return the full record
    return {
        "service":              service,
        "fault_type":           fault,
        "expected_root_cause":  expected,
        "llm_root_cause":       llm_result["root_cause"],
        "llm_correct":          llm_correct,
        "llm_confidence":       llm_result["confidence"],
        "rule_root_cause":      rule_result["root_cause"],
        "rule_correct":         rule_correct,
        "fix_applied":          fix,
        "result":               result,
        "mttr_seconds":         round(mttr, 2),
        "manual_baseline":      MANUAL_BASELINE_SECONDS,
        "time_saved":           round(MANUAL_BASELINE_SECONDS - mttr, 2),
        "revenue_per_second":   15.0,   # using payment rate as illustrative
    }


async def main():
    print("Self-Healing E-Commerce — Experiment Runner")
    print("=" * 60)
    print(f"Running {len(SCENARIOS)} scenarios...")
    print("This will take ~5-10 minutes (LLM calls + delays)\n")

    manager = ServiceManager()
    diagnosis_agent = DiagnosisAgent()

    results = []

    for i, scenario in enumerate(SCENARIOS):
        print(f"\n[{i+1}/{len(SCENARIOS)}]", end="")
        try:
            record = await run_single_experiment(manager, scenario, diagnosis_agent)
            results.append(record)
            # small delay between experiments to avoid Groq rate limits
            await asyncio.sleep(1)
        except Exception as e:
            print(f"ERROR in scenario {scenario}: {e}")
            continue

    # ── Save results to CSV ──────────────────────────────────────
    os.makedirs("experiments", exist_ok=True)
    csv_path = "experiments/results.csv"

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"\n\n{'='*60}")
    print(f"RESULTS SAVED TO: {csv_path}")
    print(f"{'='*60}")

    # ── Print summary ────────────────────────────────────────────
    total = len(results)
    llm_correct = sum(1 for r in results if r["llm_correct"])
    rule_correct = sum(1 for r in results if r["rule_correct"])
    recovered = sum(1 for r in results if r["result"] == "RECOVERED")
    avg_mttr = sum(r["mttr_seconds"] for r in results) / total

    print(f"\nSUMMARY")
    print(f"Total scenarios:        {total}")
    print(f"LLM accuracy:           {llm_correct}/{total} ({llm_correct/total*100:.0f}%)")
    print(f"Rule-based accuracy:    {rule_correct}/{total} ({rule_correct/total*100:.0f}%)")
    print(f"Recovery rate:          {recovered}/{total} ({recovered/total*100:.0f}%)")
    print(f"Average MTTR:           {avg_mttr:.2f}s")
    print(f"Manual baseline:        {MANUAL_BASELINE_SECONDS}s")
    print(f"Avg time saved:         {MANUAL_BASELINE_SECONDS - avg_mttr:.2f}s per incident")


if __name__ == "__main__":
    asyncio.run(main())