"""
fix_agent.py
============
The Fix Agent — executes remediation actions.

What it does:
- Subscribes to FIX_REQUEST events
- Looks up the fix type and calls the matching healing action
  on the actual service (via ServiceManager)
- Publishes FIX_APPLIED with the result

NOTE: this agent does NOT use AI. It's a simple dispatcher —
the "thinking" already happened in the Diagnosis Agent.
"""

import time
from orchestrator.event_bus import bus
from shared.events import FIX_REQUEST, FIX_APPLIED


class FixAgent:
    """
    Listens for FIX_REQUEST, executes the fix, publishes FIX_APPLIED.
    """

    def __init__(self, service_manager):
        # needs the service manager to actually call .heal() on services
        self.service_manager = service_manager

        # all 5 fix types this agent knows how to execute
        # (must match exactly what Diagnosis Agent's prompt promises)
        self.valid_fixes = {
            "restart",
            "clear_memory",
            "reduce_load",
            "reroute_traffic",
            "retry_with_backoff",
        }

        bus.subscribe(FIX_REQUEST, self.handle_fix_request)
        print("[FixAgent] initialized and subscribed")

    # ────────────────────────────────────────────────────────────
    # EVENT HANDLER
    # ────────────────────────────────────────────────────────────

    async def handle_fix_request(self, payload: dict):
        """
        Called automatically when FIX_REQUEST is published.
        payload contains: { service, fix, incident_id }
        """
        service = payload["service"]
        fix = payload["fix"]
        incident_id = payload.get("incident_id")

        print(f"[FixAgent] {service}: applying fix '{fix}'")

        start_time = time.time()
        result = self.apply_fix(service, fix)
        fix_duration = time.time() - start_time

        await bus.publish(FIX_APPLIED, {
            "service":      service,
            "incident_id":  incident_id,
            "fix_applied":  fix,
            "fix_time":     round(fix_duration, 3),
            "success":      result["success"],
            "timestamp":    time.time(),
        })

    # ────────────────────────────────────────────────────────────
    # CORE LOGIC — separated for standalone testing
    # ────────────────────────────────────────────────────────────

    def apply_fix(self, service: str, fix: str) -> dict:
        """
        Executes the actual fix on the service.
        Separated from the event handler so it can be tested
        directly without the event bus (see __main__ block).
        """
        if fix not in self.valid_fixes:
            print(f"[FixAgent] ⚠️  unknown fix '{fix}', defaulting to 'restart'")
            fix = "restart"

        result = self.service_manager.heal_service(service, fix)

        if "error" in result:
            print(f"[FixAgent] ❌ failed to fix {service}: {result['error']}")
            return {"success": False, "detail": result["error"]}

        print(f"[FixAgent] ✅ {service} fix '{fix}' applied")
        return {"success": True, "detail": result}


# ────────────────────────────────────────────────────────────────
# STANDALONE TEST
# ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from services.service_manager import ServiceManager

    manager = ServiceManager()
    agent = FixAgent(manager)

    # Test each of the 5 fix types
    fixes_to_test = [
        ("payment", "restart"),
        ("inventory", "clear_memory"),
        ("cart", "reduce_load"),
        ("auth", "reroute_traffic"),
        ("notification", "retry_with_backoff"),
    ]

    for service, fix in fixes_to_test:
        # break it first so the fix has something to actually fix
        manager.inject_fault(service, "crash")
        print(f"\n--- Testing fix '{fix}' on {service} ---")
        result = agent.apply_fix(service, fix)
        print(result)

        # confirm it's healthy now
        health = manager.get_service_health(service)
        print(f"Status after fix: {health['status']}")