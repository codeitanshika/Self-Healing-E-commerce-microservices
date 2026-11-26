"""
config.py
=========
Central place for all constants used across the project.
If you ever need to change a port, threshold, or service name,
you change it HERE — not scattered across 10 files.
"""
import os
# ── Service definitions ─────────────────────────────────────────
# Each service has a name and a logical port number.
# (We don't actually run them on separate ports — it's one FastAPI app
#  — but we keep port numbers for documentation and future real deployment.)

SERVICES = {
    "auth":         {"port": 8001, "description": "User login and sessions"},
    "cart":         {"port": 8002, "description": "Shopping cart management"},
    "payment":      {"port": 8003, "description": "Payment processing and billing"},
    "inventory":    {"port": 8004, "description": "Stock levels and availability"},
    "notification": {"port": 8005, "description": "Order emails and SMS alerts"},
}

# ── Real, Docker-managed services ────────────────────────────────
# Backed by an actual container (services/docker_service.py), not by
# SimulatedService. Kept separate from SERVICES above since these
# need different constructor arguments — a container name and a
# real URL, not a simulated port. Started via `docker compose up -d`
# (see docker-compose.yml at the repo root).
DOCKER_MANAGED_SERVICES = {
    "nginx": {
        "container_name": "monitored-nginx",
        "url": "http://localhost:8080",
        "description": "Real Nginx web server (Docker-managed)",
    },
}

# ── Fault types ─────────────────────────────────────────────────
# These are the 4 ways a service can break in our simulation.
FAULT_TYPES = ["crash", "slow", "memory", "error"]

# ── Anomaly detection thresholds ────────────────────────────────
# Monitor Agent flags a service as anomalous if ANY of these are exceeded.
THRESHOLDS = {
    "response_time_ms": 2000,   # anything over 2 seconds is too slow
    "error_rate":       0.3,    # more than 30% errors is a problem
    "memory_percent":   85.0,   # memory over 85% signals a leak
}

# ── Fault → Fix mapping ─────────────────────────────────────────
# Diagnosis Agent returns a root_cause.
# Fix Agent looks up what fix to try first, and what to retry with.
FIX_MAP = {
    "service_crash":  {"primary": "restart",            "retry": "reduce_load"},
    "memory_leak":    {"primary": "clear_memory",       "retry": "restart"},
    "cpu_overload":   {"primary": "reduce_load",        "retry": "restart"},
    "high_latency":   {"primary": "reroute_traffic",    "retry": "reduce_load"},
    "error_spike":    {"primary": "retry_with_backoff", "retry": "restart"},
    # When the diagnosis itself failed we know nothing, so the two attempts
    # must be DIFFERENT fixes covering the likely classes: restart (crash,
    # memory, error) then reduce_load (slow). With restart->restart a failed
    # diagnosis could never recover from an overload (first strategy run).
    "unknown":        {"primary": "restart",            "retry": "reduce_load"},
}

# ── Revenue per second (illustrative, for dashboard metric) ─────
# Used to calculate "revenue protected" vs manual 15-min baseline.
# These are made-up numbers: always present the figure as illustrative.
REVENUE_PER_SECOND = {
    "auth":         5.0,    # ₹5/s — login outage affects everything
    "cart":         8.0,    # ₹8/s — cart down = no purchases
    "payment":      15.0,   # ₹15/s — payment down = direct revenue loss
    "inventory":    4.0,    # ₹4/s — wrong stock data causes bad orders
    "notification": 1.0,    # ₹1/s — emails fail but orders still go through
}

# ── Fix effectiveness (strict healing mode) ──────────────────────
# A fix only cures the faults listed here: an ineffective fix leaves the
# service broken, so the Validation Agent reports STILL_BROKEN and the
# Orchestrator's retry/escalation loop is exercised by genuinely wrong choices.
# STRICT_HEALING=0 restores the old behaviour, where ANY fix cures ANY fault
# (which makes recovery rate tautological).
#
#   crash  : only a restart revives a dead process
#   memory : clearing memory, or restarting, frees the leak
#   slow   : shedding or re-routing load; a restart just re-meets the same load
#   error  : backoff/retry smooths a transient spike; a restart also clears it
EFFECTIVE_FIXES = {
    "crash":  {"restart"},
    "memory": {"clear_memory", "restart"},
    "slow":   {"reduce_load", "reroute_traffic"},
    "error":  {"retry_with_backoff", "restart"},
}


def strict_healing() -> bool:
    """On unless STRICT_HEALING=0. Read at call time so it can be toggled."""
    return os.getenv("STRICT_HEALING", "1") != "0"


# ── Retry policy ────────────────────────────────────────────────
# Every fix the Fix Agent can execute, in the order used once a root cause's
# own fixes from FIX_MAP have been tried.
FIX_TYPES = ("restart", "reduce_load", "clear_memory", "retry_with_backoff", "reroute_traffic")


def retry_policy() -> str:
    """
    "distinct" (default): every retry is a fix not yet tried on this incident.
    "repeat": every retry is FIX_MAP[root_cause]["retry"], even if it already
    failed. The published noise and strategy results were recorded this way.
    """
    return "repeat" if os.getenv("RETRY_POLICY", "distinct") == "repeat" else "distinct"


def next_retry_fix(root_cause: str, tried: list[str]) -> str:
    """The fix to apply after the ones in `tried` left the service broken."""
    mapped = FIX_MAP.get(root_cause, FIX_MAP["unknown"])
    if retry_policy() == "repeat":
        return mapped["retry"]
    # the Fix Agent runs an unrecognised fix name as a restart
    done = {fix if fix in FIX_TYPES else "restart" for fix in tried}
    candidates = (mapped["retry"], mapped["primary"], *FIX_TYPES)
    return next((fix for fix in candidates if fix not in done), mapped["retry"])


# ── Orchestrator settings ────────────────────────────────────────
MAX_RETRIES = 2             # how many times to retry a failed fix
MANUAL_BASELINE_SECONDS = 900   # 15 minutes — assumed manual MTTR for comparison

# ── Monitor Agent settings ───────────────────────────────────────
MONITOR_POLL_INTERVAL = int(os.getenv("MONITOR_POLL_INTERVAL", 5))   # seconds between each health check