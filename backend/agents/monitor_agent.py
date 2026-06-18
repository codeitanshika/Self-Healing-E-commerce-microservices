"""
monitor_agent.py
================
The Monitor Agent — the eyes of the system.

What it does:
- Runs as a background async task (starts with the FastAPI app)
- Every 5 seconds, checks health of all 5 services
- If any service looks unhealthy, publishes ANOMALY_DETECTED
- Keeps track of which services it already reported so it
  doesn't spam the same anomaly every 5 seconds

This is the ONLY agent that doesn't subscribe to any event.
It runs on a timer, not in response to an event.
Everything else in the system is triggered BY this agent.
"""

import asyncio
import time
from orchestrator.event_bus import bus
from shared.events import ANOMALY_DETECTED
from shared.config import THRESHOLDS, MONITOR_POLL_INTERVAL


class MonitorAgent:
    """
    Polls all services on a fixed interval and publishes
    ANOMALY_DETECTED when something looks wrong.
    """

    def __init__(self, service_manager):
        # needs the service manager to read health metrics
        self.service_manager = service_manager

        # tracks which services we have already reported
        # so we don't publish the same anomaly every 5 seconds
        self.active_anomalies: set[str] = set()

        print("[MonitorAgent] initialized")

    # ────────────────────────────────────────────────────────────
    # MAIN LOOP
    # ────────────────────────────────────────────────────────────

    async def run(self):
        """
        The main polling loop.
        Runs forever in the background.
        Called once at app startup via asyncio.create_task().
        """
        print(f"[MonitorAgent] starting — polling every {MONITOR_POLL_INTERVAL}s")

        while True:
            try:
                await self._check_all_services()
            except Exception as e:
                # never crash the monitor — log and keep going
                print(f"[MonitorAgent] ⚠️  error during check: {e}")

            # wait before next check
            await asyncio.sleep(MONITOR_POLL_INTERVAL)

    # ────────────────────────────────────────────────────────────
    # CHECK ALL SERVICES
    # ────────────────────────────────────────────────────────────

    async def _check_all_services(self):
        """
        Reads health of every service and decides
        whether to publish an anomaly.
        """
        all_health = self.service_manager.get_all_health()

        for name, health in all_health["services"].items():
            anomaly = self._detect_anomaly(health)

            if anomaly:
                if name not in self.active_anomalies:
                    # new anomaly — report it
                    self.active_anomalies.add(name)
                    await self._publish_anomaly(name, anomaly, health)
                else:
                    # already reported this one — stay quiet
                    print(f"[MonitorAgent] {name} still anomalous ({anomaly}) — waiting for fix")
            else:
                if name in self.active_anomalies:
                    # service recovered (healed externally or manually)
                    self.active_anomalies.discard(name)
                    print(f"[MonitorAgent] ✅ {name} back to healthy")

    # ────────────────────────────────────────────────────────────
    # DETECT ANOMALY
    # ────────────────────────────────────────────────────────────

    def _detect_anomaly(self, health: dict) -> str | None:
        """
        Checks ONE service's health against thresholds.
        Returns the fault type string if anomalous, None if healthy.

        This is the anomaly detection logic —
        simple threshold rules (no AI needed here).
        """

        # crashed completely
        if health["status"] == "down":
            return "crash"

        # response time too high
        if health["response_time_ms"] > THRESHOLDS["response_time_ms"]:
            return "slow"

        # error rate too high
        if health["error_rate"] > THRESHOLDS["error_rate"]:
            return "error"

        # memory too high (leak)
        if health["memory"] > THRESHOLDS["memory_percent"]:
            return "memory"

        # all good
        return None

    # ────────────────────────────────────────────────────────────
    # PUBLISH ANOMALY
    # ────────────────────────────────────────────────────────────

    async def _publish_anomaly(self, service: str, fault_type: str, health: dict):
        """
        Publishes ANOMALY_DETECTED to the event bus.
        The Orchestrator is subscribed to this and will
        wake up and start the healing pipeline.
        """
        print(f"[MonitorAgent] 🚨 ANOMALY: {service} → {fault_type}")

        await bus.publish(ANOMALY_DETECTED, {
            "service":    service,
            "fault_type": fault_type,
            "metrics": {
                "status":           health["status"],
                "response_time_ms": health["response_time_ms"],
                "error_rate":       health["error_rate"],
                "memory_percent":   health["memory"],
                "cpu_percent":      health["cpu"],
            },
            "timestamp": time.time(),
        })