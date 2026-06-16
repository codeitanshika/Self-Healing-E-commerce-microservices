# Setup Guide — From Empty VS Code to Deployed App

Follow this top to bottom for Phase 0. Later sections (frontend scaffold, deployment) are referenced from their phases.

---

## Part A — Create the repo (Phase 0)

### 1. Make the project folder
```bash
mkdir self-healing-ecommerce
cd self-healing-ecommerce
code .                       # opens VS Code in this folder
```

### 2. Initialize git
In the VS Code terminal (`Ctrl+\``):
```bash
git init
git branch -M main
```

### 3. Create the folder structure
```bash
# backend
mkdir -p backend/services backend/agents backend/orchestrator backend/shared backend/database backend/fault_injector
# python package markers
touch backend/services/__init__.py backend/agents/__init__.py backend/orchestrator/__init__.py backend/shared/__init__.py backend/database/__init__.py backend/fault_injector/__init__.py
# docs
mkdir -p docs
```
(On Windows without `touch`, create the empty `__init__.py` files via the VS Code file explorer.)

### 4. Add `.gitignore` (project root)
```
# Python
__pycache__/
*.pyc
venv/
.env

# Database
*.db

# Node
node_modules/
dist/
.env.local

# IDE / OS
.vscode/
.idea/
.DS_Store
```

### 5. Python virtualenv + dependencies
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```
Create `backend/requirements.txt`:
```
fastapi
uvicorn[standard]
httpx
psutil
groq
python-dotenv
sqlmodel
```
Install:
```bash
pip install -r requirements.txt
```

### 6. Groq API key
- Go to console.groq.com, sign up (free, no card), create an API key.
- Create `backend/.env.example` (committed, no secret):
  ```
  GROQ_API_KEY=your_key_here
  GROQ_MODEL=llama-3.3-70b-versatile
  ```
- Create `backend/.env` (NOT committed) and paste your real key.

### 7. Verify Groq works
Create `backend/test_groq.py`:
```python
import os, json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

resp = client.chat.completions.create(
    model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    messages=[{"role": "user", "content": 'Reply ONLY with JSON: {"ok": true}'}],
    max_tokens=50,
)
print(resp.choices[0].message.content)
```
Run `python test_groq.py`. You should see `{"ok": true}`. Delete the file after (or keep it as a smoke test).

### 8. First commit + push to GitHub
- Create an empty repo on github.com (no README, since you have one).
```bash
cd ..
git add .
git commit -m "chore: initial project structure and tooling"
git remote add origin https://github.com/<you>/self-healing-ecommerce.git
git push -u origin main
```

**Phase 0 done.** ✅

---

## Part B — Groq instead of Anthropic (important note)

Your original `library-docs.md` used the Anthropic SDK (paid). Use this **free** pattern everywhere instead. The only differences are the import, the client, and the response path.

```python
import os, json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def ask_llm(prompt: str) -> dict:
    resp = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0.2,                      # low = more consistent JSON
    )
    text = resp.choices[0].message.content
    try:
        # strip accidental ```json fences if present
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except json.JSONDecodeError:
        return {"root_cause": "unknown", "confidence": 0,
                "fix": "restart", "business_impact": "unknown",
                "explanation": "LLM returned invalid JSON; defaulting."}
```

Groq free-tier limits are generous for development and experiments. If you ever hit a rate limit mid-experiment, just wait a minute and continue.

---

## Part C — Frontend scaffold (Phase 5)

```bash
# from project root
npm create vite@latest frontend -- --template react
cd frontend
npm install
npm install recharts
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```
Configure Tailwind `content` to scan `./src/**/*.{js,jsx}` and add the directives to `src/index.css`. Point the frontend at the backend with an env var:
```
# frontend/.env
VITE_API_URL=http://localhost:8000
```
Run with `npm run dev` (serves on `http://localhost:5173`).

**CORS:** in `backend/main.py`, allow the frontend origin:
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],   # add your Vercel URL later
    allow_methods=["*"], allow_headers=["*"],
)
```

---

## Part D — Deployment (Phase 6)

### Backend → Render (free)
1. Push your code to GitHub.
2. On render.com: New → Web Service → connect the repo.
3. Root directory: `backend`. Build: `pip install -r requirements.txt`.
   Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`.
4. Add environment variable `GROQ_API_KEY` (and `GROQ_MODEL`).
5. Note the public URL (e.g. `https://yourapp.onrender.com`).

> Free Render services sleep when idle and take ~30s to wake. Fine for a portfolio/demo; mention it in your README.

### Frontend → Vercel (free)
1. On vercel.com: New Project → import the repo.
2. Root directory: `frontend`. Framework preset: Vite.
3. Add env var `VITE_API_URL=https://yourapp.onrender.com`.
4. Deploy → you get a public `https://...vercel.app` URL.

### Final wiring
- Add the Vercel URL to the backend CORS `allow_origins`.
- Redeploy backend. Test the live dashboard end to end.

---

## Part E — Everyday git workflow

```bash
# start of a session
git pull

# ... do work, keep it runnable ...

git add .
git commit -m "feat: monitor agent threshold rules"
git push
```
- One concern per commit. Clear message prefix: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`.
- Tag milestones: `git tag v0.1-services && git push --tags`.
- If in a team: branch per person (`feat/diagnosis-agent`), merge to `main` only when it runs.
