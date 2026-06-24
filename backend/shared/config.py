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
    "unknown":        {"primary": "restart",            "retry": "restart"},
}

# ── Revenue per second (illustrative, for dashboard metric) ─────
# Used to calculate "revenue protected" vs manual 15-min baseline.
# These are fake numbers — state clearly in the paper they are illustrative.
REVENUE_PER_SECOND = {
    "auth":         5.0,    # ₹5/s — login outage affects everything
    "cart":         8.0,    # ₹8/s — cart down = no purchases
    "payment":      15.0,   # ₹15/s — payment down = direct revenue loss
    "inventory":    4.0,    # ₹4/s — wrong stock data causes bad orders
    "notification": 1.0,    # ₹1/s — emails fail but orders still go through
}

# ── Orchestrator settings ────────────────────────────────────────
MAX_RETRIES = 2             # how many times to retry a failed fix
MANUAL_BASELINE_SECONDS = 900   # 15 minutes — assumed manual MTTR for comparison

# ── Monitor Agent settings ───────────────────────────────────────
MONITOR_POLL_INTERVAL = int(os.getenv("MONITOR_POLL_INTERVAL", 5))   # seconds between each health check