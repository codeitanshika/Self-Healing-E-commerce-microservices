"""
main.py
=======
The FastAPI application — the backbone of the entire backend.

This file:
1. Creates the FastAPI app
2. Creates one ServiceManager (shared across all requests)
3. Exposes all API routes the React dashboard and agents need
4. Will later start all agent async tasks on startup (Phase 2+)

Run with:
    uvicorn main:app --reload --reload-exclude "*.db" --port 8000
Then open http://localhost:8000/docs to test everything interactively.

Why --reload-exclude "*.db": without it, --reload watches the whole
backend/ directory including database/incidents.db. The Report Agent
writes to that file on every incident, which triggers a reload, which
wipes MonitorAgent's in-memory active_anomalies set, so any
still-unhealthy service is immediately re-detected as brand new,
re-diagnosed, re-logged - triggering another reload. If a service is
ever stuck unhealthy, this is a real, self-sustaining restart loop,
not just a cosmetic annoyance - confirmed by reproducing it directly.
"""
import sys

# The agents print status emoji (✅ 🚨 📢 🆘 💥) throughout. Windows' default
# console codepage (cp1252) can't encode those and crashes the process with
# UnicodeEncodeError on the first such print — force UTF-8 stdout/stderr
# before anything else runs, regardless of the terminal's own codepage.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import asyncio
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from services.service_manager import ServiceManager
from shared.stream import hub
from database import admin as db_admin
from fault_injector.scenarios import SCENARIOS, list_scenarios, run_scenario, valid_steps
from shared.config import MONITOR_POLL_INTERVAL
from shared.security import require_api_key, rate_limit, get_api_key


# ── Create the app ───────────────────────────────────────────────
app = FastAPI(
    title="Self-Healing E-Commerce Orchestrator",
    description="AI-powered self-healing system for e-commerce microservices",
    version="1.0.0",
)

# ── CORS — lets the React frontend talk to this backend ──────────
# Without this, the browser blocks requests from localhost:5173
# to localhost:8000 (they are on different ports = different origins)
import os

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],  # includes X-API-Key
)

# ── Create one shared ServiceManager ────────────────────────────
# This is created ONCE when the app starts.
# All routes use this same instance — so state is shared.
# ── Create one shared ServiceManager ────────────────────────────
# ── Create one shared ServiceManager ────────────────────────────
manager = ServiceManager()

# ── Initialize database ──────────────────────────────────────────
from database.models import init_db
init_db()

# ── Create the Orchestrator FIRST (other agents need its cache) ──
from orchestrator.orchestrator import Orchestrator
orchestrator = Orchestrator()

# ── Create all agents (each subscribes itself to the event bus) ──
from agents.monitor_agent import MonitorAgent
from agents.diagnosis_agent import DiagnosisAgent
from agents.fix_agent import FixAgent
from agents.validation_agent import ValidationAgent
from agents.report_agent import ReportAgent

monitor = MonitorAgent(manager)
diagnosis_agent = DiagnosisAgent()
fix_agent = FixAgent(manager)
validation_agent = ValidationAgent(manager)
report_agent = ReportAgent(orchestrator.incident_cache)

# ── Start background tasks on startup ────────────────────────────
@app.on_event("startup")
async def startup():
    """Runs once when FastAPI starts. Launches all background agents."""
    hub.attach()
    asyncio.create_task(monitor.run())
    print("✅ Monitor Agent started as background task")
    if not get_api_key():
        print("⚠️  API_KEY not set — fault-injection endpoints are open (fine for local demos)")
# ────────────────────────────────────────────────────────────────
# ROOT
# ────────────────────────────────────────────────────────────────


@app.get("/")
def root():
    """Quick check that the server is running."""
    return {
        "project": "Self-Healing E-Commerce Microservices",
        "status":  "running",
        "docs":    "http://localhost:8000/docs",
    }


# ────────────────────────────────────────────────────────────────
# SERVICE HEALTH ROUTES
# ────────────────────────────────────────────────────────────────

@app.get("/api/services")
def get_all_services():
    """
    Get health of ALL 5 services at once.
    The React dashboard polls this every 3-5 seconds
    to update all health tiles.
    """
    return manager.get_all_health()


@app.get("/api/services/{name}")
def get_one_service(name: str):
    """
    Get health of ONE specific service.
    Example: GET /api/services/payment
    """
    result = manager.get_service_health(name)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/services/{name}/metrics")
def get_service_metrics(name: str):
    """
    Get just the numeric metrics for one service.
    Used by the Diagnosis Agent to build the LLM prompt.
    """
    result = manager.get_service_metrics(name)
    if not result:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
    return result


# ────────────────────────────────────────────────────────────────
# FAULT INJECTION ROUTES
# ────────────────────────────────────────────────────────────────

@app.post("/api/services/{name}/fault/{fault_type}",
          dependencies=[Depends(require_api_key), Depends(rate_limit)])
def inject_fault(name: str, fault_type: str):
    """
    Break a service on purpose.
    Called from the React dashboard sidebar during demos.

    Example: POST /api/services/payment/fault/crash
    fault_type options: crash | slow | memory | error
    """
    result = manager.inject_fault(name, fault_type)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/admin/reset",
          dependencies=[Depends(require_api_key), Depends(rate_limit)])
