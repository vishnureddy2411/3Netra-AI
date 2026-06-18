"""
backend/services/project_graph.py

Engineering Manager — builds the complete project route map.

What it does:
  Reads all approved diagrams and the Chairman verdict,
  then generates a structured JSON map of the entire application.

Why this exists:
  Developer agent builds one module at a time.
  Without a shared map it would invent URLs and duplicate components.
  With this map every module uses consistent paths and component names.

ELI5: The city planner draws all roads and assigns all addresses
before any house is built. Every builder gets the same map.
No two builders invent different names for the same street.
"""

import json
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ════════════════════════════════════════════════════════════

async def generate_project_graph(
    idea: str,
    verdict: dict,
    diagrams: list[dict],
) -> dict:
    """
    Generates the complete project graph from verdict and diagrams.

    Args:
        idea: the project idea string
        verdict: ChairmanVerdict dict from War Room
        diagrams: list of DiagramOutput dicts from Stage 4

    Returns:
        Complete project graph as a dict ready to save to MCP.
    """
    from services.llm_client import call_strong

    v1_scope = verdict.get("v1_scope", [])
    tech_stack = verdict.get("recommended_stack", [])

    # Combine all diagram syntax for context
    diagrams_text = "\n\n".join([
        f"=== {d['diagram_type'].upper()} ===\n{d['mermaid_syntax']}"
        for d in diagrams
    ])

    prompt = f"""You are a senior software architect.
Generate a complete project graph for this application.

PROJECT IDEA: {idea}

V1 FEATURES:
{json.dumps(v1_scope, indent=2)}

TECH STACK:
{json.dumps(tech_stack, indent=2)}

ARCHITECTURE DIAGRAMS:
{diagrams_text[:6000]}

Generate a project graph in this EXACT JSON format:
{{
    "pages": [
        {{
            "name": "page display name",
            "path": "/exact-url-path",
            "description": "what this page does",
            "navigates_to": ["/path1", "/path2"],
            "api_calls": ["GET /api/endpoint", "POST /api/endpoint"],
            "components": ["ComponentName1", "ComponentName2"],
            "auth_required": true
        }}
    ],
    "shared_components": [
        {{
            "name": "ComponentName",
            "description": "what this component does",
            "used_by": ["PageName1", "PageName2"]
        }}
    ],
    "api_routes": [
        {{
            "method": "GET",
            "path": "/api/endpoint",
            "description": "what this endpoint does",
            "auth_required": true
        }}
    ],
    "navigation_structure": {{
        "public_routes": ["/login", "/signup"],
        "protected_routes": ["/dashboard"],
        "default_redirect_after_login": "/dashboard"
    }}
}}

RULES:
- Every URL must start with /
- API routes must start with /api/
- Include only V1 features
- Maximum 8 pages
- Maximum 10 shared components
- Be specific — use real names from the diagrams
- Return ONLY valid JSON, no markdown, no backticks"""

    try:
        response = await call_strong(
            system="You are a precise software architect. Return ONLY valid JSON. No markdown, no backticks, no explanations.",
            user=prompt,
            max_tokens=1500,
        )

        # Clean response — remove any markdown
        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*', '', cleaned)
        cleaned = cleaned.strip()

        # Find JSON object
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            graph = json.loads(json_match.group())
            logger.info(
                f"Project graph generated: "
                f"{len(graph.get('pages', []))} pages, "
                f"{len(graph.get('shared_components', []))} components, "
                f"{len(graph.get('api_routes', []))} API routes"
            )
            return graph

        logger.error("Could not parse project graph JSON")
        return _fallback_graph(idea, v1_scope)

    except Exception as e:
        logger.error(f"Project graph generation failed: {e}")
        return _fallback_graph(idea, v1_scope)


def _fallback_graph(idea: str, v1_scope: list) -> dict:
    """
    Returns a basic project graph if generation fails.
    Ensures the Developer agent always has something to work with.
    """
    return {
        "pages": [
            {
                "name": "Landing Page",
                "path": "/",
                "description": "Product landing page",
                "navigates_to": ["/login", "/signup"],
                "api_calls": [],
                "components": ["Navbar", "HeroSection", "Footer"],
                "auth_required": False,
            },
            {
                "name": "Login",
                "path": "/login",
                "description": "User login page",
                "navigates_to": ["/dashboard"],
                "api_calls": ["POST /api/auth/login"],
                "components": ["AuthForm"],
                "auth_required": False,
            },
            {
                "name": "Dashboard",
                "path": "/dashboard",
                "description": "Main user dashboard",
                "navigates_to": ["/projects"],
                "api_calls": ["GET /api/projects"],
                "components": ["Navbar", "ProjectList", "AuthGuard"],
                "auth_required": True,
            },
        ],
        "shared_components": [
            {"name": "Navbar", "description": "Top navigation bar", "used_by": ["Landing Page", "Dashboard"]},
            {"name": "AuthGuard", "description": "Protects authenticated routes", "used_by": ["Dashboard"]},
            {"name": "Button", "description": "Reusable button component", "used_by": ["Landing Page", "Login", "Dashboard"]},
        ],
        "api_routes": [
            {"method": "POST", "path": "/api/auth/login", "description": "User login", "auth_required": False},
            {"method": "GET", "path": "/api/projects", "description": "List user projects", "auth_required": True},
        ],
        "navigation_structure": {
            "public_routes": ["/", "/login", "/signup"],
            "protected_routes": ["/dashboard"],
            "default_redirect_after_login": "/dashboard",
        },
    }


async def run_project_graph(
    project_id: str,
    idea: str,
    verdict: dict,
    diagrams: list[dict],
) -> dict:
    """
    Main project graph function.
    Generates the graph and returns it ready to save to MCP.
    """
    logger.info(f"Project graph started for: '{idea[:60]}'")
    start_time = datetime.utcnow()

    graph = await generate_project_graph(idea, verdict, diagrams)

    elapsed = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"Project graph completed in {elapsed:.1f}s")

    return {
        "project_id": project_id,
        "idea": idea,
        "graph": graph,
        "elapsed_seconds": round(elapsed, 1),
        "summary": {
            "total_pages": len(graph.get("pages", [])),
            "total_components": len(graph.get("shared_components", [])),
            "total_api_routes": len(graph.get("api_routes", [])),
        },
        "message": (
            f"Project graph complete. "
            f"{len(graph.get('pages', []))} pages, "
            f"{len(graph.get('shared_components', []))} components, "
            f"{len(graph.get('api_routes', []))} API routes. "
            f"All navigation pre-wired."
        ),
    }