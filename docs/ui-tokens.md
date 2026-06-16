# UI Tokens — Dashboard Design

> Your original color/typography system is kept as-is (it's good). Only the framework mapping changed from Streamlit to React + Tailwind + Recharts. Put these colors in your Tailwind theme.

## Color Tokens
| Token | Hex | Usage |
|---|---|---|
| `status-healthy` | #1D9E75 | Service tile when healthy |
| `status-degraded` | #BA7517 | Service tile when degraded (slow/high CPU) |
| `status-down` | #E24B4A | Service tile when crashed |
| `bg-primary` | #0E0E10 | Dashboard background |
| `bg-card` | #1A1A1D | Card/tile background |
| `text-primary` | #F5F5F5 | Main text |
| `text-secondary` | #A0A0A5 | Labels, captions |
| `accent` | #534AB7 | Highlights, active retry indicator |

Tailwind theme example (`tailwind.config.js`):
```js
theme: { extend: { colors: {
  healthy: "#1D9E75", degraded: "#BA7517", down: "#E24B4A",
  bgPrimary: "#0E0E10", bgCard: "#1A1A1D",
  textPrimary: "#F5F5F5", textSecondary: "#A0A0A5", accent: "#534AB7",
}}}
```

## Typography
- Headers: a clean sans (Inter or system UI) — bold, larger scale.
- Metrics: large numeric weight for MTTR / revenue / counts.
- Body/labels: regular weight, `text-secondary` color.

## Layout Tokens
- Service tiles: a 5-column responsive grid (`grid grid-cols-2 md:grid-cols-5 gap-4`).
- Section spacing: a divider or generous vertical gap between sections.
- Refresh interval: 3–5 seconds (polling hook).

## Status Tile Spec
Each of the 5 tiles shows:
- Service name (bold)
- Status text: HEALTHY / DEGRADED / DOWN
- Sub-metric: "CPU X% | Mem Y%"
- Background color per `status-*` tokens.

## Incident Table Columns (display order)
1. Timestamp 2. Service 3. Root Cause 4. Fix Applied 5. Result (RECOVERED/STILL_BROKEN/ESCALATED) 6. MTTR (s) 7. Revenue Protected (₹)

## Charts (Recharts)
- **MTTR by fault type:** bar chart, one bar per root_cause, with a dashed `ReferenceLine` at y=900 labeled "Manual baseline (15 min)".
- **Revenue protected over time:** cumulative line chart (x = incident number, y = cumulative ₹).

## Icons (emoji is fine)
- Healthy 🟢 · Degraded 🟡 · Down 🔴 · Retry in progress 🔄
