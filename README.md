# Self-Healing E-Commerce Microservices

> An autonomous system where AI agents detect, diagnose, fix, and verify failures in e-commerce microservices — with zero human intervention and zero paid APIs.

![status](https://img.shields.io/badge/status-in%20development-yellow)
![python](https://img.shields.io/badge/python-3.11+-blue)
![react](https://img.shields.io/badge/react-18-61dafb)
![license](https://img.shields.io/badge/license-MIT-green)

---

## 🚀 Live Demo

| | URL |
|---|---|
| **Dashboard** | https://self-healing-e-commerce-microservices-aax3tmiok-anshika494shiv.vercel.app |
| **API Docs** | https://self-healing-backend-m1e1.onrender.com/docs |

> Note: First load may take 30-50 seconds as the free backend wakes from sleep.

### Known limitations of free deployment
- Render free tier spins down after 15 minutes of inactivity
  (first request takes 30-50 seconds to wake up)
- Background tasks (Monitor Agent) restart on wake-up
- For best demo experience, run locally with both terminals active
- The live deployment demonstrates the API and dashboard UI;
  the full autonomous healing pipeline is best observed locally

## What is this?

Real e-commerce platforms run as many small **microservices** — separate programs for login, cart, payments, inventory, and notifications. In production these services fail constantly: they crash, slow down, leak memory, or start throwing errors.

Today, when that happens, one of two things occurs:

1. **A human gets paged** (PagerDuty/Datadog) and manually diagnoses and fixes it — slow, costs 15–45 minutes of downtime.
2. **A dumb auto-restart kicks in** (Kubernetes liveness probes) — fast, but blind: it applies the same fix to every problem and never understands why it broke.

This project builds the missing middle: a system that **closes the full loop** — detect → understand → fix → verify → retry-if-needed → log — using AI reasoning and an event-driven multi-agent architecture, runnable on a single laptop for free.

---

## Goal

**Research question:**
> Can a multi-agent, LLM-orchestrated system autonomously detect, diagnose, and recover e-commerce microservice failures faster and more accurately than manual intervention — and what is the measurable reduction in Mean Time To Recovery (MTTR)?

**Engineering goal:** a real, deployable web application (not a throwaway demo) that anyone can clone, run, and watch heal itself live.

---

## How it works
```
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

```
**Key design choice:** agents never call each other directly. They publish and subscribe to events on a lightweight in-process event bus — our own replacement for enterprise tools like Solace Agent Mesh. This keeps the system decoupled, testable, and is itself part of the research contribution.

### The 5 agents

| Agent | Does | Publishes |
|---|---|---|
| **Monitor** | Polls services every 5s, flags anomalies | `ANOMALY_DETECTED` |
| **Diagnosis** | Sends metrics to Groq LLM, gets root cause + fix | `DIAGNOSIS_READY` |
| **Fix** | Executes the chosen remediation action | `FIX_APPLIED` |
| **Validation** | Re-checks service — did it recover? | `VALIDATION_RESULT` |
| **Report** | Writes incident + MTTR to database | `INCIDENT_LOGGED` |

The **Orchestrator** sequences these agents and handles the retry loop (up to 2 retries, then escalates).

---

## Why this is different from existing tools

| Tool | What it does | What it is missing |
|---|---|---|
| Datadog / PagerDuty | Detects and alerts a human | Human still diagnoses and fixes manually |
| Kubernetes probes | Auto-restarts blindly | No root cause understanding, same fix every time |
| RCAgent / OpenRCA | LLM diagnoses the root cause | Never acts on the diagnosis, never verifies |
| **This project** | Detects, diagnoses, fixes, verifies, retries | Nothing — this closes the full loop |

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | React 18 + Vite + Tailwind CSS | Real, professional, portfolio-grade UI |
| Charts | Recharts | Clean React-native charts |
| Backend | Python 3.11 + FastAPI | Async, fast, industry standard |
| AI / LLM | Groq API (Llama 3.3 70B) — FREE | No credit card, generous free tier |
| Event bus | Custom async pub/sub (our own code) | Free, fully understood, research-novel |
| Database | SQLite + SQLModel | Zero-setup, file-based |
| Deployment | Render (backend) + Vercel (frontend) | Both free tiers |

> No paid services anywhere. Groq replaces the paid Anthropic API. Our own event bus replaces Solace Agent Mesh.

---

## Repository Structure
---
```
self-healing-ecommerce/
├── backend/
│   ├── services/          # 5 simulated microservices
│   ├── agents/             # monitor, diagnosis, fix, validation, report
│   ├── orchestrator/       # event bus + orchestrator + retry logic
│   ├── shared/             # config, models, event topic definitions
│   ├── database/           # SQLite setup
│   ├── fault_injector/     # script to manually break services
│   ├── main.py             # FastAPI entry point
│   ├── requirements.txt
│   ├── .env.example
│   └── .env                # (not committed)
├── frontend/                # React + Vite dashboard (Phase 5)
│   └── src/
│       ├── components/      # HealthTile, IncidentTable, charts...
│       ├── hooks/            # usePolling
│       └── App.jsx
├── docs/                    # architecture, build plan, research paper, etc.
├── .gitignore
└── README.md
```

## Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- Free Groq API key from [console.groq.com](https://console.groq.com) (no card required)

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # paste your GROQ_API_KEY into .env
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Dashboard runs at `http://localhost:5173`.

---


## Research Paper

This project targets a publishable paper. The novel contribution is a lightweight, event-driven, LLM-diagnosed closed-loop self-healing system for microservices — runnable on commodity hardware at zero API cost — evaluated against a manual-response baseline on a reproducible testbed.

Full paper outline and methodology in [`docs/research-paper.md`](docs/research-paper.md).

---

## License

MIT