"""
backend/main.py

FastAPI application entry point for 3Netra-AI.
All performance and reliability fixes applied at startup:
  - Shared httpx.AsyncClient (connection pooling)
  - Skill files pre-loaded into memory
  - GZip compression middleware
  - CORS configured for Next.js frontend
  - Required env vars validated on startup (fail fast)
  - Health check with dependency status
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from dotenv import load_dotenv
load_dotenv("../.env.local")
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Required environment variables ────────────────────────────────────────────
# App crashes at startup if any are missing — never crashes mid-request.
REQUIRED_ENV_VARS = [
    "ANTHROPIC_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "VALKEY_URL",
    "MCP_SERVER_URL",
]


def _validate_env() -> None:
    missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {missing}\n"
            f"Check your .env.local file against .env.example"
        )
    logger.info("env_vars_validated", extra={"count": len(REQUIRED_ENV_VARS)})


# ── Lifespan (startup + shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: validate env, pre-load skills, create shared HTTP client.
    Shutdown: cleanly close the HTTP client.
    """
    # 1. Validate all required env vars — fail fast if any missing
    _validate_env()

    # 2. Pre-load all skill .md files into memory
    # Zero disk I/O after this point — all skill reads hit in-memory dict
    from services import skill_router
    skill_router.load_all_skills()

    # 3. Create shared httpx client — connection pooling for all research API calls
    # max_connections=100: supports 25 concurrent users × 4 research APIs each
    # timeout=30s: research APIs must respond within 30s
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=10.0),
        limits=httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20,
            keepalive_expiry=30,
        ),
        headers={"User-Agent": "3Netra-AI/1.0 (portfolio project; contact via GitHub)"},
    )
    logger.info("http_client_created", extra={"max_connections": 100})

    # 4. Warm up SQLite connection
    from memory.decision_store import init_db
    await init_db()
    logger.info("database_initialized")

    logger.info("3netra_ai_startup_complete", extra={"timestamp": datetime.utcnow().isoformat()})

    yield  # App runs here

    # Shutdown: close HTTP client cleanly
    await app.state.http_client.aclose()
    logger.info("http_client_closed")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="3Netra-AI Backend",
    description="Multi-agent AI project builder — See clearly before you build.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────

# GZip: compresses responses > 1KB by 60-70%
# Critical for research reports, diagram Mermaid syntax, project graph JSON
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS: allow Next.js frontend (localhost:3000 in dev, Vercel URL in prod)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    os.getenv("FRONTEND_URL", "https://3netra-ai.vercel.app"),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request timing middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def log_request_timing(request: Request, call_next):
    """Log response time for every request. Flags anything > 1000ms."""
    start = time.monotonic()
    response = await call_next(request)
    elapsed_ms = round((time.monotonic() - start) * 1000)

    log_fn = logger.warning if elapsed_ms > 1000 else logger.info
    log_fn(
        "request_complete",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": elapsed_ms,
        },
    )
    response.headers["X-Response-Time"] = f"{elapsed_ms}ms"
    return response


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health(request: Request):
    """
    Comprehensive health check. Called by Railway, Docker, and monitoring.
    Returns 200 if all dependencies healthy, 503 if any degraded.
    """
    from memory.decision_store import ping_db
    from services.skill_router import SKILL_CACHE

    checks = {}

    # Valkey check
    try:
        import aioredis
        r = await aioredis.from_url(os.getenv("VALKEY_URL", "redis://localhost:6379"))
        await r.ping()
        await r.close()
        checks["valkey"] = "ok"
    except Exception as e:
        checks["valkey"] = f"error: {str(e)[:50]}"

    # SQLite / DB check
    try:
        await ping_db()
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:50]}"

    # MCP server check
    try:
        async with request.app.state.http_client.get(
            f"{os.getenv('MCP_SERVER_URL')}/health", timeout=5.0
        ) as resp:
            checks["mcp_server"] = "ok" if resp.status_code == 200 else f"status_{resp.status_code}"
    except Exception as e:
        checks["mcp_server"] = f"error: {str(e)[:50]}"

    # Skills check
    checks["skills_loaded"] = len(SKILL_CACHE)

    all_healthy = all(v == "ok" for k, v in checks.items() if k != "skills_loaded")
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if all_healthy else "degraded",
            "service": "3netra-ai-backend",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks,
        },
    )


# ── Routes ────────────────────────────────────────────────────────────────────
# Import and register all route modules here
# Import only routes that exist so far
# Add more here as each stage is completed
from routes import research, council

app.include_router(research.router, prefix="/api")
app.include_router(council.router,  prefix="/api")

# ── Dev entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        log_level="info",
    )
