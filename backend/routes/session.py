"""
backend/routes/session.py

Returns last active project for "Continue Last Project" feature.
Uses Supabase instead of old SQLite memory system.

Endpoint: GET /api/session/last
"""

import logging
import os
from datetime import datetime
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

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    request:    Request,
    auth=Depends(require_auth),
):
    """
    Returns all messages for a specific session.
    Used by the read-only session view page at /session/[id].
    """
    try:
        supabase = get_supabase()
        user_id  = request.state.user_id

        # Get session info with project details
        session_result = supabase.table("project_sessions")\
            .select("id, session_number, stage_number, stage_name, title, status, message_count, created_at, project_id")\
            .eq("id", session_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()

        if not session_result.data:
            return JSONResponse(
                status_code=404,
                content={"error": "Session not found"}
            )

        session = session_result.data

        # Get project info
        project_result = supabase.table("user_projects")\
            .select("title, target_role")\
            .eq("id", session["project_id"])\
            .single()\
            .execute()

        project = project_result.data or {}

        # Get all messages for this session
        messages_result = supabase.table("project_chat_history")\
            .select("id, role, content, created_at")\
            .eq("session_id", session_id)\
            .eq("user_id", user_id)\
            .order("created_at", desc=False)\
            .execute()

        messages = messages_result.data or []

        return JSONResponse({
            "success": True,
            "session": {
                **session,
                "project_title": project.get("title", ""),
                "project_role":  project.get("target_role", ""),
            },
            "messages": messages,
        })

    except Exception as e:
        logger.error(f"Get session messages failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
        
        # ── Stage memory endpoints ────────────────────────────────────────────────────

@router.get("/projects/{project_id}/stages/{stage_name}/memory")
async def get_stage_memory_endpoint(
    project_id: str,
    stage_name: str,
    request:    Request,
    auth=Depends(require_auth),
):
    """
    Returns stage memory for a specific stage.
    Called at the start of every new chat session in a stage.
    Agent uses this instead of loading full previous chat history.
    """
    try:
        supabase = get_supabase()
        user_id  = request.state.user_id

        result = supabase.table("stage_memory")\
            .select("*")\
            .eq("project_id", project_id)\
            .eq("stage_name", stage_name)\
            .eq("user_id",    user_id)\
            .single()\
            .execute()

        if result.data:
            return JSONResponse({
                "success": True,
                "memory":  result.data,
                "exists":  True,
            })

        return JSONResponse({
            "success": True,
            "exists":  False,
            "memory": {
                "approved_decisions": [],
                "rejected_ideas":     [],
                "pending_questions":  [],
                "important_context":  "",
                "tech_stack":         [],
                "summary":            "",
            },
        })

    except Exception as e:
        logger.error(f"Get stage memory failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/projects/{project_id}/stages/{stage_name}/memory")
async def save_stage_memory_endpoint(
    project_id: str,
    stage_name: str,
    request:    Request,
    auth=Depends(require_auth),
):
    """
    Saves or updates stage memory after important decisions are made.
    Called automatically by chat agent after every session.
    Stores approved decisions, rejected ideas, pending questions.
    """
    try:
        supabase = get_supabase()
        user_id  = request.state.user_id
        body     = await request.json()

        supabase.table("stage_memory").upsert({
            "project_id":         project_id,
            "stage_name":         stage_name,
            "user_id":            user_id,
            "approved_decisions": body.get("approved_decisions", []),
            "rejected_ideas":     body.get("rejected_ideas",     []),
            "pending_questions":  body.get("pending_questions",  []),
            "important_context":  body.get("important_context",  ""),
            "tech_stack":         body.get("tech_stack",         []),
            "summary":            body.get("summary",            ""),
            "updated_at":         datetime.utcnow().isoformat(),
        }, on_conflict="project_id,stage_name").execute()

        return JSONResponse({"success": True})

    except Exception as e:
        logger.error(f"Save stage memory failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )