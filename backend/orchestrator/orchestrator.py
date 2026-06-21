"""
orchestrator.py
===============
The Orchestrator — the central coordinator of the whole healing pipeline.

What it does:
- Subscribes to ANOMALY_DETECTED, DIAGNOSIS_READY, FIX_APPLIED, VALIDATION_RESULT
- Drives the sequence: diagnose -> fix -> validate
- Maintains incident_cache (memory across the event chain)
- Implements the retry loop: if STILL_BROKEN, try the next fix
  for that root cause, up to MAX_RETRIES, then ESCALATED

This is the only agent that subscribes to MULTIPLE topics —
every other agent subscribes to exactly one.
"""

import time
import uuid
from orchestrator.event_bus import bus
from shared.events import (
    ANOMALY_DETECTED, DIAGNOSE_REQUEST, DIAGNOSIS_READY,
    FIX_REQUEST, FIX_APPLIED, VALIDATE_REQUEST, VALIDATION_RESULT,
)
from shared.config import FIX_MAP, MAX_RETRIES


class Orchestrator:
    """
    Coordinates the full detect -> diagnose -> fix -> validate -> retry loop.
    """

    def __init__(self):
        # shared memory across the event chain — see explanation above
        # this SAME dict object is also passed to ReportAgent so it
        # can read incident details when VALIDATION_RESULT arrives
        self.incident_cache: dict = {}

        # subscribe to every event this agent needs to react to
        bus.subscribe(ANOMALY_DETECTED, self.on_anomaly_detected)
        bus.subscribe(DIAGNOSIS_READY, self.on_diagnosis_ready)
        bus.subscribe(FIX_APPLIED, self.on_fix_applied)
        bus.subscribe(VALIDATION_RESULT, self.on_validation_result)

        print("[Orchestrator] initialized and subscribed to 4 topics")

    # ────────────────────────────────────────────────────────────
    # STEP 1: anomaly detected -> request diagnosis
    # ────────────────────────────────────────────────────────────

    async def on_anomaly_detected(self, payload: dict):
        service = payload["service"]
        fault_type = payload["fault_type"]
        metrics = payload["metrics"]

        # create a brand new incident record
        incident_id = str(uuid.uuid4())[:8]   # short unique id, e.g. "a1b2c3d4"

        self.incident_cache[incident_id] = {
            "service":      service,
            "fault_type":   fault_type,
            "detected_at":  time.time(),
            "retry_count":  0,
        }

        print(f"[Orchestrator] new incident {incident_id}: {service} ({fault_type})")

        await bus.publish(DIAGNOSE_REQUEST, {
            "service":     service,
            "metrics":     metrics,
            "incident_id": incident_id,
        })

    # ────────────────────────────────────────────────────────────
    # STEP 2: diagnosis ready -> request fix
    # ────────────────────────────────────────────────────────────

    async def on_diagnosis_ready(self, payload: dict):
        incident_id = payload["incident_id"]

        if incident_id not in self.incident_cache:
            print(f"[Orchestrator] ⚠️ unknown incident {incident_id}, ignoring")
            return

        # save the diagnosis details into the cache
        self.incident_cache[incident_id].update({
            "root_cause":      payload["root_cause"],
            "confidence":      payload["confidence"],
            "business_impact": payload["business_impact"],
            "explanation":     payload["explanation"],
            "fix_applied":     payload["fix"],   # the fix we're ABOUT to try
        })

        service = self.incident_cache[incident_id]["service"]

        await bus.publish(FIX_REQUEST, {
            "service":     service,
            "fix":         payload["fix"],
            "incident_id": incident_id,
        })

    # ────────────────────────────────────────────────────────────
    # STEP 3: fix applied -> request validation
    # ────────────────────────────────────────────────────────────

    async def on_fix_applied(self, payload: dict):
        incident_id = payload["incident_id"]

        if incident_id not in self.incident_cache:
            print(f"[Orchestrator] ⚠️ unknown incident {incident_id}, ignoring")
            return

        service = self.incident_cache[incident_id]["service"]
        detected_at = self.incident_cache[incident_id]["detected_at"]

        await bus.publish(VALIDATE_REQUEST, {
            "service":     service,
            "incident_id": incident_id,
            "detected_at": detected_at,
        })

    # ────────────────────────────────────────────────────────────
    # STEP 4: validation result -> done, OR retry, OR escalate
    # ────────────────────────────────────────────────────────────


    async def on_validation_result(self, payload: dict):
        incident_id = payload["incident_id"]
        result = payload["result"]

        # IMPORTANT: if this is an ESCALATED event we published ourselves
        # (see the escalation branch below), do NOT process it again —
        # otherwise the Orchestrator reacts to its own announcement forever.
        if result == "ESCALATED":
            print(f"[Orchestrator] incident {incident_id} escalation noted, no further action")
            return

        if incident_id not in self.incident_cache:
            print(f"[Orchestrator] ⚠️ unknown incident {incident_id}, ignoring")
            return

        cached = self.incident_cache[incident_id]

        if result == "RECOVERED":
            print(f"[Orchestrator] ✅ incident {incident_id} RECOVERED — done")
            # ReportAgent is also subscribed to VALIDATION_RESULT directly,
            # so it will independently log this. We just clean up here.
            self._cleanup(incident_id)
            return

        # result == STILL_BROKEN
        retry_count = cached["retry_count"]

        if retry_count >= MAX_RETRIES:
            # out of retries — escalate
            print(f"[Orchestrator] 🆘 incident {incident_id} ESCALATED after {retry_count} retries")
            # Republish a final VALIDATION_RESULT with ESCALATED so
            # ReportAgent logs it correctly (it only knows RECOVERED/STILL_BROKEN
            # from ValidationAgent, so Orchestrator overrides the final state)
            await bus.publish(VALIDATION_RESULT, {
                **payload,
                "result": "ESCALATED",
            })
            self._cleanup(incident_id)
            return

        # retry with the NEXT fix for this root cause
        root_cause = cached.get("root_cause", "unknown")
        next_fix = FIX_MAP.get(root_cause, FIX_MAP["unknown"])["retry"]

        cached["retry_count"] += 1
        cached["fix_applied"] = next_fix

        print(f"[Orchestrator] 🔄 incident {incident_id} STILL_BROKEN — "
              f"retry #{cached['retry_count']} with fix '{next_fix}'")

        await bus.publish(FIX_REQUEST, {
            "service":     cached["service"],
            "fix":         next_fix,
            "incident_id": incident_id,
        })

    # ────────────────────────────────────────────────────────────
    # HELPERS
    # ────────────────────────────────────────────────────────────

    def _cleanup(self, incident_id: str):
        """
        Note: we intentionally do NOT delete from incident_cache here,
        because ReportAgent (subscribed to the same VALIDATION_RESULT
        event, running concurrently) still needs to read it.
        In a production system we'd use a TTL or explicit ordering;
        for this project's scale, leaving entries in memory is fine.
        """
        pass

    def get_active_incident(self) -> dict | None:
        """
        Returns details of the most recent in-progress incident,
        or None if nothing is currently active.
        Used by the dashboard's "active incident banner" (Phase 5).
        """
        if not self.incident_cache:
            return None

        # get the most recently created incident
        latest_id = list(self.incident_cache.keys())[-1]
        return {"incident_id": latest_id, **self.incident_cache[latest_id]}