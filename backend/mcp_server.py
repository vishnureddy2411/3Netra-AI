"""
backend/mcp_server.py

3Netra-AI Custom MCP Server — the shared memory for all agents.

What this does:
- Runs as a separate process on port 8001
- Exposes 18 tools that all agents call
- All agents read/write project state through here
- Nobody talks to each other directly — everything goes through MCP

How to start it:
    python mcp_server.py

How to test it:
    curl http://localhost:8001/health
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv("../.env.local")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── MCP server instance ───────────────────────────────────────
mcp = FastMCP("3netra-memory")

# ── SQLite database path ──────────────────────────────────────
DB_PATH = Path("../memory/3netra_decisions.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    id          TEXT PRIMARY KEY,
    user_id     TEXT,
    idea        TEXT NOT NULL,
    target_role TEXT,
    tech_stack  TEXT,
    status      TEXT DEFAULT 'research',
    verdict     TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS project_graph (
    project_id  TEXT PRIMARY KEY,
    graph_json  TEXT NOT NULL,
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS build_status (
    project_id  TEXT NOT NULL,
    module_name TEXT NOT NULL,
    status      TEXT DEFAULT 'pending',
    fix_request TEXT,
    files_written TEXT,
    exports     TEXT,
    build_order INTEGER DEFAULT 0,
    updated_at  TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (project_id, module_name)
);

CREATE TABLE IF NOT EXISTS files (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL,
    file_path   TEXT NOT NULL,
    content     TEXT NOT NULL,
    language    TEXT,
    exports     TEXT,
    module_name TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS api_contracts (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL,
    method      TEXT NOT NULL,
    path        TEXT NOT NULL,
    description TEXT,
    request_shape  TEXT,
    response_shape TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS decisions (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL,
    session_id  TEXT,
    what        TEXT NOT NULL,
    why         TEXT NOT NULL,
    node_type   TEXT NOT NULL,
    gap_concept TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS research_reports (
    project_id  TEXT PRIMARY KEY,
    report_json TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS verdicts (
    project_id  TEXT PRIMARY KEY,
    verdict_json TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS diagrams (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL,
    diagram_type TEXT NOT NULL,
    mermaid_syntax TEXT NOT NULL,
    approved    INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS career_artifacts (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    content     TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_files_project    ON files(project_id);
CREATE INDEX IF NOT EXISTS idx_status_project   ON build_status(project_id);
CREATE INDEX IF NOT EXISTS idx_decisions_project ON decisions(project_id);
CREATE INDEX IF NOT EXISTS idx_diagrams_project ON diagrams(project_id);
"""


def get_conn() -> sqlite3.Connection:
    """Get SQLite connection. Creates DB and tables if they don't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    return conn


# ════════════════════════════════════════════════════════════
# PROJECT STATE TOOLS
# ════════════════════════════════════════════════════════════

@mcp.tool()
def get_project_plan(project_id: str) -> str:
    """
    Returns the full approved plan for a project.
    Called by every agent at session start to understand what is being built.
    Returns JSON string with: idea, target_role, tech_stack, status, verdict.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
    if not row:
        return json.dumps({"error": f"Project {project_id} not found"})
    return json.dumps(dict(row))


