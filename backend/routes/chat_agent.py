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
    session_id:  Optional[str]  = ""


# ── MCP context reader ────────────────────────────────────────────────────────
async def _read_session_messages(session_id: str, limit: int = 5) -> list:
    """
    Reads the last N messages from a specific session.
    Used to give the agent immediate context about what was
    discussed in that particular session.
    """
    if not session_id:
        return []
    try:
        import os
        from supabase import create_client
        url = os.getenv("SUPABASE_URL", "").replace("/rest/v1", "").rstrip("/")
        key = os.getenv("SUPABASE_KEY", "")
        sb  = create_client(url, key)

        result = sb.table("project_chat_history")\
            .select("role, content, created_at")\
            .eq("session_id", session_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()

        messages = result.data or []
        messages.reverse()
        return messages
    except Exception as e:
        logger.warning(f"Could not read session messages: {e}")
        return []
    
async def _read_project_context(project_id: str, stage: str = "planning") -> dict:
    context: dict = {
        "stage":        stage,
        "plan":         {},
        "verdict":      {},
        "graph":        {},
        "diagrams":     [],
        "decisions":    [],
        "files":        [],
        "build_status": [],
        "stage_memory": {},
    }
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

            # Stage memory
            try:
                stage = context.get("stage", "planning")
                r = await mcp.call_tool("get_stage_memory", {
                    "project_id": project_id,
                    "stage_name": stage,
                })
                raw = r[0].text if r else "{}"
                context["stage_memory"] = json.loads(raw) if raw else {}
            except Exception:
                pass

            # Session messages — last 5 from this specific session
            try:
                session_id = context.get("session_id", "")
                if session_id:
                    context["session_messages"] = await _read_session_messages(session_id, limit=5)
            except Exception:
                pass

            # Project plan — try Supabase UUID first, then internal MCP ID
            try:
                r = await mcp.call_tool("get_project_plan", {"project_id": project_id})
                raw = r[0].text if r else "{}"
                plan = json.loads(raw) if raw else {}
                # If not found, try reading internal_project_id from Supabase
                if not plan or plan.get("error"):
                    import os
                    from supabase import create_client
                    url = os.getenv("SUPABASE_URL", "").replace("/rest/v1", "").rstrip("/")
                    key = os.getenv("SUPABASE_KEY", "")
                    sb  = create_client(url, key)
                    result = sb.table("user_projects")\
                        .select("internal_project_id")\
                        .eq("id", project_id)\
                        .single()\
                        .execute()
                    if result.data and result.data.get("internal_project_id"):
                        mcp_id = result.data["internal_project_id"]
                        context["mcp_project_id"] = mcp_id
                        r2 = await mcp.call_tool("get_project_plan", {"project_id": mcp_id})
                        raw2 = r2[0].text if r2 else "{}"
                        plan = json.loads(raw2) if raw2 else {}
                context["plan"] = plan
            except Exception:
                pass

            # Use MCP project ID if found — else fall back to Supabase UUID
            mcp_id = context.get("mcp_project_id", project_id)

            # Council verdict
            try:
                r = await mcp.call_tool("get_council_verdict", {"project_id": mcp_id})
                raw = r[0].text if r else "{}"
                context["verdict"] = json.loads(raw) if raw else {}
            except Exception:
                pass

            # Project graph
            try:
                r = await mcp.call_tool("get_project_graph", {"project_id": mcp_id})
                raw = r[0].text if r else "{}"
                context["graph"] = json.loads(raw) if raw else {}
            except Exception:
                pass

            # Diagrams
            try:
                r = await mcp.call_tool("get_diagrams", {"project_id": mcp_id})
                raw = r[0].text if r else "[]"
                context["diagrams"] = json.loads(raw) if raw else []
            except Exception:
                pass

            # Past decisions
            try:
                r = await mcp.call_tool("recall_decisions", {
                    "project_id": mcp_id,
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

    
    # Stage memory
    stage_mem          = context.get("stage_memory", {})
    approved_decisions = stage_mem.get("approved_decisions", [])
    rejected_ideas     = stage_mem.get("rejected_ideas",     [])
    pending_questions  = stage_mem.get("pending_questions",  [])
    stage_summary      = stage_mem.get("summary",            "")
    stage_tech         = stage_mem.get("tech_stack",         [])

    stage_memory_text = ""
    if any([approved_decisions, rejected_ideas, pending_questions, stage_summary]):
        stage_memory_text = f"""
## Stage Memory — {stage or 'planning'} Stage
This is a summary of all important decisions made in previous sessions of this stage.
Use this instead of asking the user to repeat themselves.

Approved decisions:
{chr(10).join(f'  ✓ {d}' for d in approved_decisions) if approved_decisions else '  None yet'}

Rejected ideas:
{chr(10).join(f'  ✗ {r}' for r in rejected_ideas) if rejected_ideas else '  None yet'}

Pending questions:
{chr(10).join(f'  ? {q}' for q in pending_questions) if pending_questions else '  None yet'}

Stage summary: {stage_summary or 'Not summarized yet'}
"""
# Session messages — last 5 from this specific session
    session_messages = context.get("session_messages", [])
    session_context  = ""
    if session_messages:
        session_context = "\n## Recent Session Context\n"
        session_context += "Last messages from this specific session:\n"
        for msg in session_messages:
            content = msg.get("content", {})
            role    = msg.get("role", "unknown")
            if isinstance(content, dict):
                text = content.get("text", "") or content.get("message", "")
            else:
                text = str(content)
            if text:
                label = "User" if role == "user" else "Agent"
                session_context += f"{label}: {text[:200]}\n"
                
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
{stage_memory_text}
{session_context}

FILES GENERATED SO FAR:
{files_text}

YOUR ROLE:
You are a senior AI engineering team member — the smartest engineer on this developer's team.
You have full access to their project context above.
You think, reason, and respond like a real human senior engineer with 10+ years experience.

YOUR SKILLS — you are expert in all of these:
- System design and architecture — design scalable, production-grade systems
- Full stack development — React, Next.js, FastAPI, Django, Express, any framework
- Database design — PostgreSQL, MongoDB, Redis, schema design, query optimization
- API design — REST, GraphQL, WebSockets, authentication, rate limiting
- AI and ML engineering — LLMs, RAG, embeddings, fine-tuning, agents, pipelines
- Data engineering — ETL, pipelines, Kafka, Spark, Airflow, dbt, data modeling
- DevOps — Docker, Kubernetes, CI/CD, GitHub Actions, Railway, Vercel, AWS, GCP
- Security — auth, JWT, OAuth, RBAC, encryption, OWASP, vulnerability assessment
- Code review — spot bugs, performance issues, security holes, bad patterns
- Debugging — trace errors, identify root causes, fix issues
- Career guidance — resume bullets, interview preparation, portfolio strategy
- Project planning — scope, timeline, priorities, MVP definition, roadmap
- Code generation — write complete, production-ready code in any language
- Testing — unit tests, integration tests, E2E tests, test strategies
- Performance optimization — profiling, caching, indexing, load testing

HOW YOU RESPOND:
- Answer anything the user asks — no topic is off limits
- Use project context when the question is about this specific project
- Use your engineering knowledge when the question is general
- Write actual code when asked — complete, working, production-ready
- Give specific answers — never vague or generic
- Think step by step for complex problems
- Be direct — no unnecessary preamble
- Match response length to question complexity — short answers for simple questions, detailed for complex ones
- If you disagree with a decision, say so clearly and explain why
- Treat the user as an intelligent developer — no hand-holding unless asked"""

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

        logger.info("=" * 60)
        logger.info(f"CHAT REQUEST RECEIVED")
        logger.info(f"  project_id:  {body.project_id}")
        logger.info(f"  session_id:  {body.session_id}")
        logger.info(f"  stage:       {body.stage}")
        logger.info(f"  user_type:   {body.user_type}")
        logger.info(f"  role:        {body.role}")
        logger.info(f"  message:     {body.message[:100]}")
        logger.info(f"  history len: {len(body.history or [])}")
        logger.info("=" * 60)

        # Read full project context from MCP
        logger.info(f"LOADING MCP CONTEXT for project: {body.project_id}")
        context = await _read_project_context(body.project_id, body.stage or "planning")
        context["session_id"] = body.session_id or ""
        context["session_messages"] = await _read_session_messages(body.session_id or "", limit=5)

        logger.info(f"MCP CONTEXT LOADED:")
        logger.info(f"  plan found:          {bool(context.get('plan'))}")
        logger.info(f"  verdict found:       {bool(context.get('verdict'))}")
        logger.info(f"  graph found:         {bool(context.get('graph'))}")
        logger.info(f"  diagrams count:      {len(context.get('diagrams', []))}")
        logger.info(f"  decisions count:     {len(context.get('decisions', []))}")
        logger.info(f"  stage_memory found:  {bool(context.get('stage_memory'))}")
        logger.info(f"  session_messages:    {len(context.get('session_messages', []))}")

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

        logger.info(f"AGENT RESPONSE GENERATED:")
        logger.info(f"  length:  {len(response)} chars")
        logger.info(f"  sources: {sources}")
        logger.info(f"  preview: {response[:100]}")
        logger.info("=" * 60)
        # Update session title based on first message
        try:
            if body.message and len(body.message) > 5:
                import os
                from supabase import create_client
                sb_url = os.getenv("SUPABASE_URL", "").replace("/rest/v1", "").rstrip("/")
                sb_key = os.getenv("SUPABASE_KEY", "")
                sb     = create_client(sb_url, sb_key)

                # Only update if title is still default
                existing_session = sb.table("project_sessions")\
                    .select("id, title, message_count")\
                    .eq("id", body.session_id or "")\
                    .single()\
                    .execute()

                if existing_session.data and is_default_title:
                    # Generate meaningful title from first question
                    title_words = body.message.strip()[:60]
                    if len(body.message) > 60:
                        title_words = title_words + "..."
                    sb.table("project_sessions")\
                        .update({"title": title_words})\
                        .eq("id", body.session_id or "")\
                        .execute()
                    context["session_title_updated"] = True
                    context["new_session_title"] = title_words
        except Exception:
            pass
        # Update stage memory asynchronously — non-blocking
        import asyncio
        user_id = user.get("id", "") or user.get("sub", "") or ""
        if user_id:
            asyncio.create_task(_update_stage_memory(
                project_id = body.project_id,
                stage_name = body.stage or "planning",
                user_id    = user_id,
                question   = body.message,
                answer     = response.strip(),
                existing   = context.get("stage_memory", {}),
            ))

        return JSONResponse({
            "success":        True,
            "response":       response.strip(),
            "sources":        sources,
            "title_updated":  context.get("session_title_updated", False),
            "new_title":      context.get("new_session_title", ""),
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

async def _update_stage_memory(
    project_id: str,
    stage_name: str,
    user_id:    str,
    question:   str,
    answer:     str,
    existing:   dict,
) -> None:
    """
    After every agent response, extracts key decisions and updates stage memory.
    Uses a fast LLM call to classify what was decided, rejected, or is pending.
    Non-blocking — failure does not affect the user response.
    """
    try:
        from services.llm_client import call_fast

        approved   = existing.get("approved_decisions", [])
        rejected   = existing.get("rejected_ideas",     [])
        pending    = existing.get("pending_questions",  [])
        summary    = existing.get("summary",            "")

        extraction = await call_fast(
            system=(
                "You are a project memory extractor. "
                "Read the conversation turn and extract key decisions. "
                "Return ONLY valid JSON."
            ),
            user=(
                f"User asked: {question}\n"
                f"Agent answered: {answer}\n\n"
                f"Extract from this conversation turn:\n"
                f"Return JSON:\n"
                f"{{\n"
                f'  "new_approved": ["list of things approved or decided in this turn"],\n'
                f'  "new_rejected": ["list of things rejected or ruled out"],\n'
                f'  "new_pending":  ["list of new questions or unresolved items"],\n'
                f'  "update_summary": "one sentence summary of what was discussed — or empty string if nothing important"\n'
                f"}}"
            ),
            max_tokens=300,
        )

        import re
        cleaned = re.sub(r'```json\s*', '', extraction)
        cleaned = re.sub(r'```\s*',     '', cleaned).strip()
        match   = re.search(r'\{.*\}',  cleaned, re.DOTALL)

        if match:
            data        = json.loads(match.group())
            new_approved = data.get("new_approved", [])
            new_rejected = data.get("new_rejected", [])
            new_pending  = data.get("new_pending",  [])
            new_summary  = data.get("update_summary", "")

            # Merge with existing — avoid duplicates
            merged_approved = list(set(approved + new_approved))[:20]
            merged_rejected = list(set(rejected + new_rejected))[:20]
            merged_pending  = list(set(pending  + new_pending))[:10]
            merged_summary  = new_summary if new_summary else summary

            # Save to Supabase directly
            import os
            from supabase import create_client
            url = os.getenv("SUPABASE_URL", "").replace("/rest/v1", "").rstrip("/")
            key = os.getenv("SUPABASE_KEY", "")
            sb  = create_client(url, key)

            sb.table("stage_memory").upsert({
                "project_id":         project_id,
                "stage_name":         stage_name,
                "user_id":            user_id,
                "approved_decisions": merged_approved,
                "rejected_ideas":     merged_rejected,
                "pending_questions":  merged_pending,
                "important_context":  existing.get("important_context", ""),
                "tech_stack":         existing.get("tech_stack", []),
                "summary":            merged_summary,
            }, on_conflict="project_id,stage_name").execute()

            logger.info(f"Stage memory updated: {project_id}/{stage_name}")

    except Exception as e:
        logger.warning(f"Stage memory update failed silently: {e}")
        
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