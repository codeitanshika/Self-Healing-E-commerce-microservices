# Research Paper Guide

This turns your build into a publishable paper. Fill each section with your real numbers from Phase 6. Aim for a Scopus-indexed conference or arXiv preprint.

---

## Title (working)
*A Lightweight Event-Driven Multi-Agent System for Autonomous Closed-Loop Self-Healing of Microservices Using LLM-Based Diagnosis*

## Thesis (one sentence — memorize it)
We close the full detect→diagnose→fix→validate→retry loop for microservice failures over a self-built, zero-cost event-driven control plane, and quantify the MTTR reduction versus a manual baseline on a reproducible laptop-scale testbed.

---

## Section-by-section outline

### Abstract (~200 words, write last)
Problem (microservice failures cost downtime) → gap (existing tools only alert, only blindly restart, or only diagnose) → what you built (closed-loop multi-agent LLM healer on a lightweight event bus) → headline result (e.g. "reduced mean MTTR from a 900s manual baseline to X s, with Y% diagnosis accuracy across Z fault scenarios") → significance (reproducible, zero-cost, open source).

### 1. Introduction
- Microservices are everywhere; failures are frequent and expensive.
- The on-call human loop is slow (15–45 min MTTR).
- Blind auto-restart is fast but unaware of root cause.
- Your contribution bullets (the closed loop, the lightweight event bus, the cost-free reproducibility, the empirical MTTR comparison).
- Paper roadmap paragraph.

### 2. Related Work
Group prior work into three buckets and position yourself as the synthesis:
- **Observability/alerting:** Datadog, PagerDuty, Prometheus — detect + alert, human fixes.
- **Orchestrator self-healing:** Kubernetes liveness/readiness probes, auto-restart — act, but no root-cause reasoning.
- **LLM root-cause analysis:** RCAgent, OpenRCA, and similar — diagnose, but don't act or verify.
- Cite the multi-agent / event-driven AI framework line (e.g. Solace Agent Mesh) as related infrastructure you deliberately replaced with a lightweight alternative.
- **Gap statement:** none close the full loop with verification + retry at zero cost on a reproducible testbed.

> Collect ~10 references. For each, write one paragraph: what they do, and the one way you differ. Prefer recent peer-reviewed papers and official docs over blogs.

### 3. System Architecture
- Use `architecture.md` as the basis. Include the flow diagram.
- Describe the event bus, the five agents, the orchestrator, the retry logic, the fault→fix mapping.
- Justify each design choice (decoupling, why an LLM only for diagnosis, why simulated services for repeatability).

### 4. Methodology (Experimental Setup)
- Describe the 5 services and the 5 fault types (your fault model).
- Define metrics precisely:
  - **Detection time:** anomaly publish time − fault injection time.
  - **Diagnosis accuracy:** did the LLM's `root_cause` match the injected fault? (correct / total).
  - **MTTR:** RECOVERED time − fault injection time.
  - **First-try success rate:** fraction recovered without retry.
- Define the **baseline(s)**:
  - *Manual baseline:* fixed 900s per incident (cite a source or state it as a conservative industry estimate).
  - *(Optional, stronger) Rule-based baseline:* a fixed if-fault-then-fix table with no LLM — lets you isolate the LLM's contribution.
- State the testbed (single laptop, specs), the LLM (Llama 3.3 70B via Groq), and that everything is reproducible from the repo.

### 5. Results
- **Table 1:** MTTR per fault type — Your System vs Manual Baseline (and vs Rule-Based if you do it).
- **Table 2:** Diagnosis accuracy per fault type.
- **Figure 1:** Bar chart, MTTR by fault type with the 900s baseline as a reference line.
- **Figure 2:** First-try vs retry breakdown.
- Report aggregate numbers in prose (mean MTTR, overall accuracy, total simulated revenue protected).

### 6. Discussion
- Where the LLM helped (combinations, explanations) vs where simple rules sufficed.
- Failure cases: wrong diagnoses, retries triggered, escalations.
- Honest threats to validity: simulated (not real) services; single LLM; small N; baseline is an estimate.

### 7. Limitations & Future Work
- Real service integration; larger fault taxonomy; comparing multiple LLMs; learning the fix policy from outcomes (a genuine extension); horizontal scaling; security/authz.

### 8. Conclusion
- Restate thesis + headline result + that it's open and reproducible.

### References
- ~10+ entries, consistent format (IEEE or ACM, match your venue).

---

## How to actually run the experiments (Phase 6)

1. Write a small script that, for each (service, fault) pair you choose, injects the fault, waits for the incident to resolve, and reads the resulting DB row.
2. Run each scenario 3 times (to average out LLM variability) — report mean and spread.
3. Export the `Incident` table to CSV; build the tables/charts from that CSV.
4. Keep the raw CSV in the repo (`docs/results/`) for reproducibility.

---

## Where to submit
- **arXiv** (cs.SE or cs.DC) — free preprint, instant credibility, good first step.
- **Student/early-career conferences** or **Scopus-indexed conferences** in software engineering / cloud / AIOps.
- Check your university's preferred/recognized venue list first.

---

## Viva preparation (answers to your tracker's questions)

1. **Why an event bus instead of direct calls?** Decoupling — agents don't know about each other, so components can be added, removed, or restarted independently; mirrors real event-driven systems while staying lightweight.
2. **Why not Solace Agent Mesh?** It requires paid LLMs and heavy infra; we built a lightweight equivalent to keep the system zero-cost and fully reproducible, and to make the control plane our own contribution.
3. **How is this different from Kubernetes self-healing?** K8s restarts blindly with no root-cause understanding and no verification reasoning; we diagnose *why*, choose a *targeted* fix, *verify* it, and *retry differently* if it fails.
4. **How is it different from LLM-RCA papers (RCAgent/OpenRCA)?** They diagnose but don't act or verify; we close the full loop and measure recovery, not just diagnosis.
5. **What if the LLM is wrong?** Validation catches it (STILL_BROKEN) → orchestrator retries with the next fix → escalates after 2 failures. We also have a safe JSON-parse default.
6. **Retry limit?** 2 retries, then ESCALATED (would page a human).
7. **Is the 900s baseline realistic?** It's a conservative industry estimate for manual MTTR; we state it as illustrative and (optionally) also compare against a rule-based baseline to isolate the LLM's value.
8. **Production-ready?** No — it's a faithful, reproducible laptop-scale testbed of the pattern. That's the correct scope for the research claim.
9. **Cost?** Zero — free Groq tier, free hosting, SQLite. That's a deliberate contribution (accessible AIOps research).
10. **Scaling?** The event bus and agent model generalize to more services; the honest limitation is the single-process design, noted as future work.
