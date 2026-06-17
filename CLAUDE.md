# 3Netra-AI — CLAUDE.md

## Project Identity
**Product Name:** 3Netra-AI
**Tagline:** See your project clearly before you build it.
**Mission:** Multi-agent AI platform that guides users from idea to deployed, tested, documented portfolio project in one session.
**Current Phase:** Stage 1 — Foundation Layer (MCP Server)
**Stage 0:** COMPLETE
**Build Week:** 0 of 12

---

## What This Project Is

A ChatGPT-style chat interface where:
1. User types a project idea
2. Research Agent searches GitHub + HackerNews + arXiv + StackOverflow
3. 5 AI Advisors debate the idea in parallel (adversarial War Room)
4. Chairman synthesizes a BUILD/PIVOT/ABANDON verdict
5. Architecture diagrams generated before any code is written
6. Developer Agent builds one module at a time with live preview
7. User approves or rejects each module before the next is built
8. Career output: GitHub README, LinkedIn post, resume bullets, PDF verdict card

---

## Tech Stack (exact versions)

| Layer | Tool | Version |
|-------|------|---------|
| Frontend | Next.js (App Router, TypeScript) | 16.2.6 |
| Styling | Tailwind CSS | 4.0.0 |
| Backend | FastAPI + Uvicorn | 0.115.6 + 0.34.0 |
| Language | Python | 3.12.x |
| AI Client | litellm (model-agnostic) | 1.57.4 |
| AI Model Fast | Claude Haiku | claude-haiku-4-5 |
| AI Model Strong | Claude Sonnet | claude-sonnet-4-6 |
| MCP Server | FastMCP v2 | 2.3.3 |
| Database | Supabase (PostgreSQL + pgvector) | Managed |
| Cache | Valkey 8.1 | Docker |
| Memory | SQLite (decisions.db + rewards.db) | stdlib |
| Embeddings | all-MiniLM-L6-v2 (384 dim, local) | sentence-transformers |
| Preview Sandbox | Docker + docker-py | 7.1.0 |
| Screenshots | Playwright | 1.49.0 |
| PDF Output | WeasyPrint | 63.1 |
| GitHub API | PyGithub | 2.5.0 |
| Streaming | SSE (Server-Sent Events) | native |

---

## Model Routing Rules

**ALWAYS use litellm — never import anthropic directly**

```python
# CORRECT — every agent file
from services.llm_client import call_fast, call_strong, call_fast_parallel, stream_strong

# WRONG — never do this
import anthropic
client = anthropic.Anthropic()
```

**Haiku (call_fast):** advisors, quiz, annotations, diagram planner, module classifier, LinkedIn draft, cost tracking
**Sonnet (call_strong):** chairman verdict, architecture diagrams, code generation, README generation

---

## Critical Architecture Rules

1. **MCP Server is the single source of truth.** Never read project state from SQLite directly in agent services. Always go through MCP tools: `get_existing_files()`, `get_api_contracts()`, `get_project_graph()`, etc.

2. **Skill injection is mandatory for every module build.** Before Developer agent generates any code, call `get_relevant_skills(module_name, tech_stack)` from MCP server. Never build without skills injected.

3. **Project Graph pre-wires all routing.** Every navigation link in generated code must use exact paths from `project_graph.json`. Never use "#" as a navigation placeholder.

4. **Reward engine is non-negotiable.** Every call_fast() and call_strong() logs to reward engine automatically. When user approves (✅): call `record_reward(action="approve")`. When user fixes (✏️): `action="fix"`. When rebuild (🔄): `action="rebuild"`.

5. **One module at a time.** Never build two modules simultaneously. Wait for MCP `write_approval(status="approved")` before starting the next module.

6. **Pydantic validation on all agent outputs.** Use parse_safe() methods from `backend/models/agent_outputs.py`. Never pass raw Claude response strings downstream.

7. **Error recovery for every failure.** Use `backend/services/error_recovery.py` for all failures. Never let raw Python exceptions reach the chat UI.

---

## Project Structure

