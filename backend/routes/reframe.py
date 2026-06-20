"""
backend/routes/reframe.py

Bulletproof reframe — shorter prompt, reliable Haiku output.
New fields: skills_demonstrated, skills_lacking, how_suggestion_improves.
"""

import json
import logging
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class ReframeRequest(BaseModel):
    original_idea: str
    pivot_suggestion: str = ""
    verdict: str = "PIVOT"
    verdict_reasoning: str = ""
    top_risks: list[str] = []
    v1_scope: list[str] = []
    recommended_stack: list[str] = []
    role: str = "Software Engineer"
    purpose: str = "portfolio"


@router.post("/reframe")
async def reframe_verdict(request: Request, body: ReframeRequest):
    try:
        from services.llm_client import call_fast

        stack_str = ", ".join(body.recommended_stack[:5]) if body.recommended_stack else "not specified"
        risks_str = " | ".join(body.top_risks[:3]) if body.top_risks else "none"
        scope_str = " | ".join(body.v1_scope[:3]) if body.v1_scope else "not specified"

        prompt = f"""You are evaluating this project for a {body.role} targeting {body.purpose}.

PROJECT: {body.original_idea}
TECH STACK FROM EXPERTS: {stack_str}
EXPERT VERDICT: {body.verdict}
EXPERT REASONING: {body.verdict_reasoning[:200]}
TOP RISKS: {risks_str}
V1 SCOPE: {scope_str}
SUGGESTED ALTERNATIVE: {body.pivot_suggestion[:150] if body.pivot_suggestion else "none"}

Rules:
- Every point must reference THIS specific project, THIS role, or THESE technologies
- Name specific technologies, specific hiring signals, specific market facts
- Never write generic advice that could apply to any project
- skills_demonstrated: what THIS project proves to a hiring manager
- skills_lacking: what {body.role} roles require that THIS project does NOT show
- how_suggestion_improves: exactly how the alternative fixes each weakness

Return ONLY valid JSON:
{{
    "original_pros": [
        "specific strength referencing actual tech or market signal",
        "another specific strength"
    ],
    "original_cons": [
        "specific reason a {body.role} hiring manager skips this — name the exact problem",
        "another specific weakness with real evidence",
        "third specific weakness"
    ],
    "suggested_pros": [
        "specific reason the alternative is stronger for {body.role} {body.purpose}",
        "another concrete advantage naming specific technologies or signals"
    ],
    "suggested_cons": [
        "honest specific downside of the alternative",
        "another honest downside"
    ],
    "skills_demonstrated": [
        "specific skill this project proves",
        "another specific skill",
        "third skill"
    ],
    "skills_lacking": [
        "important {body.role} skill NOT shown by this project",
        "another missing skill",
        "third missing skill"
    ],
    "how_suggestion_improves": [
        "specifically how alternative fixes weakness 1",
        "specifically how alternative fixes weakness 2",
        "specifically how alternative adds missing skill"
    ],
    "summary": "one sentence on what this person should do for {body.role} {body.purpose}"
}}"""

        response = await call_fast(
            system="You are a direct engineering mentor. Reference specific technologies and hiring signals. Return only valid JSON. No markdown.",
            user=prompt,
            max_tokens=900,
        )

        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*', '', cleaned).strip()
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)

        if match:
            data = json.loads(match.group())

            # Detect generic fallback strings
            bad_strings = [
                "addresses a real engineering problem",
                "buildable within a reasonable timeframe",
                "more targeted to your specific goal",
                "stronger signal for your purpose",
                "it addresses the specific weaknesses",
            ]
            all_text = json.dumps(data).lower()
            if any(b in all_text for b in bad_strings):
                raise ValueError("Generic strings detected — using smart fallback")

            logger.info(f"Reframe success: {body.original_idea[:40]}")
            return JSONResponse({"success": True, **data})

        raise ValueError("Could not parse JSON")

    except Exception as e:
        logger.warning(f"Reframe primary failed ({e}) — smart fallback")

        # SMART FALLBACK using real council data
        stack = body.recommended_stack[:4] if body.recommended_stack else ["Python", "FastAPI", "PostgreSQL"]
        stack_str = ", ".join(stack)
        idea_short = body.original_idea[:80]

        # Build pros from verdict reasoning
        original_pros = []
        if body.verdict_reasoning and len(body.verdict_reasoning) > 30:
            # Extract first meaningful sentence
            sentences = body.verdict_reasoning.split('.')
            first = sentences[0].strip() if sentences else ""
            if first and len(first) > 20:
                original_pros.append(f"Expert council confirms: {first}")
        if stack_str:
            original_pros.append(
                f"{stack_str} are technologies that appear in {body.role} job descriptions — this stack is relevant"
            )
        if not original_pros:
            original_pros = [f"Demonstrates practical {body.role} engineering skills with a real use case"]

        # Build cons from actual risks
        original_cons = []
        for risk in body.top_risks[:3]:
            if risk and len(risk) > 15:
                original_cons.append(
                    f"A {body.role} hiring manager would notice: {risk}"
                )
        if not original_cons:
            original_cons = [
                f"Without measurable outcomes, this project looks like a tutorial exercise to {body.role} reviewers",
                "No concrete business domain anchor makes it hard to evaluate your engineering judgment",
                "Missing evaluation metrics or benchmark comparisons reduce technical credibility",
            ]

        # Build suggested pros
        suggested_pros = []
        if body.pivot_suggestion and len(body.pivot_suggestion) > 20:
            suggested_pros = [
                f"Directly addresses the weaknesses flagged by Risk Manager and Career Coach for {body.role}",
                f"More differentiated than typical {body.role} portfolio projects — harder to dismiss in 10 seconds",
            ]

        # Build skills from stack
        skills_demonstrated = [f"{t} integration and deployment" for t in stack[:2]]
        skills_demonstrated.append(f"End-to-end {body.role} project architecture")

        skills_lacking = [
            f"Production monitoring and observability — critical for {body.role} roles",
            f"Evaluation framework and benchmark metrics — expected in {body.role} interviews",
            "CI/CD pipeline and Docker deployment — signals production readiness",
        ]

        how_improves = []
        if body.pivot_suggestion:
            how_improves = [
                f"Adds concrete domain focus that makes engineering decisions justifiable to hiring managers",
                f"Includes measurable outcomes that {body.role} interviewers can discuss",
                f"Demonstrates system design thinking beyond framework usage",
            ]

        return JSONResponse({
            "success": True,
            "original_pros": original_pros,
            "original_cons": original_cons,
            "suggested_pros": suggested_pros,
            "suggested_cons": [
                "Requires domain research before starting — adds 1-2 days of planning",
                "Slightly higher scope — stick to MVP to avoid overbuilding",
            ] if body.pivot_suggestion else [],
            "skills_demonstrated": skills_demonstrated,
            "skills_lacking": skills_lacking,
            "how_suggestion_improves": how_improves,
            "summary": (
                body.verdict_reasoning[:150]
                if body.verdict_reasoning and len(body.verdict_reasoning) > 30
                else f"Add a specific domain use case and measurable outcomes to make this project compelling for {body.role} roles."
            ),
        })
        