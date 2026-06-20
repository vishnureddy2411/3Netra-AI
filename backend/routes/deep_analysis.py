"""
backend/routes/deep_analysis.py

Endpoint for comprehensive portfolio deep analysis.
Endpoint: POST /api/deep-analysis
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class DeepAnalysisRequest(BaseModel):
    original_idea: str
    role: str = "Software Engineer"
    purpose: str = "portfolio"
    verdict: dict = {}
    advisor_outputs: list = []
    research_summary: str = ""


@router.post("/deep-analysis")
async def deep_analysis(request: Request, body: DeepAnalysisRequest):
    try:
        from services.deep_analysis import run_deep_analysis

        result = await run_deep_analysis(
            original_idea=body.original_idea,
            role=body.role,
            purpose=body.purpose,
            verdict=body.verdict,
            advisor_outputs=body.advisor_outputs,
            research_summary=body.research_summary,
        )

        return JSONResponse({"success": True, "result": result})

    except Exception as e:
        logger.error(f"Deep analysis route failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )