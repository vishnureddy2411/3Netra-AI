# 3Netra-AI — Complete Setup Guide

This is your **exact sequence** of commands to get from zero to a working development environment.
Follow in order. Do not skip steps. Each verification command must pass before moving on.

---

## Before You Start — What You Need

- [ ] GitHub account (free)
- [ ] Supabase account (free) — supabase.com
- [ ] Anthropic account (free $5 credit) — console.anthropic.com
- [ ] Docker Desktop installed — docker.com/products/docker-desktop
- [ ] Git installed — already done (you cloned the repo)

---

## STEP 1 — Verify Core Runtimes

### Windows (PowerShell)
```powershell
# Check Node.js
node -v
# Expected: v20.x.x or higher
# If wrong: https://nodejs.org/en/download — download LTS installer

# Check Python
python --version
# Expected: Python 3.12.x
# If wrong: https://www.python.org/downloads/release/python-3123/

# Check Docker
docker --version
# Expected: Docker version 26.x.x or higher
docker ps
# Expected: empty list, no error

# Check Git
git --version
# Expected: git version 2.x.x
git config user.email
# Expected: your email address
```

### Mac/Linux
```bash
node -v          # Expected: v20.x.x
python3 --version # Expected: Python 3.12.x
docker --version  # Expected: Docker version 26.x.x
docker ps        # Expected: empty list
git --version    # Expected: git version 2.x.x
```

**All 5 must pass before Step 2.**

---

## STEP 2 — Clone Repo and Open in VS Code

```powershell
# Windows
cd C:\Users\lenovo
git clone https://github.com/vishnureddy2411/3Netra-AI.git
cd 3Netra-AI
code .
```

```bash
# Mac/Linux
git clone https://github.com/vishnureddy2411/3Netra-AI.git
cd 3Netra-AI
code .
```

VS Code opens. Open the integrated terminal: **Ctrl + `** (backtick)

---

## STEP 3 — Python Virtual Environment

**Run all remaining Python commands from inside the virtual environment.**

### Windows (PowerShell)
```powershell
# Create virtual environment
python -m venv venv

# Activate it (you must do this every time you open a new terminal)
.\venv\Scripts\Activate.ps1

# If you get a policy error, run this once:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Then activate again:
.\venv\Scripts\Activate.ps1

# Verify — you should see (venv) at the start of your prompt
python --version
# Expected: Python 3.12.x
```

### Mac/Linux
```bash
python3 -m venv venv
source venv/bin/activate
python --version   # Expected: Python 3.12.x
```

---

## STEP 4 — Install Python Dependencies

```bash
# With venv activated:
pip install --upgrade pip
pip install -r requirements.txt

# This takes 3-5 minutes (downloading torch, sentence-transformers, etc.)
# Expected: Successfully installed X packages

# Verify key packages installed correctly:
python -c "import fastapi, litellm, anthropic, tiktoken, pdfplumber, httpx; print('Python packages OK')"
# Expected: Python packages OK

# Install Playwright browsers (needed for Stage 9)
playwright install chromium
# Expected: chromium downloaded successfully
```

---

## STEP 5 — Install Node.js Dependencies

```bash
cd frontend
npm install
# Expected: added XXX packages

# Verify:
npm run build
# Expected: ✓ Compiled successfully
# OR: just check next is there:
npx next --version
# Expected: 16.x.x

cd ..
# Back to project root
```

---

## STEP 6 — Start Docker Services

```bash
# Start Valkey (cache)
docker compose up -d

# Verify Valkey is running:
docker ps
# Expected: 3netra-valkey container with status "Up"

# Test Valkey responds:
docker exec 3netra-valkey valkey-cli ping
# Expected: PONG
```

---

## STEP 7 — Set Up Environment Variables

```powershell
# Windows PowerShell
Copy-Item .env.example .env.local
notepad .env.local
```

```bash
# Mac/Linux
cp .env.example .env.local
nano .env.local  # or code .env.local
```

**Fill in these values (minimum to start):**

### ANTHROPIC_API_KEY
1. Go to: console.anthropic.com
2. Click "API Keys" → "Create Key"
3. Copy and paste into `.env.local`

### SUPABASE_URL + SUPABASE_KEY + SUPABASE_ANON_KEY
1. Go to: supabase.com → New Project
2. Wait for project to provision (~2 minutes)
3. Go to: Project Settings → API
4. Copy: Project URL → SUPABASE_URL
5. Copy: service_role secret → SUPABASE_KEY
6. Copy: anon public key → SUPABASE_ANON_KEY (also NEXT_PUBLIC_SUPABASE_ANON_KEY)

### GITHUB_TOKEN
1. Go to: github.com → Settings → Developer Settings → Personal Access Tokens → Tokens (classic)
2. Generate new token → Name: "3netra-ai" → Expiration: 90 days
3. Scopes: check `public_repo`
4. Copy and paste into `.env.local`

### Leave these as-is for local dev:
```
VALKEY_URL=redis://localhost:6379
MCP_SERVER_URL=http://localhost:8001
PORT=8000
NEXT_PUBLIC_API_URL=http://localhost:8000
ENVIRONMENT=development
```

---

## STEP 8 — Set Up Supabase Database

1. Go to your Supabase project dashboard
2. Click **SQL Editor** → **New Query**
3. Copy the entire contents of `database/schema.sql`
4. Paste into SQL Editor → click **Run**
5. Expected: "Success. No rows returned"
6. Open another New Query
7. Copy `database/rls_policies.sql` → Paste → Run
8. Expected: "Success. No rows returned"

**Verify RLS works:**
In SQL Editor, run:
```sql
SELECT * FROM projects;
```
Expected: empty result set (0 rows), NOT an error. If it says "relation does not exist" → schema.sql didn't run correctly.

---

## STEP 9 — Verify Anthropic API Key

```bash
# With venv activated and .env.local filled:
cd backend
python -c "
import os
from dotenv import load_dotenv
load_dotenv('../.env.local')
import anthropic
c = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
r = c.messages.create(model='claude-haiku-4-5', max_tokens=10, messages=[{'role':'user','content':'ping'}])
print('Anthropic OK:', r.content[0].text)
"
# Expected: Anthropic OK: [some short response]
# If 401: wrong API key
# If 429: wait 60 seconds and retry
```

---

## STEP 10 — Start the Backend

```bash
# Terminal 1 — with venv activated, from project root:
cd backend
uvicorn main:app --reload --port 8000

# Expected output (after a few seconds):
# INFO: skills loaded: 19 skills
# INFO: http_client created
# INFO: database initialized
# INFO: 3netra_ai_startup_complete
# INFO: Uvicorn running on http://0.0.0.0:8000

# Verify health check works — open new terminal:
curl http://localhost:8000/health
# Expected: {"status":"ok","service":"3netra-ai-backend","checks":{...}}
```

---

## STEP 11 — Start the MCP Server

```bash
# Terminal 2 — with venv activated, from backend/:
python mcp_server.py

# Expected:
# INFO: FastMCP server starting on port 8001
# INFO: 18 tools registered

# Verify:
curl http://localhost:8001/health
# Expected: {"status":"ok"}
```

---

## STEP 12 — Start the Frontend

```bash
# Terminal 3 — from frontend/:
cd frontend
npm run dev

# Expected:
# ▲ Next.js 16.2.6
# - Local: http://localhost:3000
# ✓ Ready in 2.1s

# Open browser: http://localhost:3000
# Expected: Chat interface with "What are you building today?" input
```

---

## STEP 13 — Final Verification

Run all 8 Stage 0 gates:

```bash
# Gate 1: Node.js
node -v
# Expected: v20.x.x ✓

# Gate 2: Python
python --version
# Expected: Python 3.12.x ✓

# Gate 3: Valkey
docker exec 3netra-valkey valkey-cli ping
# Expected: PONG ✓

# Gate 4: Backend health
curl http://localhost:8000/health
# Expected: {"status":"ok",...} ✓

# Gate 5: MCP server health
curl http://localhost:8001/health
# Expected: {"status":"ok"} ✓

# Gate 6: Python packages
python -c "import fastapi, litellm, anthropic, tiktoken, pdfplumber; print('OK')"
# Expected: OK ✓

# Gate 7: Anthropic API call
# (run the test from Step 9 above)
# Expected: Anthropic OK: [response] ✓

# Gate 8: Frontend loads
# Open http://localhost:3000
# Expected: Chat interface with input box ✓
```

**All 8 gates must show ✓ before Stage 1 starts.**

---

## Common Problems

### Problem: PowerShell says "cannot be loaded, running scripts is disabled"
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Problem: `pip install` fails with "Microsoft Visual C++ required"
Download and install: Visual C++ Build Tools from visualstudio.microsoft.com/visual-cpp-build-tools/

### Problem: `playwright install chromium` says "no browser found"
```bash
playwright install
# This installs all browsers. Then:
playwright install chromium
```

### Problem: Supabase schema fails with "extension vector does not exist"
Go to Supabase → Database → Extensions → search "vector" → enable it. Then re-run schema.sql.

### Problem: `uvicorn main:app` fails with "No module named 'main'"
Make sure you are in the `backend/` folder: `cd backend` then `uvicorn main:app --reload`

### Problem: Port 8000 already in use (Windows)
```powershell
netstat -ano | findstr :8000
taskkill /PID [PID_NUMBER] /F
```

### Problem: weasyprint fails to install on Windows
weasyprint needs GTK on Windows. Install via: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer
Then: `pip install weasyprint`

---

## Terminal Layout (keep these open while developing)

```
Terminal 1: venv + uvicorn (backend)
Terminal 2: venv + python mcp_server.py (MCP)
Terminal 3: npm run dev (frontend)
Terminal 4: free for commands
```

VS Code split terminal: Ctrl+Shift+5 (split), Ctrl+Shift+` (new terminal)

---

## Every Day When You Return

```bash
# Terminal 1:
cd 3Netra-AI/backend
.\venv\Scripts\Activate.ps1   # Windows
source ../venv/bin/activate    # Mac/Linux
uvicorn main:app --reload

# Terminal 2:
python mcp_server.py

# Terminal 3:
cd 3Netra-AI/frontend
npm run dev

# Check Docker is still running:
docker ps   # should show 3netra-valkey
# If not: docker compose up -d
```
