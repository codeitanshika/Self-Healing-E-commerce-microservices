"""
docker_service.py
==================
A real, Docker-managed service — the one non-simulated member of
ServiceManager's service dict.

Implements the exact same interface as SimulatedService (get_health,
inject_fault, heal) so every existing agent (Monitor, Diagnosis, Fix,
Validation, Report) works with it completely unmodified — they only
ever call these three methods through ServiceManager, never touch a
service's concrete class directly.

Where SimulatedService fakes its numbers, this class asks Docker and
the container itself:
- status/cpu/memory come from `docker inspect` / `docker stats`
- response_time_ms/error_rate come from an actual HTTP request to the
  container's published port
- heal() issues a real `docker restart` — the first fix in this
  system that can genuinely fail, unlike SimulatedService.heal(),
  which always succeeds by construction (see the project's paper,
  Limitations §11, on why that's a real gap this class addresses
  for exactly one service).

Only the "crash" fault type has a real-world equivalent here
(stopping the real container). Other fault types are rejected rather
than faked, since there's no honest way to simulate "slow" or
"memory leak" on a bare Nginx container without traffic-shaping
tools that are out of scope for this addition.
"""

import time
from datetime import datetime

import httpx

try:
    import docker
    from docker.errors import DockerException, NotFound
except ImportError:
    docker = None

    class DockerException(Exception):
        pass

    class NotFound(DockerException):
        pass


