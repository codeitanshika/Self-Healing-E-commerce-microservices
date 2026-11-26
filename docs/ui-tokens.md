# UI Tokens — Dashboard Design

The dashboard uses a dark "operations console" theme written in plain CSS. Tokens are CSS variables on `:root` in [`frontend/src/index.css`](../frontend/src/index.css), which is the source of truth.

## Surfaces and text
| Token | Value | Use |
|---|---|---|
| `--bg` | `#0a0b0e` | Page background |
| `--bg-elevated` | `#101217` | Drawer, card gradient end |
| `--surface` | `#14171d` | Cards |
| `--surface-2` | `#1a1e26` | Inputs, tracks, hover |
| `--border` | `#242933` | Card borders, grid lines |
| `--border-strong` | `#323946` | Controls |
| `--text` | `#eceef2` | Main text |
| `--text-2` | `#a4abb8` | Secondary text |
| `--text-3` | `#6f7787` | Labels, captions, axes |

## Status colours
Reserved for state. Each has a tinted background variant (`--ok-bg` and so on).

| Token | Value | Meaning |
|---|---|---|
| `--ok` | `#2fbf8f` | Healthy, recovered |
| `--warn` | `#e0a030` | Degraded, retry |
| `--down` | `#ec5b5b` | Down, escalated, destructive action |
| `--info` | `#5b9dff` | Selection, validation messages |
| `--accent` | `#8a7dff` | Agents at work, diagnosis, confidence |

## Chart series
Fixed order: `--series-1` `#3987e5`, `--series-2` `#d95926`, `--series-3` `#199e70`, `--series-4` `#c98500`, `--series-5` `#d55181`.

`ServiceGrid.jsx` (sparklines) and `Charts.jsx` repeat some of these values as literal hex strings. Change both places together.

## Type and shape
| Token | Value |
|---|---|
| `--sans` | Inter, then the system UI font |
| `--mono` | JetBrains Mono, then the system monospace font |
| `--radius` / `--radius-sm` | `14px` / `9px` |
| Base size | `14px`, line height 1.5 |

Numbers that update live use the `.num` class (tabular figures) so they do not shift.

## Layout
| Element | Rule |
|---|---|
| Page width | 1320px maximum |
| Key figures | 1 wide card + 4; two columns below 1100px |
| Service cards | `repeat(auto-fill, minmax(205px, 1fr))`; two columns below 640px, one below 380px |
| Pipeline and fault lab | two columns; stacked below 980px |
| Detail drawer | `min(480px, 100vw)` |

## Meter thresholds
| Meter | Amber at | Red at |
|---|---|---|
| CPU | 70% | 85% |
| Memory | 70% | 85% |
| Error rate | 15% | 30% |
