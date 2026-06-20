"""
backend/routes/council.py

FastAPI route for the War Room Council.
Fetches research from MCP → runs War Room → saves verdict to MCP.

Endpoint: POST /api/council
"""

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class CouncilRequest(BaseModel):
    project_id: str
    idea: str
    target_role: str = "Software Engineer"
    purpose: str = "portfolio"

@router.post("/council")
async def council(request: Request, body: CouncilRequest):
    """
    Run the War Room Council for a project.

    What happens:
    1. Fetch research report from MCP server
    2. Run 5 advisors in parallel
    3. Run peer review round
    4. Run Chairman synthesis
    5. Save verdict to MCP server
    6. Return full War Room result
    """
    try:
        from fastmcp import Client
        from services.council import run_war_room

        # Step 1: Fetch research report from MCP
        async with Client("http://localhost:8001/mcp") as mcp:
            result = await mcp.call_tool(
                "get_research_report",
                {"project_id": body.project_id},
            )
            # FastMCP returns result as a list of content objects
            # Extract the text value from the first content item
            if hasattr(result, 'content') and result.content:
                report_json = result.content[0].text
            elif isinstance(result, list) and result:
                report_json = result[0].text
            else:
                report_json = str(result)
            research_data = json.loads(report_json)

        # Get the generated report text for advisors
        research_report = research_data.get(
            "generated_report",
            json.dumps(research_data.get("summary", {}))
        )

        if not research_report:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "No research report found. Run research first.",
                }
            )

        logger.info(f"Research report loaded for project: {body.project_id}")

        # Step 2: Run War Room
        war_room_result = await run_war_room(
            idea=body.idea,
            target_role=body.target_role,
            research_report=research_report,
            purpose=body.purpose,
        )

        # Step 3: Save verdict to MCP
        async with Client("http://localhost:8001/mcp") as mcp:
            await mcp.call_tool(
                "save_council_verdict",
                {
                    "project_id": body.project_id,
                    "verdict_json": json.dumps(war_room_result["verdict"]),
                },
            )

            # Save verdict as a decision in memory
            await mcp.call_tool(
                "write_decision",
                {
                    "project_id": body.project_id,
                    "what": f"Chairman verdict: {war_room_result['verdict']['verdict']}",
                    "why": war_room_result["verdict"]["verdict_reasoning"],
                    "node_type": "chairman_verdict",
                },
            )

        logger.info(f"Verdict saved: {war_room_result['verdict']['verdict']}")

        return JSONResponse({
            "success": True,
            "project_id": body.project_id,
            "result": war_room_result,
            "message": f"War Room complete. Verdict: {war_room_result['verdict']['verdict']}",
        })

    except Exception as e:
        logger.error(f"Council failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "War Room failed. Please try again.",
            }
        )