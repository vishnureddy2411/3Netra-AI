"""
backend/routes/discuss.py

Project confirmation discussion loop.
User can ask any doubt about their selected project.
Agent answers with role-specific, project-specific guidance.
Uses Sonnet — this is a high-trust decision moment.

Endpoint: POST /api/discuss
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class DiscussRequest(BaseModel):
    selected_project: dict
    user_message: str
    discussion_history: list = []
    role: str = "Software Engineer"
    purpose: str = "portfolio"


READY_SIGNALS = [
    "ready", "yes", "proceed", "continue", "let's go", "move on",
    "sounds good", "ok", "okay", "got it", "understood", "confirmed",
    "let's proceed", "start diagrams", "go ahead", "next step",
    "i'm ready", "im ready", "move forward", "start building",
    "let's start", "lets start", "begin", "start now",
]


@router.post("/discuss")
async def discuss_project(request: Request, body: DiscussRequest):
    """
    Answers user doubts about their selected project.
    Ends every response by asking if user is ready to continue.
    Never pushes user forward before they confirm.
    """
    try:
        from services.llm_client import call_strong

        project     = body.selected_project
        title       = project.get('title', 'Selected Project')
        description = project.get('description', '')
        tech_stack  = ', '.join(project.get('techStack', []))
        level       = project.get('level', 'Intermediate')
        build_time  = project.get('buildTime', '6 weeks')
        skills      = ', '.join(project.get('skillsDemonstrated', []))
        risks       = project.get('risks', [])
        risks_text  = ' | '.join(r for r in risks[:3] if r) if risks else 'none identified'
        portfolio_value = project.get('portfolioValue', '')

        # Build conversation history
        history_text = ""
        if body.discussion_history:
            history_text = "\nPREVIOUS DISCUSSION:\n"
            for turn in body.discussion_history[-8:]:
                label = "User" if turn.get('role') == 'user' else "Mentor"
                history_text += f"{label}: {turn.get('content', '')}\n"

        system_prompt = f"""You are a senior technical mentor helping a candidate decide whether to proceed with building their selected project.

SELECTED PROJECT: {title}
DESCRIPTION: {description}
TECH STACK: {tech_stack or 'not specified'}
DIFFICULTY: {level}
BUILD TIME: {build_time}
SKILLS DEMONSTRATED: {skills or 'not specified'}
KNOWN RISKS: {risks_text}
PORTFOLIO VALUE: {portfolio_value or 'not specified'}
TARGET ROLE: {body.role}
PURPOSE: {body.purpose}
{history_text}

YOUR BEHAVIOR RULES:
1. Answer the user's SPECIFIC question — do not give generic advice
2. Reference the actual project title, actual technologies, and actual {body.role} requirements
3. Be honest about risks — do not oversell the project
4. Keep responses under 120 words — focused and clear
5. If the user asks to compare with alternatives, briefly compare but remind them they can request more options from the previous step
6. ALWAYS end your response with exactly this line: "Are you ready to move to diagrams, or do you have more questions?"
7. Never move forward unless the user explicitly confirms readiness
8. Treat the user as an intelligent adult making an important career decision"""

        response = await call_strong(
            system=system_prompt,
            user=body.user_message,
            max_tokens=250,
        )

        # Ensure the response ends with the readiness question
        response_text = response.strip()
        if "ready to move to diagrams" not in response_text.lower():
            response_text += "\n\nAre you ready to move to diagrams, or do you have more questions?"

        # Detect if user signal indicates readiness
        user_seems_ready = any(
            signal in body.user_message.lower()
            for signal in READY_SIGNALS
        )

        logger.info(
            f"Discussion: project={title[:30]} | role={body.role} | "
            f"ready_signal={user_seems_ready} | "
            f"history_turns={len(body.discussion_history)}"
        )

        return JSONResponse({
            "success": True,
            "response": response_text,
            "user_seems_ready": user_seems_ready,
        })

    except Exception as e:
        logger.error(f"Discussion failed: {e}")
        project_name = body.selected_project.get('title', 'your selected project')
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "response": (
                    f"I had a technical issue answering that. "
                    f"For {project_name}: your concern is valid and worth thinking through. "
                    f"Are you ready to move to diagrams, or do you have more questions?"
                ),
                "user_seems_ready": False,
            }
        )