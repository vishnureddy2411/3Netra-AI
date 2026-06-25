"""
backend/main.py

FastAPI application entry point.
All routes registered here.
Auth middleware applied to protected routes.
"""

import logging
import os
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
import sys
sys.path.insert(0, os.path.dirname(__file__))
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse as _JSONResponse

# Load environment variables
load_dotenv("../.env.local")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Import routes ─────────────────────────────

from routes import (
    research,
    council,
    pro_council,
    workflow,
    diagrams,
    project_graph,
    ideas,
    session,
    reframe,
    deep_analysis,
    discuss,
    auth_routes,
    projects_db,
    quiz
)

# ── Lifespan ──────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.http_client = httpx.AsyncClient(
        limits=httpx.Limits(
            max_connections=20,
            max_keepalive_connections=10,
            keepalive_expiry=30,
        ),
        timeout=httpx.Timeout(60.0),
    )
    logger.info("HTTP client initialized")
    yield
    # Shutdown
    await app.state.http_client.aclose()
    logger.info("HTTP client closed")


# ── App ───────────────────────────────────────

app = FastAPI(
    title="3Netra-AI Backend",
    version="2.0.0",
    lifespan=lifespan,
)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(f"Validation error on {request.url}: {exc.errors()}")
    return _JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )
# ── CORS ──────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────

# AI pipeline routes (no auth required for now)
app.include_router(research.router,      prefix="/api")
app.include_router(council.router,       prefix="/api")
app.include_router(diagrams.router,      prefix="/api")
app.include_router(project_graph.router, prefix="/api")
app.include_router(ideas.router,         prefix="/api")
app.include_router(session.router,       prefix="/api")
app.include_router(reframe.router,       prefix="/api")
app.include_router(deep_analysis.router, prefix="/api")
app.include_router(discuss.router,       prefix="/api")
app.include_router(pro_council.router,   prefix="/api")
app.include_router(workflow.router,      prefix="/api")
app.include_router(quiz.router,          prefix="/api")
# Auth + user project routes (JWT required)
app.include_router(auth_routes.router,   prefix="/api")
app.include_router(projects_db.router,   prefix="/api")

# ── Health check ──────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/")
async def root():
    return {"message": "3Netra-AI Backend v2.0.0"}