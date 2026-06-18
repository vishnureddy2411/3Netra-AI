"""
backend/services/diagrams.py

Engineering Manager agent — generates architecture diagrams using Mermaid.js.

Flow:
  1. Read Chairman verdict from MCP
  2. Generate 5 diagrams in batches of 4 using asyncio.gather
  3. Save all diagrams to MCP
  4. Return diagrams for user approval

Why diagrams BEFORE code:
  Without diagrams the Developer agent guesses architecture.
  With diagrams every URL, table, and API endpoint is pre-defined.
  Result: zero broken links, zero missing tables, consistent code.

Why Mermaid.js:
  Renders in browser with zero dependencies.
  Plain text — stored in SQLite easily.
  Used by GitHub, Notion, and most developer tools.
"""

import asyncio
import json
import logging
import re
from datetime import datetime

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════
# OUTPUT MODEL
# ════════════════════════════════════════════════════════════

class DiagramOutput(BaseModel):
    diagram_type: str
    title: str
    mermaid_syntax: str
    approved: bool = False


# ════════════════════════════════════════════════════════════
# DIAGRAM CONFIGS
# ════════════════════════════════════════════════════════════

DIAGRAM_CONFIGS = {
    "system_architecture": {
        "title": "System Architecture",
        "instructions": """Generate a system architecture diagram showing all major components.
Include: Frontend, Backend API, Database, Cache, External APIs.
Use graph TD (top-down) layout.
Example:
graph TD
    A[Browser / Next.js] -->|HTTP + SSE| B[FastAPI Backend]
    B -->|queries| C[(PostgreSQL DB)]
    B -->|cache| D[(Redis Cache)]
    B -->|calls| E[External API]""",
    },
    "database_erd": {
        "title": "Database Schema",
        "instructions": """Generate an ERD showing database tables and relationships.
Show only main tables for V1 scope.
Include primary keys, foreign keys, and key columns only.
Example:
erDiagram
    USERS {
        uuid id PK
        string email
        timestamp created_at
    }
    PROJECTS {
        uuid id PK
        uuid user_id FK
        string name
    }
    USERS ||--o{ PROJECTS : creates""",
    },
    "api_contracts": {
        "title": "API Contracts",
        "instructions": """Generate an API diagram showing all endpoints.
Show HTTP method, path, and what data goes in and out.
Use graph LR (left-right) layout.
Example:
graph LR
    A[POST /api/auth/login] -->|email, password| B[returns: token, user]
    C[GET /api/projects] -->|auth header| D[returns: project list]
    E[POST /api/projects] -->|name, idea| F[returns: project id]""",
    },
    "auth_flow": {
        "title": "Authentication Flow",
        "instructions": """Generate a sequence diagram for authentication.
Show User, Frontend, Backend, Database interactions for login and signup.
Include JWT token generation and validation steps.
Example:
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant DB as Database
    U->>F: Enter email + password
    F->>B: POST /api/auth/login
    B->>DB: Check credentials
    DB-->>B: User found
    B-->>F: JWT token
    F-->>U: Redirect to dashboard""",
    },
    "deployment_plan": {
        "title": "Deployment Architecture",
        "instructions": """Generate a deployment diagram showing hosting infrastructure.
Show where each service runs and how they connect.
Keep it simple for a solo developer deployment.
Example:
graph TD
    A[vercel.com] -->|hosts| B[Next.js Frontend]
    C[railway.app] -->|hosts| D[FastAPI Backend]
    E[supabase.com] -->|hosts| F[(PostgreSQL + Auth)]
    B -->|API calls| D
    D -->|queries| F""",
    },
}


# ════════════════════════════════════════════════════════════
# MERMAID CLEANER
# ════════════════════════════════════════════════════════════

def clean_mermaid(raw: str) -> str:
    """
    Strips markdown code blocks from Claude response.
    Returns only pure Mermaid syntax.

    ELI5: Claude sometimes wraps the diagram in backticks like a code block.
    This function removes those wrappers and returns only the diagram code.
    """
    raw = re.sub(r'```mermaid\s*', '', raw)
    raw = re.sub(r'```\s*', '', raw)
    raw = raw.strip()

    valid_starts = [
        'graph', 'flowchart', 'sequenceDiagram',
        'erDiagram', 'classDiagram', 'stateDiagram',
    ]

    if not any(raw.startswith(kw) for kw in valid_starts):
        for kw in valid_starts:
            idx = raw.find(kw)
            if idx != -1:
                raw = raw[idx:]
                break

    return raw


# ════════════════════════════════════════════════════════════
# SINGLE DIAGRAM GENERATOR
# ════════════════════════════════════════════════════════════

