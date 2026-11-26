# UI Rules — Dashboard

## Principles
- One page, no routing: everything is reachable by scrolling.
- Updates without clicks: polling, plus Server-Sent Events for immediate refresh.
- Show numbers as well as status, for example recovery time and retry count.
- Be honest about state: show when the backend is unreachable or the live stream is reconnecting.

## Page order (top to bottom)
1. **Top bar:** overall health and live-stream status.
2. **Key figures:** recovery time against the manual baseline, recovery rate, diagnosis accuracy, first-try rate, revenue protected.
3. **Service health:** one card per service.
4. **Healing pipeline** and **event bus** beside the **fault lab**.
5. **Performance:** four charts.
6. **Incident history**, with a detail drawer per row.

## Incidents in progress
- Several can be active at once; each gets its own stepper (Detect → Diagnose → Fix → Validate → Resolved).
- A service card with an open incident says which stage the agents are in.
- A card can read healthy while still validating. Keep the badge until the incident closes.

## Colour
- Status colours mean state and nothing else.
- Never rely on colour alone: pair it with a word (HEALTHY, DEGRADED, DOWN, recovered, escalated).
- Pair a "down" summary with "agents responding" so it does not look stuck.

## Charts
- Every chart has a table view.
- Every chart has an empty state that says how to fill it.
- Say when a figure is illustrative (revenue) or assumed (the 900 s baseline).

## Controls
- Confirm destructive actions (reset demo data).
- Disable buttons while a request is running and report the outcome in text.
- Offer only faults a service really supports (the Nginx container: crash only).

## Accessibility and resilience
- Rows and controls work from the keyboard; Escape closes the drawer.
- Respect `prefers-reduced-motion`.
- Layout works at phone width.
- Never inject server text as HTML.
- If the chart code fails to load, the rest of the dashboard keeps working.
- Do not show raw JSON on the page.
