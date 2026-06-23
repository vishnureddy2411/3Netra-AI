"""
backend/routes/projects_db.py

Project storage and retrieval endpoints.
Every project is tied to a user_id from JWT.
Users can only access their own projects.
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from middleware.auth import require_auth

logger = logging.getLogger(__name__)
router = APIRouter()

TOTAL_REQUIRED_STAGES = [
    "project_selected",
    "confirmation_gate",
    "diagram_creation",
    "implementation_plan",
    "readme_generation",
    "resume_generation",
]


def get_supabase():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL", "").replace("/rest/v1", "").rstrip("/")
    key = os.getenv("SUPABASE_KEY", "")
    return create_client(url, key)


def calculate_progress(completed_stages: list) -> int:
    if not completed_stages:
        return 0
    completed = [s for s in completed_stages if s in TOTAL_REQUIRED_STAGES]
    return int((len(completed) / len(TOTAL_REQUIRED_STAGES)) * 100)


def get_overall_status(progress: int) -> str:
    if progress == 0:
        return "pending"
    if progress < 100:
        return "in_progress"
    return "completed"


# ── Request models ────────────────────────────

class CreateProjectRequest(BaseModel):
    title: str
    description: str = ""
    target_role: str = ""
    purpose: str = "portfolio"
    difficulty_level: str = ""
    estimated_duration: str = ""
    tech_stack: list = []
    risks: list = []
    portfolio_value: str = ""
    full_idea: str = ""
    deep_analysis: dict = {}
    verdict: dict = {}
    advisor_outputs: list = []
    internal_project_id: str = ""

    class Config:
        extra = "allow"


class UpdateProjectRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    overall_status: Optional[str] = None
    current_stage: Optional[str] = None
    progress_percentage: Optional[int] = None
    deep_analysis: Optional[dict] = None
    verdict: Optional[dict] = None

    class Config:
        extra = "allow"


class StageUpdateRequest(BaseModel):
    stage_name: str
    stage_status: str = "completed"
    output_data: dict = {}


class ChatMessageRequest(BaseModel):
    role: str
    content_type: str
    content: dict
    project_id: str


# ── Endpoints ─────────────────────────────────

@router.post("/projects")
async def create_project(
    request: Request,
    auth=Depends(require_auth),
):
    """Creates a new project for the authenticated user."""
    try:
        supabase = get_supabase()
        user_id  = request.state.user_id
        body     = await request.json()

        data = {
            "user_id":             user_id,
            "title":               body.get("title", ""),
            "description":         body.get("description", ""),
            "target_role":         body.get("target_role", ""),
            "purpose":             body.get("purpose", "portfolio"),
            "difficulty_level":    body.get("difficulty_level", ""),
            "estimated_duration":  body.get("estimated_duration", ""),
            "tech_stack":          body.get("tech_stack", []),
            "risks":               body.get("risks", []),
            "portfolio_value":     body.get("portfolio_value", ""),
            "full_idea":           body.get("full_idea", ""),
            "deep_analysis":       body.get("deep_analysis", {}),
            "verdict":             body.get("verdict", {}),
            "advisor_outputs":     body.get("advisor_outputs", []),
            "internal_project_id": body.get("internal_project_id", ""),
            "overall_status":      "pending",
            "current_stage":       "project_selected",
            "progress_percentage": 0,
        }

        result = supabase.table("user_projects").insert(data).execute()

        if result.data:
            project = result.data[0]
            supabase.table("project_stages").insert({
                "project_id":   project["id"],
                "stage_name":   "project_selected",
                "stage_status": "completed",
            }).execute()
            logger.info(f"Project created: {project['id']} for user {user_id}")
            return JSONResponse({"success": True, "project": project})

        raise ValueError("Insert returned no data")

    except Exception as e:
        logger.error(f"Create project failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.get("/projects")
async def list_projects(
    request: Request,
    status: Optional[str] = None,
    auth=Depends(require_auth),
):
    """Lists all projects for the authenticated user."""
    try:
        supabase = get_supabase()
        user_id  = request.state.user_id

        query = supabase.table("user_projects")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("updated_at", desc=True)

        if status and status != "all":
            query = query.eq("overall_status", status)

        result = query.execute()

        return JSONResponse({
            "success":  True,
            "projects": result.data or [],
            "total":    len(result.data or []),
        })

    except Exception as e:
        logger.error(f"List projects failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    request: Request,
    auth=Depends(require_auth),
):
    """Gets a single project. Verifies it belongs to the current user."""
    try:
        supabase = get_supabase()
        user_id  = request.state.user_id

        result = supabase.table("user_projects")\
            .select("*")\
            .eq("id", project_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()

        if not result.data:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Project not found"}
            )

        stages = supabase.table("project_stages")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at")\
            .execute()

        project = result.data
        project["stages"] = stages.data or []

        return JSONResponse({"success": True, "project": project})

    except Exception as e:
        logger.error(f"Get project failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/projects/{project_id}/stage")
async def update_stage(
    project_id: str,
    request: Request,
    auth=Depends(require_auth),
):
    """Marks a stage as completed and updates project progress."""
    try:
        body     = await request.json()
        supabase = get_supabase()
        user_id  = request.state.user_id

        stage_name   = body.get("stage_name", "")
        stage_status = body.get("stage_status", "completed")
        output_data  = body.get("output_data", {})

        existing = supabase.table("user_projects")\
            .select("id")\
            .eq("id", project_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()

        if not existing.data:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Project not found"}
            )

        supabase.table("project_stages").insert({
            "project_id":   project_id,
            "stage_name":   stage_name,
            "stage_status": stage_status,
            "output_data":  output_data,
        }).execute()

        all_stages = supabase.table("project_stages")\
            .select("stage_name, stage_status")\
            .eq("project_id", project_id)\
            .execute()

        completed = [
            s["stage_name"] for s in (all_stages.data or [])
            if s["stage_status"] == "completed"
        ]

        progress = calculate_progress(completed)
        status   = get_overall_status(progress)

        supabase.table("user_projects").update({
            "progress_percentage": progress,
            "overall_status":      status,
            "current_stage":       stage_name,
        }).eq("id", project_id).execute()

        logger.info(f"Stage {stage_name} updated — {progress}%")

        return JSONResponse({
            "success":  True,
            "stage":    stage_name,
            "progress": progress,
            "status":   status,
        })

    except Exception as e:
        logger.error(f"Stage update failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    request: Request,
    auth=Depends(require_auth),
):
    """Deletes a project. Only the owner can delete."""
    try:
        supabase = get_supabase()
        user_id  = request.state.user_id

        supabase.table("user_projects")\
            .delete()\
            .eq("id", project_id)\
            .eq("user_id", user_id)\
            .execute()

        return JSONResponse({"success": True, "message": "Project deleted"})

    except Exception as e:
        logger.error(f"Delete project failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/projects/{project_id}/stage")
async def update_stage(
    project_id: str,
    request: Request,
    body: StageUpdateRequest,
    auth=Depends(require_auth),
):
    """Marks a stage as completed and updates project progress."""
    try:
        supabase = get_supabase()
        user_id  = request.state.user_id

        existing = supabase.table("user_projects")\
            .select("id")\
            .eq("id", project_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()

        if not existing.data:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Project not found"}
            )

        supabase.table("project_stages").insert({
            "project_id":   project_id,
            "stage_name":   body.stage_name,
            "stage_status": body.stage_status,
            "output_data":  body.output_data,
        }).execute()

        all_stages = supabase.table("project_stages")\
            .select("stage_name, stage_status")\
            .eq("project_id", project_id)\
            .execute()

        completed = [
            s["stage_name"] for s in (all_stages.data or [])
            if s["stage_status"] == "completed"
        ]

        progress = calculate_progress(completed)
        status   = get_overall_status(progress)

        supabase.table("user_projects").update({
            "progress_percentage": progress,
            "overall_status":      status,
            "current_stage":       body.stage_name,
        }).eq("id", project_id).execute()

        logger.info(f"Stage {body.stage_name} updated — {progress}%")

        return JSONResponse({
            "success":  True,
            "stage":    body.stage_name,
            "progress": progress,
            "status":   status,
        })

    except Exception as e:
        logger.error(f"Stage update failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/projects/{project_id}/history")
async def get_chat_history(
    project_id: str,
    request: Request,
    auth=Depends(require_auth),
):
    """Gets full chat history for a project."""
    try:
        supabase = get_supabase()
        user_id  = request.state.user_id

        result = supabase.table("project_chat_history")\
            .select("*")\
            .eq("project_id", project_id)\
            .eq("user_id", user_id)\
            .order("created_at")\
            .execute()

        return JSONResponse({
            "success": True,
            "history": result.data or [],
        })

    except Exception as e:
        logger.error(f"Get history failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/projects/history")
async def save_chat_message(
    request: Request,
    auth=Depends(require_auth),
):
    """Saves a single chat message to project history."""
    try:
        body     = await request.json()
        supabase = get_supabase()
        user_id  = request.state.user_id

        result = supabase.table("project_chat_history").insert({
            "project_id":   body.get("project_id"),
            "user_id":      user_id,
            "role":         body.get("role"),
            "content_type": body.get("content_type"),
            "content":      body.get("content", {}),
        }).execute()

        return JSONResponse({
            "success": True,
            "message": result.data[0] if result.data else {},
        })

    except Exception as e:
        logger.error(f"Save message failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )
        
@router.post("/projects/{project_id}/sessions")
async def create_session(
    project_id: str,
    request: Request,
    auth=Depends(require_auth),
):
    """Creates a new chat session for a project stage."""
    try:
        body     = await request.json()
        supabase = get_supabase()
        user_id  = request.state.user_id

        stage_number   = body.get("stage_number", 6)
        stage_name     = body.get("stage_name", "planning")

        # Get next session number for this stage
        existing = supabase.table("project_sessions")\
            .select("session_number")\
            .eq("project_id", project_id)\
            .eq("stage_number", stage_number)\
            .order("session_number", desc=True)\
            .limit(1)\
            .execute()

        next_num = 1
        if existing.data:
            next_num = existing.data[0]["session_number"] + 1

        title = body.get("title", f"{stage_name.replace('_', ' ').title()} Session {next_num}")

        # Archive previous active sessions for this stage
        supabase.table("project_sessions")\
            .update({"status": "archived"})\
            .eq("project_id", project_id)\
            .eq("stage_number", stage_number)\
            .eq("status", "active")\
            .execute()

        result = supabase.table("project_sessions").insert({
            "project_id":     project_id,
            "user_id":        user_id,
            "stage_number":   stage_number,
            "stage_name":     stage_name,
            "session_number": next_num,
            "title":          title,
            "status":         "active",
            "message_count":  0,
        }).execute()

        if result.data:
            logger.info(f"Session created: {result.data[0]['id']} stage={stage_number} num={next_num}")
            return JSONResponse({"success": True, "session": result.data[0]})

        raise ValueError("Session insert returned no data")

    except Exception as e:
        logger.error(f"Create session failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/projects/{project_id}/sessions")
async def list_sessions(
    project_id: str,
    request: Request,
    auth=Depends(require_auth),
):
    """Lists all sessions for a project grouped by stage."""
    try:
        supabase = get_supabase()
        user_id  = request.state.user_id

        # Verify ownership
        existing = supabase.table("user_projects")\
            .select("id")\
            .eq("id", project_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()

        if not existing.data:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Project not found"}
            )

        result = supabase.table("project_sessions")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("stage_number")\
            .order("session_number")\
            .execute()

        # Group by stage
        stages: dict = {}
        for session in (result.data or []):
            stage_key = f"stage_{session['stage_number']}"
            if stage_key not in stages:
                stages[stage_key] = {
                    "stage_number": session["stage_number"],
                    "stage_name":   session["stage_name"],
                    "sessions":     [],
                }
            stages[stage_key]["sessions"].append(session)

        return JSONResponse({
            "success": True,
            "stages":  list(stages.values()),
            "total":   len(result.data or []),
        })

    except Exception as e:
        logger.error(f"List sessions failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/projects/{project_id}/sessions/{session_id}/messages")
async def save_session_message(
    project_id: str,
    session_id: str,
    request: Request,
    auth=Depends(require_auth),
):
    """Saves a message to a specific session."""
    try:
        body     = await request.json()
        supabase = get_supabase()
        user_id  = request.state.user_id

        result = supabase.table("project_chat_history").insert({
            "project_id":   project_id,
            "session_id":   session_id,
            "user_id":      user_id,
            "role":         body.get("role"),
            "content_type": body.get("content_type"),
            "content":      body.get("content", {}),
        }).execute()

        # Increment message count
        supabase.rpc("increment_session_messages", {
            "session_id_param": session_id
        }).execute()

        return JSONResponse({
            "success": True,
            "message": result.data[0] if result.data else {},
        })

    except Exception as e:
        logger.error(f"Save session message failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/projects/{project_id}/sessions/{session_id}/messages")
async def get_session_messages(
    project_id: str,
    session_id: str,
    request: Request,
    auth=Depends(require_auth),
):
    """Gets all messages for a specific session."""
    try:
        supabase = get_supabase()
        user_id  = request.state.user_id

        result = supabase.table("project_chat_history")\
            .select("*")\
            .eq("project_id", project_id)\
            .eq("session_id", session_id)\
            .eq("user_id", user_id)\
            .order("created_at")\
            .execute()

        return JSONResponse({
            "success":  True,
            "messages": result.data or [],
            "total":    len(result.data or []),
        })

    except Exception as e:
        logger.error(f"Get session messages failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )
        
        
@router.get("/projects/{project_id}/artifacts")
async def get_project_artifacts(
    project_id: str,
    request: Request,
    auth=Depends(require_auth),
):
    """Gets all artifacts for a project — graph, diagrams, career output."""
    try:
        supabase = get_supabase()
        user_id  = request.state.user_id

        result = supabase.table("project_artifacts")\
            .select("*")\
            .eq("project_id", project_id)\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()

        artifacts = {}
        for artifact in (result.data or []):
            artifacts[artifact["artifact_type"]] = artifact

        return JSONResponse({
            "success":   True,
            "artifacts": artifacts,
        })

    except Exception as e:
        logger.error(f"Get artifacts failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )