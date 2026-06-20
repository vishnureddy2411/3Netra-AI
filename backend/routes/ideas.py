"""
backend/routes/ideas.py

Generates 3 tailored project ideas.

Flow 1 (no idea): research + council run first silently,
then ideas are generated using that context for accuracy.

Flow 2 alternatives: receives original idea problems,
generates alternatives that specifically fix those problems.
"""

import json
import logging
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class IdeasRequest(BaseModel):
    role: str = ""
    purpose: str = "portfolio"
    context: str = ""
    research_context: str = ""
    verdict_context: str = ""
    original_idea: str = ""
    original_problems: str = ""
    show_why_better: bool = False


@router.post("/ideas")
async def generate_ideas(request: Request, body: IdeasRequest):
    try:
        from services.llm_client import call_fast

        purpose_desc = {
            "job_role":  f"getting hired as {body.role or 'a software engineer'}",
            "portfolio": f"building a strong portfolio{' for ' + body.role + ' roles' if body.role else ''}",
            "startup":   "building a real business product",
            "learning":  f"learning technologies{' for ' + body.role if body.role else ''}",
        }.get(body.purpose, "building a portfolio project")

        # Build context from research and verdict if available
        context_block = ""
        if body.research_context:
            context_block += f"\nMARKET RESEARCH CONTEXT:\n{body.research_context[:1000]}\n"
        if body.verdict_context:
            context_block += f"\nEXPERT VERDICT CONTEXT:\n{body.verdict_context[:500]}\n"

        # Build original problems block for alternatives
        problems_block = ""
        if body.original_idea and body.original_problems:
            problems_block = f"""
ORIGINAL IDEA (that did not pass expert review):
{body.original_idea}

SPECIFIC PROBLEMS WITH ORIGINAL:
{body.original_problems}

Each idea MUST specifically address and fix these problems.
Explain clearly why each idea avoids these exact issues.
"""

        why_better_instruction = ""
        if body.show_why_better:
            why_better_instruction = """
For each idea, add a "why_better_than_original" field explaining
in one sentence how this idea specifically avoids the problems
of the original idea listed above.
"""

        prompt = f"""Generate exactly 3 project ideas for someone focused on {purpose_desc}.
{f'User context: {body.context}' if body.context else ''}
{context_block}
{problems_block}

Rules:
- One idea must be Beginner level, one Intermediate, one Expert
- No generic apps — be specific and unique
- At least one idea must use AI or ML
- Each idea must directly help with {purpose_desc}
- Be specific about what makes each idea stand out
{why_better_instruction}

Return ONLY this JSON, no markdown, no explanation:
{{
    "ideas": [
        {{
            "title": "project name under 6 words",
            "one_liner": "one sentence what it does",
            "why_good": "one sentence why this helps with {purpose_desc}",
            "why_better_than_original": "",
            "skills_demonstrated": ["skill1", "skill2", "skill3"],
            "tech_stack": ["tech1", "tech2", "tech3"],
            "level": "Beginner",
            "build_time": "4 weeks",
            "market_gap": "one sentence what problem this solves"
        }}
    ]
}}"""

        response = await call_fast(
            system="You are a senior engineering mentor. Return only valid JSON.",
            user=prompt,
            max_tokens=1200,
        )

        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*', '', cleaned).strip()
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)

        if match:
            data = json.loads(match.group())
            logger.info(f"Generated {len(data.get('ideas', []))} ideas for {body.role}")
            return JSONResponse({
                "success": True,
                "ideas": data.get("ideas", []),
                "role": body.role,
                "purpose": body.purpose,
            })

        raise ValueError("Could not parse response")

    except Exception as e:
        logger.error(f"Ideas generation failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )