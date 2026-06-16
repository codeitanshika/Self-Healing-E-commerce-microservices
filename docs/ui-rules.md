# UI Rules — Dashboard

> Your original rules kept; "Streamlit" references updated to React. The single-page, auto-refresh, numbers-not-just-dots philosophy is unchanged.

## General Principles
- Single page, no routing — examiner sees everything by scrolling.
- Auto-refresh every 3–5s (polling hook) so the live demo updates without clicks.
- Show numbers, not just status — "RECOVERED in 47s, ₹8,400 protected" beats a green dot.

## Page Sections (top to bottom)
1. **Title + tagline** — "Self-Healing E-Commerce Platform Monitor"
2. **Live service health row** — 5 tiles (Auth, Cart, Payment, Inventory, Notification), colors per `ui-tokens.md`.
3. **Summary metrics row** (4 metric cards):
   - Avg MTTR (your system)
   - Manual baseline MTTR (900s)
   - Total revenue protected (₹)
   - Incidents auto-resolved (count)
4. **Active incident banner** (only when an incident is in progress):
   - "🔄 Payment service: diagnosing… / fixing… / validating…"
   - Shows current pipeline stage in real time.
5. **Incident history table** — most recent first.
6. **MTTR comparison chart** — bar per fault type vs baseline.
7. **Revenue protected chart** — cumulative.

## Active Incident Banner
- One active incident at a time (faults injected one at a time during demo).
- Stage comes from `GET /api/active-incident` (backend tracks current stage in the orchestrator).
- Clears once result is RECOVERED or ESCALATED.

## Color Rules
- Never show red + a rising number without context — pair "DOWN" with "agents responding…" so it doesn't look stuck.
- Green consistently means good (recovered, healthy, revenue protected).

## Empty State
- If there are zero incidents: show "No incidents yet — inject a fault to see the system respond" instead of empty table/charts.

## Do NOT
- No multi-page routing — keep it single page for demo flow.
- No manual-refresh-only — polling auto-refresh must work.
- No raw JSON on the main view — keep it human-readable (a collapsible "debug" panel is fine).

## Demo Mode Helper
A sidebar with fault-injection controls (service + fault-type select + one "Inject" button) calling `POST /api/services/{name}/inject-fault`, so the demo needs no separate terminal.
