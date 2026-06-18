"""
backend/routes/diagrams.py

FastAPI route for Architecture Diagrams.
Fetches verdict from MCP → generates diagrams → saves to MCP.

Endpoint: POST /api/diagrams
"""

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class DiagramsRequest(BaseModel):
    project_id: str
    idea: str


@router.post("/diagrams")
async def diagrams(request: Request, body: DiagramsRequest):
    """
    Generate architecture diagrams for a project.

    What happens:
    1. Fetch Chairman verdict from MCP
    2. Generate 5 diagrams using Sonnet
    3. Save all diagrams to MCP
    4. Return diagrams for user approval
    """
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
                content={
                    "success": False,
                    "error": "No verdict found. Run War Room first.",
                }
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
                        "project_id": body.project_id,
                        "diagram_type": diagram["diagram_type"],
                        "mermaid_syntax": diagram["mermaid_syntax"],
                    },
                )

        logger.info(f"All {result['total']} diagrams saved to MCP")

        return JSONResponse({
            "success": True,
            "project_id": body.project_id,
            "result": result,
            "message": result["message"],
        })

    except Exception as e:
        logger.error(f"Diagrams failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Diagram generation failed. Please try again.",
            }
        )