def reset_demo_data(confirm: bool = False):
    """
    Wipe incident history and return every service to healthy, so a demo
    starts from a clean slate. Destructive, so it must be called with
    ?confirm=true (the dashboard asks the user first).
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="Pass ?confirm=true to reset all data")
    removed = db_admin.reset_all()
    orchestrator.incident_cache.clear()
    monitor.active_anomalies.clear()
    monitor.history.clear()
    healed = []
    for name in list(manager.services):
        if not manager.is_service_healthy(name):
            manager.reset_service(name)
            healed.append(name)
    return {**removed, "services_healed": healed, "status": "reset"}


@app.get("/api/scenarios")
def get_scenarios():
    """Scripted multi-fault / cascade scenarios the dashboard can launch."""
    return {"scenarios": list_scenarios()}


@app.post("/api/scenarios/{scenario_id}/run",
          dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def start_scenario(scenario_id: str, background: BackgroundTasks):
    """Launch a scenario; delayed (cascade) steps continue in the background."""
    if scenario_id not in SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Unknown scenario '{scenario_id}'")
    steps = valid_steps(manager, scenario_id)
    if not steps:
        raise HTTPException(status_code=409, detail="No service in this scenario is available")
    background.add_task(run_scenario, manager, scenario_id)
    return {"scenario": scenario_id, "steps": len(steps), "status": "started"}


@app.post("/api/services/{name}/heal",
          dependencies=[Depends(require_api_key), Depends(rate_limit)])
def heal_service(name: str, fix_type: str = "restart"):
    """
    Manually heal a service (reset to healthy).
    Normally called by the Fix Agent automatically.
    This manual route is useful for testing.

    Example: POST /api/services/payment/heal?fix_type=restart
    """
    result = manager.heal_service(name, fix_type)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ────────────────────────────────────────────────────────────────
# SUMMARY ROUTES
# ────────────────────────────────────────────────────────────────

@app.get("/api/unhealthy")
def get_unhealthy():
    """
    Returns only the services that are currently broken.
    The Monitor Agent uses this to find what needs attention.
    Returns an empty list if everything is healthy.
    """
    return {
        "unhealthy": manager.get_unhealthy_services(),
        "count":     len(manager.get_unhealthy_services()),
    }


# ────────────────────────────────────────────────────────────────
# ROUTES ADDED IN LATER PHASES
# ────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────
# DASHBOARD DATA ROUTES (Phase 5)
# ────────────────────────────────────────────────────────────────

from database.queries import (
    get_all_incidents, get_stats, get_mttr_by_fault_type, get_incident_detail,
    get_revenue_series, get_breakdown,
)


@app.get("/api/incidents")
def get_incidents(limit: int = 50):
    """Incident history for the dashboard table, newest first."""
    return {"incidents": get_all_incidents(limit)}


@app.get("/api/stats")
def get_dashboard_stats():
    """Aggregate stats for the summary metric cards."""
    return get_stats()


@app.get("/api/mttr-chart")
def get_mttr_chart():
    """Average MTTR grouped by root cause, for the bar chart."""
    return {"data": get_mttr_by_fault_type()}


@app.get("/api/revenue-series")
def revenue_series():
    """Cumulative revenue protected, one point per incident."""
    return {"data": get_revenue_series()}


@app.get("/api/breakdown")
def breakdown():
    """Incident counts and mean MTTR by service, fix and outcome."""
    return get_breakdown()


@app.get("/api/history")
def metrics_history():
    """Rolling per-service metric samples (response time, errors, memory, CPU)."""
    return {"history": monitor.get_history(), "poll_interval": MONITOR_POLL_INTERVAL}


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: int):
    """One incident plus its stage-by-stage timeline."""
    detail = get_incident_detail(incident_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return detail


@app.get("/api/active-incidents")
def get_active_incidents():
    """Every in-progress incident with its live stage and timeline."""
    return {"incidents": orchestrator.get_active_incidents()}


@app.get("/api/active-incident")
def get_active_incident():
    """
    The most recent in-progress incident, for the live banner.
    Returns {active: false} if nothing is currently being handled.
    """
    incident = orchestrator.get_active_incident()
    if incident is None:
        return {"active": False}
    return {"active": True, **incident}

@app.get("/api/events")
def get_recent_events(limit: int = 20):
    """
    Returns recent events from the event bus log.
    Used by the dashboard debug panel.
    """
    from orchestrator.event_bus import bus
    return {
        "events": bus.get_recent_events(limit),
        "subscribers": bus.get_subscriber_count(),
    }


@app.get("/api/stream")
async def stream_events():
    """
    Server-Sent Events: every pipeline event (ANOMALY_DETECTED,
    DIAGNOSIS_READY, FIX_APPLIED, ...) is pushed to the browser the
    instant it is published on the bus. Replays the last few events on
    connect so a freshly opened dashboard is never empty.
    """
    return StreamingResponse(
        hub.listen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
