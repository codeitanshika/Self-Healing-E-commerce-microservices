# Project Overview

## Title
Autonomous Self-Healing E-Commerce Microservices Monitor using Multi-Agent LLM Orchestration over a Lightweight Event-Driven Control Plane

## One-line pitch
A simulated e-commerce platform that detects its own failures, asks a language model for the cause, applies a fix, verifies recovery, retries a different fix if needed, and records the result, using only free services.

## Problem
Online shops run as many small services that crash, leak memory, slow down or return errors. Common responses leave a gap:
- **Alerting tools** notify a person, who then diagnoses and fixes.
- **Restart probes** act quickly but take the same action for every fault.
- **LLM root-cause tools** explain a likely cause, and many stop there.

Research systems that close the loop in real cloud environments also exist. This project is a small testbed that runs on a laptop and measures what each stage contributes.

## Research question
Can a multi-agent, LLM-assisted system detect, diagnose and recover microservice failures without a person, how long does it take compared with an assumed manual response, and how much does verifying each fix add?

## Services
| Service | Role | Example failure |
|---|---|---|
| Auth | Login and sessions | Crash: no one can log in |
| Cart | Cart items | Overload: cart actions slow down |
| Payment | Checkout and billing | Error spike: failed payments |
| Inventory | Stock levels | Memory leak: eventual crash |
| Notification | Order emails and SMS | Crash: no confirmations |

These are simulated. With Docker running, a real Nginx container can be added as a sixth service (crash fault only).

## Agents
1. **Monitor:** polls every 5 s and publishes `ANOMALY_DETECTED`.
2. **Diagnosis:** the only agent that uses AI; asks a Groq-hosted model (default `openai/gpt-oss-120b`) for cause, confidence, fix, impact and explanation.
3. **Fix:** applies `restart`, `reduce_load`, `clear_memory`, `retry_with_backoff` or `reroute_traffic`.
4. **Validation:** waits 2 s and re-reads real health.
5. **Report:** stores the incident and its timeline in SQLite.

An **Orchestrator** sequences them, allows 2 retries with untried fixes, then escalates. All communication goes over a small in-process **event bus**.

## Dashboard
Key figures, live service cards, healing pipeline, event-bus feed, fault lab, charts, and incident history with a detail panel.

## Demo moment
Inject a fault into Payment and touch nothing: within seconds the dashboard shows detect, diagnose, fix, validate and log.

## Results in brief
| Question | Result |
|---|---|
| Diagnosis accuracy | LLM 179/180; rule baseline 180/180 |
| Recovery under strict healing (660 incidents) | closed loop 99.8%, open loop 95.5%, blind restart 75% |
| Mean recovery time, diagnosis benchmark | 3.20 s against an assumed 900 s manual response |
| Real Nginx container | 10/10 recovered, mean 10.0 s |

Simulated services and a hand-written table of effective fixes limit what these show. Details and caveats: [`docs/results/`](results/).

## Contribution
A lightweight, event-driven closed loop (diagnose, fix, verify, retry) that runs on ordinary hardware at no cost, with measurements of when verification helps and when the model adds no accuracy over rules.

## Tech stack
React + Vite + Recharts · FastAPI · Groq open-weight models · custom async event bus · SQLite + SQLModel · pytest + GitHub Actions · Render + Vercel

## Team roles (suggested split)
- Services and Fix agent
- Fault scenarios and Validation agent
- Monitor, Diagnosis agent and event bus
- Dashboard, Report agent and experiments

How it was built: [build-plan.md](build-plan.md).
