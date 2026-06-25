"""
backend/routes/workflow.py

Workflow API — Stage management endpoints

Connects Loop Engineer (workflow_engine.py) to the frontend.
Both student and professional flows use these endpoints
after their respective councils approve the plan.

Endpoints:
  POST /api/workflow/start   — Initialize workflow, execute Stage 1 (Planning)
  POST /api/workflow/stage   — Execute a specific stage
  POST /api/workflow/approve — User approves stage, advance to next
  POST /api/workflow/reject  — User requests changes, regenerate stage
  GET  /api/workflow/status/{project_id} — Get current workflow state
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from middleware.auth import require_auth
from services.workflow_engine import (
    execute_stage,
    get_next_stage,
    get_stage_display,
    get_stage_roles,
    get_approval_prompt,
    is_final_stage,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request models ────────────────────────────────────────────────────────────

class WorkflowStartRequest(BaseModel):
    project_id: str
    idea: str
    role: str
    purpose: str
    approved_verdict: Optional[dict] = None


class WorkflowStageRequest(BaseModel):
    project_id: str
    stage: str
    idea: str
    role: str
    purpose: str
    approved_decisions: Optional[dict] = {}


class WorkflowApproveRequest(BaseModel):
    project_id: str
    current_stage: str
    stage_output: Optional[dict] = {}
    feedback: Optional[str] = ""


class WorkflowRejectRequest(BaseModel):
    project_id: str
    current_stage: str
    idea: str
    role: str
    purpose: str
    feedback: str
    approved_decisions: Optional[dict] = {}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/workflow/start")
async def start_workflow(request: Request, body: WorkflowStartRequest):
    """
    Initialize a new workflow for a project.
    Executes Stage 1 — Planning Agent activates.
    Called after student or professional council approves.
    """
    user = await require_auth(request)

    try:
        logger.info(f"Workflow starting — project: {body.project_id} | idea: {body.idea[:60]}")

        project_context = {
            "idea":               body.idea,
            "role":               body.role,
            "purpose":            body.purpose,
            "approved_decisions": {},
        }

        # If verdict from council is provided, add it to context
        if body.approved_verdict:
            project_context["approved_decisions"]["council_verdict"] = body.approved_verdict

        # Execute Stage 1 — Planning
        stage_output = await execute_stage("planning", project_context)

        # Save to Supabase
        await _save_stage_to_db(
            project_id=body.project_id,
            stage="planning",
            output=stage_output,
            status="in_progress",
        )

        next_stage = get_next_stage("planning")

        logger.info(f"Workflow Stage 1 (planning) complete for project: {body.project_id}")

        return JSONResponse({
            "success":         True,
            "project_id":      body.project_id,
            "current_stage":   "planning",
            "stage_display":   "Planning",
            "active_roles":    get_stage_roles("planning"),
            "active_agent":    stage_output.get("_agent", "planning_agent"),
            "output":          stage_output,
            "next_stage":      next_stage,
            "next_stage_display": get_stage_display(next_stage) if next_stage else None,
            "approval_required": True,
            "approval_prompt": get_approval_prompt("planning"),
            "is_final":        False,
        })

    except Exception as e:
        logger.error(f"Workflow start failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "message": "Workflow failed to start."},
        )


@router.post("/workflow/stage")
async def execute_workflow_stage(request: Request, body: WorkflowStageRequest):
    """
    Execute a specific workflow stage.
    Called when user approves the previous stage and we need to generate the next one.
    """
    user = await require_auth(request)

    try:
        logger.info(f"Executing stage: {body.stage} | project: {body.project_id}")

        project_context = {
            "idea":               body.idea,
            "role":               body.role,
            "purpose":            body.purpose,
            "approved_decisions": body.approved_decisions or {},
        }

        stage_output = await execute_stage(body.stage, project_context)

        # Save to Supabase
        await _save_stage_to_db(
            project_id=body.project_id,
            stage=body.stage,
            output=stage_output,
            status="in_progress",
        )

        next_stage = get_next_stage(body.stage)
        final      = is_final_stage(body.stage)

        return JSONResponse({
            "success":            True,
            "project_id":         body.project_id,
            "current_stage":      body.stage,
            "stage_display":      get_stage_display(body.stage),
            "active_roles":       get_stage_roles(body.stage),
            "active_agent":       stage_output.get("_agent", ""),
            "supporting_agents":  stage_output.get("_supporting_agents", []),
            "output":             stage_output,
            "next_stage":         next_stage,
            "next_stage_display": get_stage_display(next_stage) if next_stage else None,
            "approval_required":  not final,
            "approval_prompt":    get_approval_prompt(body.stage),
            "is_final":           final,
        })

    except Exception as e:
        logger.error(f"Stage execution failed for {body.stage}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "message": f"Stage {body.stage} failed."},
        )


@router.post("/workflow/approve")
async def approve_stage(request: Request, body: WorkflowApproveRequest):
    """
    User approves the current stage output.
    Marks stage as approved in DB.
    Returns info about next stage — frontend calls /workflow/stage to generate it.
    """
    user = await require_auth(request)

    try:
        logger.info(f"Stage approved: {body.current_stage} | project: {body.project_id}")

        # Mark current stage as approved
        await _update_stage_status(
            project_id=body.project_id,
            stage=body.current_stage,
            status="approved",
        )

        next_stage = get_next_stage(body.current_stage)
        final      = is_final_stage(body.current_stage)

        if final:
            return JSONResponse({
                "success":         True,
                "project_id":      body.project_id,
                "approved_stage":  body.current_stage,
                "next_stage":      None,
                "project_complete":True,
                "message":         "All stages complete. Your project is ready.",
            })

        return JSONResponse({
            "success":             True,
            "project_id":          body.project_id,
            "approved_stage":      body.current_stage,
            "next_stage":          next_stage,
            "next_stage_display":  get_stage_display(next_stage) if next_stage else None,
            "active_roles":        get_stage_roles(next_stage) if next_stage else [],
            "project_complete":    False,
            "message":             f"Stage approved. Beginning {get_stage_display(next_stage)}.",
        })

    except Exception as e:
        logger.error(f"Approve stage failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.post("/workflow/reject")
async def reject_stage(request: Request, body: WorkflowRejectRequest):
    """
    User requests changes to the current stage.
    Regenerates the stage output using feedback as additional context.
    """
    user = await require_auth(request)

    try:
        logger.info(
            f"Stage rejected: {body.current_stage} | "
            f"project: {body.project_id} | "
            f"feedback: {body.feedback[:60]}"
        )

        # Mark as needs revision
        await _update_stage_status(
            project_id=body.project_id,
            stage=body.current_stage,
            status="needs_revision",
        )

        # Regenerate with feedback injected into context
        project_context = {
            "idea":               body.idea,
            "role":               body.role,
            "purpose":            body.purpose,
            "approved_decisions": body.approved_decisions or {},
            "revision_feedback":  body.feedback,
        }

        stage_output = await execute_stage(
            body.current_stage,
            project_context,
        )

        await _save_stage_to_db(
            project_id=body.project_id,
            stage=body.current_stage,
            output=stage_output,
            status="in_progress",
        )

        next_stage = get_next_stage(body.current_stage)

        return JSONResponse({
            "success":            True,
            "project_id":         body.project_id,
            "current_stage":      body.current_stage,
            "stage_display":      get_stage_display(body.current_stage),
            "active_roles":       get_stage_roles(body.current_stage),
            "active_agent":       stage_output.get("_agent", ""),
            "output":             stage_output,
            "next_stage":         next_stage,
            "approval_required":  True,
            "approval_prompt":    get_approval_prompt(body.current_stage),
            "message":            f"Stage regenerated with your feedback.",
        })

    except Exception as e:
        logger.error(f"Reject stage failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.get("/workflow/status/{project_id}")
async def get_workflow_status(project_id: str, request: Request):
    """
    Get current workflow state for a project.
    Returns all stages with their status.
    """
    user = await require_auth(request)

    try:
        stages = await _get_project_stages(project_id)

        approved_stages  = []
        current_stage    = None
        pending_stages   = []

        stage_order = [
            "planning", "architecture", "database_design",
            "frontend_build", "backend_build", "integration",
            "testing", "deployment", "final_review",
        ]

        stages_by_name = {s.get("stage_name"): s for s in stages}

        for stage_name in stage_order:
            stage_data = stages_by_name.get(stage_name)
            if not stage_data:
                pending_stages.append(stage_name)
            elif stage_data.get("status") == "approved":
                approved_stages.append(stage_name)
            elif stage_data.get("status") in ("in_progress", "needs_revision"):
                current_stage = stage_data
            else:
                pending_stages.append(stage_name)

        total      = len(stage_order)
        approved_n = len(approved_stages)

        return JSONResponse({
            "success":          True,
            "project_id":       project_id,
            "current_stage":    current_stage,
            "approved_stages":  approved_stages,
            "pending_stages":   pending_stages,
            "total_stages":     total,
            "completed_stages": approved_n,
            "progress_pct":     round((approved_n / total) * 100),
            "is_complete":      approved_n == total,
        })

    except Exception as e:
        logger.error(f"Get workflow status failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


# ── Supabase helpers ──────────────────────────────────────────────────────────

async def _save_stage_to_db(
    project_id: str,
    stage:      str,
    output:     dict,
    status:     str = "in_progress",
):
    try:
        from services.supabase_client import get_supabase
        supabase = get_supabase()
        await supabase.table("project_stages").upsert({
            "project_id":    project_id,
            "stage_name":    stage,
            "stage_display": get_stage_display(stage),
            "output":        json.dumps(output),
            "status":        status,
            "active_roles":  json.dumps(get_stage_roles(stage)),
        }).execute()
        logger.info(f"Stage {stage} saved to DB — project: {project_id}")
    except Exception as e:
        logger.warning(f"Could not save stage to DB: {e}")


async def _update_stage_status(project_id: str, stage: str, status: str):
    try:
        from services.supabase_client import get_supabase
        supabase = get_supabase()
        await supabase.table("project_stages").update({"status": status}).eq(
            "project_id", project_id
        ).eq("stage_name", stage).execute()
    except Exception as e:
        logger.warning(f"Could not update stage status: {e}")


async def _get_project_stages(project_id: str) -> list:
    try:
        from services.supabase_client import get_supabase
        supabase = get_supabase()
        result = await supabase.table("project_stages").select("*").eq(
            "project_id", project_id
        ).execute()
        return result.data or []
    except Exception as e:
        logger.warning(f"Could not get project stages: {e}")
        return []