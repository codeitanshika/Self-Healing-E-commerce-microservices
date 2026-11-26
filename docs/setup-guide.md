# Setup guide

From a fresh clone to a running system, then deployment. Commands are shown for Windows PowerShell; differences for macOS and Linux are noted.

## 1. Prerequisites

| Tool | Version | Needed for |
|---|---|---|
| Python | 3.12 or newer | backend, tests, analysis (CI uses 3.13) |
| Node.js | 20.19 or newer | dashboard (CI uses 22) |
| Git | any recent | cloning |
| Groq API key | free, from [console.groq.com](https://console.groq.com) | LLM diagnosis |
| Docker Desktop | optional | the real Nginx service |

The tests and the `--mode rule` experiments run without an API key.

## 2. Clone

```powershell
git clone https://github.com/codeitanshika/Self-Healing-E-commerce-microservices
cd Self-Healing-E-commerce-microservices
```

## 3. Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1          # macOS/Linux: source venv/bin/activate
pip install -r requirements-dev.txt
copy ..\.env.example .env            # macOS/Linux: cp ../.env.example .env
```

Open `backend/.env` and replace `your_groq_key_here` with your key. Never commit this file.

Optional check that the key works (should print `{"ok": true}`):

```powershell
python test_groq.py
```

Start the server:

```powershell
uvicorn main:app --reload --reload-exclude "*.db" --port 8000
```

Keep `--reload-exclude "*.db"`: without it every saved incident restarts the server, which can loop while a service is unhealthy. API documentation is at <http://localhost:8000/docs>.

## 4. Dashboard

In a second terminal, from the project folder:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The dashboard talks to `http://localhost:8000` unless `VITE_API_URL` is set in `frontend/.env.local`.

## 5. Real Nginx service (optional)

With Docker Desktop running, from the project folder:

```powershell
docker compose up -d
```

Restart the backend. A sixth card, `nginx`, appears. Only the crash fault applies to it.

## 6. Checks

```powershell
cd backend
python -m pytest -q

cd ..\frontend
npm run lint
npm run build
```

GitHub Actions runs the same checks on pushes to `main` and on pull requests.

## 7. Configuration

All settings are environment variables, listed with comments in [`.env.example`](../.env.example) and in the [README](../README.md).

## 8. Deployment

### Backend on Render
1. New, then Web Service, and connect the repository.
2. Root directory `backend`. Build: `pip install -r requirements.txt`. Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`.
3. Environment variables: `GROQ_API_KEY`, `GROQ_MODEL`, `ALLOWED_ORIGINS` (your Vercel URL) and `API_KEY`. Without `API_KEY`, anyone who finds the URL can inject faults or reset the data.

Free services sleep when idle, so the first request can take up to a minute. The incident database does not survive a restart.

### Dashboard on Vercel
1. New Project, and import the repository.
2. Root directory `frontend`, framework preset Vite.
3. Environment variables: `VITE_API_URL` (your Render URL) and `VITE_API_KEY` (same value as `API_KEY`).

`VITE_API_KEY` is compiled into the public JavaScript, so visitors can read it. It deters casual abuse and is not real access control.

### After deploying
Open the dashboard, inject one fault and confirm that it recovers.

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| "Backend unreachable" | Start uvicorn; check the port and `VITE_API_URL` |
| Browser blocks requests (CORS) | Add the dashboard's address to `ALLOWED_ORIGINS` |
| Diagnosis shows `unknown` | Check the network and `GROQ_API_KEY` |
| 401 on fault injection | `VITE_API_KEY` must match `API_KEY` |
| 429 rate limit | Wait a minute, or raise `RATE_LIMIT_MAX` |
| Event feed stops updating after a backend restart | Reload the page |
| `Activate.ps1` is blocked | Run `Set-ExecutionPolicy -Scope Process RemoteSigned` first |