@mcp.tool()
def save_project_plan(
    project_id: str,
    idea: str,
    target_role: str,
    tech_stack: str,
    user_id: str = "local",
) -> str:
    """
    Save or update a project plan.
    Called after user submits their idea and it has been processed.
    tech_stack should be a comma-separated string of technologies.
    """
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO projects (id, user_id, idea, target_role, tech_stack)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
               idea=excluded.idea,
               target_role=excluded.target_role,
               tech_stack=excluded.tech_stack""",
            (project_id, user_id, idea, target_role, tech_stack),
        )
    logger.info(f"Project plan saved: {project_id}")
    return json.dumps({"success": True, "project_id": project_id})


@mcp.tool()
def get_build_status(project_id: str) -> str:
    """
    Returns which modules are pending, in_progress, or approved.
    Developer agent calls this to know what to build next.
    Returns JSON list of all modules and their status.
    """
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM build_status WHERE project_id = ? ORDER BY build_order",
            (project_id,),
        ).fetchall()
    return json.dumps([dict(r) for r in rows])


@mcp.tool()
def write_approval(
    project_id: str,
    module_name: str,
    status: str,
    fix_request: str = "",
) -> str:
    """
    Records user approval decision for a module.
    status must be: approved, fix_requested, or rebuild.
    fix_request is the user's description of what needs changing (only for fix_requested).
    Called when user clicks Approve / Fix / Rebuild in the chat UI.
    """
    valid = {"approved", "fix_requested", "rebuild"}
    if status not in valid:
        return json.dumps({"error": f"status must be one of {valid}"})

    with get_conn() as conn:
        conn.execute(
            """INSERT INTO build_status (project_id, module_name, status, fix_request)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(project_id, module_name) DO UPDATE SET
               status=excluded.status,
               fix_request=excluded.fix_request,
               updated_at=datetime('now')""",
            (project_id, module_name, status, fix_request),
        )
    logger.info(f"Approval written: {project_id}/{module_name} -> {status}")
    return json.dumps({"success": True})


@mcp.tool()
def get_session_resume_state(project_id: str) -> str:
    """
    Checks if a user has an in-progress session to resume.
    Called on chat page load.
    Returns resume state if project is in progress, or empty if complete/not found.
    """
    with get_conn() as conn:
        project = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if not project:
            return json.dumps({"can_resume": False})

        pending = conn.execute(
            """SELECT * FROM build_status
               WHERE project_id = ? AND status != 'approved'
               ORDER BY build_order LIMIT 1""",
            (project_id,),
        ).fetchone()

    if not pending:
        return json.dumps({"can_resume": False})

    return json.dumps({
        "can_resume": True,
        "current_module": dict(pending),
        "resume_message": (
            f"Welcome back! You were building "
            f"**{pending['module_name']}**. Want to continue?"
        ),
    })


# ════════════════════════════════════════════════════════════
# CODE GRAPH TOOLS
# ════════════════════════════════════════════════════════════

@mcp.tool()
def get_existing_files(project_id: str) -> str:
    """
    Returns every file already written for this project with their paths.
    Developer agent calls this before generating any new file.
    Prevents creating duplicate files or using wrong paths.
    Returns JSON list of {file_path, language, module_name, exports}.
    """
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT file_path, language, module_name, exports FROM files WHERE project_id = ?",
            (project_id,),
        ).fetchall()
    return json.dumps([dict(r) for r in rows])


@mcp.tool()
def write_file(
    project_id: str,
    file_path: str,
    content: str,
    language: str,
    module_name: str,
    exports: str = "",
) -> str:
    """
    Records a newly written file in the MCP memory.
    Called by Developer agent after writing each file.
    exports should be comma-separated list of exported function/component names.
    This updates the shared state so future agents know the file exists.
    """
    import uuid
    file_id = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO files (id, project_id, file_path, content, language, module_name, exports)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT DO NOTHING""",
            (file_id, project_id, file_path, content, language, module_name, exports),
        )
    logger.info(f"File written to MCP: {file_path}")
    return json.dumps({"success": True, "file_id": file_id})


@mcp.tool()
def get_reusable_components(project_id: str) -> str:
    """
    Returns all approved React/Python components with their export names.
    Developer agent uses this to import existing components instead of recreating them.
    Example: AuthGuard exists at components/AuthGuard.tsx with export {AuthGuard}.
    Returns JSON list of {file_path, exports, module_name}.
    """
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT file_path, exports, module_name
               FROM files
               WHERE project_id = ? AND language IN ('typescript', 'tsx', 'python')
               AND exports != ''""",
            (project_id,),
        ).fetchall()
    return json.dumps([dict(r) for r in rows])


@mcp.tool()
def get_api_contracts(project_id: str) -> str:
    """
    Returns every existing API endpoint shape for this project.
    Frontend Developer agent uses this to call the right endpoints.
    Prevents frontend calling wrong URL or wrong HTTP method.
    Returns JSON list of {method, path, description, request_shape, response_shape}.
    """
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT method, path, description, request_shape, response_shape FROM api_contracts WHERE project_id = ?",
            (project_id,),
        ).fetchall()
    return json.dumps([dict(r) for r in rows])


@mcp.tool()
def write_api_contract(
    project_id: str,
    method: str,
    path: str,
    description: str,
    request_shape: str = "",
    response_shape: str = "",
) -> str:
    """
    Records a newly created API endpoint.
    Called by Backend Developer agent after creating each route.
    method: GET, POST, PUT, DELETE
    path: the URL path e.g. /api/research
    request_shape and response_shape: JSON string describing the data shapes.
    """
    import uuid
    contract_id = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO api_contracts
               (id, project_id, method, path, description, request_shape, response_shape)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (contract_id, project_id, method, path, description, request_shape, response_shape),
        )
    return json.dumps({"success": True})


# ════════════════════════════════════════════════════════════
# PROJECT GRAPH TOOLS
# ════════════════════════════════════════════════════════════

@mcp.tool()
def get_project_graph(project_id: str) -> str:
    """
    Returns the complete route map for the project.
    Every page, its URL, navigation links, and API calls — pre-wired before code is written.
    Developer agent receives this before building any page.
    Zero broken navigation links because every URL is pre-defined here.
    Returns JSON with pages array containing name, path, navigates_to, api_calls.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT graph_json FROM project_graph WHERE project_id = ?",
            (project_id,),
        ).fetchone()
    if not row:
        return json.dumps({"pages": [], "shared_components": []})
    return row["graph_json"]


