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

**Research question:**
> Can a multi-agent, LLM-orchestrated system autonomously detect, diagnose, and recover e-commerce microservice failures faster and more accurately than manual intervention — and what is the measurable reduction in Mean Time To Recovery (MTTR)?

**Engineering goal:** a real, deployable web application (not a throwaway demo) that anyone can clone, run, and watch heal itself live.

---

## How it works (the architecture in one picture)