"""
backend/services/project_graph.py

Project Graph Generator — The Brain of 3Netra-AI

This graph is the source of truth for ALL future stages.
Every agent in every stage reads from this graph.
It grows and updates as code is generated.

Generation strategy:
1. Try LLM with full context (verdict + diagrams + scope)
2. If JSON malformed: repair truncation
3. If repair fails: smart domain-specific fallback
4. Store full graph in project_artifacts for all future agents
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
    start = time.time()

    try:
        from services.llm_client import call_strong

        tech_stack   = verdict.get("recommended_stack", []) if verdict else []
        v1_scope     = verdict.get("v1_scope", []) if verdict else []
        career_value = verdict.get("career_value", "") if verdict else ""
        tech_str     = ", ".join(tech_stack) if tech_stack else "FastAPI, React, PostgreSQL, Docker"
        scope_str    = "\n".join(f"- {s}" for s in v1_scope) if v1_scope else "Core MVP features"

        prompt = f"""You are a senior software architect. Generate the COMPLETE project graph.

PROJECT: {idea}
TECH STACK: {tech_str}
V1 SCOPE:
{scope_str}
CAREER VALUE: {career_value}

Every page, component, and API route must be SPECIFIC to THIS project.
No generic names. No placeholders. Real names from the project domain.

Return ONLY valid JSON — no markdown, no explanation, just the JSON object:
{{
    "pages": [
        {{
            "name": "specific page name",
            "path": "/exact/path",
            "description": "what this page does in THIS project",
            "navigates_to": ["/other/paths"],
            "api_calls": ["METHOD /api/endpoint"],
            "components": ["ComponentName1", "ComponentName2"],
            "auth_required": true
        }}
    ],
    "shared_components": [
        {{
            "name": "ComponentName",
            "description": "specific purpose in this project",
            "used_by": ["Page Name 1", "Page Name 2"],
            "props": ["key prop 1", "key prop 2"]
        }}
    ],
    "api_routes": [
        {{
            "method": "GET",
            "path": "/api/specific/endpoint",
            "description": "what this endpoint does",
            "auth_required": true,
            "input": "request description",
            "output": "response description",
            "used_by_pages": ["Page Name"]
        }}
    ],
    "navigation_structure": {{
        "public_routes": ["/", "/login"],
        "protected_routes": ["/dashboard"],
        "default_redirect_after_login": "/dashboard",
        "nav_groups": [
            {{"label": "Main", "routes": ["/dashboard", "/data"]}}
        ]
    }},
    "tech_decisions": {{
        "frontend": "framework and specific reason for THIS project",
        "backend": "framework and specific reason",
        "database": "database and why it fits THIS project's data model",
        "auth": "auth approach and why",
        "deployment": "deployment strategy",
        "key_libraries": ["library1 — purpose", "library2 — purpose"]
    }},
    "data_models": [
        {{
            "name": "ModelName",
            "table": "table_name",
            "key_fields": ["field1: type", "field2: type"],
            "relationships": ["belongs to ModelX", "has many ModelY"]
        }}
    ]
}}

