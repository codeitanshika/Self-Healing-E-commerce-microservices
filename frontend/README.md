# Dashboard

React + Vite front end for the self-healing control plane. It shows live service health, the healing pipeline, the event-bus feed, charts and incident history, and includes a fault lab for demos.

## Run

Start the backend first (see the [setup guide](../docs/setup-guide.md)), then from this folder:

```bash
npm install
npm run dev        # http://localhost:5173
```

## Configuration

Optional, in `.env.local`. Values are read when the app is built.

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Backend address |
| `VITE_API_KEY` | empty | Sent as `X-API-Key`; must match the backend's `API_KEY`. Visible to anyone who loads the page |

## Scripts

| Command | Does |
|---|---|
| `npm run dev` | Development server |
| `npm run lint` | ESLint |
| `npm run build` | Production build in `dist/` |
| `npm run preview` | Serve the build |

## Layout

```
src/
  App.jsx          fetches data and arranges the page
  components/      one file per dashboard section
  lib/             API client, polling and stream hooks, formatters
  index.css        design tokens and all styles
```

See the [component registry](../docs/ui-registry.md), [UI rules](../docs/ui-rules.md) and [design tokens](../docs/ui-tokens.md).
