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
    uvicorn main:app --reload --port 8000
Then open http://localhost:8000/docs to test everything interactively.
"""
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from services.service_manager import ServiceManager


# ── Create the app ───────────────────────────────────────────────
app = FastAPI(
    title="Self-Healing E-Commerce Orchestrator",
    description="AI-powered self-healing system for e-commerce microservices",
    version="1.0.0",
)

# ── CORS — lets the React frontend talk to this backend ──────────
# Without this, the browser blocks requests from localhost:5173
# to localhost:8000 (they are on different ports = different origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",    # React dev server (Phase 5)
        "http://localhost:3000",    # alternate React port
    ],
    allow_methods=["*"],
    allow_headers=["*"],
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
    asyncio.create_task(monitor.run())
    print("✅ Monitor Agent started as background task")
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

@app.post("/api/services/{name}/fault/{fault_type}")
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


@app.post("/api/services/{name}/heal")
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

# Phase 3+:
# GET  /api/incidents          → incident history from SQLite
# GET  /api/stats              → avg MTTR, total revenue protected
# GET  /api/active-incident    → current incident pipeline stage
# POST /api/orchestrator/run   → manually trigger the healing pipeline

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