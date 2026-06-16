"""
service_manager.py
==================
Manages all 5 simulated e-commerce services together.

Think of this as the "container orchestrator" — like a simplified
Kubernetes. It knows about all services and can:
- Get health of one or all services
- Inject faults into any service
- Heal any service
- Report which services are currently unhealthy

This is what the FastAPI routes and Monitor Agent talk to.
They never touch SimulatedService directly — always go through here.
"""

import time
from services.simulated_service import SimulatedService
from shared.config import SERVICES, FAULT_TYPES


class ServiceManager:
    """
    Single point of control for all 5 microservices.
    Created once when the FastAPI app starts and lives for
    the entire lifetime of the application.
    """

    def __init__(self):
        # Create all 5 services using the config we defined
        self.services: dict[str, SimulatedService] = {}

        for name, info in SERVICES.items():
            self.services[name] = SimulatedService(
                name=name,
                port=info["port"],
                description=info["description"],
            )

        print(f"✅ ServiceManager: {len(self.services)} services initialized")

    # ────────────────────────────────────────────────────────────
    # GET HEALTH
    # ────────────────────────────────────────────────────────────

    def get_all_health(self) -> dict:
        """
        Returns health of ALL services at once.
        The React dashboard calls this every 3-5 seconds
        to update all 5 health tiles simultaneously.
        """
        all_health = {}
        summary = {"ok": 0, "degraded": 0, "down": 0}

        for name, service in self.services.items():
            health = service.get_health()
            all_health[name] = health
            summary[health["status"]] += 1

        return {
            "services": all_health,
            "summary":  summary,
            "total":    len(self.services),
            "timestamp": time.time(),
        }

    def get_service_health(self, name: str) -> dict:
        """
        Returns health of ONE specific service.
        Used by the Monitor Agent when it needs to recheck
        a specific service after a fix is applied.
        """
        if name not in self.services:
            return {"error": f"Service '{name}' not found",
                    "available": list(self.services.keys())}

        return self.services[name].get_health()

    # ────────────────────────────────────────────────────────────
    # INJECT FAULT
    # ────────────────────────────────────────────────────────────

    def inject_fault(self, name: str, fault_type: str) -> dict:
        """
        Break a specific service on purpose.
        Called from:
        - The React dashboard sidebar (demo controls)
        - The fault injector script (inject.py)
        - Automated experiment scripts (Phase 6)
        """
        if name not in self.services:
            return {"error": f"Service '{name}' not found"}

        if fault_type not in FAULT_TYPES:
            return {"error": f"Invalid fault. Choose from: {FAULT_TYPES}"}

        result = self.services[name].inject_fault(fault_type)
        print(f"💥 FAULT INJECTED: {name} → {fault_type}")
        return result

    # ────────────────────────────────────────────────────────────
    # HEAL
    # ────────────────────────────────────────────────────────────

    def heal_service(self, name: str, fix_type: str = "restart") -> dict:
        """
        Heal a specific service.
        Called by the Fix Agent after it decides what action to take.
        fix_type comes from the Diagnosis Agent's recommendation.
        """
        if name not in self.services:
            return {"error": f"Service '{name}' not found"}

        result = self.services[name].heal(fix_type)
        print(f"✅ HEALED: {name} via {fix_type}")
        return result

    # ────────────────────────────────────────────────────────────
    # HELPERS FOR AGENTS
    # ────────────────────────────────────────────────────────────

    def get_unhealthy_services(self) -> list[dict]:
        """
        Returns a list of services that are NOT healthy right now.
        The Monitor Agent calls this to find what needs attention.
        Returns an empty list if everything is fine.
        """
        unhealthy = []

        for name, service in self.services.items():
            health = service.get_health()
            if health["status"] != "ok":
                unhealthy.append(health)

        return unhealthy

    def is_service_healthy(self, name: str) -> bool:
        """
        Simple yes/no health check for one service.
        The Validation Agent uses this after a fix is applied
        to decide RECOVERED or STILL_BROKEN.
        """
        if name not in self.services:
            return False

        health = self.services[name].get_health()
        return health["status"] == "ok"

    def get_service_metrics(self, name: str) -> dict:
        """
        Returns just the numeric metrics for one service
        (no status, no description — just the numbers).
        The Diagnosis Agent sends these to the LLM.
        """
        if name not in self.services:
            return {}

        h = self.services[name].get_health()
        return {
            "service":          name,
            "response_time_ms": h["response_time_ms"],
            "error_rate":       h["error_rate"],
            "memory_percent":   h["memory"],
            "cpu_percent":      h["cpu"],
            "status":           h["status"],
            "active_fault":     h["active_fault"],
            "timestamp":        time.time(),
        }