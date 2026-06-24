"""
backend/routes/ideas.py

Two flows:

1. Ideas flow (default):
   Strong model — silently runs council-level analysis,
   returns one deeply analyzed project per level
   (Beginner / Intermediate / Expert) with full
   hiring-manager-grade justification.

2. Alternatives flow (show_why_better=True):
   Fast model — generates targeted alternatives that
   specifically fix problems with a rejected idea.
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
    role:             str  = ""
    purpose:          str  = "portfolio"
    context:          str  = ""
    research_context: str  = ""
    verdict_context:  str  = ""
    original_idea:    str  = ""
    original_problems:str  = ""
    show_why_better:  bool = False


@router.post("/ideas")
async def generate_ideas(request: Request, body: IdeasRequest):
    try:
        if body.show_why_better:
            return await _generate_alternatives(body)
        return await _generate_enriched_ideas(body)
    except Exception as e:
        logger.error(f"Ideas generation failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


# ── Enriched ideas — strong model ────────────────────────────────────────────

async def _generate_enriched_ideas(body: IdeasRequest):
    import asyncio
    from services.llm_client import call_strong

    purpose_desc = {
        "job_role":  f"getting hired as {body.role or 'a software engineer'}",
        "portfolio": f"building a strong portfolio{' for ' + body.role + ' roles' if body.role else ''}",
        "startup":   "building a real business product",
        "learning":  f"learning technologies{' for ' + body.role if body.role else ''}",
    }.get(body.purpose, "building a portfolio project")

    context_block = ""
    if body.research_context:
        context_block += f"\nMARKET RESEARCH:\n{body.research_context[:400]}\n"
    if body.verdict_context:
        context_block += f"\nEXPERT CONTEXT:\n{body.verdict_context[:200]}\n"

    async def generate_one(level: str) -> dict:
        prompt = f"""You are a senior engineering hiring manager.
Generate ONE {level} level project idea for: {purpose_desc}
{f'User context: {body.context}' if body.context else ''}
{context_block}

CRITICAL: Never use double quote characters inside string values. Use apostrophes instead.

Return ONLY this JSON — no markdown:
{{
    "title": "project name under 6 words",
    "level": "{level}",
    "one_liner": "one sentence what it does",
    "why_good": "why this is right for {purpose_desc}",
    "build_time": "X weeks",
    "market_gap": "one sentence what problem this solves",
    "tech_stack": ["list ALL technologies — no limit"],
    "tech_stack_detail": [
        {{"name": "each tech", "purpose": "why this tech for this project"}}
    ],
    "skills_demonstrated": ["skill1", "skill2", "skill3"],
    "hiring_manager_impression": "What a hiring manager thinks in 10 seconds. Specific to this project domain. No double quotes inside this string.",
    "engineering_signals": ["signal1", "signal2", "signal3"],
    "generic_web_dev_excluded": ["generic thing 1", "generic thing 2"],
    "council_decision": "Why this project was selected for {level} level.",
    "why_selected": "Single most important reason this wins at {level} level.",
    "real_world_use_case": "Concrete real-world scenario for this project.",
    "portfolio_strength": "What this proves to a hiring manager.",
    "risk_weakness": "What could look weak if candidate cuts corners.",
    "how_to_stand_out": "3 specific implementation decisions to make this exceptional."
}}
REQUIREMENTS:
- tech_stack must include ALL layers: core framework, database, AI/ML libraries, testing, deployment, monitoring, infrastructure, any domain-specific tools — no artificial limit, list everything the project genuinely needs
- All content must be specific to this exact project."""

        response = await call_strong(
            system=(
                "Return only valid JSON. "
                "Never use double quote characters inside string values — use apostrophes. "
                "All content must be specific to this exact project."
            ),
            user=prompt,
            max_tokens=1500,
        )

        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*', '', cleaned).strip()
        match   = re.search(r'\{.*\}', cleaned, re.DOTALL)

        if not match:
            raise ValueError(f"No JSON found for {level}")

        raw = match.group()

        # Repair truncation
        open_braces   = raw.count('{') - raw.count('}')
        open_brackets = raw.count('[') - raw.count(']')
        if open_braces > 0 or open_brackets > 0:
            raw = raw.rstrip(',\n\r\t ')
            raw += ']' * open_brackets
            raw += '}' * open_braces

        # Repair trailing commas
        raw = re.sub(r',\s*([}\]])', r'\1', raw)

        idea = json.loads(raw)

        # Ensure tech_stack exists as string[]
        if not idea.get("tech_stack") and idea.get("tech_stack_detail"):
            idea["tech_stack"] = [t["name"] for t in idea["tech_stack_detail"]]

        return idea

    # Run all 3 levels in parallel
    results = await asyncio.gather(
        generate_one("Beginner"),
        generate_one("Intermediate"),
        generate_one("Expert"),
        return_exceptions=True,
    )

    ideas = []
    for i, result in enumerate(results):
        level = ["Beginner", "Intermediate", "Expert"][i]
        if isinstance(result, Exception):
            logger.error(f"Failed to generate {level} idea: {result}")
        else:
            ideas.append(result)

    if not ideas:
        raise ValueError("All 3 idea generation calls failed")

    logger.info(f"Generated {len(ideas)} enriched ideas for role={body.role}")
    return JSONResponse({
        "success":  True,
        "ideas":    ideas,
        "role":     body.role,
        "purpose":  body.purpose,
        "enriched": True,
    })


# ── Alternatives — fast model ─────────────────────────────────────────────────

async def _generate_alternatives(body: IdeasRequest):
    from services.llm_client import call_fast

    purpose_desc = {
        "job_role":  f"getting hired as {body.role or 'a software engineer'}",
        "portfolio": f"building a strong portfolio{' for ' + body.role + ' roles' if body.role else ''}",
        "startup":   "building a real business product",
        "learning":  f"learning technologies{' for ' + body.role if body.role else ''}",
    }.get(body.purpose, "building a portfolio project")

    problems_block = ""
    if body.original_idea and body.original_problems:
        problems_block = f"""
ORIGINAL IDEA (rejected by expert council):
{body.original_idea}

SPECIFIC PROBLEMS TO FIX:
{body.original_problems}

Each alternative MUST specifically address and fix these problems.
"""

    prompt = f"""Generate exactly 3 alternative project ideas for {purpose_desc}.
{f'User context: {body.context}' if body.context else ''}
{problems_block}

Rules:
- One Beginner, one Intermediate, one Expert
- Each must specifically fix the problems listed above
- No generic apps — be specific

Return ONLY this JSON:
{{
    "ideas": [
        {{
            "title": "project name under 6 words",
            "one_liner": "one sentence what it does",
            "why_good": "why this helps with {purpose_desc}",
            "why_better_than_original": "how this specifically fixes the original problems",
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
    cleaned = re.sub(r'```\s*',     '', cleaned).strip()
    match   = re.search(r'\{.*\}',  cleaned, re.DOTALL)

    if match:
        data  = json.loads(match.group())
        ideas = data.get("ideas", [])
        logger.info(f"Generated {len(ideas)} alternatives for role={body.role}")
        return JSONResponse({
            "success":  True,
            "ideas":    ideas,
            "role":     body.role,
            "purpose":  body.purpose,
            "enriched": False,
        })

    raise ValueError("Could not parse alternatives response")