```
3netra-ai/
├── CLAUDE.md                    ← this file
├── requirements.txt
├── docker-compose.yml
├── .env.example
├── .env.local                   ← never commit
├── frontend/
│   ├── package.json
│   ├── app/
│   │   ├── page.tsx             ← THE chat interface (entire product)
│   │   └── layout.tsx
│   ├── components/
│   │   ├── MessageList.tsx
│   │   ├── ChatInput.tsx
│   │   ├── CostBadge.tsx
│   │   └── cards/               ← 8 message card types
│   └── hooks/
│       └── useSSE.ts
├── backend/
│   ├── main.py                  ← FastAPI entry point (port 8000)
│   ├── mcp_server.py            ← FastMCP server (port 8001)
│   ├── models/
│   │   └── agent_outputs.py     ← Pydantic models for ALL agent responses
│   ├── services/
│   │   ├── llm_client.py        ← ALL LLM calls go here (litellm)
│   │   ├── reward_engine.py     ← RL reward signals + fine-tune export
│   │   ├── skill_router.py      ← skill injection per module type
│   │   ├── error_recovery.py    ← structured error handlers
│   │   ├── token_optimizer.py   ← PDF/DOCX/HTML → Markdown (60-75% token saving)
│   │   ├── research.py          ← Stage 2: 4-source parallel research
│   │   ├── council.py           ← Stage 3: 5 advisors + chairman
│   │   ├── diagram.py           ← Stage 4: architecture diagrams (Mermaid)
│   │   ├── project_graph.py     ← Stage 4: pre-wired route map
│   │   ├── job_match.py         ← Stage 4: stack vs job posting comparison
│   │   ├── quiz.py              ← Stage 7: optional understanding quiz
│   │   ├── code_gen.py          ← Stage 8: module-by-module generation
│   │   ├── symbol_index.py      ← Stage 8: SQLite AST symbol index
│   │   ├── preview.py           ← Stage 9: Docker warm pool + Playwright
│   │   ├── career.py            ← Stage 10: README, LinkedIn, resume, PDF
│   │   ├── verdict_pdf.py       ← Stage 3: WeasyPrint PDF card
│   │   └── cost_tracker.py      ← tracks API spend per session
│   ├── memory/
│   │   ├── decision_store.py    ← SQLite + pgvector decision memory
│   │   └── schema.sql           ← SQLite table definitions
│   ├── routes/                  ← FastAPI route handlers
│   │   ├── research.py
│   │   ├── council.py
│   │   ├── diagrams.py
│   │   ├── build.py             ← approval endpoint (calls reward_engine)
│   │   ├── preview.py
│   │   ├── memory.py
│   │   ├── career.py
│   │   └── session.py
│   └── database/
│       ├── schema.sql           ← Supabase tables (run in SQL Editor)
│       └── rls_policies.sql     ← Supabase Row Level Security
├── prompts/
│   └── skills/                  ← 19 skill .md files
├── data/
│   └── job_postings/            ← static JSON per role (LinkedIn substitute)
├── docs/
│   └── decisions/               ← ADRs auto-generated here
├── tests/                       ← Playwright tests auto-generated here
└── memory/                      ← SQLite databases (auto-created, .gitignore)
```

---

## Environment Variables Required

See `.env.example` for the full list with explanations.

Minimum to start Stage 0:
- `ANTHROPIC_API_KEY` — test: `python -c "import anthropic; c=anthropic.Anthropic(); r=c.messages.create(model='claude-haiku-4-5',max_tokens=10,messages=[{'role':'user','content':'ping'}]); print('OK')"`
- `SUPABASE_URL` + `SUPABASE_KEY` — test: `python -c "from supabase import create_client; import os; c=create_client(os.getenv('SUPABASE_URL'),os.getenv('SUPABASE_KEY')); print('OK')"`
- `VALKEY_URL=redis://localhost:6379` — test: `docker exec 3netra-valkey valkey-cli ping` → PONG

---

## Stage Gates — Never Skip

Before moving to the next stage, every gate must pass:

| Stage | Gate Command | Expected Output |
|-------|-------------|-----------------|
| 0 | `node -v` | v20.x.x or higher |
| 0 | `python3 --version` | Python 3.12.x |
| 0 | `docker exec 3netra-valkey valkey-cli ping` | PONG |
| 0 | `curl localhost:8000/health` | `{"status":"ok"}` |
| 0 | `curl localhost:8001/health` | MCP server healthy |
| 1 | `python -c "from services.llm_client import call_fast; import asyncio; print(asyncio.run(call_fast('test','ping',10)))"` | Any text response |
| 2 | Research agent returns JSON with 4 sources | No empty sources |
| 3 | Chairman returns valid ChairmanVerdict JSON | Parseable by Pydantic |
| 4 | project_graph.json has all pages with URLs | No missing routes |
| 8 | Each module: E2B health check 200 | Preview shows screenshot |

---

## What NOT to Do

- Never create `anthropic.Anthropic()` outside `llm_client.py`
- Never use `print()` for logging — use `logger = logging.getLogger(__name__)`
- Never hardcode API keys, URLs, or model names — always from env vars
- Never build 2 modules simultaneously — one at a time, user approves each
- Never skip Pydantic validation on agent outputs — always use `parse_safe()`
- Never use `SELECT *` in database queries — specify columns
- Never create new `httpx.AsyncClient()` in a function — use `request.app.state.http_client`
