"""
backend/memory/decision_store.py

Persistent decision memory for 3Netra-AI.
Replaces Graphiti + Neo4j for portfolio/early-production scale.

Storage:
  - SQLite for decision nodes (fast reads, zero infrastructure)
  - pgvector on Supabase for semantic recall (cosine similarity)
  - Valkey for query + decision embedding cache (zero re-embedding cost)

Embedding model: all-MiniLM-L6-v2 (384 dimensions)
  - Free, runs on CPU, 80MB, 14,000 tokens/second
  - Pinned explicitly — changing this breaks vector dimension compatibility
  - Install: pip install sentence-transformers
"""

import hashlib
import json
import logging
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

logger = logging.getLogger(__name__)

# ── Embedding model — PINNED ──────────────────────────────────────────────────
# DO NOT change this without dropping and recreating the vectors column.
# Changing models produces incompatible dimension vectors that silently corrupt recall.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION  = 384  # must match pgvector column: vector(384)

_embedding_model = None  # lazy-loaded on first use


def _get_model():
    """Lazy-load embedding model — only downloads on first call."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("loading_embedding_model", extra={"model": EMBEDDING_MODEL_NAME})
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info("embedding_model_loaded")
    return _embedding_model


def _embed(text: str) -> list[float]:
    """Embed a string. Returns 384-dimensional float list."""
    model = _get_model()
    return model.encode(text, normalize_embeddings=True).tolist()


# ── Valkey embedding cache ────────────────────────────────────────────────────
# Cache key: sha256(text) → avoids re-embedding same text in same session
# TTL: 1 hour for queries (reused within session), 30 days for decisions (immutable)

_valkey = None

async def _get_valkey():
    global _valkey
    if _valkey is None:
        import aioredis
        _valkey = await aioredis.from_url(
            os.getenv("VALKEY_URL", "redis://localhost:6379"),
            encoding="utf-8",
            decode_responses=True,
        )
    return _valkey


async def _embed_cached(text: str, ttl_seconds: int = 3600) -> list[float]:
    """Embed with Valkey cache. Returns cached embedding if exists."""
    cache_key = f"embedding:{hashlib.sha256(text.encode()).hexdigest()}"

    try:
        r = await _get_valkey()
        cached = await r.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning("embedding_cache_miss", extra={"error": str(e)})

    # Cache miss — embed and store
    embedding = _embed(text)

    try:
        r = await _get_valkey()
        await r.set(cache_key, json.dumps(embedding), ex=ttl_seconds)
    except Exception as e:
        logger.warning("embedding_cache_write_failed", extra={"error": str(e)})

    return embedding


# ── SQLite setup ──────────────────────────────────────────────────────────────
DB_PATH = Path("memory/3netra_decisions.db")

NodeType = Literal[
    "chairman_verdict",
    "adr",
    "quiz_gap",
    "correction",
    "v2_feature",
    "architecture_decision",
]

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS decisions (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL,
    session_id  TEXT NOT NULL,
    what        TEXT NOT NULL,
    why         TEXT NOT NULL,
    node_type   TEXT NOT NULL,
    gap_concept TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_decisions_project ON decisions(project_id);
CREATE INDEX IF NOT EXISTS idx_decisions_type    ON decisions(node_type);

CREATE TABLE IF NOT EXISTS build_status (
    project_id  TEXT NOT NULL,
    module_name TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    fix_request TEXT,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (project_id, module_name)
);
"""


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


async def init_db() -> None:
    """Call once at startup to create tables."""
    with _get_conn() as conn:
        conn.executescript(SCHEMA_SQL)
    logger.info("sqlite_initialized", extra={"path": str(DB_PATH)})


async def ping_db() -> bool:
    """Health check for DB connectivity."""
    with _get_conn() as conn:
        conn.execute("SELECT 1")
    return True


# ── Write ─────────────────────────────────────────────────────────────────────

async def write_decision(
    what: str,
    why: str,
    project_id: str,
    session_id: str,
    node_type: NodeType,
    gap_concept: Optional[str] = None,
) -> str:
    """
    Write a decision node to SQLite and embed to Supabase pgvector.
    Non-blocking: runs embedding + Supabase write in background.
    Returns decision ID immediately.
    """
    import uuid
    decision_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    # SQLite write (fast, synchronous)
    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO decisions (id, project_id, session_id, what, why, node_type, gap_concept, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (decision_id, project_id, session_id, what, why, node_type, gap_concept, created_at),
        )

    logger.info("decision_written", extra={
        "id": decision_id,
        "project_id": project_id,
        "node_type": node_type,
    })

    # Embed + Supabase write in background (non-blocking — user doesn't wait)
    import asyncio
    asyncio.create_task(_embed_and_store(decision_id, what + " " + why, project_id))

    return decision_id


