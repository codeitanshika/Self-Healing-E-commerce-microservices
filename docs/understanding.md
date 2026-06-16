# Understanding This Project (Deep Dive)

This document exists so that you *truly understand* what you're building — not just copy code. Read it before Phase 2. If an examiner asks "explain your project," everything you need is here in plain language.

---

## 1. The real-world problem (in plain words)

Imagine Flipkart on sale day. Behind the website, the work is split across many small programs:

- one handles **login** (auth)
- one handles the **shopping cart**
- one handles **payments**
- one tracks **inventory** (how many units left)
- one sends **notifications** (order confirmation emails/SMS)

These are **microservices** — small, independent programs that talk to each other over the network. The opposite is a **monolith**: one giant program doing everything. Big companies use microservices because if the notification service breaks, people can still shop — only emails stop, not the whole site.

**The problem:** with many services, *something is always breaking*. A service might:
- **crash** (stop responding entirely)
- get **slow** (takes 5 seconds instead of 50ms)
- **leak memory** (slowly eats RAM until it dies)
- **spike errors** (starts failing half its requests)

In a real company, a human on-call engineer gets woken up, reads logs, guesses the cause, applies a fix, and checks if it worked. This takes 15–45 minutes. During that time, customers can't check out = lost money.

**Our idea:** what if software could do that whole loop itself, in under a minute?

---

## 2. What "agent" actually means here (no magic)

You hear "AI agent" and it sounds complicated. It's not. In this project:

> **An agent is just a Python function (running as an async task) that waits for a specific kind of event, does one job, and announces a result.**

That's it. Four of our five agents don't even use AI — they're plain logic:

- **Monitor Agent** = a loop that pings services and checks numbers against thresholds. No AI.
- **Fix Agent** = a function that, given a fix name like `"restart"`, calls the right reset function. No AI.
- **Validation Agent** = re-checks a service and returns RECOVERED or STILL_BROKEN. No AI.
- **Report Agent** = writes a row to the database. No AI.
- **Diagnosis Agent** = the *only* one that uses AI. It sends the failure's symptoms to a free LLM and asks "what's the root cause and best fix?" No AI training, no model building — just one API call with a carefully written prompt.

So "multi-agent AI system" really means: *five small programs that cooperate, one of which asks an LLM for advice.* That honesty will serve you well in the viva.

---

## 3. What "LLM" means and why we don't train one

An **LLM** (Large Language Model) is the technology behind ChatGPT — a model trained to read text and produce sensible text back. You will **not** train one (that needs millions of dollars and huge datasets). You will **use** one that already exists, for free, through **Groq**.

Groq runs open models like **Llama 3.3 70B** and gives you a free API key. You send it text, it sends text back. Our Diagnosis Agent sends it something like:

> "A service called payment has response_time=6000ms, error_rate=0.5, cpu=95%. Here are the possible root causes and fixes: [...]. Reply ONLY as JSON with root_cause, confidence, fix, business_impact, explanation."

And it replies with structured JSON we can act on. The "intelligence" of the project is in **how we prompt it**, not in any model we build.

**Why not just use if-else rules instead of an LLM?** You could — and that's exactly your research baseline to compare against. The LLM's advantage is handling *combinations* and *unseen patterns* a rule wouldn't anticipate, and producing a human-readable explanation. Your paper measures whether that advantage is real and worth it.

---

## 4. What "event-driven" means and why we built our own event bus

There are two ways to make programs cooperate:

**Direct calls (tight coupling):**
`monitor.call(diagnosis.call(fix.call(...)))`
Problem: every agent must know about every other agent. Change one, you break others. If one is slow, everything waits.

**Events (loose coupling):**
The Monitor doesn't know the Diagnosis Agent exists. It just shouts into a room: *"ANOMALY_DETECTED on payment!"* Whoever cares is listening and reacts. The Diagnosis Agent is listening, so it wakes up. When done, it shouts *"DIAGNOSIS_READY!"* and the Orchestrator reacts. Nobody is hardwired to anybody.

That "room" is the **event bus**. Enterprise products like **Solace Agent Mesh** or **Kafka** are industrial-strength event buses. We don't need that scale, and they cost money / need heavy setup and paid LLMs. So we write our own tiny one — an async publish/subscribe dictionary, about 40 lines. It does the same *conceptual* job:

```python
# the entire idea, simplified
subscribers = {}                      # topic -> list of functions

def subscribe(topic, fn):
    subscribers.setdefault(topic, []).append(fn)

async def publish(topic, payload):
    for fn in subscribers.get(topic, []):
        await fn(payload)             # notify everyone listening
```

**Why this is a feature, not a shortcut:** your paper can honestly claim you built a *lightweight event-driven self-healing system for cost-constrained environments*. "We used Solace" is configuration. "We designed a minimal event-driven control plane" is engineering.

---

## 5. The full lifecycle of one incident (trace it end to end)

This is the single most important thing to understand. Walk through it until you can recite it:

1. **Everything healthy.** Monitor Agent polls all 5 services every 5s. Numbers look normal.
2. **Fault injected.** You click "crash payment" (or in experiments, a script does). The payment service now returns `status: down`.
3. **Detection.** On its next poll, Monitor sees payment is down (error_rate=1.0). It publishes `ANOMALY_DETECTED {service: payment, metrics: {...}}`.
4. **Orchestration begins.** The Orchestrator hears the anomaly, creates an incident record (start time = now), and publishes `DIAGNOSE_REQUEST {service: payment, metrics}`.
5. **Diagnosis.** The Diagnosis Agent hears it, builds a prompt, calls Groq. Groq replies `{root_cause: service_crash, fix: restart, confidence: 92, ...}`. Agent publishes `DIAGNOSIS_READY`.
6. **Fixing.** Orchestrator hears the diagnosis, publishes `FIX_REQUEST {service: payment, fix: restart}`. Fix Agent hears it, runs the restart (resets the service to healthy), publishes `FIX_APPLIED`.
7. **Validation.** Orchestrator publishes `VALIDATE_REQUEST`. Validation Agent waits a moment, re-polls payment. It's healthy now → publishes `VALIDATION_RESULT {result: RECOVERED, mttr: 47.0}`.
8. **Reporting.** Report Agent hears the result, writes the incident to SQLite: service, root cause, fix, RECOVERED, MTTR=47s, revenue protected.
9. **Dashboard updates.** On its next poll the React frontend sees the new incident row and the healthy tile, and shows "RECOVERED in 47s".

**If validation says STILL_BROKEN:** the Orchestrator picks the *next* fix in the priority list for that root cause and loops back to step 6. After 2 failed retries it marks the incident `ESCALATED` (in real life: page a human).

---

## 6. Key terms cheat-sheet (for viva)

| Term | One-line meaning |
|---|---|
| Microservice | A small independent program doing one job (e.g. payments) |
| Monolith | One big program doing everything (the opposite) |
| Agent | A small program that reacts to an event and does one task |
| LLM | A pre-trained text model (like ChatGPT's brain); we *use* one, don't train one |
| Event bus / pub-sub | A "room" where programs broadcast and listen for events |
| Orchestrator | The coordinator that sequences agents and handles retries |
| MTTR | Mean Time To Recovery — how long from break to fix; our key metric |
| Root cause | The actual reason something broke (crash, memory leak, etc.) |
| Closed loop | Detect → fix → *verify the fix worked* (the verify part is what's rare) |
| Baseline | The thing you compare against (manual 15-min response, or dumb rules) |
| Telemetry | The metrics we collect (CPU, memory, latency, error rate) |

---

## 7. Why each technology was chosen (defend it in viva)

- **FastAPI** — async (agents run concurrently without blocking), auto-generates API docs, industry standard.
- **Groq + Llama 3.3** — genuinely free, fast inference, no card. Removes the cost barrier that blocks most student AI projects.
- **Our own event bus** — zero cost, fully understood (you can explain every line), and a legitimate research contribution vs. bolting on a heavy framework.
- **React + Vite** — a real frontend skill employers want; Vite is fast and modern. (Streamlit would have been quicker but isn't a "real app.")
- **SQLite** — no database server to install or pay for; perfect for a reproducible single-machine testbed.
- **Render + Vercel** — both deploy from GitHub for free, so the project lives online for your portfolio.

---

## 8. What this project is NOT (scope honesty)

- It is **not** a real e-commerce site — the services are *simulated* (they track fake health metrics, they don't process real orders). This is standard and correct for research: you need controllable, repeatable failures.
- It does **not** train any AI model — it uses an existing free one.
- It is **not** production-grade infrastructure — it's a faithful, reproducible, laptop-scale demonstration of a real architectural pattern. Say exactly this in the viva and it becomes a strength, not a weakness.

---

## 9. The honest novelty statement

> Prior work either only *alerts* humans (Datadog), only *restarts blindly* (Kubernetes), or only *diagnoses without acting* (LLM-RCA papers like RCAgent, OpenRCA). This project closes the full loop — detect, LLM-diagnose, fix, validate, and retry — over a lightweight self-built event-driven control plane, runnable at zero API cost, and quantifies the MTTR reduction against a manual baseline on a reproducible testbed.

Memorize the shape of that sentence. It's your paper's thesis and your viva's opening answer.
