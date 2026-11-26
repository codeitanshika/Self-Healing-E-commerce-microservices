# Retry Loop Verification — Test Report

> Historical report: the manual test below used the earlier policy, where both retries used the same fix (now `RETRY_POLICY=repeat`). The bounded-retry and escalation behaviour is unchanged.

## Current behaviour

By default (`RETRY_POLICY=distinct`) each retry uses a fix not yet tried on the incident. In the example below the sequence would now be `reduce_load`, then `restart`, then `clear_memory`, then escalation. Automated tests cover this: `test_still_broken_retries_then_escalates` and `test_orchestrator_ignores_its_own_escalation_event` in `backend/tests/test_orchestrator.py`, and the retry-policy tests in `backend/tests/test_fix_map.py`.

## Objective

Verify that the Orchestrator's retry mechanism behaves correctly under
repeated fix failure: it should retry with an alternate remediation up
to a configured limit (`MAX_RETRIES = 2`), then escalate the incident
rather than retrying indefinitely.

## Test Design

Real STILL_BROKEN outcomes are rare in this testbed because most
configured fixes succeed on the first attempt (see Phase 6 experiment
results for first-try success rate). To exercise the retry path
deterministically, the Orchestrator's `on_validation_result()` handler
was invoked directly with synthetic STILL_BROKEN payloads for a single
incident (`073cfa76`, service: `cart`, root_cause: `cpu_overload`,
primary fix: `reduce_load`, configured retry fix: `restart`).

This isolates the retry/escalation logic from the rest of the pipeline
and allows repeated failure to be simulated without depending on
service-level non-determinism.

## Results

| Attempt | Input | Orchestrator Decision | retry_count |
|---|---|---|---|
| 1 | STILL_BROKEN (1st fix failed) | Dispatch retry fix `restart` | 1 |
| 2 | STILL_BROKEN (2nd fix failed) | Dispatch retry fix `restart` | 2 |
| 3 | STILL_BROKEN (3rd fix failed) | `retry_count >= MAX_RETRIES` → mark `ESCALATED`, stop retrying | 2 (unchanged) |

The system correctly bounded retries at the configured limit and
transitioned to a terminal `ESCALATED` state exactly once, with no
further fix dispatches after escalation.

## Log Excerpt
```
--- Simulating incident 073cfa76: first fix FAILED (STILL_BROKEN) ---

[Orchestrator] incident 073cfa76 STILL_BROKEN — retry #1 with fix 'restart'

[EventBus] FIX_REQUEST → cart

retry_count is now: 1
--- Simulating incident 073cfa76: SECOND fix also FAILED ---

[Orchestrator] incident 073cfa76 STILL_BROKEN — retry #2 with fix 'restart'

[EventBus] FIX_REQUEST → cart

retry_count is now: 2
--- Simulating incident 073cfa76: THIRD failure → should ESCALATE ---

[Orchestrator] incident 073cfa76 ESCALATED after 2 retries
```
## Defect Identified and Resolved: Self-Triggered Feedback Loop

**Symptom.** The first implementation of the escalation path caused the
Orchestrator to publish `ESCALATED` events indefinitely once `MAX_RETRIES`
was exceeded — observed as an unbroken stream of identical log lines with
no termination.

**Root cause.** The escalation branch re-published on the
`VALIDATION_RESULT` topic so the Report Agent (a separate subscriber to
the same topic) could persist the outcome. However, the Orchestrator is
itself subscribed to `VALIDATION_RESULT`. Publishing to that topic caused
the event bus to invoke the Orchestrator's own handler again, which
re-evaluated `retry_count >= MAX_RETRIES`, found it still true, and
republished — a self-sustaining cycle with no exit condition.

**Resolution.** Added an idempotency guard at the top of
`on_validation_result()`: if the incoming `result` is already `ESCALATED`,
the handler returns immediately without further processing. This
preserves single-write delivery to the Report Agent while preventing the
Orchestrator from reacting to its own terminal-state announcements.

**Significance.** A component that both consumes and produces events on the same topic can feed back into itself. This is a typical hazard of publish/subscribe systems, and building the control plane ourselves means such guarantees have to be handled in our own code.