async def _embed_and_store(decision_id: str, text: str, project_id: str) -> None:
    """Background task: embed decision text and store in Supabase pgvector."""
    try:
        embedding = await _embed_cached(text, ttl_seconds=60 * 60 * 24 * 30)  # 30-day cache

        # Write to Supabase via REST (supabase-py client)
        from supabase import create_client
        supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        supabase.table("decision_embeddings").insert({
            "decision_id": decision_id,
            "project_id": project_id,
            "embedding": embedding,
        }).execute()

    except Exception as e:
        logger.error("background_embed_failed", extra={"decision_id": decision_id, "error": str(e)})


# ── Recall ────────────────────────────────────────────────────────────────────

async def recall(
    query: str,
    project_id: str,
    limit: int = 3,
) -> list[dict]:
    """
    Semantic recall of relevant past decisions.
    Uses: query embedding (Valkey-cached) → pgvector cosine similarity → top-k results.
    Falls back to SQLite keyword search if pgvector unavailable.

    Returns list of decision dicts ordered by relevance.
    """
    start = time.monotonic()

    # Embed query (Valkey-cached — same session queries hit cache)
    query_embedding = await _embed_cached(query, ttl_seconds=3600)

    try:
        # pgvector cosine similarity search via Supabase RPC
        from supabase import create_client
        supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

        result = supabase.rpc("recall_decisions", {
            "query_embedding": query_embedding,
            "project_id_filter": project_id,
            "match_count": limit,
            "match_threshold": 0.5,
        }).execute()

        decisions = result.data or []

    except Exception as e:
        logger.warning("pgvector_recall_failed", extra={"error": str(e)})
        # Fallback: keyword search in SQLite
        decisions = _sqlite_keyword_search(query, project_id, limit)

    elapsed_ms = round((time.monotonic() - start) * 1000)
    logger.info("recall_complete", extra={
        "query": query[:50],
        "results": len(decisions),
        "ms": elapsed_ms,
    })

    return decisions


def _sqlite_keyword_search(query: str, project_id: str, limit: int) -> list[dict]:
    """Keyword fallback when pgvector is unavailable."""
    words = query.lower().split()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM decisions WHERE project_id = ? ORDER BY created_at DESC LIMIT 20",
            (project_id,)
        ).fetchall()

    # Simple keyword scoring
    scored = []
    for row in rows:
        text = (row["what"] + " " + row["why"]).lower()
        score = sum(1 for w in words if w in text)
        if score > 0:
            scored.append((score, dict(row)))

    scored.sort(reverse=True)
    return [item[1] for item in scored[:limit]]


# ── Session resumption ────────────────────────────────────────────────────────

async def get_session_resume_state(project_id: str) -> Optional[dict]:
    """
    Check if user has an in-progress session to resume.
    Returns resume state dict if project is in progress, None if complete or not found.

    Called on chat page load — if returns non-None, show "Resume your project?" card.
    """
    with _get_conn() as conn:
        # Check build status for any pending or in-progress modules
        rows = conn.execute(
            "SELECT * FROM build_status WHERE project_id = ? AND status != 'approved'",
            (project_id,)
        ).fetchall()

        if not rows:
            return None

        # Get last 5 decisions for context
        recent_decisions = conn.execute(
            "SELECT what, why, node_type, created_at FROM decisions "
            "WHERE project_id = ? ORDER BY created_at DESC LIMIT 5",
            (project_id,)
        ).fetchall()

    pending_modules = [dict(r) for r in rows if r["status"] == "pending"]
    in_progress = [dict(r) for r in rows if r["status"] == "in_progress"]
    current_module = in_progress[0] if in_progress else (pending_modules[0] if pending_modules else None)

    return {
        "can_resume": True,
        "current_module": current_module,
        "pending_count": len(pending_modules),
        "recent_context": [dict(r) for r in recent_decisions],
        "resume_message": (
            f"Welcome back! You were building **{current_module['module_name']}** "
            f"with {len(pending_modules)} more modules after it. Want to continue?"
            if current_module else "Your project has pending modules. Want to continue?"
        ),
    }
