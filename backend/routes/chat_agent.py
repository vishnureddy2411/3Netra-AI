"""
backend/routes/chat_agent.py

Conversational Agent — Interactive Chat for Every Stage

Reads full project context from MCP and answers any question
the user has about their project at any stage.

Works for both student and professional users.
Student context: council verdict, quiz gaps, diagrams, career advice
Professional context: execution plan, architecture decisions, business constraints

Endpoint: POST /api/chat
"""

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from middleware.auth import require_auth

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    project_id:  str
    message:     str
    history:     Optional[list] = []
    role:        Optional[str]  = "Software Engineer"
    purpose:     Optional[str]  = "portfolio"
    user_type:   Optional[str]  = "student"
    stage:       Optional[str]  = ""


# ── MCP context reader ────────────────────────────────────────────────────────

async def _read_project_context(project_id: str) -> dict:
    """
    Reads all available project context from MCP.
    Returns a structured dict of everything the agent needs to answer questions.
    Never fails — returns empty values if MCP tools fail.
    """
    from fastmcp import Client

    context = {
        "plan":      {},
        "verdict":   {},
        "graph":     {},
        "diagrams":  [],
        "decisions": [],
        "files":     [],
        "build_status": [],
    }

    try:
        async with Client("http://localhost:8001/mcp") as mcp:

            # Project plan
            try:
                r = await mcp.call_tool("get_project_plan", {"project_id": project_id})
                raw = r[0].text if r else "{}"
                context["plan"] = json.loads(raw) if raw else {}
            except Exception:
                pass

            # Council verdict
            try:
                r = await mcp.call_tool("get_council_verdict", {"project_id": project_id})
                raw = r[0].text if r else "{}"
                context["verdict"] = json.loads(raw) if raw else {}
            except Exception:
                pass

            # Project graph
            try:
                r = await mcp.call_tool("get_project_graph", {"project_id": project_id})
                raw = r[0].text if r else "{}"
                context["graph"] = json.loads(raw) if raw else {}
            except Exception:
                pass

            # Diagrams
            try:
                r = await mcp.call_tool("get_diagrams", {"project_id": project_id})
                raw = r[0].text if r else "[]"
                context["diagrams"] = json.loads(raw) if raw else []
            except Exception:
                pass

            # Past decisions
            try:
                r = await mcp.call_tool("recall_decisions", {
                    "project_id": project_id,
                    "query": "all",
                    "limit": 10,
                })
                raw = r[0].text if r else "[]"
                context["decisions"] = json.loads(raw) if raw else []
            except Exception:
                pass

            # Existing files
            try:
                r = await mcp.call_tool("get_existing_files", {"project_id": project_id})
                raw = r[0].text if r else "[]"
                context["files"] = json.loads(raw) if raw else []
            except Exception:
                pass

            # Build status
            try:
                r = await mcp.call_tool("get_build_status", {"project_id": project_id})
                raw = r[0].text if r else "[]"
                context["build_status"] = json.loads(raw) if raw else []
            except Exception:
                pass

    except Exception as e:
        logger.warning(f"MCP context read failed: {e}")

    return context


# ── System prompt builder ─────────────────────────────────────────────────────

def _build_system_prompt(
    context:   dict,
    role:      str,
    purpose:   str,
    user_type: str,
    stage:     str,
) -> str:
    plan      = context.get("plan", {})
    verdict   = context.get("verdict", {})
    graph     = context.get("graph", {})
    diagrams  = context.get("diagrams", [])
    decisions = context.get("decisions", [])
    files     = context.get("files", [])

    # Project info
    idea       = plan.get("idea", "")
    tech_stack = plan.get("tech_stack", "")
    status     = plan.get("status", "")

    # Verdict info
    verdict_result    = verdict.get("verdict", "")
    verdict_reasoning = verdict.get("verdict_reasoning", "")
    recommended_stack = verdict.get("recommended_stack", [])
    v1_scope          = verdict.get("v1_scope", [])
    top_risks         = verdict.get("top_risks", [])
    career_value      = verdict.get("career_value", "")
    estimated_time    = verdict.get("estimated_build_time", "")

    # Graph info
    pages      = graph.get("pages", [])
    routes     = graph.get("api_routes", [])
    components = graph.get("shared_components", [])
    models     = graph.get("data_models", [])
    tech_dec   = graph.get("tech_decisions", {})

    # Diagram types
    diagram_types = [d.get("diagram_type", "") for d in diagrams]

    # Past decisions
    decisions_text = "\n".join([
        f"- [{d.get('node_type')}] {d.get('what')}: {d.get('why')}"
        for d in decisions[:8]
    ]) if decisions else "No decisions recorded yet."

    # Files built so far
    files_text = "\n".join([
        f"- {f.get('file_path')} ({f.get('language')})"
        for f in files[:10]
    ]) if files else "No files generated yet."

    # Stack summary
    stack_text = tech_stack or ", ".join(recommended_stack[:5]) if recommended_stack else "Not determined yet"

    # Persona based on user type
    if user_type == "professional":
        persona = f"""You are a senior engineering consultant embedded in the user's development team.
You have full knowledge of their business problem, architecture decisions, and execution plan.
You speak like a trusted senior engineer — direct, specific, practical.
You never give generic advice — every answer references their specific project, stack, and business context."""
    else:
        persona = f"""You are a senior engineering mentor helping a developer build their portfolio project.
You have full knowledge of their project, the council's analysis, and their learning gaps.
You speak like a patient technical mentor — clear, encouraging but honest, specific to their project.
You never give generic advice — every answer references their specific project, tech stack, and career goals."""

    # Purpose framing
    purpose_context = {
        "job_hunt":     f"The user is building this to get hired as {role}. Career impact matters.",
        "learning":     f"The user is learning {role} technologies through this project.",
        "professional": f"The user is building this as a real work project. Business ROI matters.",
    }.get(purpose, f"The user is building this for {purpose}.")

    prompt = f"""{persona}

PROJECT CONTEXT:
Idea: {idea}
Tech Stack: {stack_text}
Target Role: {role}
{purpose_context}
Current Stage: {stage or status}

COUNCIL VERDICT: {verdict_result}
Verdict Reasoning: {verdict_reasoning[:300] if verdict_reasoning else "Not available"}
V1 Scope: {", ".join(v1_scope[:5]) if v1_scope else "Not defined yet"}
Top Risks: {", ".join(top_risks[:3]) if top_risks else "None identified"}
Career Value: {career_value[:200] if career_value else "Not analyzed yet"}
Estimated Build Time: {estimated_time}

ARCHITECTURE:
Frontend: {tech_dec.get("frontend", "Not set")}
Backend: {tech_dec.get("backend", "Not set")}
Database: {tech_dec.get("database", "Not set")}
Auth: {tech_dec.get("auth", "Not set")}
Deployment: {tech_dec.get("deployment", "Not set")}

PAGES BUILT: {", ".join([p.get("name", "") for p in pages[:8]]) if pages else "None yet"}
API ROUTES: {", ".join([r.get("path", "") for r in routes[:8]]) if routes else "None yet"}
COMPONENTS: {", ".join([c.get("name", "") for c in components[:6]]) if components else "None yet"}
DATA MODELS: {", ".join([m.get("name", "") for m in models[:6]]) if models else "None yet"}
DIAGRAMS GENERATED: {", ".join(diagram_types) if diagram_types else "None yet"}

PAST DECISIONS:
{decisions_text}

FILES GENERATED SO FAR:
{files_text}

BEHAVIOR RULES:
1. Answer the SPECIFIC question asked — do not give a lecture
2. Reference actual project components by name — not generic examples
3. If the user asks about something not in the context, say so honestly
4. Keep responses focused — under 200 words unless the question requires depth
5. If the user wants to change something, explain the impact on the existing architecture
6. For technical questions, give code examples using the ACTUAL tech stack ({stack_text})
7. For career questions, reference the actual project and actual {role} requirements
8. Never say "it depends" — give a specific answer for this specific project
9. If asked about a diagram, explain it in plain language referencing the actual components
10. If the user is confused, simplify without losing accuracy"""

    return prompt


