"""
backend/routes/session.py

Returns last active project for "Continue Last Project" feature.
Uses Supabase instead of old SQLite memory system.

Endpoint: GET /api/session/last
"""

import logging
import os

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from middleware.auth import require_auth

logger = logging.getLogger(__name__)
router = APIRouter()


def get_supabase():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL", "").replace("/rest/v1", "").rstrip("/")
    key = os.getenv("SUPABASE_KEY", "")
    return create_client(url, key)


@router.get("/session/last")
async def get_last_session(
    request: Request,
    auth=Depends(require_auth),
):
    """
    Returns the last active project for the authenticated user.
    Used by GateStep1 to enable "Continue Last Project" button.
    """
    try:
        supabase = get_supabase()
        user_id  = request.state.user_id

        # Get most recent project
        result = supabase.table("user_projects")\
            .select("id, title, full_idea, overall_status, current_stage, progress_percentage, updated_at")\
            .eq("user_id", user_id)\
            .neq("overall_status", "archived")\
            .order("updated_at", desc=True)\
            .limit(1)\
            .execute()

        if not result.data:
            return JSONResponse({
                "found":   False,
                "message": "No previous projects found",
            })

        project = result.data[0]

        # Get last active session for this project
        session_result = supabase.table("project_sessions")\
            .select("id, stage_name, session_number, message_count, status")\
            .eq("project_id", project["id"])\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()

        last_session = session_result.data[0] if session_result.data else None

        idea = project.get("full_idea", project.get("title", ""))

        return JSONResponse({
            "found":            True,
            "project_id":       project["id"],
            "idea":             idea,
            "title":            project.get("title", ""),
            "status":           project.get("overall_status", "pending"),
            "current_stage":    project.get("current_stage", "project_selected"),
            "progress":         project.get("progress_percentage", 0),
            "last_session":     last_session,
            "resume_message":   f"{idea[:60]}{'...' if len(idea) > 60 else ''}",
        })

    except Exception as e:
        logger.error(f"Session resume failed: {e}")
        return JSONResponse({
            "found":   False,
            "message": str(e),
        })