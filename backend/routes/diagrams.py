"""
backend/routes/diagrams.py

FastAPI route for Architecture Diagrams.
Fetches verdict from MCP → generates diagrams → saves to MCP + Supabase artifacts.

Endpoint: POST /api/diagrams
"""

import json
import logging
import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from middleware.auth import require_auth

logger = logging.getLogger(__name__)
router = APIRouter()


class DiagramsRequest(BaseModel):
    project_id: str
    db_project_id: str | None = None
    idea: str


def get_supabase():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL", "").replace("/rest/v1", "").rstrip("/")
    key = os.getenv("SUPABASE_KEY", "")
    return create_client(url, key)


@router.post("/diagrams")
async def diagrams(request: Request, body: DiagramsRequest, auth=Depends(require_auth)):
    try:
        from fastmcp import Client
        from services.diagrams import run_diagrams

        # Step 1: Fetch verdict from MCP
        async with Client("http://localhost:8001/mcp") as mcp:
            result = await mcp.call_tool(
                "get_council_verdict",
                {"project_id": body.project_id},
            )
            if hasattr(result, 'content') and result.content:
                verdict_json = result.content[0].text
            elif isinstance(result, list) and result:
                verdict_json = result[0].text
            else:
                verdict_json = str(result)

            verdict = json.loads(verdict_json)

        if not verdict:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "No verdict found. Run War Room first."}
            )

        logger.info(f"Verdict loaded for project: {body.project_id}")

        # Step 2: Generate diagrams
        result = await run_diagrams(
            project_id=body.project_id,
            idea=body.idea,
            verdict=verdict,
        )

        # Step 3: Save diagrams to MCP
        async with Client("http://localhost:8001/mcp") as mcp:
            for diagram in result["diagrams"]:
                await mcp.call_tool(
                    "save_diagram",
                    {
                        "project_id":    body.project_id,
                        "diagram_type":  diagram["diagram_type"],
                        "mermaid_syntax": diagram["mermaid_syntax"],
                    },
                )

        logger.info(f"All {result['total']} diagrams saved to MCP")

        # Step 4: Save to project_artifacts for permanent storage
        save_id = body.db_project_id or body.project_id
        try:
            user_id = request.state.user_id if hasattr(request.state, 'user_id') else None
            if user_id and save_id:
                supabase = get_supabase()

                existing = supabase.table("project_artifacts")\
                    .select("id")\
                    .eq("project_id", save_id)\
                    .eq("artifact_type", "diagrams")\
                    .execute()

                artifact_data = {
                    "project_id":    save_id,
                    "user_id":       user_id,
                    "artifact_type": "diagrams",
                    "title":         "Architecture Diagrams",
                    "content":       result["diagrams"],
                    "metadata": {
                        "total": result["total"],
                        "idea":  body.idea,
                    },
                }

                if existing.data:
                    supabase.table("project_artifacts")\
                        .update(artifact_data)\
                        .eq("id", existing.data[0]["id"])\
                        .execute()
                    logger.info(f"Diagrams artifact updated for: {save_id}")
                else:
                    supabase.table("project_artifacts")\
                        .insert(artifact_data)\
                        .execute()
                    logger.info(f"Diagrams artifact saved for: {save_id}")

        except Exception as db_err:
            logger.warning(f"Could not save diagrams to Supabase: {db_err}")

        return JSONResponse({
            "success":    True,
            "project_id": body.project_id,
            "result":     result,
            "message":    result["message"],
        })

    except Exception as e:
        logger.error(f"Diagrams failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error":   str(e),
                "message": "Diagram generation failed. Please try again.",
            }
        )