class DockerService:
    """
    Drop-in replacement for SimulatedService, backed by a real
    Docker container instead of in-memory fields.
    """

    # Kept short deliberately: this HTTP probe runs inside
    # MonitorAgent's poll loop (monitor_agent.py). A slow timeout
    # here would reintroduce, at smaller scale, the same
    # blocking-event-loop problem that was fixed for the LLM call
    # in shared/llm.py — see the asyncio.to_thread wrap added around
    # ServiceManager.get_all_health() in MonitorAgent for the other
    # half of that mitigation.
    HTTP_TIMEOUT_SECONDS = 1.5

    def __init__(self, name: str, container_name: str, url: str, description: str):
        self.name = name
        self.container_name = container_name
        self.url = url
        self.description = description
        self.port = None  # no simulated port; kept only for interface parity

        self.active_fault: str | None = None
        self.heal_count = 0
        self.request_count = 0
        self.started_at = datetime.now()

        self._client = None
        if docker is not None:
            try:
                self._client = docker.from_env()
            except DockerException:
                self._client = None  # Docker Desktop not running — degrade, don't crash

    def is_available(self) -> bool:
        """
        True only if a real Docker daemon actually answers right now —
        not just that a client object was constructed. docker.from_env()
        doesn't contact the daemon, so a dead/absent daemon only
        surfaces on a real call like ping(). ServiceManager uses this
        at startup to decide whether to register this service at all:
        environments with no Docker (e.g. a Render free-tier deploy)
        should fall back to the simulated-only service set rather than
        show a sixth tile that can never recover.
        """
        if self._client is None:
            return False
        try:
            return bool(self._client.ping())
        except DockerException:
            return False

    # ────────────────────────────────────────────────────────────
    # GET HEALTH
    # ────────────────────────────────────────────────────────────

    def get_health(self) -> dict:
        """
        Same return shape as SimulatedService.get_health(), so
        ServiceManager and every agent that reads it work unmodified.
        """
        self.request_count += 1

        if not self._is_container_running():
            # Matches the exact "crash" signature the rest of the
            # system already understands: status == "down". Covers
            # both "container stopped" and "Docker unavailable" —
            # both are indistinguishable from this service's point
            # of view without a human checking Docker Desktop, and
            # both should trigger the same recovery attempt.
            return self._health_dict(
                status="down", cpu=0.0, memory=0.0,
                response_time_ms=0, error_rate=1.0,
                active_fault=self.active_fault or "crash",
            )

        response_time_ms, reachable = self._probe_http()

        if not reachable:
            # Container process is alive but not actually serving —
            # the "running but unhealthy" case that's distinct from a
            # crash. Maps onto the existing error_rate > 0.3 anomaly
            # rule (error_spike), since the current fault taxonomy
            # (paper Table IV) has no dedicated "unhealthy" root cause.
            return self._health_dict(
                status="degraded", cpu=0.0, memory=0.0,
                response_time_ms=response_time_ms, error_rate=1.0,
                active_fault=self.active_fault or "error",
            )

        # Healthy — clear whatever fault was previously active.
        self.active_fault = None
        cpu, memory = self._read_container_stats()
        return self._health_dict(
            status="ok", cpu=cpu, memory=memory,
            response_time_ms=response_time_ms, error_rate=0.0,
            active_fault=None,
        )

    def _health_dict(self, *, status, cpu, memory, response_time_ms, error_rate, active_fault) -> dict:
        return {
            "status": status,
            "service": self.name,
            "port": self.port,
            "description": self.description,
            "cpu": cpu,
            "memory": memory,
            "response_time_ms": response_time_ms,
            "error_rate": error_rate,
            "request_count": self.request_count,
            "active_fault": active_fault,
            "heal_count": self.heal_count,
            "uptime_seconds": int((datetime.now() - self.started_at).total_seconds()),
        }

    # ────────────────────────────────────────────────────────────
    # INJECT FAULT
    # ────────────────────────────────────────────────────────────

    def inject_fault(self, fault_type: str) -> dict:
        if fault_type != "crash":
            return {
                "error": (
                    f"fault type '{fault_type}' is not supported for the "
                    f"Docker-managed service '{self.name}' — only 'crash' "
                    f"(stopping the real container) has a real-world "
                    f"equivalent here."
                )
            }

        container = self._get_container()
        if container is None:
            return {"error": f"container '{self.container_name}' not found or Docker unavailable"}

        try:
            container.stop()
        except DockerException as e:
            return {"error": f"failed to stop container '{self.container_name}': {e}"}

        self.active_fault = "crash"
        return {
            "service": self.name,
            "fault_injected": "crash",
            "new_status": "down",
            "message": f"Real container '{self.container_name}' stopped",
            "timestamp": time.time(),
        }

    # ────────────────────────────────────────────────────────────
    # HEAL
    # ────────────────────────────────────────────────────────────

    def heal(self, fix_type: str = "restart") -> dict:
        """
        Unlike SimulatedService.heal(), this can genuinely fail: a
        real `docker restart` has no guarantee of success. fix_type
        is accepted for interface parity with the rest of the system
        (Table III's fault-to-fix map still names it when this
        service's incidents are diagnosed), but the only real action
        currently implemented is a container restart regardless of
        which fix label was chosen — mapping different fix labels to
        differentiated real Docker actions is future work, not yet
        built for this one service.
        """
        container = self._get_container()
        if container is None:
            return {"error": f"container '{self.container_name}' not found or Docker unavailable"}

        old_fault = self.active_fault

        try:
            container.restart()
        except DockerException as e:
            return {"error": f"failed to restart container '{self.container_name}': {e}"}

        self.heal_count += 1
        self.active_fault = None

        return {
            "service": self.name,
            "fix_applied": fix_type,
            "old_status": "down" if old_fault else "ok",
            "old_fault": old_fault,
            "new_status": "ok",
            "heal_count": self.heal_count,
            "message": f"Real container '{self.container_name}' restarted via {fix_type}",
            "timestamp": time.time(),
        }

    # ────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ────────────────────────────────────────────────────────────

    def _get_container(self):
        if self._client is None:
            return None
        try:
            return self._client.containers.get(self.container_name)
        except (NotFound, DockerException):
            return None

    def _is_container_running(self) -> bool:
        container = self._get_container()
        if container is None:
            return False
        try:
            container.reload()
            return container.status == "running"
        except DockerException:
            return False

    def _probe_http(self) -> tuple[int, bool]:
        """Returns (response_time_ms, reachable)."""
        start = time.time()
        try:
            response = httpx.get(self.url, timeout=self.HTTP_TIMEOUT_SECONDS)
            elapsed_ms = int((time.time() - start) * 1000)
            return elapsed_ms, response.status_code < 500
        except httpx.HTTPError:
            elapsed_ms = int((time.time() - start) * 1000)
            return elapsed_ms, False

    def _read_container_stats(self) -> tuple[float, float]:
        """
        Best-effort real CPU/memory percentage from a single-shot
        `docker stats` call. Falls back to 0.0/0.0 on any failure —
        Monitor's crash/error thresholds key off status/error_rate,
        not these two fields, so a fallback here must never block
        detection of a real failure.
        """
        container = self._get_container()
        if container is None:
            return 0.0, 0.0
        try:
            stats = container.stats(stream=False)
            memory_percent = round(
                100.0 * stats["memory_stats"]["usage"] / stats["memory_stats"]["limit"], 1
            )
            cpu_delta = (
                stats["cpu_stats"]["cpu_usage"]["total_usage"]
                - stats["precpu_stats"]["cpu_usage"]["total_usage"]
            )
            system_delta = (
                stats["cpu_stats"]["system_cpu_usage"]
                - stats["precpu_stats"]["system_cpu_usage"]
            )
            cpu_percent = round((cpu_delta / system_delta) * 100.0, 1) if system_delta > 0 else 0.0
            return cpu_percent, memory_percent
        except (DockerException, KeyError, ZeroDivisionError):
            return 0.0, 0.0
