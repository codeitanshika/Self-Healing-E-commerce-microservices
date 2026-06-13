# Self-Healing E-Commerce Microservices

> An autonomous system where AI agents detect, diagnose, fix, and verify failures in e-commerce microservices — with zero human intervention and zero paid APIs.

![status](https://img.shields.io/badge/status-in%20development-yellow)
![python](https://img.shields.io/badge/python-3.11+-blue)
![react](https://img.shields.io/badge/react-18-61dafb)
![license](https://img.shields.io/badge/license-MIT-green)

---

## What is this?

Real e-commerce platforms run as many small **microservices** — separate programs for login, cart, payments, inventory, and notifications. In production these services fail constantly: they crash, slow down, leak memory, or start throwing errors.

Today, when that happens, one of two things occurs:

1. **A human gets paged** (PagerDuty/Datadog) and manually diagnoses + fixes it — slow, costs 15–45 minutes of downtime.
2. **A dumb auto-restart kicks in** (Kubernetes liveness probes) — fast, but blind: it applies the *same* fix to every problem and never understands *why* it broke.

This project builds the missing middle: a system that **closes the full loop** —
**detect → understand → fix → verify → retry-if-needed → log** — using AI reasoning and an event-driven multi-agent architecture, runnable on a single laptop for free.

---

## Goal

**Engineering goal:** a real, deployable web application (not a throwaway demo) that anyone can clone, run, and watch heal itself live.

---

**Key design choice:** agents never call each other directly. They publish and subscribe to *events* on a lightweight in-process event bus (our own ~40-line replacement for enterprise tools like Solace Agent Mesh). This keeps the system decoupled, testable, and is itself part of the research contribution.

---
## How it works?(architecture)

┌──────────────────────────────────────────────────┐
   │              React Dashboard (frontend)            │
   │   health tiles · incident log · MTTR chart · etc   │
   └───────────────────────┬───────────────────────────┘
                           │  REST + polling (every 3-5s)
                           ▼
   ┌──────────────────────────────────────────────────┐
   │                FastAPI Backend                     │
   │                                                    │
   │   5 Simulated Services   ◄──polls──┐               │
   │   (auth, cart, payment,            │               │
   │    inventory, notification)   ┌────┴─────┐         │
   │                               │ Monitor  │         │
   │                               │  Agent   │         │
   │                               └────┬─────┘         │
   │                          ANOMALY_DETECTED          │
   │                                    ▼               │
   │                            ┌──────────────┐        │
   │                            │ Orchestrator │        │
   │                            │ (event bus + │        │
   │                            │  retry loop) │        │
   │                            └──────┬───────┘        │
   │             ┌─────────────────────┼──────────┐     │
   │             ▼          ▼           ▼          ▼     │
   │        Diagnosis     Fix      Validation   Report  │
   │          Agent      Agent       Agent      Agent   │
   │         (Groq LLM)                            │     │
   │                                               ▼     │
   │                                          SQLite DB  │
   └──────────────────────────────────────────────────┘

### The 5 agents

| Agent | Subscribes to | Does | Publishes |
|---|---|---|---|
| **Monitor** | (polls services) | Watches metrics, flags anomalies | `ANOMALY_DETECTED` |
| **Diagnosis** | `DIAGNOSE_REQUEST` | Sends metrics to free LLM, gets root cause + fix | `DIAGNOSIS_READY` |
| **Fix** | `FIX_REQUEST` | Executes the chosen remediation | `FIX_APPLIED` |
| **Validation** | `VALIDATE_REQUEST` | Re-checks service, did it recover? | `VALIDATION_RESULT` |
| **Report** | `VALIDATION_RESULT` | Writes incident + metrics to DB | `INCIDENT_LOGGED` |

The **Orchestrator** ties them together and runs the retry loop (up to 2 retries, then escalate).

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | **React 18 + Vite + Tailwind CSS** | Real, professional, portfolio-grade UI |
| Charts | **Recharts** | Clean React-native charts |
| Backend | **Python 3.11 + FastAPI** | Async, fast, industry standard |
| AI / LLM | **Groq API (Llama 3.3 70B) — FREE** |
| Event bus | **Custom async pub/sub (our own code)** | Free, fully understood, research-novel |
| Database | **SQLite + SQLModel** | Zero-setup, file-based |
| Metrics | **psutil + simulated metrics** | Real CPU/mem readings where useful |
| Deployment | **Render (backend) + Vercel (frontend)** | Both have free tiers |


---

## Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- A free Groq API key from [console.groq.com](https://console.groq.com) (no card required)

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then paste your GROQ_API_KEY into .env
uvicorn main:app --reload --port 8000
```
Backend runs at `http://localhost:8000` (interactive API docs at `/docs`).

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Dashboard runs at `http://localhost:5173`.

### Try it
1. Open the dashboard — all 5 services show green/healthy.
2. Click **Inject Fault → Payment → crash** in the sidebar.
3. Watch live: the incident banner moves through *detecting → diagnosing → fixing → validating*, then logs a green RECOVERED row with its MTTR.


---

## Repository Structure
self-healing-ecommerce/
├── backend/
│   ├── services/          # 5 simulated microservices
│   ├── agents/            # monitor, diagnosis, fix, validation, report
│   ├── orchestrator/      # event bus + orchestrator + retry logic
│   ├── shared/            # config, models, event definitions
│   ├── database/          # SQLite setup
│   ├── main.py            # FastAPI entry point
│   ├── requirements.txt
│   └── .env.example
├── frontend/              # React + Vite app
│   ├── src/
│   │   ├── components/     # HealthTile, IncidentTable, charts, etc.
│   │   ├── hooks/          # usePolling, useServices
│   │   └── App.jsx
│   └── package.json
├── docs/                  # all project documentation (this folder)
└── README.md
---

## Research Paper

This project targets a publishable paper.

**Novel contribution:** a lightweight, event-driven, LLM-diagnosed *closed-loop* (with retry) self-healing system for microservices, runnable on commodity hardware at zero API cost — evaluated against a manual-response baseline on a reproducible testbed.

---

## License

MIT