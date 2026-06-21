"""
report_agent.py
================
The Report Agent — the only agent allowed to write to the database.

What it does:
- Subscribes to VALIDATION_RESULT events
- Calculates revenue protected
- Writes one Incident row to SQLite
- Publishes INCIDENT_LOGGED (mostly for the debug event log;
  the dashboard reads the DB directly, not via this event)

IMPORTANT: this is the ONLY agent that writes to incidents.db.
Everything else (dashboard, other agents) only reads.
"""

import time
from sqlmodel import Session
from orchestrator.event_bus import bus
from shared.events import VALIDATION_RESULT, INCIDENT_LOGGED
from shared.config import MANUAL_BASELINE_SECONDS, REVENUE_PER_SECOND
from database.models import Incident, engine


class ReportAgent:
    """
    Listens for VALIDATION_RESULT, writes the incident to SQLite.
    """

    def __init__(self, incident_cache: dict):
        """
        incident_cache: a shared dict the Orchestrator uses to track
        in-progress incident details (root_cause, fix, etc.) by incident_id.
        The Report Agent reads from this cache to assemble the full row,
        since VALIDATION_RESULT alone doesn't carry the diagnosis details.
        """
        self.incident_cache = incident_cache
        bus.subscribe(VALIDATION_RESULT, self.handle_validation_result)
        print("[ReportAgent] initialized and subscribed")

    # ────────────────────────────────────────────────────────────
    # EVENT HANDLER
    # ────────────────────────────────────────────────────────────

    async def handle_validation_result(self, payload: dict):
        """
        Called automatically when VALIDATION_RESULT is published.
        payload contains: { service, incident_id, result, mttr_seconds }
        """
        incident_id = payload.get("incident_id")
        result = payload["result"]
        mttr = payload["mttr_seconds"]
        service = payload["service"]

        # Pull the rest of the incident's details from the shared cache
        # (root_cause, fix_applied, etc. were stored there earlier
        #  by the Orchestrator as the incident progressed)
        details = self.incident_cache.get(incident_id, {})

        incident_id_saved = self.log_incident(
            service=service,
            fault_type=details.get("fault_type", "unknown"),
            root_cause=details.get("root_cause", "unknown"),
            confidence=details.get("confidence", 0),
            business_impact=details.get("business_impact", ""),
            explanation=details.get("explanation", ""),
            fix_applied=details.get("fix_applied", "unknown"),
            retry_count=details.get("retry_count", 0),
            result=result,
            mttr_seconds=mttr,
        )

        print(f"[ReportAgent] logged incident #{incident_id_saved} for {service} → {result}")

        await bus.publish(INCIDENT_LOGGED, {
            "incident_db_id": incident_id_saved,
            "service":        service,
            "result":         result,
            "mttr_seconds":   mttr,
            "timestamp":      time.time(),
        })

    # ────────────────────────────────────────────────────────────
    # CORE LOGIC — separated for standalone testing
    # ────────────────────────────────────────────────────────────

    def log_incident(self, service: str, fault_type: str, root_cause: str,
                      confidence: int, business_impact: str, explanation: str,
                      fix_applied: str, retry_count: int,
                      result: str, mttr_seconds: float) -> int:
        """
        Writes one Incident row to the database.
        Returns the new row's id.
        """
        revenue = self._calculate_revenue_protected(service, mttr_seconds, result)

        incident = Incident(
            service=service,
            fault_type=fault_type,
            root_cause=root_cause,
            confidence=confidence,
            business_impact=business_impact,
            explanation=explanation,
            fix_applied=fix_applied,
            retry_count=retry_count,
            result=result,
            mttr_seconds=mttr_seconds,
            revenue_protected=revenue,
            timestamp=time.time(),
        )

        with Session(engine) as session:
            session.add(incident)
            session.commit()
            session.refresh(incident)
            return incident.id

    def _calculate_revenue_protected(self, service: str, mttr: float, result: str) -> float:
        """
        revenue_protected = max(0, baseline - actual_mttr) * revenue_per_second

        Only counts if RECOVERED — an escalated/still-broken incident
        didn't actually protect any revenue.
        """
        if result != "RECOVERED":
            return 0.0

        seconds_saved = max(0, MANUAL_BASELINE_SECONDS - mttr)
        rate = REVENUE_PER_SECOND.get(service, 1.0)
        return round(seconds_saved * rate, 2)


# ────────────────────────────────────────────────────────────────
# STANDALONE TEST
# ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from database.models import init_db

    init_db()   # creates incidents.db if it doesn't exist

    agent = ReportAgent(incident_cache={})

    print("\n--- Logging a sample RECOVERED incident ---")
    incident_id = agent.log_incident(
        service="payment",
        fault_type="crash",
        root_cause="service_crash",
        confidence=100,
        business_impact="Customers unable to checkout",
        explanation="Status was down with 100% error rate",
        fix_applied="restart",
        retry_count=0,
        result="RECOVERED",
        mttr_seconds=47.0,
    )
    print(f"Saved incident #{incident_id}")

    print("\n--- Logging a sample ESCALATED incident (no revenue protected) ---")
    incident_id_2 = agent.log_incident(
        service="cart",
        fault_type="slow",
        root_cause="cpu_overload",
        confidence=70,
        business_impact="Slow cart actions",
        explanation="High CPU detected",
        fix_applied="reduce_load",
        retry_count=2,
        result="ESCALATED",
        mttr_seconds=180.0,
    )
    print(f"Saved incident #{incident_id_2}")

    # Read back what we wrote, to confirm it's really in the DB
    from sqlmodel import Session, select
    with Session(engine) as session:
        all_incidents = session.exec(select(Incident)).all()
        print(f"\n--- Total incidents in DB: {len(all_incidents)} ---")
        for inc in all_incidents:
            print(f"#{inc.id} | {inc.service} | {inc.root_cause} | {inc.result} | "
                  f"MTTR={inc.mttr_seconds}s | Revenue=₹{inc.revenue_protected}")