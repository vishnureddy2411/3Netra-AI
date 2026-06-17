# CI/CD and Deployment Standards

You are building a deployment module or configuration. Every rule below is required for Railway + Vercel + Docker deployment to work correctly.

---

## Dockerfile — Required Patterns

```dockerfile
# Multi-stage build — smaller final image
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime
WORKDIR /app

# Never run as root in production
RUN adduser --disabled-password --gecos "" appuser
USER appuser

COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY . .

# Port from environment — never hardcoded
EXPOSE ${PORT:-8000}

# Health check built into Dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

---

## .dockerignore — Always Include

```
.env
.env.local
.env.*.local
__pycache__/
*.pyc
*.pyo
.git/
.gitignore
node_modules/
.next/
*.md
tests/
.codegraph/
graphify-out/
```

---

## Environment Variables — Rules

NEVER hardcode any value that differs between environments:

```python
# WRONG
DATABASE_URL = "postgresql://localhost:5432/mydb"

# CORRECT
import os
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")
```

Port MUST come from environment (Railway sets PORT automatically):
```python
PORT = int(os.getenv("PORT", 8000))
```

---

## railway.toml — Required at Repo Root

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "./Dockerfile"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

---

## vercel.json — Required at Frontend Root

```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "env": {
    "NEXT_PUBLIC_API_URL": "@api_url"
  },
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {"key": "X-Content-Type-Options", "value": "nosniff"},
        {"key": "X-Frame-Options", "value": "DENY"},
        {"key": "Referrer-Policy", "value": "strict-origin-when-cross-origin"}
      ]
    }
  ]
}
```

---

## Health Check Endpoint — Required

Every service must expose GET /health returning HTTP 200:

```python
@app.get("/health")
async def health():
    checks = {
        "database": await check_db(),
        "valkey": await check_valkey(),
        "mcp_server": await check_mcp()
    }
    all_healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if all_healthy else 503,
        content={"status": "ok" if all_healthy else "degraded", "checks": checks}
    )
```

---

## Startup Validation — Fail Fast

At startup, validate all required environment variables exist. Crash immediately with a clear message if any are missing — don't crash 3 minutes later when the first request tries to use them:

```python
REQUIRED_ENV_VARS = [
    "ANTHROPIC_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "VALKEY_URL",
    "MCP_SERVER_URL"
]

@app.on_event("startup")
async def validate_env():
    missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {missing}")
```
