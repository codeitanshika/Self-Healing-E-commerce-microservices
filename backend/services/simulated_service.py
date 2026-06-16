"""
simulated_service.py
====================
A class that pretends to be a real microservice.

It tracks health metrics (response time, error rate, memory, CPU)
and can be "broken" by injecting faults — just like a real service
would behave when something goes wrong in production.

We use this instead of running 5 real servers because:
- It's controllable (we can break it on demand)
- It's repeatable (same fault = same symptoms every time)
- It runs on one laptop with zero extra setup
"""

import random
import time
from datetime import datetime


class SimulatedService:
    """
    Represents one e-commerce microservice.

    Think of it as a health tracker — it doesn't actually process
    orders or payments, but it pretends to have response times,
    error rates, and crashes just like a real service would.
    """

    def __init__(self, name: str, port: int, description: str):
        self.name = name
        self.port = port
        self.description = description

        # ── Health metrics (all start healthy) ──────────────────
        self.status = "ok"              # ok | degraded | down
        self.response_time_ms = 50      # fast and healthy
        self.error_rate = 0.0           # no errors
        self.memory_percent = 40.0      # normal memory usage
        self.cpu_percent = 15.0         # normal CPU usage
        self.request_count = 0          # total requests handled

        # ── Fault tracking ───────────────────────────────────────
        self.active_fault = None        # which fault is active right now
        self.fault_injected_at = None   # when the fault was injected
        self.heal_count = 0             # how many times it has been healed
        self.started_at = datetime.now()

    # ────────────────────────────────────────────────────────────
    # GET HEALTH
    # ────────────────────────────────────────────────────────────

    def get_health(self) -> dict:
        """
        Returns current health snapshot.
        This is what the Monitor Agent reads every 5 seconds.
        It matches the endpoint contract in code-standards.md:
        { status, service, cpu, memory, response_time_ms, error_rate }
        """
        self._simulate_traffic()    # add small natural fluctuations

        return {
            "status":           self.status,
            "service":          self.name,
            "port":             self.port,
            "description":      self.description,
            "cpu":              round(self.cpu_percent, 1),
            "memory":           round(self.memory_percent, 1),
            "response_time_ms": int(self.response_time_ms),
            "error_rate":       round(self.error_rate, 3),
            "request_count":    self.request_count,
            "active_fault":     self.active_fault,
            "heal_count":       self.heal_count,
            "uptime_seconds":   int((datetime.now() - self.started_at).total_seconds()),
        }

    # ────────────────────────────────────────────────────────────
    # INJECT FAULT
    # ────────────────────────────────────────────────────────────

    def inject_fault(self, fault_type: str) -> dict:
        """
        Break this service on purpose.

        fault_type options:
        - crash   → service completely down, no response
        - slow    → service works but takes 3-8 seconds (CPU maxed)
        - memory  → memory slowly climbing (leak simulation)
        - error   → service up but failing 50% of requests
        """
        self.active_fault = fault_type
        self.fault_injected_at = datetime.now()

        if fault_type == "crash":
            self.status = "down"
            self.response_time_ms = 0
            self.error_rate = 1.0
            self.cpu_percent = 0.0

        elif fault_type == "slow":
            self.status = "degraded"
            self.response_time_ms = random.randint(3000, 8000)
            self.error_rate = 0.1
            self.cpu_percent = random.randint(90, 99)

        elif fault_type == "memory":
            self.status = "degraded"
            self.response_time_ms = random.randint(200, 400)
            self.error_rate = 0.05
            self.memory_percent = random.uniform(87.0, 95.0)

        elif fault_type == "error":
            self.status = "degraded"
            self.response_time_ms = random.randint(200, 500)
            self.error_rate = 0.5
            self.cpu_percent = random.randint(55, 70)

        return {
            "service":        self.name,
            "fault_injected": fault_type,
            "new_status":     self.status,
            "message":        f"Fault '{fault_type}' injected into {self.name}",
            "timestamp":      time.time(),
        }

    # ────────────────────────────────────────────────────────────
    # HEAL
    # ────────────────────────────────────────────────────────────

    def heal(self, fix_type: str = "restart") -> dict:
        """
        Reset this service back to healthy.

        fix_type tells us WHAT action was taken:
        - restart            → full service restart
        - clear_memory       → memory reset
        - reduce_load        → traffic throttled down
        - reroute_traffic    → requests sent to backup
        - retry_with_backoff → failed requests retried with delays
        """
        old_status = self.status
        old_fault = self.active_fault

        # Reset all metrics to healthy values
        self.status = "ok"
        self.response_time_ms = random.randint(30, 80)
        self.error_rate = 0.0
        self.memory_percent = random.uniform(35.0, 55.0)
        self.cpu_percent = random.uniform(10.0, 25.0)
        self.active_fault = None
        self.fault_injected_at = None
        self.heal_count += 1

        return {
            "service":        self.name,
            "fix_applied":    fix_type,
            "old_status":     old_status,
            "old_fault":      old_fault,
            "new_status":     "ok",
            "heal_count":     self.heal_count,
            "message":        f"{self.name} healed via {fix_type}",
            "timestamp":      time.time(),
        }

    # ────────────────────────────────────────────────────────────
    # PRIVATE: simulate natural traffic fluctuations
    # ────────────────────────────────────────────────────────────

    def _simulate_traffic(self):
        """
        Adds tiny random changes each time health is checked.
        Makes the dashboard feel alive even when nothing is broken.
        """
        self.request_count += random.randint(1, 10)

        if self.status == "ok":
            # Small natural fluctuations — normal behaviour
            self.response_time_ms = max(
                20, self.response_time_ms + random.randint(-10, 10)
            )
            self.cpu_percent = max(
                5.0, min(40.0, self.cpu_percent + random.uniform(-2, 2))
            )
            self.memory_percent = max(
                20.0, min(75.0, self.memory_percent + random.uniform(-1, 1))
            )

        elif self.status == "degraded" and self.active_fault == "memory":
            # Memory leak — keeps growing over time until it crashes
            self.memory_percent += random.uniform(2.0, 8.0)
            if self.memory_percent >= 99.0:
                # Finally crashes from memory exhaustion
                self.status = "down"
                self.error_rate = 1.0
                self.response_time_ms = 0