async def generate_single_diagram(
    diagram_type: str,
    config: dict,
    idea: str,
    v1_scope: list,
    tech_stack: list,
) -> DiagramOutput:
    """
    Generates one Mermaid.js diagram.
    Uses Sonnet — diagrams are the blueprint for all code.
    Getting them right here saves hours of debugging later.

    ELI5: The architect draws one blueprint page at a time.
    Each call draws one specific page of the blueprint.
    """
    from services.llm_client import call_strong

    prompt = f"""Generate a {config['title']} diagram for this project.

PROJECT IDEA: {idea}

V1 FEATURES:
{json.dumps(v1_scope, indent=2)}

TECH STACK:
{json.dumps(tech_stack, indent=2)}

INSTRUCTIONS:
{config['instructions']}

RULES:
- Return ONLY valid Mermaid.js syntax
- No markdown code blocks, no backticks
- No explanations outside the diagram
- Start directly with the Mermaid keyword (graph, erDiagram, sequenceDiagram)
- Focus on V1 scope only
- Maximum 15 nodes — keep it readable"""

    try:
        response = await call_strong(
            system="You are a software architect. Generate clean Mermaid.js diagrams. Return ONLY raw Mermaid syntax, no markdown.",
            user=prompt,
            max_tokens=600,
        )

        mermaid = clean_mermaid(response)
        logger.info(f"Diagram generated: {diagram_type} ({len(mermaid)} chars)")

        return DiagramOutput(
            diagram_type=diagram_type,
            title=config["title"],
            mermaid_syntax=mermaid,
            approved=False,
        )

    except Exception as e:
        logger.error(f"Diagram {diagram_type} failed: {e}")
        fallback = f"""graph TD
    A[{idea[:40]}] -->|V1| B[Core Feature]
    B --> C[Database]
    B --> D[Backend API]
    D --> E[Frontend]"""
        return DiagramOutput(
            diagram_type=diagram_type,
            title=config["title"],
            mermaid_syntax=fallback,
            approved=False,
        )


# ════════════════════════════════════════════════════════════
# BATCH GENERATOR
# ════════════════════════════════════════════════════════════

async def generate_all_diagrams(
    idea: str,
    verdict: dict,
) -> list[DiagramOutput]:
    """
    Generates all 5 diagrams in two batches.
    Batch 1: system_architecture, database_erd, api_contracts, auth_flow (parallel)
    Batch 2: deployment_plan (single)

    Why batches of 4:
    Sonnet allows ~5 concurrent calls safely.
    We use 4 to stay safe and leave room for other calls.

    ELI5: Draw 4 blueprint pages at the same time, then draw the last one.
    Faster than drawing one page at a time.
    """
    v1_scope = verdict.get("v1_scope", [])
    tech_stack = verdict.get("recommended_stack", [])

    logger.info(f"Generating 5 diagrams for: '{idea[:60]}'")
    start_time = datetime.utcnow()

    # Batch 1 — 4 diagrams in parallel
    batch_1 = await asyncio.gather(
        generate_single_diagram("system_architecture", DIAGRAM_CONFIGS["system_architecture"], idea, v1_scope, tech_stack),
        generate_single_diagram("database_erd",        DIAGRAM_CONFIGS["database_erd"],        idea, v1_scope, tech_stack),
        generate_single_diagram("api_contracts",       DIAGRAM_CONFIGS["api_contracts"],       idea, v1_scope, tech_stack),
        generate_single_diagram("auth_flow",           DIAGRAM_CONFIGS["auth_flow"],           idea, v1_scope, tech_stack),
    )

    # Batch 2 — last diagram
    deployment = await generate_single_diagram(
        "deployment_plan",
        DIAGRAM_CONFIGS["deployment_plan"],
        idea,
        v1_scope,
        tech_stack,
    )

    all_diagrams = list(batch_1) + [deployment]

    elapsed = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"All 5 diagrams generated in {elapsed:.1f}s")

    return all_diagrams


# ════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ════════════════════════════════════════════════════════════

async def run_diagrams(
    project_id: str,
    idea: str,
    verdict: dict,
) -> dict:
    """
    Main diagrams function.
    Generates all 5 diagrams and returns them for user approval.

    Args:
        project_id: the project identifier
        idea: the project idea string
        verdict: ChairmanVerdict dict from War Room

    Returns:
        dict with all diagrams ready for display and approval.
    """
    diagrams = await generate_all_diagrams(idea, verdict)

    return {
        "project_id": project_id,
        "idea": idea,
        "diagrams": [d.model_dump() for d in diagrams],
        "total": len(diagrams),
        "message": f"Generated {len(diagrams)} architecture diagrams. Review and approve each one before code is written.",
    }