REQUIREMENTS:
- Minimum 5 pages specific to THIS project domain
- Minimum 6 shared components with real names
- Minimum 8 API routes matching actual functionality
- Data models for every major entity in the project
- Every name must reference THIS project's specific domain
- CRITICAL: Return complete valid JSON — close ALL brackets and braces"""

        response = await call_strong(
            system=(
                "You are a senior software architect generating a project graph. "
                "Return ONLY valid JSON. No markdown. No explanation. "
                "CRITICAL: Your JSON must be 100% complete and valid. "
                "Never truncate. Close every bracket and brace before ending."
            ),
            user=prompt,
            max_tokens=4000,
        )

        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*',     '', cleaned).strip()
        match   = re.search(r'\{.*\}',  cleaned, re.DOTALL)

        if match:
            raw = match.group()

            # Repair JSON truncation
            open_braces   = raw.count('{') - raw.count('}')
            open_brackets = raw.count('[') - raw.count(']')

            if open_braces > 0 or open_brackets > 0:
                logger.warning(
                    f"JSON truncated — repairing {open_braces} unclosed braces, "
                    f"{open_brackets} unclosed brackets"
                )
                raw = raw.rstrip(',\n\r\t ')
                raw += ']' * open_brackets
                raw += '}' * open_braces

            graph   = json.loads(raw)
            elapsed = round(time.time() - start, 1)

            pages      = graph.get("pages", [])
            components = graph.get("shared_components", [])
            routes     = graph.get("api_routes", [])
            models     = graph.get("data_models", [])

            if len(pages) < 3 or len(routes) < 3:
                raise ValueError(f"Graph too small: {len(pages)} pages, {len(routes)} routes")

            logger.info(
                f"Project graph generated in {elapsed}s: "
                f"{len(pages)} pages, {len(components)} components, "
                f"{len(routes)} routes, {len(models)} data models"
            )

            return _build_result(project_id, idea, graph, elapsed)

        raise ValueError("Could not extract JSON from LLM response")

    except Exception as e:
        logger.error(f"Project graph LLM FAILED — {type(e).__name__}: {e}")
        elapsed = round(time.time() - start, 1)
        graph   = _smart_fallback_graph(idea, verdict)
        logger.warning(f"Using smart fallback — {len(graph.get('pages', []))} pages generated")
        return _build_result(project_id, idea, graph, elapsed, fallback=True)


def _build_result(project_id, idea, graph, elapsed, fallback=False):
    pages      = graph.get("pages", [])
    components = graph.get("shared_components", [])
    routes     = graph.get("api_routes", [])
    models     = graph.get("data_models", [])

    return {
        "project_id": project_id,
        "idea":       idea,
        "graph":      graph,
        "fallback":   fallback,
        "elapsed_seconds": elapsed,
        "summary": {
            "total_pages":       len(pages),
            "total_components":  len(components),
            "total_api_routes":  len(routes),
            "total_data_models": len(models),
        },
        "message": (
            f"Project graph {'(fallback) ' if fallback else ''}complete in {elapsed}s. "
            f"{len(pages)} pages, {len(components)} components, "
            f"{len(routes)} API routes, {len(models)} data models. "
            f"All navigation pre-wired."
        ),
    }


def _smart_fallback_graph(idea: str, verdict: dict | None = None) -> dict:
    tech_stack = verdict.get("recommended_stack", []) if verdict else []
    idea_lower = idea.lower()

    is_ml   = any(w in idea_lower for w in ["ml", "model", "training", "inference", "rag", "llm", "ai", "neural", "recommendation", "classify"])
    is_data = any(w in idea_lower for w in ["data", "pipeline", "etl", "warehouse", "analytics", "dashboard", "stream", "kafka", "spark"])

    if is_ml:
        pages = [
            {"name": "Model Dashboard",  "path": "/",             "description": "Overview of models and performance metrics", "navigates_to": ["/models", "/experiments"], "api_calls": ["GET /api/models", "GET /api/metrics"], "components": ["ModelCard", "MetricChart", "Navbar"], "auth_required": False},
            {"name": "Model Registry",   "path": "/models",       "description": "Browse, version, and manage ML models",      "navigates_to": ["/models/:id"],             "api_calls": ["GET /api/models", "POST /api/models"], "components": ["ModelList", "ModelCard", "VersionBadge"], "auth_required": True},
            {"name": "Model Detail",     "path": "/models/:id",   "description": "Model details, metrics, and inference",      "navigates_to": ["/experiments"],            "api_calls": ["GET /api/models/:id", "POST /api/predict"], "components": ["ModelViewer", "MetricChart", "PredictionForm"], "auth_required": True},
            {"name": "Experiments",      "path": "/experiments",  "description": "Track and compare training runs",             "navigates_to": ["/experiments/:id"],        "api_calls": ["GET /api/experiments", "POST /api/experiments"], "components": ["ExperimentList", "RunChart", "CompareTable"], "auth_required": True},
            {"name": "Live Monitoring",  "path": "/monitoring",   "description": "Real-time model performance and drift alerts","navigates_to": [],                          "api_calls": ["GET /api/metrics/live", "GET /api/alerts"], "components": ["LiveChart", "AlertPanel", "DriftDetector"], "auth_required": True},
            {"name": "API Playground",   "path": "/playground",   "description": "Test model inference interactively",          "navigates_to": [],                          "api_calls": ["POST /api/predict"],                          "components": ["InputBuilder", "ResponseViewer", "CodeSnippet"], "auth_required": False},
        ]
        components = [
            {"name": "ModelCard",       "description": "Model summary with accuracy, latency, version",        "used_by": ["Model Dashboard", "Model Registry"], "props": ["model", "onSelect"]},
            {"name": "MetricChart",     "description": "Time-series chart for accuracy, loss, F1",             "used_by": ["Model Dashboard", "Model Detail", "Live Monitoring"], "props": ["data", "metric", "timeRange"]},
            {"name": "PredictionForm",  "description": "Input builder for model inference requests",           "used_by": ["Model Detail", "API Playground"], "props": ["schema", "onPredict"]},
            {"name": "ExperimentList",  "description": "Sortable list of training runs with metrics",          "used_by": ["Experiments"], "props": ["experiments", "onCompare"]},
            {"name": "LiveChart",       "description": "WebSocket-powered real-time metrics visualization",    "used_by": ["Live Monitoring"], "props": ["modelId", "metric"]},
            {"name": "AlertPanel",      "description": "Drift and performance degradation alerts",             "used_by": ["Live Monitoring", "Model Dashboard"], "props": ["alerts", "onAcknowledge"]},
            {"name": "Navbar",          "description": "Navigation with model status indicator",               "used_by": ["Model Dashboard", "Model Registry", "Experiments", "Live Monitoring"], "props": ["user", "activeModel"]},
        ]
        routes = [
            {"method": "GET",  "path": "/api/models",           "description": "List all registered models with metadata",  "auth_required": True,  "input": "?page&limit&status", "output": "paginated model list", "used_by_pages": ["Model Registry"]},
            {"method": "POST", "path": "/api/models",           "description": "Register a new model version",              "auth_required": True,  "input": "model metadata + artifact path", "output": "created model", "used_by_pages": ["Model Registry"]},
            {"method": "GET",  "path": "/api/models/:id",       "description": "Get model with full metrics history",       "auth_required": True,  "input": "model id", "output": "model + metrics", "used_by_pages": ["Model Detail"]},
            {"method": "POST", "path": "/api/predict",          "description": "Run inference — returns prediction + confidence", "auth_required": True,  "input": "feature JSON", "output": "prediction result", "used_by_pages": ["Model Detail", "API Playground"]},
            {"method": "GET",  "path": "/api/experiments",      "description": "List training experiments with metrics",    "auth_required": True,  "input": "?model_id&status", "output": "experiment list", "used_by_pages": ["Experiments"]},
            {"method": "POST", "path": "/api/experiments",      "description": "Create and start a training run",           "auth_required": True,  "input": "training config JSON", "output": "experiment + run_id", "used_by_pages": ["Experiments"]},
            {"method": "GET",  "path": "/api/metrics/live",     "description": "Server-sent events stream of live metrics", "auth_required": True,  "input": "?model_id", "output": "SSE stream", "used_by_pages": ["Live Monitoring"]},
            {"method": "GET",  "path": "/api/alerts",           "description": "Get drift and performance alerts",          "auth_required": True,  "input": "?model_id&severity", "output": "alert list", "used_by_pages": ["Live Monitoring"]},
            {"method": "POST", "path": "/api/auth/login",       "description": "Authenticate user",                        "auth_required": False, "input": "email, password", "output": "JWT token", "used_by_pages": []},
        ]
        models = [
            {"name": "Model",      "table": "models",       "key_fields": ["id: uuid", "name: str", "version: str", "artifact_path: str", "accuracy: float"], "relationships": ["has many Experiments", "has many Predictions"]},
            {"name": "Experiment", "table": "experiments",  "key_fields": ["id: uuid", "model_id: uuid", "config: json", "status: str", "started_at: datetime"], "relationships": ["belongs to Model", "has many Runs"]},
            {"name": "Prediction", "table": "predictions",  "key_fields": ["id: uuid", "model_id: uuid", "input: json", "output: json", "latency_ms: int"], "relationships": ["belongs to Model"]},
            {"name": "Alert",      "table": "alerts",       "key_fields": ["id: uuid", "model_id: uuid", "type: str", "severity: str", "acknowledged: bool"], "relationships": ["belongs to Model"]},
        ]

    elif is_data:
        pages = [
            {"name": "Pipeline Dashboard", "path": "/",                   "description": "Overview of all pipelines and run status",       "navigates_to": ["/pipelines", "/data"],  "api_calls": ["GET /api/pipelines", "GET /api/health"], "components": ["PipelineCard", "StatusBadge", "Navbar"], "auth_required": False},
            {"name": "Pipeline Builder",   "path": "/pipelines/new",      "description": "Visual pipeline configuration and scheduling",    "navigates_to": ["/pipelines"],           "api_calls": ["POST /api/pipelines", "GET /api/sources"], "components": ["PipelineBuilder", "SourceSelector", "TransformConfig"], "auth_required": True},
            {"name": "Pipeline Detail",    "path": "/pipelines/:id",      "description": "Monitor runs, logs, and lineage for a pipeline",  "navigates_to": ["/pipelines/:id/runs"],  "api_calls": ["GET /api/pipelines/:id", "GET /api/runs"], "components": ["RunHistory", "LogViewer", "LineageGraph"], "auth_required": True},
            {"name": "Data Explorer",      "path": "/data",               "description": "Browse, query, and preview processed datasets",   "navigates_to": [],                       "api_calls": ["GET /api/data", "POST /api/query"], "components": ["DataTable", "QueryEditor", "FilterPanel"], "auth_required": True},
            {"name": "Quality Monitor",    "path": "/quality",            "description": "Data quality metrics, anomaly detection, alerts", "navigates_to": [],                       "api_calls": ["GET /api/quality", "GET /api/anomalies"], "components": ["QualityChart", "AnomalyTable", "AlertPanel"], "auth_required": True},
            {"name": "Settings",           "path": "/settings",           "description": "Configure data sources, credentials, schedules",  "navigates_to": [],                       "api_calls": ["GET /api/settings", "PUT /api/settings"], "components": ["ConnectionForm", "ScheduleConfig"], "auth_required": True},
        ]
        components = [
            {"name": "PipelineCard",    "description": "Pipeline summary with last run status and schedule",       "used_by": ["Pipeline Dashboard"], "props": ["pipeline", "onEdit", "onRun"]},
            {"name": "PipelineBuilder", "description": "Drag-and-drop visual pipeline editor",                     "used_by": ["Pipeline Builder"], "props": ["sources", "transforms", "onSave"]},
            {"name": "DataTable",       "description": "Paginated virtualized table with column sorting/filtering", "used_by": ["Data Explorer"], "props": ["data", "columns", "onFilter"]},
            {"name": "QualityChart",    "description": "Time-series quality score with threshold lines",            "used_by": ["Quality Monitor"], "props": ["scores", "threshold", "metric"]},
            {"name": "LogViewer",       "description": "Real-time streaming log display for pipeline runs",         "used_by": ["Pipeline Detail"], "props": ["runId", "autoScroll"]},
            {"name": "AlertPanel",      "description": "Data quality and pipeline failure alerts",                  "used_by": ["Quality Monitor", "Pipeline Dashboard"], "props": ["alerts", "onAcknowledge"]},
            {"name": "Navbar",          "description": "Navigation with pipeline health indicator",                 "used_by": ["Pipeline Dashboard", "Data Explorer", "Quality Monitor"], "props": ["user", "pipelineHealth"]},
        ]
        routes = [
            {"method": "GET",  "path": "/api/pipelines",           "description": "List all pipelines with run status",         "auth_required": True,  "input": "?status&page", "output": "pipeline list", "used_by_pages": ["Pipeline Dashboard"]},
            {"method": "POST", "path": "/api/pipelines",           "description": "Create pipeline from config",                "auth_required": True,  "input": "pipeline config JSON", "output": "created pipeline", "used_by_pages": ["Pipeline Builder"]},
            {"method": "GET",  "path": "/api/pipelines/:id",       "description": "Get pipeline with runs and lineage",         "auth_required": True,  "input": "pipeline id", "output": "pipeline + runs", "used_by_pages": ["Pipeline Detail"]},
            {"method": "POST", "path": "/api/pipelines/:id/run",   "description": "Trigger immediate pipeline execution",       "auth_required": True,  "input": "run config", "output": "run object with id", "used_by_pages": ["Pipeline Detail", "Pipeline Dashboard"]},
            {"method": "GET",  "path": "/api/data",                "description": "Browse paginated processed dataset",         "auth_required": True,  "input": "?table&page&filters", "output": "paginated rows", "used_by_pages": ["Data Explorer"]},
            {"method": "POST", "path": "/api/query",               "description": "Execute ad-hoc SQL or filter query",         "auth_required": True,  "input": "query string or filter JSON", "output": "query results", "used_by_pages": ["Data Explorer"]},
            {"method": "GET",  "path": "/api/quality",             "description": "Get quality scores by dataset and time",     "auth_required": True,  "input": "?dataset&from&to", "output": "quality metrics", "used_by_pages": ["Quality Monitor"]},
            {"method": "GET",  "path": "/api/anomalies",           "description": "Get detected data anomalies",                "auth_required": True,  "input": "?severity&dataset", "output": "anomaly list", "used_by_pages": ["Quality Monitor"]},
            {"method": "GET",  "path": "/api/health",              "description": "Overall pipeline health status",             "auth_required": False, "input": "none", "output": "health object", "used_by_pages": ["Pipeline Dashboard"]},
        ]
        models = [
            {"name": "Pipeline",   "table": "pipelines",   "key_fields": ["id: uuid", "name: str", "config: json", "schedule: str", "status: str"], "relationships": ["has many Runs", "has many Sources"]},
            {"name": "Run",        "table": "runs",        "key_fields": ["id: uuid", "pipeline_id: uuid", "started_at: datetime", "status: str", "rows_processed: int"], "relationships": ["belongs to Pipeline", "has many Logs"]},
            {"name": "DataSource", "table": "data_sources","key_fields": ["id: uuid", "type: str", "connection_string: str", "schema: json"], "relationships": ["belongs to many Pipelines"]},
            {"name": "QualityCheck","table": "quality_checks","key_fields": ["id: uuid", "dataset: str", "score: float", "checked_at: datetime", "issues: json"], "relationships": []},
        ]

    else:
        domain = " ".join(idea.split()[:3]).title()
        pages = [
            {"name": f"{domain} Home",    "path": "/",           "description": f"Landing page with value proposition for {domain}", "navigates_to": ["/login", "/signup"],  "api_calls": [],                                       "components": ["Navbar", "HeroSection", "FeatureGrid", "Footer"], "auth_required": False},
            {"name": "Sign Up",           "path": "/signup",     "description": "New user registration with validation",              "navigates_to": ["/dashboard"],         "api_calls": ["POST /api/auth/register"],               "components": ["AuthForm", "PasswordStrength"], "auth_required": False},
            {"name": "Login",             "path": "/login",      "description": "Returning user authentication",                      "navigates_to": ["/dashboard"],         "api_calls": ["POST /api/auth/login"],                 "components": ["AuthForm", "SocialLogin"], "auth_required": False},
            {"name": "Dashboard",         "path": "/dashboard",  "description": f"Main {domain} workspace and activity overview",     "navigates_to": ["/profile"],           "api_calls": ["GET /api/user/me", "GET /api/dashboard"],"components": ["Navbar", "StatCard", "ActivityFeed", "AuthGuard"], "auth_required": True},
            {"name": "Profile",           "path": "/profile",    "description": "User profile and preferences management",            "navigates_to": ["/settings"],          "api_calls": ["GET /api/user/me", "PUT /api/user/me"],  "components": ["ProfileForm", "AvatarUpload", "AuthGuard"], "auth_required": True},
            {"name": "Settings",          "path": "/settings",   "description": "Account settings and notification preferences",      "navigates_to": [],                     "api_calls": ["GET /api/settings", "PUT /api/settings"],"components": ["SettingsTabs", "DangerZone", "AuthGuard"], "auth_required": True},
        ]
        components = [
            {"name": "Navbar",       "description": "Responsive navigation with auth-aware links",         "used_by": [f"{domain} Home", "Dashboard", "Profile"], "props": ["user", "isAuthenticated"]},
            {"name": "AuthForm",     "description": "Shared login/signup form with client validation",     "used_by": ["Sign Up", "Login"], "props": ["mode", "onSubmit", "isLoading"]},
            {"name": "AuthGuard",    "description": "HOC that redirects unauthenticated users to /login",  "used_by": ["Dashboard", "Profile", "Settings"], "props": ["children"]},
            {"name": "StatCard",     "description": "KPI metric card with trend indicator",                "used_by": ["Dashboard"], "props": ["label", "value", "trend", "icon"]},
            {"name": "ActivityFeed", "description": "Chronological list of recent user actions",           "used_by": ["Dashboard"], "props": ["activities", "limit"]},
            {"name": "Footer",       "description": "Site footer with legal links",                        "used_by": [f"{domain} Home"], "props": []},
            {"name": "Toast",        "description": "Global notification system for success/error states", "used_by": ["Dashboard", "Profile", "Settings", "Sign Up"], "props": ["message", "type", "duration"]},
        ]
        routes = [
            {"method": "POST", "path": "/api/auth/register", "description": "Register new user, send verification email",  "auth_required": False, "input": "name, email, password",  "output": "user + JWT token", "used_by_pages": ["Sign Up"]},
            {"method": "POST", "path": "/api/auth/login",    "description": "Authenticate and return JWT",                 "auth_required": False, "input": "email, password",        "output": "JWT token",        "used_by_pages": ["Login"]},
            {"method": "POST", "path": "/api/auth/logout",   "description": "Invalidate refresh token",                   "auth_required": True,  "input": "refresh_token",          "output": "success",          "used_by_pages": []},
            {"method": "GET",  "path": "/api/auth/me",       "description": "Get current authenticated user",             "auth_required": True,  "input": "JWT header",             "output": "user object",      "used_by_pages": ["Dashboard", "Profile"]},
            {"method": "GET",  "path": "/api/user/me",       "description": "Get user profile with preferences",          "auth_required": True,  "input": "JWT header",             "output": "profile object",   "used_by_pages": ["Profile"]},
            {"method": "PUT",  "path": "/api/user/me",       "description": "Update user profile fields",                 "auth_required": True,  "input": "profile fields JSON",    "output": "updated profile",  "used_by_pages": ["Profile"]},
            {"method": "GET",  "path": "/api/dashboard",     "description": "Get dashboard stats and activity feed",      "auth_required": True,  "input": "JWT header",             "output": "stats + feed",     "used_by_pages": ["Dashboard"]},
            {"method": "GET",  "path": "/api/settings",      "description": "Get user settings and preferences",          "auth_required": True,  "input": "JWT header",             "output": "settings object",  "used_by_pages": ["Settings"]},
            {"method": "PUT",  "path": "/api/settings",      "description": "Update settings",                            "auth_required": True,  "input": "settings JSON",          "output": "updated settings", "used_by_pages": ["Settings"]},
        ]
        models = [
            {"name": "User",     "table": "users",    "key_fields": ["id: uuid", "email: str", "name: str", "avatar_url: str", "created_at: datetime"], "relationships": ["has one Profile", "has many Activities"]},
            {"name": "Profile",  "table": "profiles", "key_fields": ["id: uuid", "user_id: uuid", "bio: str", "preferences: json"], "relationships": ["belongs to User"]},
            {"name": "Activity", "table": "activities","key_fields": ["id: uuid", "user_id: uuid", "type: str", "metadata: json", "created_at: datetime"], "relationships": ["belongs to User"]},
            {"name": "Settings", "table": "settings", "key_fields": ["id: uuid", "user_id: uuid", "notifications: json", "theme: str"], "relationships": ["belongs to User"]},
        ]

    return {
        "pages": pages,
        "shared_components": components,
        "api_routes": routes,
        "data_models": models,
        "navigation_structure": {
            "public_routes":               [p["path"] for p in pages if not p["auth_required"]],
            "protected_routes":            [p["path"] for p in pages if p["auth_required"]],
            "default_redirect_after_login": "/dashboard",
            "nav_groups": [
                {"label": "Main",    "routes": [p["path"] for p in pages[:3]]},
                {"label": "Account", "routes": [p["path"] for p in pages[3:]]},
            ],
        },
        "tech_decisions": {
            "frontend":    tech_stack[0] if tech_stack else "Next.js — SSR + file-based routing",
            "backend":     next((t for t in tech_stack if any(w in t.lower() for w in ["fast", "django", "express", "node"])), "FastAPI — async, type-safe, auto-docs"),
            "database":    next((t for t in tech_stack if any(w in t.lower() for w in ["postgres", "mysql", "mongo", "redis"])), "PostgreSQL — ACID, row-level security"),
            "auth":        "JWT with refresh tokens — 15min access, 7d refresh",
            "deployment":  "Docker + GitHub Actions CI/CD",
            "key_libraries": ["Pydantic — request validation", "SQLAlchemy — ORM", "Tailwind — utility CSS"],
        },
    }