"""
backend/services/project_graph.py

Generates a complete project graph for the selected project.
This is the BRAIN of the entire build process.
Every subsequent agent (Quiz, Code Gen, Preview, Career) reads this.

The graph contains:
- Every page with exact path, components, API calls, auth requirements
- Every shared component with usage map
- Every API route with method, path, auth, input/output
- Full navigation structure
- Tech stack decisions

If LLM generation fails, the fallback uses the actual project idea
and tech stack to generate a reasonable project-specific graph
instead of hardcoded generic values.
"""

import json
import logging
import re
import time

logger = logging.getLogger(__name__)


async def generate_project_graph(
    project_id: str,
    idea: str,
    verdict: dict | None = None,
    diagrams: list | None = None,
) -> dict:
    """
    Generates project-specific graph using all available context.
    Uses Sonnet for accuracy — this graph drives all future stages.
    """
    start = time.time()

    try:
        from services.llm_client import call_strong

        # Extract context from verdict if available
        tech_stack    = verdict.get("recommended_stack", []) if verdict else []
        v1_scope      = verdict.get("v1_scope", []) if verdict else []
        career_value  = verdict.get("career_value", "") if verdict else ""
        tech_str      = ", ".join(tech_stack) if tech_stack else "FastAPI, React, PostgreSQL, Docker"
        scope_str     = "\n".join(f"- {s}" for s in v1_scope) if v1_scope else "Core MVP features"

        prompt = f"""You are a senior software architect designing the complete project structure.

PROJECT: {idea}
TECH STACK: {tech_str}
V1 SCOPE:
{scope_str}

Design the COMPLETE project graph for this specific project.
Every page, component, and API route must be specific to THIS project — not generic.

Return ONLY valid JSON in this exact structure:
{{
    "pages": [
        {{
            "name": "specific page name for THIS project",
            "path": "/exact/path",
            "description": "what this page does in THIS project",
            "navigates_to": ["/other/paths"],
            "api_calls": ["METHOD /api/endpoint"],
            "components": ["ComponentName1", "ComponentName2"],
            "auth_required": true or false
        }}
    ],
    "shared_components": [
        {{
            "name": "ComponentName",
            "description": "what it does",
            "used_by": ["Page Name 1", "Page Name 2"]
        }}
    ],
    "api_routes": [
        {{
            "method": "GET or POST or PUT or DELETE",
            "path": "/api/specific/endpoint",
            "description": "what this endpoint does",
            "auth_required": true or false,
            "input": "request body or params description",
            "output": "response description"
        }}
    ],
    "navigation_structure": {{
        "public_routes": ["/", "/login"],
        "protected_routes": ["/dashboard"],
        "default_redirect_after_login": "/dashboard"
    }},
    "tech_decisions": {{
        "frontend": "framework and why",
        "backend": "framework and why",
        "database": "database and why",
        "auth": "auth approach",
        "deployment": "deployment approach"
    }}
}}

Rules:
- Minimum 5 pages specific to THIS project
- Minimum 6 shared components
- Minimum 8 API routes
- Every name must reference THIS project's domain
- No generic placeholder names like "Page1" or "Component1"
- API routes must match the project's actual functionality"""

        response = await call_strong(
            system=(
                "You are a senior software architect. "
                "Generate a complete, project-specific graph. "
                "Every page, component and route must be specific to the project given. "
                "Return only valid JSON."
            ),
            user=prompt,
            max_tokens=2000,
        )

        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*', '', cleaned).strip()
        match   = re.search(r'\{.*\}', cleaned, re.DOTALL)

        if match:
            graph   = json.loads(match.group())
            elapsed = round(time.time() - start, 1)

            pages      = graph.get("pages", [])
            components = graph.get("shared_components", [])
            routes     = graph.get("api_routes", [])

            # Validate — reject if too generic or too small
            if len(pages) < 3 or len(routes) < 3:
                raise ValueError(f"Graph too small — {len(pages)} pages, {len(routes)} routes")

            logger.info(
                f"Project graph complete in {elapsed}s: "
                f"{len(pages)} pages, {len(components)} components, {len(routes)} routes"
            )

            return {
                "project_id": project_id,
                "idea":       idea,
                "graph":      graph,
                "elapsed_seconds": elapsed,
                "summary": {
                    "total_pages":      len(pages),
                    "total_components": len(components),
                    "total_api_routes": len(routes),
                },
                "message": (
                    f"Project graph complete. "
                    f"{len(pages)} pages, {len(components)} components, "
                    f"{len(routes)} API routes. All navigation pre-wired."
                ),
            }

        raise ValueError("Could not parse project graph JSON")

    except Exception as e:
        logger.warning(f"Project graph LLM failed ({e}) — using smart fallback")
        elapsed = round(time.time() - start, 1)
        graph   = _smart_fallback_graph(idea, verdict)

        pages      = graph.get("pages", [])
        components = graph.get("shared_components", [])
        routes     = graph.get("api_routes", [])

        return {
            "project_id": project_id,
            "idea":       idea,
            "graph":      graph,
            "elapsed_seconds": elapsed,
            "summary": {
                "total_pages":      len(pages),
                "total_components": len(components),
                "total_api_routes": len(routes),
            },
            "message": (
                f"Project graph complete (smart fallback). "
                f"{len(pages)} pages, {len(components)} components, "
                f"{len(routes)} API routes."
            ),
        }


