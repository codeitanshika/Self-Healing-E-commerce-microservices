"""
validation_agent.py
====================
The Validation Agent — confirms whether a fix actually worked.

What it does:
- Subscribes to VALIDATE_REQUEST events
- Waits a short delay (simulates real recovery time)
- Re-checks the service's REAL health (not just trusting the fix)
- Calculates MTTR (Mean Time To Recovery)
- Publishes VALIDATION_RESULT: RECOVERED or STILL_BROKEN

This is the step most existing tools skip — verifying the fix
actually worked, not just assuming it did.
"""

import asyncio
import time
from orchestrator.event_bus import bus
from shared.events import VALIDATE_REQUEST, VALIDATION_RESULT


class ValidationAgent:
    """
    Listens for VALIDATE_REQUEST, re-checks health, publishes VALIDATION_RESULT.
    """

    # how long to wait before re-checking (simulates real recovery time)
    VALIDATION_DELAY_SECONDS = 2

    def __init__(self, service_manager):
        self.service_manager = service_manager
        bus.subscribe(VALIDATE_REQUEST, self.handle_validate_request)
        print("[ValidationAgent] initialized and subscribed")

    # ────────────────────────────────────────────────────────────
    # EVENT HANDLER
    # ────────────────────────────────────────────────────────────

    async def handle_validate_request(self, payload: dict):
        """
        Called automatically when VALIDATE_REQUEST is published.
        payload contains: { service, incident_id, detected_at }
        """
        service = payload["service"]
        incident_id = payload.get("incident_id")
        detected_at = payload.get("detected_at", time.time())

        print(f"[ValidationAgent] {service}: waiting {self.VALIDATION_DELAY_SECONDS}s before re-checking...")

        # Wait before checking — gives the "fix" time to take effect
        await asyncio.sleep(self.VALIDATION_DELAY_SECONDS)

        result, mttr = self.validate(service, detected_at)

        print(f"[ValidationAgent] {service} → {result} (MTTR: {mttr:.2f}s)")

        await bus.publish(VALIDATION_RESULT, {
            "service":      service,
            "incident_id":  incident_id,
            "result":       result,
            "mttr_seconds": round(mttr, 2),
            "timestamp":    time.time(),
        })

    # ────────────────────────────────────────────────────────────
    # CORE LOGIC — separated for standalone testing
    # ────────────────────────────────────────────────────────────

    def validate(self, service: str, detected_at: float) -> tuple[str, float]:
        """
        Re-checks the service's actual health and calculates MTTR.
        Separated from the event handler for standalone testing
        (see __main__ block below).

        Returns: (result, mttr_seconds)
        result is "RECOVERED" or "STILL_BROKEN"
        """
        is_healthy = self.service_manager.is_service_healthy(service)
        mttr = time.time() - detected_at

        if is_healthy:
            return "RECOVERED", mttr
        else:
            return "STILL_BROKEN", mttr


# ────────────────────────────────────────────────────────────────
# STANDALONE TEST
# ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import time as time_module
    from services.service_manager import ServiceManager

    manager = ServiceManager()
    agent = ValidationAgent(manager)

    print("\n--- Test 1: service is healthy (should be RECOVERED) ---")
    detected_at = time_module.time() - 5   # pretend anomaly was detected 5s ago
    result, mttr = agent.validate("payment", detected_at)
    print(f"Result: {result}, MTTR: {mttr:.2f}s")

    print("\n--- Test 2: service is still broken (should be STILL_BROKEN) ---")
    manager.inject_fault("cart", "crash")
    detected_at = time_module.time() - 10  # pretend anomaly was detected 10s ago
    result, mttr = agent.validate("cart", detected_at)
    print(f"Result: {result}, MTTR: {mttr:.2f}s")

    print("\n--- Test 3: heal it, then validate again (should be RECOVERED) ---")
    manager.heal_service("cart", "restart")
    result, mttr = agent.validate("cart", detected_at)
    print(f"Result: {result}, MTTR: {mttr:.2f}s")