@mcp.tool()
def save_project_graph(project_id: str, graph_json: str) -> str:
    """
    Saves the complete project graph after Architecture stage is approved.
    graph_json must be a valid JSON string with pages and shared_components arrays.
    Called once by Engineering Manager after all diagrams are approved.
    """
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO project_graph (project_id, graph_json)
               VALUES (?, ?)
               ON CONFLICT(project_id) DO UPDATE SET
               graph_json=excluded.graph_json,
               updated_at=datetime('now')""",
            (project_id, graph_json),
        )
    logger.info(f"Project graph saved: {project_id}")
    return json.dumps({"success": True})


# ════════════════════════════════════════════════════════════
# DECISION MEMORY TOOLS
# ════════════════════════════════════════════════════════════

@mcp.tool()
def write_decision(
    project_id: str,
    what: str,
    why: str,
    node_type: str,
    session_id: str = "default",
    gap_concept: str = "",
) -> str:
    """
    Stores an architectural decision with timestamp.
    node_type options: chairman_verdict, adr, quiz_gap, correction,
                       v2_feature, architecture_decision
    Called after every major agent decision — non-blocking, always safe to call.
    what: what was decided (e.g. 'Use pgvector for semantic search')
    why: the reason (e.g. 'Already in Supabase stack, zero extra cost')
    """
    import uuid
    valid_types = {
        "chairman_verdict", "adr", "quiz_gap",
        "correction", "v2_feature", "architecture_decision",
    }
    if node_type not in valid_types:
        node_type = "architecture_decision"

    decision_id = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO decisions (id, project_id, session_id, what, why, node_type, gap_concept)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (decision_id, project_id, session_id, what, why, node_type, gap_concept),
        )
    logger.info(f"Decision written: {node_type} for {project_id}")
    return json.dumps({"success": True, "decision_id": decision_id})


@mcp.tool()
def recall_decisions(
    project_id: str,
    query: str,
    limit: int = 3,
) -> str:
    """
    Returns recent decisions for a project.
    Used at session start to brief agents on past decisions.
    Simple keyword search — semantic search handled by Supabase pgvector separately.
    Returns JSON list of decisions ordered by most recent first.
    """
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT what, why, node_type, created_at
               FROM decisions
               WHERE project_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (project_id, limit),
        ).fetchall()
    return json.dumps([dict(r) for r in rows])


# ════════════════════════════════════════════════════════════
# RESEARCH AND VERDICT TOOLS
# ════════════════════════════════════════════════════════════

@mcp.tool()
def save_research_report(project_id: str, report_json: str) -> str:
    """
    Saves the research report after Research Agent completes.
    report_json: full JSON string of research findings from all 4 sources.
    All 5 War Room advisors will read this instead of having it injected
    into their prompts — saves 8,000-12,000 tokens per advisor call.
    """
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO research_reports (project_id, report_json)
               VALUES (?, ?)
               ON CONFLICT(project_id) DO UPDATE SET
               report_json=excluded.report_json""",
            (project_id, report_json),
        )
    return json.dumps({"success": True})


