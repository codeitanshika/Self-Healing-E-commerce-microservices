"""
rule_based_diagnosis.py
=======================
Rule-Based Baseline Healer — used for research paper comparison.

This is Baseline 2 (the stronger one). It diagnoses faults using
plain if-else threshold rules instead of an LLM.

WHY THIS EXISTS:
The paper needs to prove the LLM adds value over simple rules.
We run the same 20 fault scenarios through both this rule-based
system AND the LLM-based system, then compare:
- Diagnosis accuracy (did it name the right root cause?)
- MTTR (how fast did it recover?)
- First-try success rate

If the LLM is meaningfully better → that IS the paper's result.
If they're roughly equal → that is ALSO a valid finding (saves cost).
Either way, you have a real, measured comparison.
"""


def rule_based_diagnose(service: str, metrics: dict) -> dict:
    """
    Diagnoses a fault using explicit threshold rules.
    Same input/output shape as the LLM-based Diagnosis Agent
    so results are directly comparable.

    Decision logic matches the priority rules we gave the LLM
    (so any difference in accuracy is due to the LLM's reasoning,
    not different rule sets — a fair comparison).
    """
    status = metrics.get("status", "ok")
    response_time = metrics.get("response_time_ms", 0)
    error_rate = metrics.get("error_rate", 0.0)
    memory = metrics.get("memory_percent", 0.0)
    cpu = metrics.get("cpu_percent", 0.0)

    # Rule 1: service is completely down
    if status == "down":
        return {
            "root_cause":      "service_crash",
            "confidence":      100,
            "fix":             "restart",
            "business_impact": f"{service} is completely unavailable",
            "explanation":     "Rule: status == down → service_crash",
            "method":          "rule_based",
        }

    # Rule 2: memory very high → memory leak
    if memory > 85.0:
        return {
            "root_cause":      "memory_leak",
            "confidence":      90,
            "fix":             "clear_memory",
            "business_impact": f"{service} memory exhaustion causing degradation",
            "explanation":     f"Rule: memory_percent {memory:.1f}% > 85% → memory_leak",
            "method":          "rule_based",
        }

    # Rule 3: error rate high → error spike
    if error_rate > 0.3:
        return {
            "root_cause":      "error_spike",
            "confidence":      90,
            "fix":             "retry_with_backoff",
            "business_impact": f"{service} failing {error_rate*100:.0f}% of requests",
            "explanation":     f"Rule: error_rate {error_rate:.2f} > 0.3 → error_spike",
            "method":          "rule_based",
        }

    # Rule 4: slow response but normal CPU → high latency
    if response_time > 2000 and cpu < 50:
        return {
            "root_cause":      "high_latency",
            "confidence":      80,
            "fix":             "reroute_traffic",
            "business_impact": f"{service} responding slowly ({response_time}ms)",
            "explanation":     f"Rule: response_time {response_time}ms > 2000 and cpu {cpu:.0f}% < 50 → high_latency",
            "method":          "rule_based",
        }

    # Rule 5: high CPU → cpu overload
    if cpu > 85:
        return {
            "root_cause":      "cpu_overload",
            "confidence":      85,
            "fix":             "reduce_load",
            "business_impact": f"{service} CPU saturated at {cpu:.0f}%",
            "explanation":     f"Rule: cpu_percent {cpu:.0f}% > 85 → cpu_overload",
            "method":          "rule_based",
        }

    # No rule matched — default
    return {
        "root_cause":      "unknown",
        "confidence":      30,
        "fix":             "restart",
        "business_impact": "Unknown degradation",
        "explanation":     "No rule matched — defaulting to restart",
        "method":          "rule_based",
    }


# ────────────────────────────────────────────────────────────────
# STANDALONE TEST
# ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Same 5 test cases as the LLM diagnosis agent
    # so we can directly compare accuracy
    test_cases = [
        {"service": "payment",      "metrics": {"status": "down",     "response_time_ms": 0,    "error_rate": 1.0,  "memory_percent": 0,    "cpu_percent": 0}},
        {"service": "inventory",    "metrics": {"status": "degraded", "response_time_ms": 300,  "error_rate": 0.05, "memory_percent": 92.0, "cpu_percent": 45}},
        {"service": "cart",         "metrics": {"status": "degraded", "response_time_ms": 5000, "error_rate": 0.1,  "memory_percent": 40,   "cpu_percent": 96}},
        {"service": "auth",         "metrics": {"status": "degraded", "response_time_ms": 4500, "error_rate": 0.08, "memory_percent": 38,   "cpu_percent": 35}},
        {"service": "notification", "metrics": {"status": "degraded", "response_time_ms": 350,  "error_rate": 0.55, "memory_percent": 42,   "cpu_percent": 60}},
    ]

    print("Rule-Based Baseline Results:")
    print("=" * 60)
    for case in test_cases:
        result = rule_based_diagnose(case["service"], case["metrics"])
        print(f"\nService:    {case['service']}")
        print(f"Root cause: {result['root_cause']}")
        print(f"Fix:        {result['fix']}")
        print(f"Confidence: {result['confidence']}%")
        print(f"Reasoning:  {result['explanation']}")