"""
backend/routes/research.py

FastAPI route for the Research Agent.
Receives user idea → runs research → saves to MCP → returns report.

ELI5: This is the waiter who takes your order (idea),
gives it to the kitchen (research agent),
and brings the food back to your table (chat UI).

Endpoint: POST /api/research
"""

import json
import logging
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request model ─────────────────────────────────────────────
class ResearchRequest(BaseModel):
    idea: str
    project_id: str = ""  # optional — generated if not provided
    target_role: str = "Software Engineer"


# ── Route ─────────────────────────────────────────────────────
@router.post("/research")
async def research(request: Request, body: ResearchRequest):
    """
    Run research on a project idea.

    What happens step by step:
    1. Generate project_id if not provided
    2. Call research agent (4 APIs in parallel)
    3. Save report to MCP server
    4. Save project plan to MCP server
    5. Return full research report

    Request body:
        idea: the user's project idea
        project_id: optional existing project ID
        target_role: job role to target (default: Software Engineer)

    Response:
        Full research report with GitHub, HN, arXiv, SO results
    """
    try:
        # Step 1: Generate project ID if not provided
        project_id = body.project_id or str(uuid.uuid4())
        logger.info(f"Research request: project={project_id}, idea='{body.idea[:50]}'")

        # Step 2: Run research agent (all 4 sources in parallel)
        from services.research import run_research
        report = await run_research(
            idea=body.idea,
            http_client=request.app.state.http_client,
        )

        # Step 3: Save research report to MCP server
        from fastmcp import Client
        async with Client("http://localhost:8001/mcp") as mcp:
            # Save research report
            await mcp.call_tool(
                "save_research_report",
                {
                    "project_id": project_id,
                    "report_json": json.dumps(report),
                },
            )

            # Save project plan
            await mcp.call_tool(
                "save_project_plan",
                {
                    "project_id": project_id,
                    "idea": body.idea,
                    "target_role": body.target_role,
                    "tech_stack": "",
                },
            )

        logger.info(f"Research saved to MCP: project={project_id}")

        # Step 4: Return full report to chat UI
        return JSONResponse({
            "success": True,
            "project_id": project_id,
            "report": report,
            "message": "Research complete. Ready for War Room.",
        })

    except Exception as e:
        logger.error(f"Research failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Research failed. Please try again.",
            },
        )