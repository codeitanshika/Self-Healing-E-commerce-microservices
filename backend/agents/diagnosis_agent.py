"""
diagnosis_agent.py
===================
The Diagnosis Agent — the ONLY agent that uses AI.

What it does:
- Subscribes to DIAGNOSE_REQUEST events
- Builds a structured prompt with the service's metrics
- Asks Groq (Llama 3.3) to return a root cause + recommended fix
- Publishes DIAGNOSIS_READY with the result

It NEVER fixes anything itself — it only diagnoses.
"""

import time
from orchestrator.event_bus import bus
from shared.events import DIAGNOSE_REQUEST, DIAGNOSIS_READY
from shared.llm import ask_llm


class DiagnosisAgent:
    """
    Listens for DIAGNOSE_REQUEST, calls the LLM, publishes DIAGNOSIS_READY.
    """

    def __init__(self):
        # Subscribe to the event bus immediately on creation
        bus.subscribe(DIAGNOSE_REQUEST, self.handle_diagnose_request)
        print("[DiagnosisAgent] initialized and subscribed")

    # ────────────────────────────────────────────────────────────
    # EVENT HANDLER
    # ────────────────────────────────────────────────────────────

    async def handle_diagnose_request(self, payload: dict):
        """
        Called automatically by the event bus whenever
        DIAGNOSE_REQUEST is published.

        payload contains: { service, metrics, incident_id }
        """
        service = payload["service"]
        metrics = payload["metrics"]
        incident_id = payload.get("incident_id")

        print(f"[DiagnosisAgent] diagnosing {service}...")

        diagnosis = self.diagnose(service, metrics)

        print(f"[DiagnosisAgent] {service} → {diagnosis['root_cause']} "
              f"(confidence {diagnosis['confidence']}%) → fix: {diagnosis['fix']}")

        # Publish the result for the Orchestrator to pick up
        await bus.publish(DIAGNOSIS_READY, {
            "service":         service,
            "incident_id":     incident_id,
            "root_cause":      diagnosis["root_cause"],
            "confidence":      diagnosis["confidence"],
            "fix":             diagnosis["fix"],
            "business_impact": diagnosis["business_impact"],
            "explanation":     diagnosis["explanation"],
            "timestamp":       time.time(),
        })

    # ────────────────────────────────────────────────────────────
    # CORE LOGIC — build prompt, call LLM
    # ────────────────────────────────────────────────────────────

    def diagnose(self, service: str, metrics: dict) -> dict:
        """
        Builds the prompt and calls the LLM.
        Separated from the event handler so we can test it directly
        with hardcoded metrics (see __main__ block below).
        """
        prompt = self._build_prompt(service, metrics)
        return ask_llm(prompt)

    def _build_prompt(self, service: str, metrics: dict) -> str:
        """
        The actual prompt engineering.
        Notice the 4 parts: context, data, constraints, output format.
        """
        return f"""You are a Site Reliability Engineer diagnosing a microservice failure.

SERVICE: {service}
METRICS:
- status: {metrics.get('status')}
- response_time_ms: {metrics.get('response_time_ms')}
- error_rate: {metrics.get('error_rate')}
- memory_percent: {metrics.get('memory_percent')}
- cpu_percent: {metrics.get('cpu_percent')}
Based on these metrics, identify the SINGLE most abnormal signal and classify accordingly.

Decision priority (check in this order, stop at the first match):
1. If status is "down" → service_crash
2. If memory_percent > 85 → memory_leak
3. If error_rate > 0.3 → error_spike
4. If response_time_ms > 2000 AND cpu_percent < 50 → high_latency
5. If cpu_percent > 85 → cpu_overload

root_cause MUST be exactly one of:
- service_crash
- memory_leak
- cpu_overload
- high_latency
- error_spike

fix MUST be exactly one of:
- restart
- clear_memory
- reduce_load
- reroute_traffic
- retry_with_backoff

Reply with ONLY this JSON, no other text, no markdown formatting:
{{
  "root_cause": "...",
  "confidence": <integer 0-100>,
  "fix": "...",
  "business_impact": "<one short sentence on customer/revenue impact>",
  "explanation": "<one short sentence on why you chose this root cause>"
}}"""


# ────────────────────────────────────────────────────────────────
# STANDALONE TEST (run this file directly to test without the event bus)
# ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    agent = DiagnosisAgent()

    # 5 test scenarios — one per fault type, matching code-standards.md
    test_cases = [
        {"service": "payment", "metrics": {"status": "down", "response_time_ms": 0,
         "error_rate": 1.0, "memory_percent": 0, "cpu_percent": 0}},

        {"service": "inventory", "metrics": {"status": "degraded", "response_time_ms": 300,
         "error_rate": 0.05, "memory_percent": 92.0, "cpu_percent": 45}},

        {"service": "cart", "metrics": {"status": "degraded", "response_time_ms": 5000,
         "error_rate": 0.1, "memory_percent": 40, "cpu_percent": 96}},

        {"service": "auth", "metrics": {"status": "degraded", "response_time_ms": 4500,
         "error_rate": 0.08, "memory_percent": 38, "cpu_percent": 35}},

        {"service": "notification", "metrics": {"status": "degraded", "response_time_ms": 350,
         "error_rate": 0.55, "memory_percent": 42, "cpu_percent": 60}},
    ]

    for case in test_cases:
        print(f"\n--- Testing {case['service']} ---")
        result = agent.diagnose(case["service"], case["metrics"])
        print(result)