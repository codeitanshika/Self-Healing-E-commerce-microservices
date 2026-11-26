# Build Plan

How the project was built, phase by phase. Each phase ended with something runnable. Current status is in [progress-tracker.md](progress-tracker.md).

| Phase | Goal | What was built | Done when |
|---|---|---|---|
| 0. Setup | Repository and tools | Folder structure, virtual environment, Groq key | A test call to Groq replies |
| 1. Services | Things that can break | `SimulatedService`, `ServiceManager`, fault-injection endpoints, four fault types | Any service can be broken and its health shows it |
| 2. Detection | Notice faults | Event bus, topic constants, Monitor Agent with thresholds | A fault publishes `ANOMALY_DETECTED` |
| 3. Agents | One job each | Diagnosis (LLM), Fix, Validation, Report | Each handles its event correctly |
| 4. Closed loop | Run unattended | Orchestrator with retries and escalation | A fault heals and is logged with no human action |
| 5. Dashboard | See and drive it | React dashboard, statistics endpoints, live stream, fault lab | The loop is visible in the browser |
| 6. Deploy and evaluate | Public and measured | Render and Vercel deployment, experiment suite, figures | A live URL and result tables |

## Later additions
- Multi-fault and cascade scenarios
- A real Nginx container as an optional sixth service
- Strict healing (only a suitable fix cures a fault) and distinct retries
- Optional API key and rate limiting
- Per-incident stage timelines
- Test suite and continuous integration

## Remaining work
- Keep polling while incidents are being healed
- Validate the fields of the model's reply
- Re-run the strategy and noise experiments with the current retry policy
- Escalation notifications
- Slides, backup demo video and a release tag

## Commit discipline
- Small, working commits with `feat:`, `fix:`, `docs:`, `chore:`, `test:` or `ci:` prefixes.
- Never commit `.env` or `*.db`.
- Changes reach `main` through a pull request with passing checks.
