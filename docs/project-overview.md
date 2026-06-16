# Project Overview

## Title
Autonomous Self-Healing E-Commerce Microservices Monitor using Multi-Agent LLM Orchestration over a Lightweight Event-Driven Control Plane

## One-Line Pitch
A simulated e-commerce platform (Auth, Cart, Payment, Inventory, Notification) that detects its own failures, diagnoses root causes using a free LLM, applies the correct fix, validates recovery, retries if needed, and logs business impact — entirely autonomously, coordinated through a self-built event-driven agent architecture, at zero API cost.

## Problem Statement
Modern e-commerce platforms run as many small services. When one fails (crash, memory leak, slow response, error spike), existing tools either:
- Only **alert** a human (PagerDuty, Datadog) — human diagnoses + fixes manually (avg MTTR 15–45 min).
- Only **restart blindly** (Kubernetes liveness probes) — no understanding of *why*; same fix for every problem.
- Only **diagnose**, never fix (LLM-RCA research like RCAgent, OpenRCA).

No accessible open system closes the full loop: detect → understand → fix → verify → retry — using LLM reasoning over an event-driven multi-agent architecture, reproducibly and for free.

## Research Question
Can a multi-agent, LLM-orchestrated system autonomously detect, diagnose, and recover e-commerce microservice failures faster and more accurately than manual intervention — and what is the measurable MTTR reduction?

## The 5 Simulated Services
| Service | Real Role | Example Failure |
|---|---|---|
| Auth | Login, sessions | Crash → no one can log in |
| Cart | Add/remove items | CPU overload → cart actions fail |
| Payment | Checkout, billing | Error spike / high latency → failed transactions |
| Inventory | Stock levels | Memory leak → wrong stock data |
| Notification | Order emails/SMS | Crash → no confirmation emails |

## The 5 Agents
1. **Monitor** — polls all services every 5s; publishes `ANOMALY_DETECTED`.
2. **Diagnosis** — sends metrics to Groq (Llama 3.3); publishes `DIAGNOSIS_READY {root_cause, confidence, fix, business_impact}`. *(Only AI agent.)*
3. **Fix** — executes remediation (restart/reduce_load/clear_memory/reroute_traffic/retry_with_backoff); publishes `FIX_APPLIED`.
4. **Validation** — re-checks the service; publishes `VALIDATION_RESULT` (RECOVERED/STILL_BROKEN).
5. **Report** — writes the incident to SQLite.

## Orchestrator
Listens for anomalies, sequences agent calls via the event bus, manages the retry loop (max 2 retries → ESCALATED).

## Control Plane
A self-built async publish/subscribe **event bus** (~40 lines), replacing Solace Agent Mesh — zero cost, fully understood, and a research contribution in its own right.

## Dashboard
React + Vite app: live service health tiles (green/yellow/red), incident history table, MTTR-per-fault-type chart, total revenue protected vs 15-min manual baseline, sidebar fault-injection controls.

## Demo Moment
Inject a fault into Payment → walk away → within ~60s the dashboard shows the full detect→diagnose→fix→validate→log cycle with MTTR and revenue protected.

## Novel Contribution
A lightweight, event-driven, LLM-diagnosed *closed-loop* (with retry + verification) self-healing system for microservices, runnable on commodity hardware at zero API cost, evaluated on a reproducible testbed against a manual-response baseline.

## Tech Stack
React + Vite + Tailwind + Recharts (frontend) · FastAPI (backend) · Groq/Llama 3.3 (free LLM) · custom async event bus · SQLite/SQLModel · Render + Vercel (free deploy).

## Team Roles (optional — plan also works solo)
- Person A: Services + Fix agent
- Person B: Fault injector + Validation agent
- Person C: Monitor + Diagnosis agent + event-bus wiring
- Person D: React dashboard + Report agent + research paper

## Approach
Self-paced, 6 phases (see `build-plan.md`). Each phase ends with something runnable and a git commit. Solo or team — same phases.
