"""
backend/routes/project_graph.py

FastAPI route for Project Graph generation.
Fetches verdict + diagrams from MCP → generates graph → saves to MCP.

Endpoint: POST /api/project-graph
"""

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class ProjectGraphRequest(BaseModel):
    project_id: str
    idea: str


@router.post("/project-graph")
async def project_graph(request: Request, body: ProjectGraphRequest):
    """
    Generate the project graph for a project.

    What happens:
    1. Fetch Chairman verdict from MCP
    2. Fetch all diagrams from MCP
    3. Generate project graph
    4. Save graph to MCP
    5. Return graph summary
    """
    try:
        from fastmcp import Client
        from services.project_graph import run_project_graph

        async with Client("http://localhost:8001/mcp") as mcp:

            # Fetch verdict
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

            # Fetch diagrams
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

        if not verdict:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "No verdict found. Run War Room first.",
                }
            )

        logger.info(f"Loaded verdict and {len(diagrams)} diagrams for: {body.project_id}")

        # Generate project graph
        result = await run_project_graph(
            project_id=body.project_id,
            idea=body.idea,
            verdict=verdict,
            diagrams=diagrams,
        )

        # Save graph to MCP
        async with Client("http://localhost:8001/mcp") as mcp:
            await mcp.call_tool(
                "save_project_graph",
                {
                    "project_id": body.project_id,
                    "graph_json": json.dumps(result["graph"]),
                },
            )

            # Save as decision
            await mcp.call_tool(
                "write_decision",
                {
                    "project_id": body.project_id,
                    "what": f"Project graph: {result['summary']['total_pages']} pages, {result['summary']['total_api_routes']} API routes",
                    "why": "Pre-wired all navigation and API contracts before code generation",
                    "node_type": "architecture_decision",
                },
            )

        logger.info(f"Project graph saved for: {body.project_id}")

        return JSONResponse({
            "success": True,
            "project_id": body.project_id,
            "result": result,
            "message": result["message"],
        })

    except Exception as e:
        logger.error(f"Project graph failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Project graph generation failed. Please try again.",
            }
        )