# ── Main endpoint ─────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat_with_agent(request: Request, body: ChatRequest):
    """
    Conversational agent for interactive Q&A at any stage.

    Reads full project context from MCP.
    Answers any question about the project specifically.
    Works for both student and professional users.
    """
    user = await require_auth(request)

    try:
        from services.llm_client import call_strong

        logger.info(
            f"Chat agent — project: {body.project_id} | "
            f"user_type: {body.user_type} | "
            f"message: {body.message[:60]}"
        )

        # Read full project context from MCP
        context = await _read_project_context(body.project_id)

        # Build system prompt with full context
        system_prompt = _build_system_prompt(
            context=context,
            role=body.role or "Software Engineer",
            purpose=body.purpose or "portfolio",
            user_type=body.user_type or "student",
            stage=body.stage or "",
        )

        # Build conversation history
        history_text = ""
        if body.history:
            history_text = "\n\nCONVERSATION SO FAR:\n"
            for turn in body.history[-8:]:
                label = "User" if turn.get("role") == "user" else "Agent"
                history_text += f"{label}: {turn.get('content', '')}\n"

        # Determine which MCP tools were actually used
        sources = []
        if context.get("plan"):     sources.append("project_plan")
        if context.get("verdict"):  sources.append("council_verdict")
        if context.get("graph"):    sources.append("project_graph")
        if context.get("diagrams"): sources.append("diagrams")
        if context.get("decisions"):sources.append("decisions")

        response = await call_strong(
            system=system_prompt,
            user=f"{history_text}\n\nUser question: {body.message}",
            max_tokens=600,
        )

        # Save Q&A to MCP decisions for context continuity
        try:
            from fastmcp import Client
            async with Client("http://localhost:8001/mcp") as mcp:
                await mcp.call_tool("write_decision", {
                    "project_id": body.project_id,
                    "what":       f"User asked: {body.message[:100]}",
                    "why":        f"Agent answered: {response[:100]}",
                    "node_type":  "architecture_decision",
                    "session_id": "chat",
                })
        except Exception:
            pass

        logger.info(
            f"Chat agent response — "
            f"length: {len(response)} chars | "
            f"sources: {sources}"
        )

        return JSONResponse({
            "success":  True,
            "response": response.strip(),
            "sources":  sources,
        })

    except Exception as e:
        logger.error(f"Chat agent failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success":  False,
                "error":    str(e),
                "response": "I had a technical issue. Please try again.",
                "sources":  [],
            }
        )


class BriefingRequest(BaseModel):
    project_id: str
    role:       Optional[str] = "Software Engineer"
    purpose:    Optional[str] = "portfolio"
    user_type:  Optional[str] = "student"


@router.post("/chat/briefing")
async def get_project_briefing(request: Request, body: BriefingRequest):
    """
    Generates a project briefing when user opens an existing project.
    Reads full MCP context and summarizes where they left off.
    """
    user = await require_auth(request)

    try:
        from services.llm_client import call_strong

        logger.info(f"Generating briefing for project: {body.project_id}")

        context = await _read_project_context(body.project_id)

        plan      = context.get("plan", {})
        verdict   = context.get("verdict", {})
        graph     = context.get("graph", {})
        decisions = context.get("decisions", [])
        build     = context.get("build_status", [])

        idea         = plan.get("idea", "")
        tech_stack   = plan.get("tech_stack", "")
        status       = plan.get("status", "")
        v1_scope     = verdict.get("v1_scope", [])
        stack        = verdict.get("recommended_stack", [])
        pages        = graph.get("pages", [])
        routes       = graph.get("api_routes", [])
        tech_dec     = graph.get("tech_decisions", {})

        approved = [b for b in build if b.get("status") == "approved"]
        pending  = [b for b in build if b.get("status") != "approved"]

        decisions_text = "\n".join([
            f"- {d.get('what', '')}"
            for d in decisions[:5]
        ]) if decisions else "No decisions recorded yet"

        response = await call_strong(
            system=(
                f"You are a senior engineering assistant briefing a developer "
                f"returning to their project. Be specific, concise, and immediately useful. "
                f"Never use generic phrases. Reference actual project components by name."
            ),
            user=(
                f"Generate a returning-user briefing for this project.\n\n"
                f"Project: {idea}\n"
                f"Role: {body.role}\n"
                f"Tech Stack: {tech_stack or ', '.join(stack[:4])}\n"
                f"Status: {status}\n"
                f"V1 Scope: {', '.join(v1_scope[:4]) if v1_scope else 'not defined'}\n"
                f"Pages built: {', '.join([p.get('name','') for p in pages[:5]]) if pages else 'none yet'}\n"
                f"API routes: {len(routes)} defined\n"
                f"Frontend: {tech_dec.get('frontend', 'not set')}\n"
                f"Backend: {tech_dec.get('backend', 'not set')}\n"
                f"Database: {tech_dec.get('database', 'not set')}\n"
                f"Approved stages: {len(approved)}\n"
                f"Recent decisions:\n{decisions_text}\n\n"
                f"Write a briefing in this exact format:\n"
                f"Welcome back. Here is where you left off:\n\n"
                f"Project: [project name]\n"
                f"[2-3 bullet points of what was decided — specific tech choices and scope]\n\n"
                f"What comes next:\n"
                f"[1-2 bullet points of immediate next steps]\n\n"
                f"Type any question or continue to the next stage."
            ),
            max_tokens=300,
        )

        return JSONResponse({
            "success":  True,
            "briefing": response.strip(),
            "sources":  ["project_plan", "council_verdict", "project_graph", "decisions"],
        })

    except Exception as e:
        logger.error(f"Briefing failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )