# Understanding This Project

A plain-language explanation, so you can explain the project rather than recite it.

---

## 1. The real-world problem

Imagine an online shop on sale day. Behind the website the work is split across small programs:

- **auth** handles login
- **cart** handles the shopping cart
- **payment** handles payments
- **inventory** tracks stock
- **notification** sends order emails and SMS

These are **microservices**: small, independent programs that talk over a network. The opposite is a **monolith**, one program doing everything. With microservices, if notifications break, people can still shop.

With many services, something is often breaking. A service might:
- **crash** (stop responding)
- get **slow** (seconds instead of milliseconds)
- **leak memory** (use more and more until it dies)
- **spike errors** (fail many requests)

Usually a person is alerted, reads the data, guesses the cause, applies a fix and checks it. That takes minutes, and customers feel it.

**Our idea:** software that runs that whole loop itself, in seconds.

---

## 2. What "agent" means here

> An agent is a piece of code that waits for a particular kind of event, does one job, and announces the result.

Four of the five use no AI:

- **Monitor** checks every service's numbers against limits.
- **Fix** applies a named fix such as `restart`.
- **Validation** re-reads the service and answers RECOVERED or STILL_BROKEN.
- **Report** writes the incident to the database.
- **Diagnosis** is the one that uses AI: it sends the numbers to a language model and asks for the cause and a fix.

So "multi-agent AI system" means: **small components that cooperate, one of which asks a language model for advice.** Say it that plainly.

---

## 3. The language model

An **LLM** (large language model) is a model trained to read and write text. We do not train one. We use open-weight models hosted by **Groq** on its free tier, by default `openai/gpt-oss-120b` (set with `GROQ_MODEL`; hosted model names get retired from time to time).

The prompt gives the model the service's numbers, an order of checks, the allowed causes and fixes, and asks for JSON only: `root_cause`, `confidence`, `fix`, `business_impact`, `explanation`.

**Why not just if-else rules?** That is the comparison we ran. On our four fault types the rules were right 180 times out of 180 and the model 179. The model's added benefit is a readable explanation. Whether it handles messier, combined symptoms better than rules is a reasonable idea that we have **not tested**.

---

## 4. Event-driven design

**Direct calls:** each component calls the next. Every part has to know about the others.

**Events:** the Monitor announces `ANOMALY_DETECTED` and does not care who listens. The Orchestrator is listening and asks for a diagnosis. The Diagnosis agent announces `DIAGNOSIS_READY`, and so on.

The channel is the **event bus**. Products such as Kafka do this at industrial scale; ours is a short module of our own:

```python
# the idea, simplified
subscribers = {}                      # topic -> list of functions

def subscribe(topic, fn):
    subscribers.setdefault(topic, []).append(fn)

async def publish(topic, payload):
    await asyncio.gather(*[fn(payload) for fn in subscribers.get(topic, [])])
```

It is easy to understand and needs no extra server. It also has limits: one process only, no stored messages, no delivery guarantee.

---

## 5. One incident from start to finish

1. **Healthy.** The Monitor polls every 5 s.
2. **Fault.** You click "Inject crash into payment".
3. **Detection.** On its next poll the Monitor sees `status: down` and publishes `ANOMALY_DETECTED`.
4. **Incident opened.** The Orchestrator creates a record, starts the clock and publishes `DIAGNOSE_REQUEST`.
5. **Diagnosis.** The model answers, for example `service_crash`, fix `restart`. This becomes `DIAGNOSIS_READY`.
6. **Fix.** `FIX_REQUEST`, then `FIX_APPLIED`.
7. **Validation.** `VALIDATE_REQUEST`; the Validation agent waits 2 s, re-reads health and publishes `VALIDATION_RESULT`.
8. **Report.** The incident and its timeline are saved.
9. **Dashboard.** The event stream updates the screen as each step happens.

**If it is still broken,** the Orchestrator picks a fix not yet tried and goes back to step 6. After 2 failed retries the incident is `ESCALATED`: a person is needed (no notification is sent).

The recovery time shown on the dashboard starts at **detection**, so it does not include the wait for the next poll.

---

## 6. Key terms

| Term | Meaning |
|---|---|
| Microservice | A small independent program doing one job |
| Monolith | One program doing everything |
| Agent | A component that reacts to an event and does one task |
| LLM | A pre-trained text model |
| Event bus / publish-subscribe | A channel where components send and listen for messages |
| Orchestrator | The coordinator that orders the steps and retries |
| MTTR | Mean time to recovery |
| Root cause | The underlying reason for a failure |
| Closed loop | Act, **check that it worked**, act again if not |
| Open loop | Act once and assume it worked |
| Baseline | What we compare against (manual response, rules, blind restart) |
| Strict healing | In the simulator, only a suitable fix cures a fault |
| Telemetry | The measurements collected: CPU, memory, response time, errors |

---

## 7. Why each technology

- **FastAPI:** handles many waiting tasks at once and documents the API itself.
- **Groq with open-weight models:** free tier and fast.
- **Our own event bus:** no extra infrastructure, and every line is explainable.
- **React with Vite:** component-based dashboard with fast builds.
- **SQLite:** one file, no database server.
- **Render and Vercel:** free hosting that deploys from GitHub.

---

## 8. What this project is not

- Not a shopping website: there are no customers, products or logins. The services are **simulated** so failures can be controlled and repeated.
- Not a trained AI model.
- Not production infrastructure. It is a small, reproducible demonstration of an architectural pattern, with measurements.

---

## 9. The summary statement

> We built a closed loop for microservice failures (detect, diagnose with a language model, fix, verify, retry, escalate) on a lightweight event bus of our own, running at no cost. In a simulated testbed, verifying and retrying recovered 99.8% of incidents against 95.5% when the first fix was trusted and 75% for blind restart.

When you say it, add that the services are simulated and that we wrote the table of which fix cures which fault. Other systems that close this loop exist, so do not claim to be the first.
