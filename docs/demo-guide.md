# Demo guide

Commands are for **PowerShell on Windows** (the repo root is the folder containing `backend/` and `frontend/`). On macOS/Linux use `source venv/bin/activate` instead of `.\venv\Scripts\Activate.ps1`.

## One-time setup

```powershell
# 1) backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy ..\.env.example .env        # then open .env and paste your real GROQ_API_KEY

# 2) frontend (new terminal)
cd frontend
npm install
```

`frontend/.env` already points at `http://localhost:8000`. If you set `API_KEY` in the backend `.env`, also put `VITE_API_KEY=<same value>` in `frontend/.env.local`.

## Every demo: start it (two terminals)

```powershell
# Terminal 1: backend
cd backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload --reload-exclude "*.db" --port 8000

# Terminal 2: dashboard
cd frontend
npm run dev
```

Open **http://localhost:5173** (dashboard) and **http://localhost:8000/docs** (API docs).

Optional real container (needs Docker Desktop running): `docker compose up -d`, then restart the backend. A sixth tile, `nginx`, appears.

## Before the audience arrives

1. Open the dashboard and click **Reset demo data** (confirm). The page starts clean.
2. Make sure the top-right pills read **All systems operational** and **Live stream**.

## Suggested 6-minute script

| Min | Do | Say |
|---|---|---|
| 0:00 | Show the dashboard, point at the five service cards | "Five e-commerce services, monitored live. Sparklines are response time." |
| 0:45 | **Fault lab**: Payment + Crash, click Inject | "I just killed the payment service. I touch nothing from here." |
| 1:00 | Watch the **Healing pipeline** and **Event bus** | "Monitor detects it, the LLM diagnoses, the fix agent acts, and the validator re-checks real health. Every message is on this bus." |
| 2:00 | Incident appears in the table; the KPI strip updates | "Recovered in a few seconds. A manual response is assumed at 900 s." |
| 2:30 | Click the incident row | "The timeline shows each stage, and the LLM's own reasoning and business impact." |
| 3:30 | Run **Flash-sale surge** (3 faults at once) | "Three services fail simultaneously. Incidents are handled concurrently." |
| 4:30 | Run **Checkout cascade** | "One failure drags others down seconds later." |
| 5:00 | Click **Table** on a chart | "Every chart has an accessible table view." |
| 5:30 | Show `docs/results/figures/fig8_strategies.png` | "With strict healing, a blind restart recovers 75%. The closed loop recovers everything, even when the model's first fix is wrong." |

## If something goes wrong on stage

| Symptom | Fix |
|---|---|
| Pill says "Backend unreachable" | Backend terminal not running or wrong port; restart uvicorn |
| "Reconnecting..." pill | Stream dropped; it reconnects on its own within seconds |
| Diagnosis says `unknown` | Groq unreachable or key invalid; the system falls back to a restart and still recovers crashes. Check `GROQ_API_KEY`. |
| Service stuck anomalous | Click **Reset demo data**, or `POST /api/services/<name>/heal` |
| Nothing happens on Inject | If you set `API_KEY`, the frontend needs a matching `VITE_API_KEY` |

## Commands to show the engineering and the research

```powershell
cd backend
python -m pytest -q                                   # 66 tests
curl.exe -N http://localhost:8000/api/stream          # the raw live event stream
curl.exe -X POST http://localhost:8000/api/services/cart/fault/slow   # inject from a terminal

# research (outputs land in docs/results/)
python -m experiments.analyze                         # statistics.md
python -m experiments.analyze_pipeline                # pipeline-latency.md
python -m experiments.analyze_noise                   # verification-under-noise.md
python -m experiments.analyze_strategies              # strategy-comparison.md
python -m experiments.make_figures                    # figures

# rerun experiments (LLM ones need GROQ_API_KEY)
python -m experiments.run_pipeline --service payment --fault all --trials 5 --mode rule
python -m experiments.run_pipeline --scenario everything-breaks --trials 5 --mode rule
python -m experiments.run_strategies --mode llm --model openai/gpt-oss-120b --trials 3
python -m experiments.run_pipeline --service nginx --fault crash --trials 10 --mode rule   # needs Docker
```
