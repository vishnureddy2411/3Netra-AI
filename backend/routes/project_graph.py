"""
backend/routes/project_graph.py

Project Graph route — saves full graph to project_artifacts table.
The graph is the source of truth for ALL future agents.
"""

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from middleware.auth import require_auth
from fastapi import Depends

logger = logging.getLogger(__name__)
router = APIRouter()


class ProjectGraphRequest(BaseModel):
    project_id: str
    db_project_id: str | None = None
    idea: str


def get_supabase():
    import os
    from supabase import create_client
    url = os.getenv("SUPABASE_URL", "").replace("/rest/v1", "").rstrip("/")
    key = os.getenv("SUPABASE_KEY", "")
    return create_client(url, key)


@router.post("/project-graph")
async def project_graph(request: Request, body: ProjectGraphRequest, auth=Depends(require_auth)):
    try:
        from fastmcp import Client
        from services.project_graph import generate_project_graph

        async with Client("http://localhost:8001/mcp") as mcp:
            verdict_result = await mcp.call_tool(
                "get_council_verdict",
                {"project_id": body.project_id},
            )
            if hasattr(verdict_result, 'content') and verdict_result.content:
                verdict_json = verdict_result.content[0].text
            elif isinstance(verdict_result, list) and verdict_result:
                verdict_json = verdict_result[0].text
            else:
                verdict_json = str(verdict_result)
            verdict = json.loads(verdict_json)

            diagrams_result = await mcp.call_tool(
                "get_diagrams",
                {"project_id": body.project_id},
            )
            if hasattr(diagrams_result, 'content') and diagrams_result.content:
                diagrams_json = diagrams_result.content[0].text
            elif isinstance(diagrams_result, list) and diagrams_result:
                diagrams_json = diagrams_result[0].text
            else:
                diagrams_json = str(diagrams_result)
            diagrams = json.loads(diagrams_json)

        logger.info(f"Loaded verdict and {len(diagrams)} diagrams for: {body.project_id}")

        result = await generate_project_graph(
            project_id=body.project_id,
            idea=body.idea,
            verdict=verdict,
            diagrams=diagrams,
        )

        # Save full graph to MCP
        async with Client("http://localhost:8001/mcp") as mcp:
            await mcp.call_tool(
                "save_project_graph",
                {
                    "project_id": body.project_id,
                    "graph_json": json.dumps(result["graph"]),
                },
            )
            await mcp.call_tool(
                "write_decision",
                {
                    "project_id": body.project_id,
                    "what": (
                        f"Project graph: {result['summary']['total_pages']} pages, "
                        f"{result['summary']['total_api_routes']} API routes, "
                        f"{result['summary']['total_data_models']} data models"
                    ),
                    "why": "Pre-wired all navigation and API contracts before code generation",
                    "node_type": "architecture_decision",
                },
            )

        # Save full graph to project_artifacts in Supabase
        try:
            import os
            user_id = request.state.user_id if hasattr(request.state, 'user_id') else None
            if user_id:
                supabase = get_supabase()
                existing = supabase.table("project_artifacts")\
                    .select("id")\
                    .eq("project_id", body.project_id)\
                    .eq("artifact_type", "project_graph")\
                    .execute()
                save_id = body.db_project_id or body.project_id
                artifact_data = {
                    "project_id":    save_id,
                    "user_id":       user_id,
                    "artifact_type": "project_graph",
                    "title":         "Project Architecture Graph",
                    "content":       result["graph"],
                    "metadata": {
                        "summary":  result["summary"],
                        "fallback": result.get("fallback", False),
                        "elapsed":  result["elapsed_seconds"],
                    },
                }

                if existing.data:
                    supabase.table("project_artifacts")\
                        .update(artifact_data)\
                        .eq("id", existing.data[0]["id"])\
                        .execute()
                    logger.info(f"Project graph artifact updated for: {body.project_id}")
                else:
                    supabase.table("project_artifacts")\
                        .insert(artifact_data)\
                        .execute()
                    logger.info(f"Project graph artifact saved for: {body.project_id}")
        except Exception as db_err:
            logger.warning(f"Could not save graph to Supabase artifacts: {db_err}")

        logger.info(f"Project graph complete for: {body.project_id}")

        return JSONResponse({
            "success":    True,
            "project_id": body.project_id,
            "result":     result,
            "message":    result["message"],
        })

    except Exception as e:
        logger.error(f"Project graph failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error":   str(e),
                "message": "Project graph generation failed. Please try again.",
            }
        )