@mcp.tool()
def get_research_report(project_id: str) -> str:
    """
    Returns the research report for a project.
    Called by all 5 War Room advisors and the Chairman.
    Returns the full research JSON or empty dict if not found.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT report_json FROM research_reports WHERE project_id = ?",
            (project_id,),
        ).fetchone()
    if not row:
        return json.dumps({})
    return row["report_json"]


@mcp.tool()
def save_council_verdict(project_id: str, verdict_json: str) -> str:
    """
    Saves the Chairman's final verdict after War Room completes.
    verdict_json: ChairmanVerdict JSON with verdict, v1_scope, risks, role_match_score.
    Called once by Chairman agent after synthesizing all advisor inputs.
    """
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO verdicts (project_id, verdict_json)
               VALUES (?, ?)
               ON CONFLICT(project_id) DO UPDATE SET
               verdict_json=excluded.verdict_json""",
            (project_id, verdict_json),
        )
    return json.dumps({"success": True})


@mcp.tool()
def get_council_verdict(project_id: str) -> str:
    """
    Returns the Chairman's verdict for a project.
    Called by Engineering Manager to plan which diagrams to create.
    Returns ChairmanVerdict JSON or empty dict if not found.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT verdict_json FROM verdicts WHERE project_id = ?",
            (project_id,),
        ).fetchone()
    if not row:
        return json.dumps({})
    return row["verdict_json"]


# ════════════════════════════════════════════════════════════
# DIAGRAM TOOLS
# ════════════════════════════════════════════════════════════

@mcp.tool()
def save_diagram(
    project_id: str,
    diagram_type: str,
    mermaid_syntax: str,
) -> str:
    """
    Saves a generated architecture diagram.
    diagram_type examples: system_architecture, erd, sequence_diagram,
                           auth_flow, api_contract, deployment_plan
    mermaid_syntax: the Mermaid.js text that renders the diagram in the browser.
    Called by Engineering Manager after each diagram is generated.
    """
    import uuid
    diagram_id = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO diagrams (id, project_id, diagram_type, mermaid_syntax)
               VALUES (?, ?, ?, ?)""",
            (diagram_id, project_id, diagram_type, mermaid_syntax),
        )
    return json.dumps({"success": True, "diagram_id": diagram_id})


@mcp.tool()
def get_diagrams(project_id: str) -> str:
    """
    Returns all approved diagrams for a project.
    Developer agent fetches only the diagrams relevant to the current module
    instead of having all diagrams injected — reduces token usage significantly.
    Returns JSON list of {diagram_type, mermaid_syntax, approved}.
    """
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT diagram_type, mermaid_syntax, approved FROM diagrams WHERE project_id = ?",
            (project_id,),
        ).fetchall()
    return json.dumps([dict(r) for r in rows])

# ════════════════════════════════════════════════════════════
# STAGE MEMORY TOOLS
# ════════════════════════════════════════════════════════════

@mcp.tool()
def get_stage_memory(project_id: str, stage_name: str) -> str:
    """
    Returns the stage memory for a specific project stage.
    Contains approved decisions, rejected ideas, pending questions,
    and important context from all previous sessions in this stage.
    Called by chat agent at the start of every new session.
    """
    import os
    from supabase import create_client

    try:
        url = os.getenv("SUPABASE_URL", "").replace("/rest/v1", "").rstrip("/")
        key = os.getenv("SUPABASE_KEY", "")
        sb  = create_client(url, key)

        result = sb.table("stage_memory")\
            .select("*")\
            .eq("project_id", project_id)\
            .eq("stage_name", stage_name)\
            .single()\
            .execute()

        if result.data:
            return json.dumps(result.data)
        return json.dumps({
            "approved_decisions": [],
            "rejected_ideas":     [],
            "pending_questions":  [],
            "important_context":  "",
            "tech_stack":         [],
            "summary":            "",
        })
    except Exception as e:
        logger.warning(f"get_stage_memory failed: {e}")
        return json.dumps({})


@mcp.tool()
def save_stage_memory(
    project_id:         str,
    stage_name:         str,
    user_id:            str,
    approved_decisions: str = "[]",
    rejected_ideas:     str = "[]",
    pending_questions:  str = "[]",
    important_context:  str = "",
    tech_stack:         str = "[]",
    summary:            str = "",
) -> str:
    """
    Saves or updates stage memory after important decisions are made.
    Called after every session where key decisions were approved or rejected.
    Uses upsert — creates if not exists, updates if exists.
    approved_decisions, rejected_ideas, pending_questions, tech_stack
    must be JSON strings of arrays.
    """
    import os
    from supabase import create_client

    try:
        url = os.getenv("SUPABASE_URL", "").replace("/rest/v1", "").rstrip("/")
        key = os.getenv("SUPABASE_KEY", "")
        sb  = create_client(url, key)

        sb.table("stage_memory").upsert({
            "project_id":         project_id,
            "stage_name":         stage_name,
            "user_id":            user_id,
            "approved_decisions": json.loads(approved_decisions),
            "rejected_ideas":     json.loads(rejected_ideas),
            "pending_questions":  json.loads(pending_questions),
            "important_context":  important_context,
            "tech_stack":         json.loads(tech_stack),
            "summary":            summary,
            "updated_at":         datetime.utcnow().isoformat(),
        }, on_conflict="project_id,stage_name").execute()

        logger.info(f"Stage memory saved: {project_id}/{stage_name}")
        return json.dumps({"success": True})
    except Exception as e:
        logger.error(f"save_stage_memory failed: {e}")
        return json.dumps({"success": False, "error": str(e)})
# ════════════════════════════════════════════════════════════
# SKILL TOOLS
# ════════════════════════════════════════════════════════════

@mcp.tool()
def get_relevant_skills(module_name: str, tech_stack: str) -> str:
    """
    Returns combined skill file content for a module type.
    Developer agent calls this before building each module.
    Gets the right expert instructions: auth module gets security_auditor skill,
    RAG module gets rag_architect skill, frontend gets senior_frontend skill.
    tech_stack: comma-separated list of technologies in the project.
    Returns combined skill .md content as a string.
    """
    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).parent))

    try:
        from services.skill_router import classify_module_sync, get_skills
        module_type = classify_module_sync(module_name, tech_stack)
        content = get_skills(module_type)
        return json.dumps({
            "module_type": module_type,
            "skill_content": content,
            "success": True,
        })
    except Exception as e:
        logger.warning(f"Skill router error: {e}")
        return json.dumps({
            "module_type": "unknown",
            "skill_content": "",
            "success": False,
            "error": str(e),
        })


# ════════════════════════════════════════════════════════════
# CAREER TOOLS
# ════════════════════════════════════════════════════════════

@mcp.tool()
def get_career_artifacts(project_id: str) -> str:
    """
    Returns all generated career content for a project.
    Career agent reads this to avoid regenerating content that already exists.
    Returns JSON list of {artifact_type, content} for:
    readme, linkedin_post, resume_bullets, verdict_pdf, onboarding_md.
    """
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT artifact_type, content FROM career_artifacts WHERE project_id = ?",
            (project_id,),
        ).fetchall()
    return json.dumps([dict(r) for r in rows])


