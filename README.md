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

![dashboard screenshot](assets/dashboard.png)

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
| AI / LLM | Groq API (open-weight models — default `openai/gpt-oss-120b`, validated against `gpt-oss-20b` and `qwen3.8-27b` too) — FREE | No credit card, generous free tier, not locked to one model |
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
│   ├── services/            # simulated service state + fault injection (service_manager.py)
│   ├── agents/               # monitor, diagnosis, fix, validation, report (+ rule-based baseline)
│   ├── orchestrator/         # event bus + orchestrator + retry logic
│   ├── shared/                # config, event topics, Groq LLM client
│   ├── database/              # SQLite models + queries
│   ├── experiments/            # automated multi-model experiment runner + raw/summary CSVs
│   ├── fault_injector/          # (reserved) — faults are currently triggered via the
│   │                             #  POST /api/services/{name}/fault/{fault_type} route
│   ├── main.py                 # FastAPI entry point
│   ├── requirements.txt
│   ├── .env.example
│   └── .env                    # (not committed)
├── frontend/                    # React + Vite dashboard
│   └── src/
│       ├── components/          # HealthTiles, IncidentTable, MttrChart, StatsCards
│       ├── usePolling.js         # polling hook
│       └── App.jsx
├── docs/                         # architecture, build plan, research paper, experiment results
│   └── results/                   # model-comparison.md, retry-loop-test.md, and archived runs
├── assets/                        # README images
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

### Triggering a fault manually
With the backend running, break a service on purpose and watch the agents heal it:
```bash
curl -X POST http://localhost:8000/api/services/payment/fault/crash
```
`fault_type` is one of `crash | slow | memory | error`. The same route is what the dashboard's sidebar calls during a live demo. Watch the terminal (or `GET /api/events`) to see `ANOMALY_DETECTED → DIAGNOSIS_READY → FIX_APPLIED → VALIDATION_RESULT → INCIDENT_LOGGED` fire in sequence.

### Running the experiment suite
The same pipeline can be driven headlessly (no dashboard) to benchmark diagnosis accuracy and MTTR across models:
```bash
cd backend
python -m experiments.run_experiments openai/gpt-oss-120b
```
This runs 20 fault scenarios × 3 trials against the given Groq model and the rule-based baseline, writing per-trial and summary CSVs to `backend/experiments/`. See [`docs/results/model-comparison.md`](docs/results/model-comparison.md) for published results across three models.

---

## Documentation

| Doc | What's in it |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | System design in detail |
| [`docs/research-paper.md`](docs/research-paper.md) | Public paper outline and methodology |
| [`docs/results/model-comparison.md`](docs/results/model-comparison.md) | Multi-model accuracy/MTTR comparison (Sept 2026 re-run) |
| [`docs/results/retry-loop-test.md`](docs/results/retry-loop-test.md) | Verification of the retry/escalation logic, including a feedback-loop bug found and fixed |
| [`backend/experiments/findings.md`](backend/experiments/findings.md) | Full experiment write-up: setup, per-fault-type breakdown, limitations |
| [`docs/setup-guide.md`](docs/setup-guide.md) | Build-from-scratch setup walkthrough |
| [`docs/progress-tracker.md`](docs/progress-tracker.md) | Phase-by-phase build status |

> `docs/paper.md` (the unpublished full paper draft) is intentionally excluded from version control until it's published — see `.gitignore`.

---

## Research Findings So Far

Latest experiment run (Sept 2026, 180 trials across 3 free Groq models):

| Metric | Result |
|---|---|
| LLM diagnosis accuracy (pooled) | 99.4% (179/180) |
| Rule-based baseline accuracy | 100% (180/180) |
| Mean MTTR | 3.20s vs. 900s manual baseline (~99.6% reduction) |
| Model dependency | Accuracy held up across all 3 models tested — not locked to one vendor's model |

Full breakdown, per-model numbers, and honest caveats (e.g. why "recovery rate" isn't yet a fix-sensitive metric) are in [`docs/results/model-comparison.md`](docs/results/model-comparison.md) and [`backend/experiments/findings.md`](backend/experiments/findings.md).

---

## Research Paper

This project targets a publishable paper. The novel contribution is a lightweight, event-driven, LLM-diagnosed closed-loop self-healing system for microservices — runnable on commodity hardware at zero API cost — evaluated against a manual-response baseline on a reproducible testbed.

Full paper outline and methodology in [`docs/research-paper.md`](docs/research-paper.md).

---

## License

MIT