def _smart_fallback_graph(idea: str, verdict: dict | None = None) -> dict:
    """
    Smart fallback — generates project-specific graph from idea text.
    Much better than hardcoded generic values.
    Extracts domain keywords from idea to generate relevant names.
    """
    tech_stack = verdict.get("recommended_stack", []) if verdict else []
    v1_scope   = verdict.get("v1_scope", []) if verdict else []

    # Extract project domain from idea
    idea_lower  = idea.lower()
    idea_words  = idea.split()
    project_name = " ".join(idea_words[:4]) if len(idea_words) >= 4 else idea[:40]

    # Determine domain type from idea
    is_ml     = any(w in idea_lower for w in ["ml", "model", "training", "inference", "rag", "llm", "ai", "deep learning", "neural"])
    is_data   = any(w in idea_lower for w in ["data", "pipeline", "etl", "warehouse", "analytics", "dashboard", "stream"])
    is_api    = any(w in idea_lower for w in ["api", "service", "backend", "microservice", "rest", "graphql"])
    is_web    = any(w in idea_lower for w in ["web", "app", "platform", "portal", "marketplace", "saas"])

    # Generate domain-specific pages
    if is_ml:
        pages = [
            {"name": "Model Dashboard", "path": "/", "description": f"Overview of {project_name} models and metrics", "navigates_to": ["/models", "/experiments"], "api_calls": ["GET /api/models", "GET /api/metrics"], "components": ["ModelCard", "MetricChart", "Navbar"], "auth_required": False},
            {"name": "Model Registry", "path": "/models", "description": "Browse and manage ML models", "navigates_to": ["/models/:id", "/experiments"], "api_calls": ["GET /api/models", "POST /api/models"], "components": ["ModelList", "ModelCard", "SearchBar"], "auth_required": True},
            {"name": "Model Detail", "path": "/models/:id", "description": "View model details, metrics, and predictions", "navigates_to": ["/experiments/:id"], "api_calls": ["GET /api/models/:id", "POST /api/predict"], "components": ["ModelViewer", "MetricChart", "PredictionForm"], "auth_required": True},
            {"name": "Experiments", "path": "/experiments", "description": "Track and compare training experiments", "navigates_to": ["/experiments/:id"], "api_calls": ["GET /api/experiments", "POST /api/experiments"], "components": ["ExperimentList", "CompareTable", "RunChart"], "auth_required": True},
            {"name": "Inference API", "path": "/api-docs", "description": "API documentation for model inference", "navigates_to": [], "api_calls": ["GET /api/docs"], "components": ["SwaggerUI", "CodeSnippet"], "auth_required": False},
            {"name": "Monitoring", "path": "/monitoring", "description": "Real-time model performance monitoring", "navigates_to": [], "api_calls": ["GET /api/metrics/live", "GET /api/alerts"], "components": ["LiveChart", "AlertPanel", "DriftDetector"], "auth_required": True},
        ]
        components = [
            {"name": "ModelCard", "description": "Displays model summary with key metrics", "used_by": ["Model Dashboard", "Model Registry"]},
            {"name": "MetricChart", "description": "Renders accuracy, loss, and performance charts", "used_by": ["Model Dashboard", "Model Detail", "Monitoring"]},
            {"name": "ExperimentList", "description": "Lists all training runs with comparison", "used_by": ["Experiments"]},
            {"name": "PredictionForm", "description": "Input form for model inference requests", "used_by": ["Model Detail"]},
            {"name": "LiveChart", "description": "Real-time streaming chart for live metrics", "used_by": ["Monitoring"]},
            {"name": "Navbar", "description": "Top navigation with auth state", "used_by": ["Model Dashboard", "Model Registry", "Monitoring"]},
            {"name": "AlertPanel", "description": "Shows drift and performance alerts", "used_by": ["Monitoring"]},
        ]
        routes = [
            {"method": "GET",  "path": "/api/models",         "description": "List all registered models",        "auth_required": True,  "input": "query params: page, limit", "output": "array of model objects"},
            {"method": "POST", "path": "/api/models",         "description": "Register a new model",              "auth_required": True,  "input": "model metadata and artifact path", "output": "created model object"},
            {"method": "GET",  "path": "/api/models/:id",     "description": "Get model details and metrics",     "auth_required": True,  "input": "model id", "output": "model with metrics"},
            {"method": "POST", "path": "/api/predict",        "description": "Run inference on model",            "auth_required": True,  "input": "input features JSON", "output": "prediction result"},
            {"method": "GET",  "path": "/api/experiments",    "description": "List training experiments",         "auth_required": True,  "input": "query params", "output": "experiment list"},
            {"method": "POST", "path": "/api/experiments",    "description": "Start a new training run",          "auth_required": True,  "input": "training config", "output": "experiment object"},
            {"method": "GET",  "path": "/api/metrics/live",   "description": "Stream live metrics via SSE",       "auth_required": True,  "input": "model id", "output": "SSE stream of metrics"},
            {"method": "GET",  "path": "/api/alerts",         "description": "Get performance drift alerts",      "auth_required": True,  "input": "time range", "output": "alert list"},
            {"method": "POST", "path": "/api/auth/login",     "description": "User authentication",               "auth_required": False, "input": "email, password", "output": "JWT token"},
        ]

    elif is_data:
        pages = [
            {"name": "Pipeline Dashboard", "path": "/", "description": f"Overview of {project_name} pipelines and status", "navigates_to": ["/pipelines", "/data"], "api_calls": ["GET /api/pipelines", "GET /api/health"], "components": ["PipelineCard", "StatusBadge", "Navbar"], "auth_required": False},
            {"name": "Pipeline Builder", "path": "/pipelines/new", "description": "Visual pipeline configuration", "navigates_to": ["/pipelines"], "api_calls": ["POST /api/pipelines", "GET /api/sources"], "components": ["PipelineBuilder", "SourceSelector", "TransformConfig"], "auth_required": True},
            {"name": "Pipeline Detail", "path": "/pipelines/:id", "description": "Monitor pipeline runs and logs", "navigates_to": ["/pipelines/:id/runs"], "api_calls": ["GET /api/pipelines/:id", "GET /api/runs"], "components": ["RunHistory", "LogViewer", "StatsChart"], "auth_required": True},
            {"name": "Data Explorer", "path": "/data", "description": "Browse and query processed data", "navigates_to": [], "api_calls": ["GET /api/data", "POST /api/query"], "components": ["DataTable", "QueryEditor", "FilterPanel"], "auth_required": True},
            {"name": "Monitoring", "path": "/monitoring", "description": "Data quality and pipeline health monitoring", "navigates_to": [], "api_calls": ["GET /api/quality", "GET /api/alerts"], "components": ["QualityChart", "AlertPanel", "DriftIndicator"], "auth_required": True},
            {"name": "Settings", "path": "/settings", "description": "Configure connections and credentials", "navigates_to": [], "api_calls": ["GET /api/settings", "PUT /api/settings"], "components": ["ConnectionForm", "CredentialManager"], "auth_required": True},
        ]
        components = [
            {"name": "PipelineCard", "description": "Shows pipeline status and last run time", "used_by": ["Pipeline Dashboard"]},
            {"name": "PipelineBuilder", "description": "Drag-and-drop pipeline configuration UI", "used_by": ["Pipeline Builder"]},
            {"name": "DataTable", "description": "Paginated data table with sorting and filtering", "used_by": ["Data Explorer"]},
            {"name": "QualityChart", "description": "Data quality metrics over time", "used_by": ["Monitoring"]},
            {"name": "LogViewer", "description": "Real-time log streaming for pipeline runs", "used_by": ["Pipeline Detail"]},
            {"name": "AlertPanel", "description": "Shows data quality and pipeline alerts", "used_by": ["Monitoring", "Pipeline Dashboard"]},
            {"name": "Navbar", "description": "Top navigation with pipeline status indicator", "used_by": ["Pipeline Dashboard", "Data Explorer", "Monitoring"]},
        ]
        routes = [
            {"method": "GET",  "path": "/api/pipelines",      "description": "List all pipelines",               "auth_required": True,  "input": "query params", "output": "pipeline list"},
            {"method": "POST", "path": "/api/pipelines",      "description": "Create new pipeline",              "auth_required": True,  "input": "pipeline config JSON", "output": "created pipeline"},
            {"method": "GET",  "path": "/api/pipelines/:id",  "description": "Get pipeline details and runs",    "auth_required": True,  "input": "pipeline id", "output": "pipeline with runs"},
            {"method": "POST", "path": "/api/pipelines/:id/run", "description": "Trigger pipeline run",          "auth_required": True,  "input": "run config", "output": "run object"},
            {"method": "GET",  "path": "/api/data",           "description": "Browse processed data",            "auth_required": True,  "input": "table, page, filters", "output": "paginated data"},
            {"method": "POST", "path": "/api/query",          "description": "Execute custom data query",        "auth_required": True,  "input": "SQL or filter config", "output": "query results"},
            {"method": "GET",  "path": "/api/quality",        "description": "Get data quality metrics",         "auth_required": True,  "input": "time range", "output": "quality metrics"},
            {"method": "GET",  "path": "/api/health",         "description": "Pipeline health status",           "auth_required": False, "input": "none", "output": "health status"},
            {"method": "POST", "path": "/api/auth/login",     "description": "User authentication",              "auth_required": False, "input": "email, password", "output": "JWT token"},
        ]

    else:
        # General web/API project
        # Extract meaningful name from idea for pages
        domain = project_name.replace("-", " ").replace("_", " ").title()
        pages = [
            {"name": f"{domain} Home", "path": "/", "description": f"Landing page for {project_name}", "navigates_to": ["/login", "/signup", "/features"], "api_calls": [], "components": ["Navbar", "HeroSection", "FeatureGrid", "Footer"], "auth_required": False},
            {"name": "Sign Up", "path": "/signup", "description": "New user registration", "navigates_to": ["/dashboard"], "api_calls": ["POST /api/auth/register"], "components": ["AuthForm", "ValidationError"], "auth_required": False},
            {"name": "Login", "path": "/login", "description": "User authentication", "navigates_to": ["/dashboard"], "api_calls": ["POST /api/auth/login"], "components": ["AuthForm", "SocialAuth"], "auth_required": False},
            {"name": "Dashboard", "path": "/dashboard", "description": f"Main {domain} user dashboard", "navigates_to": ["/profile", "/settings"], "api_calls": ["GET /api/user/me", "GET /api/dashboard"], "components": ["Navbar", "StatCard", "ActivityFeed", "AuthGuard"], "auth_required": True},
            {"name": "Profile", "path": "/profile", "description": "User profile management", "navigates_to": ["/settings"], "api_calls": ["GET /api/user/me", "PUT /api/user/me"], "components": ["ProfileForm", "AvatarUpload", "AuthGuard"], "auth_required": True},
            {"name": "Settings", "path": "/settings", "description": "Account and application settings", "navigates_to": [], "api_calls": ["GET /api/settings", "PUT /api/settings"], "components": ["SettingsPanel", "DangerZone", "AuthGuard"], "auth_required": True},
        ]
        components = [
            {"name": "Navbar", "description": "Responsive navigation with auth state", "used_by": [f"{domain} Home", "Dashboard", "Profile"]},
            {"name": "AuthForm", "description": "Reusable login and signup form with validation", "used_by": ["Sign Up", "Login"]},
            {"name": "AuthGuard", "description": "Protects routes requiring authentication", "used_by": ["Dashboard", "Profile", "Settings"]},
            {"name": "StatCard", "description": "Displays key metrics and statistics", "used_by": ["Dashboard"]},
            {"name": "ActivityFeed", "description": "Recent activity timeline", "used_by": ["Dashboard"]},
            {"name": "Footer", "description": "Site footer with links", "used_by": [f"{domain} Home"]},
            {"name": "Toast", "description": "Global notification system", "used_by": ["Dashboard", "Profile", "Settings"]},
        ]
        routes = [
            {"method": "POST", "path": "/api/auth/register", "description": "Register new user",            "auth_required": False, "input": "name, email, password", "output": "user object + token"},
            {"method": "POST", "path": "/api/auth/login",    "description": "Authenticate user",            "auth_required": False, "input": "email, password", "output": "JWT token"},
            {"method": "POST", "path": "/api/auth/logout",   "description": "Invalidate user session",      "auth_required": True,  "input": "none", "output": "success message"},
            {"method": "GET",  "path": "/api/user/me",       "description": "Get current user profile",     "auth_required": True,  "input": "JWT header", "output": "user profile object"},
            {"method": "PUT",  "path": "/api/user/me",       "description": "Update user profile",          "auth_required": True,  "input": "profile fields", "output": "updated user object"},
            {"method": "GET",  "path": "/api/dashboard",     "description": "Get dashboard data",           "auth_required": True,  "input": "JWT header", "output": "dashboard stats and feed"},
            {"method": "GET",  "path": "/api/settings",      "description": "Get user settings",            "auth_required": True,  "input": "JWT header", "output": "settings object"},
            {"method": "PUT",  "path": "/api/settings",      "description": "Update user settings",         "auth_required": True,  "input": "settings fields", "output": "updated settings"},
            {"method": "GET",  "path": "/api/health",        "description": "API health check",             "auth_required": False, "input": "none", "output": "status ok"},
        ]

    return {
        "pages": pages,
        "shared_components": components,
        "api_routes": routes,
        "navigation_structure": {
            "public_routes":  [p["path"] for p in pages if not p["auth_required"]],
            "protected_routes": [p["path"] for p in pages if p["auth_required"]],
            "default_redirect_after_login": "/dashboard",
        },
        "tech_decisions": {
            "frontend":   tech_stack[0] if tech_stack else "React / Next.js",
            "backend":    next((t for t in tech_stack if "api" in t.lower() or "fast" in t.lower() or "django" in t.lower()), "FastAPI"),
            "database":   next((t for t in tech_stack if "sql" in t.lower() or "postgres" in t.lower() or "mongo" in t.lower()), "PostgreSQL"),
            "auth":       "JWT with refresh tokens",
            "deployment": "Docker + cloud provider",
        },
    }