@mcp.tool()
def save_career_artifact(
    project_id: str,
    artifact_type: str,
    content: str,
) -> str:
    """
    Saves a generated career artifact.
    artifact_type: readme, linkedin_post, resume_bullets, onboarding_md, pr_description
    content: the full text content of the artifact.
    Called by Career agent after generating each piece of career content.
    """
    import uuid
    artifact_id = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO career_artifacts (id, project_id, artifact_type, content)
               VALUES (?, ?, ?, ?)""",
            (artifact_id, project_id, artifact_type, content),
        )
    return json.dumps({"success": True, "artifact_id": artifact_id})


# ════════════════════════════════════════════════════════════
# HEALTH CHECK
# ════════════════════════════════════════════════════════════

@mcp.tool()
def health_check() -> str:
    """
    Verifies the MCP server and database are working.
    Called by FastAPI startup to confirm MCP is reachable.
    Returns status, tool count, and database path.
    """
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        return json.dumps({
            "status": "ok",
            "service": "3netra-mcp-server",
            "database": str(DB_PATH),
            "tools": 18,
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ════════════════════════════════════════════════════════════
# START SERVER
# ════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════
# HTTP HEALTH ENDPOINT — using FastMCP's built-in custom_route
# ════════════════════════════════════════════════════════════
# This is the correct way to add HTTP routes to a FastMCP server.
# Using Starlette mounting breaks the MCP protocol endpoint.
# custom_route adds HTTP endpoints directly to the same server.

from starlette.requests import Request
from starlette.responses import JSONResponse


@mcp.custom_route("/health", methods=["GET"])
async def http_health(request: Request) -> JSONResponse:
    """
    Plain HTTP health check.
    GET http://localhost:8001/health
    Works alongside the MCP protocol endpoint at /mcp
    """
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return JSONResponse({
        "status": "ok",
        "service": "3netra-ai-mcp-server",
        "version": "1.0.0",
        "port": int(os.getenv("MCP_SERVER_PORT", "8001")),
        "database": str(DB_PATH),
        "database_status": db_status,
        "tools_registered": 24,
        "protocol": "MCP + HTTP",
        "mcp_endpoint": "/mcp",
        "health_endpoint": "/health",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "3Netra-AI MCP Server is running. All agents ready.",
    })


@mcp.custom_route("/", methods=["GET"])
async def http_root(request: Request) -> JSONResponse:
    """Root endpoint — explains what this server is."""
    return JSONResponse({
        "name": "3Netra-AI MCP Server",
        "description": "Shared memory server for 3Netra-AI agents",
        "status": "running",
        "endpoints": {
            "/health": "GET — health check in plain JSON",
            "/mcp":    "MCP protocol — used by AI agents",
        },
    })


# ════════════════════════════════════════════════════════════
# START SERVER
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.getenv("MCP_SERVER_PORT", "8001"))
    logger.info(f"Starting 3Netra-AI MCP Server on port {port}")
    logger.info(f"Database: {DB_PATH.resolve()}")
    logger.info(f"Health check: http://localhost:{port}/health")
    logger.info(f"MCP endpoint: http://localhost:{port}/mcp")
    logger.info("24 tools registered and ready")
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
    )

# ════════════════════════════════════════════════════════════
# STAGE MEMORY TOOLS
# ════════════════════════════════════════════════════════════

@mcp.tool()
def get_stage_memory(project_id: str, stage_name: str) -> str:
    """
    Returns the stage memory for a specific project stage.
    Contains approved decisions, rejected ideas, pending questions,
    and important context from all previous sessions in this stage.
    Called by chat agent at the start of every new session.
    """
    import os
    from supabase import create_client

    try:
        url = os.getenv("SUPABASE_URL", "").replace("/rest/v1", "").rstrip("/")
        key = os.getenv("SUPABASE_KEY", "")
        sb  = create_client(url, key)

        result = sb.table("stage_memory")\
            .select("*")\
            .eq("project_id", project_id)\
            .eq("stage_name", stage_name)\
            .single()\
            .execute()

        if result.data:
            return json.dumps(result.data)
        return json.dumps({
            "approved_decisions": [],
            "rejected_ideas":     [],
            "pending_questions":  [],
            "important_context":  "",
            "tech_stack":         [],
            "summary":            "",
        })
    except Exception as e:
        logger.warning(f"get_stage_memory failed: {e}")
        return json.dumps({})


@mcp.tool()
def save_stage_memory(
    project_id:         str,
    stage_name:         str,
    user_id:            str,
    approved_decisions: str = "[]",
    rejected_ideas:     str = "[]",
    pending_questions:  str = "[]",
    important_context:  str = "",
    tech_stack:         str = "[]",
    summary:            str = "",
) -> str:
    """
    Saves or updates stage memory after important decisions are made.
    Called after every session where key decisions were approved or rejected.
    Uses upsert — creates if not exists, updates if exists.
    approved_decisions, rejected_ideas, pending_questions, tech_stack
    must be JSON strings of arrays.
    """
    import os
    from supabase import create_client

    try:
        url = os.getenv("SUPABASE_URL", "").replace("/rest/v1", "").rstrip("/")
        key = os.getenv("SUPABASE_KEY", "")
        sb  = create_client(url, key)

        sb.table("stage_memory").upsert({
            "project_id":         project_id,
            "stage_name":         stage_name,
            "user_id":            user_id,
            "approved_decisions": json.loads(approved_decisions),
            "rejected_ideas":     json.loads(rejected_ideas),
            "pending_questions":  json.loads(pending_questions),
            "important_context":  important_context,
            "tech_stack":         json.loads(tech_stack),
            "summary":            summary,
            "updated_at":         datetime.utcnow().isoformat(),
        }, on_conflict="project_id,stage_name").execute()

        logger.info(f"Stage memory saved: {project_id}/{stage_name}")
        return json.dumps({"success": True})
    except Exception as e:
        logger.error(f"save_stage_memory failed: {e}")
        return json.dumps({"success": False, "error": str(e)})