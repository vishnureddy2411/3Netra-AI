"""
backend/routes/session.py
Returns last active project for Continue Last Project feature.
Endpoint: GET /api/session/last
"""
import logging, sqlite3
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()
DB_PATH = Path("../memory/3netra_decisions.db")

@router.get("/session/last")
async def get_last_session():
    try:
        if not DB_PATH.exists():
            return JSONResponse({"found": False, "message": "No previous projects found"})

        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row

        project = conn.execute(
            "SELECT * FROM projects ORDER BY created_at DESC LIMIT 1"
        ).fetchone()

        if not project:
            conn.close()
            return JSONResponse({"found": False, "message": "No previous projects found"})

        project_id = project["id"]
        idea = project["idea"]
        status = project["status"]

        pending = conn.execute(
            """SELECT * FROM build_status
               WHERE project_id = ? AND status != 'approved'
               ORDER BY build_order LIMIT 1""",
            (project_id,)
        ).fetchone()

        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM decisions WHERE project_id = ?",
            (project_id,)
        ).fetchone()

        conn.close()

        return JSONResponse({
            "found": True,
            "project_id": project_id,
            "idea": idea,
            "status": status,
            "current_module": dict(pending) if pending else None,
            "decisions_made": count["cnt"] if count else 0,
            "resume_message": f"{idea[:60]}{'...' if len(idea) > 60 else ''}",
        })

    except Exception as e:
        logger.error(f"Session resume failed: {e}")
        return JSONResponse({"found": False, "message": str(e)})