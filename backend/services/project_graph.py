"""
backend/services/project_graph.py

Project Graph Generator — The Brain of 3Netra-AI

Uses 3 parallel LLM calls instead of one giant call.
Each call generates one section — routes, pages, components.
Merges results into the full graph.
Eliminates truncation and JSON corruption permanently.
"""

import asyncio
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
        tech_stack   = verdict.get("recommended_stack", []) if verdict else []
        v1_scope     = verdict.get("v1_scope", []) if verdict else []
        career_value = verdict.get("career_value", "") if verdict else ""
        tech_str     = ", ".join(tech_stack) if tech_stack else "FastAPI, React, PostgreSQL, Docker"
        scope_str    = "\n".join(f"- {s}" for s in v1_scope) if v1_scope else "Core MVP features"

        base_context = f"""PROJECT: {idea}
TECH STACK: {tech_str}
V1 SCOPE:
{scope_str}
CAREER VALUE: {career_value}

CRITICAL: Every name must be SPECIFIC to this project domain. No generic names. No placeholders."""

        # ── 3 parallel calls ─────────────────────────────────────────────────

        results = await asyncio.gather(
            _generate_routes_and_models(base_context, idea, tech_str),
            _generate_pages_and_navigation(base_context, idea, tech_str),
            _generate_components_and_tech(base_context, idea, tech_str),
            _generate_data_models(base_context, idea, tech_str),
            return_exceptions=True,
        )

        routes_result     = results[0]
        pages_result      = results[1]
        components_result = results[2]
        models_result     = results[3]

        # ── Merge results ─────────────────────────────────────────────────────

        api_routes   = []
        data_models  = []
        pages        = []
        navigation   = {}
        components   = []
        tech_decisions = {}

        if not isinstance(routes_result, Exception):
            api_routes  = routes_result.get("api_routes", [])
            data_models = routes_result.get("data_models", [])
        else:
            logger.warning(f"Routes call failed: {routes_result}")

        if not isinstance(models_result, Exception):
            data_models = models_result.get("data_models", [])

        if not isinstance(pages_result, Exception):
            pages      = pages_result.get("pages", [])
            navigation = pages_result.get("navigation_structure", {})
        else:
            logger.warning(f"Pages call failed: {pages_result}")

        if not isinstance(components_result, Exception):
            components     = components_result.get("shared_components", [])
            tech_decisions = components_result.get("tech_decisions", {})
        else:
            logger.warning(f"Components call failed: {components_result}")

        # ── Validate ──────────────────────────────────────────────────────────

        if len(pages) < 3 or len(api_routes) < 3:
            raise ValueError(
                f"Graph too small after merge: {len(pages)} pages, {len(api_routes)} routes"
            )

        graph = {
            "pages":               pages,
            "shared_components":   components,
            "api_routes":          api_routes,
            "data_models":         data_models,
            "navigation_structure": navigation,
            "tech_decisions":      tech_decisions,
        }

        elapsed = round(time.time() - start, 1)
        logger.info(
            f"Project graph generated in {elapsed}s: "
            f"{len(pages)} pages, {len(components)} components, "
            f"{len(api_routes)} routes, {len(data_models)} data models"
        )
        return _build_result(project_id, idea, graph, elapsed)

    except Exception as e:
        logger.error(f"Project graph failed — {type(e).__name__}: {e}")
        elapsed = round(time.time() - start, 1)
        graph   = _smart_fallback_graph(idea, verdict)
        logger.warning(f"Using smart fallback — {len(graph.get('pages', []))} pages")
        return _build_result(project_id, idea, graph, elapsed, fallback=True)


# ── Parallel call 1: API routes + data models ─────────────────────────────────

async def _generate_routes_and_models(context: str, idea: str, tech_str: str) -> dict:
    from services.llm_client import call_strong

    prompt = f"""{context}

Generate ONLY the api_routes and data_models for this project.
Every route and model must be specific to THIS project domain.

Return ONLY this JSON:
{{
    "api_routes": [
        {{
            "method": "GET",
            "path": "/api/specific/endpoint",
            "description": "what this endpoint does for THIS project",
            "auth_required": true,
            "input": "request description",
            "output": "response description",
            "used_by_pages": ["Page Name"]
        }}
    ],
    "data_models": [
        {{
            "name": "ModelName",
            "table": "table_name",
            "key_fields": ["field1: type", "field2: type"],
            "relationships": ["belongs to ModelX", "has many ModelY"]
        }}
    ]
}}

Requirements:
- Minimum 8 API routes matching actual project functionality
- One data model per major entity in the project
- Every name must reference THIS project domain specifically
- No generic CRUD routes — make them project-specific"""

    return await _call_and_parse(prompt, "routes_and_models")


# ── Parallel call 2: Pages + navigation ──────────────────────────────────────

async def _generate_pages_and_navigation(context: str, idea: str, tech_str: str) -> dict:
    from services.llm_client import call_strong

    prompt = f"""{context}

Generate ONLY the pages and navigation_structure for this project.
Every page must be specific to THIS project domain.

Return ONLY this JSON:
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
    "navigation_structure": {{
        "public_routes": ["/", "/login"],
        "protected_routes": ["/dashboard"],
        "default_redirect_after_login": "/dashboard",
        "nav_groups": [
            {{"label": "Main", "routes": ["/dashboard"]}}
        ]
    }}
}}

Requirements:
- Minimum 5 pages specific to THIS project domain
- Every page name must reference the project's actual domain
- No generic page names — be specific"""

    return await _call_and_parse(prompt, "pages_and_navigation")


# ── Parallel call 3: Shared components + tech decisions ───────────────────────

async def _generate_components_and_tech(context: str, idea: str, tech_str: str) -> dict:
    from services.llm_client import call_strong

    prompt = f"""{context}

Generate ONLY the shared_components and tech_decisions for this project.

Return ONLY this JSON:
{{
    "shared_components": [
        {{
            "name": "ComponentName",
            "description": "specific purpose in this project",
            "used_by": ["Page Name 1", "Page Name 2"],
            "props": ["key prop 1", "key prop 2"]
        }}
    ],
    "tech_decisions": {{
        "frontend": "framework and specific reason for THIS project",
        "backend": "framework and specific reason",
        "database": "database and why it fits THIS project's data model",
        "auth": "auth approach and why",
        "deployment": "deployment strategy",
        "key_libraries": ["library1 — purpose", "library2 — purpose"]
    }}
}}

Requirements:
- Minimum 6 shared components with real project-specific names
- Tech decisions must explain WHY each choice for THIS project
- Component names must reference this project's actual domain"""

    return await _call_and_parse(prompt, "components_and_tech")

async def _generate_data_models(context: str, idea: str, tech_str: str) -> dict:
    from services.llm_client import call_strong

    prompt = f"""{context}

Generate ONLY the data_models for this project.
One model per major entity. Every model must be specific to THIS project domain.

Return ONLY this JSON:
{{
    "data_models": [
        {{
            "name": "ModelName",
            "table": "table_name",
            "key_fields": ["field1: type", "field2: type", "field3: type"],
            "relationships": ["belongs to ModelX", "has many ModelY"]
        }}
    ]
}}

Requirements:
- Minimum 4 data models — one per major entity in this project
- Every model name must reference THIS project domain
- key_fields must include realistic fields for this specific domain"""

    return await _call_and_parse(prompt, "data_models")


# ── Shared parser ─────────────────────────────────────────────────────────────

async def _call_and_parse(prompt: str, section: str) -> dict:
    from services.llm_client import call_strong

    response = await call_strong(
        system=(
            "You are a senior software architect generating a project graph section. "
            "Return ONLY valid JSON. No markdown. No explanation. "
            "Every name must be specific to the project described — no generic placeholders."
        ),
        user=prompt,
        max_tokens=2000,
    )

    cleaned = re.sub(r'```json\s*', '', response)
    cleaned = re.sub(r'```\s*',     '', cleaned).strip()
    match   = re.search(r'\{.*\}',  cleaned, re.DOTALL)

    if not match:
        raise ValueError(f"No JSON found in {section} response")

    raw = match.group()

    # Repair unclosed brackets
    open_braces   = raw.count('{') - raw.count('}')
    open_brackets = raw.count('[') - raw.count(']')
    if open_braces > 0 or open_brackets > 0:
        raw = raw.rstrip(',\n\r\t ')
        raw += ']' * open_brackets
        raw += '}' * open_braces

    # Repair trailing commas and bad delimiters
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raw = re.sub(r',\s*([}\]])', r'\1', raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            error_msg = str(e)
            if "Unterminated string" in error_msg or "Expecting" in error_msg:
                pos_match = re.search(r'char (\d+)', error_msg)
                if pos_match:
                    char_pos = int(pos_match.group(1))
                    raw = raw[:char_pos - 1].rstrip(',\n\r\t :{[ ')
                    open_braces   = raw.count('{') - raw.count('}')
                    open_brackets = raw.count('[') - raw.count(']')
                    raw += ']' * open_brackets
                    raw += '}' * open_braces
                    raw = re.sub(r',\s*([}\]])', r'\1', raw)
                    return json.loads(raw)
            raise


# ── Result builder ────────────────────────────────────────────────────────────

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


# ── Smart fallback ────────────────────────────────────────────────────────────

def _extract_domain_terms(idea: str) -> dict:
    words = idea.lower().split()
    stop_words = {
        "i", "want", "to", "build", "a", "an", "the", "that", "with", "for",
        "and", "or", "in", "on", "of", "is", "are", "using", "based", "make",
        "create", "develop", "system", "platform", "app", "application", "tool",
        "service", "product", "solution", "project"
    }
    meaningful  = [w for w in words if w not in stop_words and len(w) > 3]
    domain_terms = meaningful[:3] if meaningful else ["item", "user", "record"]
    capitalized  = [t.capitalize() for t in domain_terms]
    domain_label = " ".join(capitalized[:2]) if len(capitalized) >= 2 else capitalized[0]
    return {
        "label":      domain_label,
        "entity":     capitalized[0],
        "action":     capitalized[1] if len(capitalized) > 1 else "Analysis",
        "sub_entity": capitalized[2] if len(capitalized) > 2 else "Report",
        "raw":        domain_terms,
    }
def _build_tech_decisions(tech_stack: list, idea: str) -> dict:
    """
    Dynamically maps council recommended_stack into tech_decisions categories.
    Never hardcodes a specific framework — always reads from what council chose.
    """
    if not tech_stack:
        return {
            "frontend":    "To be determined based on project requirements",
            "backend":     "To be determined based on project requirements",
            "database":    "To be determined based on project requirements",
            "auth":        "To be determined based on project requirements",
            "deployment":  "To be determined based on project requirements",
            "key_libraries": [],
        }

    stack_lower = [t.lower() for t in tech_stack]

    # ── Frontend detection ────────────────────────────────────────────────
    frontend_keywords = {
        "next":      "Next.js",
        "react":     "React",
        "vue":       "Vue.js",
        "nuxt":      "Nuxt.js",
        "svelte":    "SvelteKit",
        "angular":   "Angular",
        "remix":     "Remix",
        "astro":     "Astro",
        "gatsby":    "Gatsby",
        "flutter":   "Flutter",
        "react native": "React Native",
        "swift":     "SwiftUI",
        "kotlin":    "Jetpack Compose",
        "electron":  "Electron",
        "tauri":     "Tauri",
    }
    frontend = next(
        (tech_stack[i] for i, s in enumerate(stack_lower)
         if any(kw in s for kw in frontend_keywords)),
        None
    )

    # ── Backend detection ─────────────────────────────────────────────────
    backend_keywords = {
        "fastapi":   "FastAPI",
        "django":    "Django",
        "flask":     "Flask",
        "express":   "Express.js",
        "node":      "Node.js",
        "nest":      "NestJS",
        "spring":    "Spring Boot",
        "rails":     "Ruby on Rails",
        "laravel":   "Laravel",
        "gin":       "Gin",
        "fiber":     "Fiber",
        "actix":     "Actix",
        "axum":      "Axum",
        "phoenix":   "Phoenix",
        "dotnet":    ".NET",
        "asp.net":   "ASP.NET",
        "fastify":   "Fastify",
        "hono":      "Hono",
    }
    backend = next(
        (tech_stack[i] for i, s in enumerate(stack_lower)
         if any(kw in s for kw in backend_keywords)),
        None
    )

    # ── Database detection ────────────────────────────────────────────────
    database_keywords = {
        "postgres":   "PostgreSQL",
        "mysql":      "MySQL",
        "mongodb":    "MongoDB",
        "mongo":      "MongoDB",
        "sqlite":     "SQLite",
        "redis":      "Redis",
        "valkey":     "Valkey",
        "dynamodb":   "DynamoDB",
        "firestore":  "Firestore",
        "supabase":   "Supabase",
        "planetscale":"PlanetScale",
        "cockroach":  "CockroachDB",
        "cassandra":  "Cassandra",
        "clickhouse": "ClickHouse",
        "elasticsearch": "Elasticsearch",
        "neo4j":      "Neo4j",
        "prisma":     "PostgreSQL via Prisma",
        "drizzle":    "PostgreSQL via Drizzle",
    }
    database = next(
        (tech_stack[i] for i, s in enumerate(stack_lower)
         if any(kw in s for kw in database_keywords)),
        None
    )

    # ── Auth detection ────────────────────────────────────────────────────
    auth_keywords = {
        "supabase":   "Supabase Auth — built-in JWT + OAuth providers",
        "firebase":   "Firebase Auth — Google, email/password, social providers",
        "auth0":      "Auth0 — enterprise SSO + social login",
        "clerk":      "Clerk — drop-in auth with UI components",
        "nextauth":   "NextAuth.js — OAuth + JWT for Next.js",
        "passport":   "Passport.js — flexible auth middleware",
        "keycloak":   "Keycloak — self-hosted identity provider",
        "cognito":    "AWS Cognito — managed auth for AWS deployments",
        "jwt":        "JWT with refresh tokens — 15min access, 7d refresh",
    }
    auth = next(
        (desc for kw, desc in auth_keywords.items()
         if any(kw in s for s in stack_lower)),
        "JWT with refresh tokens — 15min access, 7d refresh"
    )

    # ── Deployment detection ──────────────────────────────────────────────
    deploy_keywords = {
        "vercel":     "Vercel (frontend) + Railway (backend) + Docker",
        "railway":    "Railway — full stack deployment with Docker",
        "aws":        "AWS — ECS or Lambda + RDS + S3 + CloudFront",
        "gcp":        "Google Cloud — Cloud Run + Cloud SQL + GCS",
        "azure":      "Azure — Container Apps + Azure SQL + Blob Storage",
        "heroku":     "Heroku — git push deployment with add-ons",
        "fly":        "Fly.io — Docker deployment close to users",
        "render":     "Render — Docker + managed PostgreSQL",
        "netlify":    "Netlify (frontend) + serverless functions",
        "docker":     "Docker + Docker Compose — containerized deployment",
        "kubernetes": "Kubernetes — container orchestration at scale",
        "terraform":  "Terraform IaC + cloud provider of choice",
    }
    deployment = next(
        (desc for kw, desc in deploy_keywords.items()
         if any(kw in s for s in stack_lower)),
        "Docker + GitHub Actions CI/CD → cloud provider of choice"
    )

    # ── Key libraries — remaining stack items not categorized above ───────
    categorized = set()
    if frontend: categorized.add(frontend.lower().split()[0])
    if backend:  categorized.add(backend.lower().split()[0])
    if database: categorized.add(database.lower().split()[0])

    key_libraries = [
        t for t in tech_stack
        if not any(c in t.lower() for c in categorized)
        and not any(kw in t.lower() for kw in ["docker", "vercel", "railway", "aws", "gcp", "azure"])
    ][:6]

    return {
        "frontend":    frontend or tech_stack[0],
        "backend":     backend  or (tech_stack[1] if len(tech_stack) > 1 else "server-side framework from recommended stack"),
        "database":    database or (tech_stack[2] if len(tech_stack) > 2 else "database from recommended stack"),
        "auth":        auth,
        "deployment":  deployment,
        "key_libraries": key_libraries,
    }

def _smart_fallback_graph(idea: str, verdict: dict | None = None) -> dict:
    tech_stack = verdict.get("recommended_stack", []) if verdict else []
    idea_lower = idea.lower()

    is_ml   = any(w in idea_lower for w in [
        "ml", "model", "training", "inference", "rag", "llm", "ai",
        "neural", "recommendation", "classify", "prediction", "detection",
        "fraud", "anomaly", "forecast", "nlp", "computer vision"
    ])
    is_data = any(w in idea_lower for w in [
        "data", "pipeline", "etl", "warehouse", "analytics", "dashboard",
        "stream", "kafka", "spark", "sentiment", "scraper", "crawler",
        "ingest", "transform", "batch"
    ])

    d  = _extract_domain_terms(idea)
    E  = d["entity"]
    A  = d["action"]
    S  = d["sub_entity"]
    DL = d["label"]

    if is_ml:
        pages = [
            {"name": f"{DL} Dashboard",   "path": "/",            "description": f"Overview of {DL.lower()} models and live performance metrics", "navigates_to": ["/models", "/experiments"], "api_calls": ["GET /api/models", "GET /api/metrics"],          "components": [f"{E}ModelCard", "MetricChart", "Navbar"],        "auth_required": False},
            {"name": f"{E} Model Registry","path": "/models",      "description": f"Browse, version, and compare {DL.lower()} models",            "navigates_to": ["/models/:id"],             "api_calls": ["GET /api/models", "POST /api/models"],             "components": [f"{E}ModelList", f"{E}ModelCard", "VersionBadge"], "auth_required": True},
            {"name": f"{E} Model Detail",  "path": "/models/:id",  "description": f"Full metrics and live inference for a {E.lower()} model",     "navigates_to": ["/experiments"],            "api_calls": ["GET /api/models/:id", "POST /api/predict"],        "components": [f"{E}ModelViewer", "MetricChart", f"{E}PredictionForm"], "auth_required": True},
            {"name": f"{A} Experiments",   "path": "/experiments", "description": f"Track and compare {DL.lower()} training runs",                "navigates_to": ["/experiments/:id"],        "api_calls": ["GET /api/experiments", "POST /api/experiments"],   "components": ["ExperimentList", "RunChart", "CompareTable"],     "auth_required": True},
            {"name": f"Live {A} Monitor",  "path": "/monitoring",  "description": f"Real-time {DL.lower()} performance and drift alerts",          "navigates_to": [],                          "api_calls": ["GET /api/metrics/live", "GET /api/alerts"],        "components": ["LiveChart", f"{S}AlertPanel", "DriftDetector"],   "auth_required": True},
            {"name": f"{E} API Playground","path": "/playground",  "description": f"Test {DL.lower()} inference interactively",                   "navigates_to": [],                          "api_calls": ["POST /api/predict"],                               "components": [f"{E}InputBuilder", "ResponseViewer", "CodeSnippet"], "auth_required": False},
        ]
        components = [
            {"name": f"{E}ModelCard",      "description": f"{E} model summary with accuracy, latency, version",          "used_by": [f"{DL} Dashboard", f"{E} Model Registry"], "props": ["model", "onSelect"]},
            {"name": "MetricChart",         "description": f"Time-series chart for {DL.lower()} accuracy and performance", "used_by": [f"{DL} Dashboard", f"{E} Model Detail"],   "props": ["data", "metric", "timeRange"]},
            {"name": f"{E}PredictionForm",  "description": f"Input builder for {DL.lower()} inference requests",          "used_by": [f"{E} Model Detail", f"{E} API Playground"],"props": ["schema", "onPredict"]},
            {"name": "ExperimentList",      "description": "Sortable list of training runs with metric comparison",        "used_by": [f"{A} Experiments"],                        "props": ["experiments", "onCompare"]},
            {"name": "LiveChart",           "description": "WebSocket real-time metrics visualization",                    "used_by": [f"Live {A} Monitor"],                       "props": ["modelId", "metric"]},
            {"name": f"{S}AlertPanel",      "description": f"Drift and {DL.lower()} degradation alerts",                  "used_by": [f"Live {A} Monitor", f"{DL} Dashboard"],   "props": ["alerts", "onAcknowledge"]},
            {"name": "Navbar",              "description": "Navigation with active model status indicator",                "used_by": [f"{DL} Dashboard", f"{E} Model Registry"],  "props": ["user", "activeModel"]},
        ]
        routes = [
            {"method": "GET",  "path": "/api/models",       "description": f"List all {DL.lower()} models",          "auth_required": True,  "input": "?page&limit&status",        "output": "paginated model list",    "used_by_pages": [f"{E} Model Registry"]},
            {"method": "POST", "path": "/api/models",       "description": f"Register new {E.lower()} model",        "auth_required": True,  "input": "model metadata + artifact", "output": "created model",           "used_by_pages": [f"{E} Model Registry"]},
            {"method": "GET",  "path": "/api/models/:id",   "description": f"Get {E.lower()} model with metrics",    "auth_required": True,  "input": "model id",                  "output": "model + metrics",         "used_by_pages": [f"{E} Model Detail"]},
            {"method": "POST", "path": "/api/predict",      "description": f"Run {DL.lower()} inference",            "auth_required": True,  "input": "feature JSON",              "output": "prediction + confidence", "used_by_pages": [f"{E} Model Detail", f"{E} API Playground"]},
            {"method": "GET",  "path": "/api/experiments",  "description": f"List {DL.lower()} training runs",       "auth_required": True,  "input": "?model_id&status",          "output": "experiment list",         "used_by_pages": [f"{A} Experiments"]},
            {"method": "POST", "path": "/api/experiments",  "description": "Create and start training run",           "auth_required": True,  "input": "training config JSON",      "output": "experiment + run_id",     "used_by_pages": [f"{A} Experiments"]},
            {"method": "GET",  "path": "/api/metrics/live", "description": "SSE stream of live model metrics",        "auth_required": True,  "input": "?model_id",                 "output": "SSE stream",              "used_by_pages": [f"Live {A} Monitor"]},
            {"method": "GET",  "path": "/api/alerts",       "description": f"Get {DL.lower()} drift alerts",         "auth_required": True,  "input": "?model_id&severity",        "output": "alert list",              "used_by_pages": [f"Live {A} Monitor"]},
            {"method": "POST", "path": "/api/auth/login",   "description": "Authenticate user",                       "auth_required": False, "input": "email, password",           "output": "JWT token",               "used_by_pages": []},
        ]
        models = [
            {"name": f"{E}Model",      "table": f"{E.lower()}_models",     "key_fields": ["id: uuid", "name: str", "version: str", f"{A.lower()}_score: float"], "relationships": [f"has many {E}{A}Runs", f"has many {E}Predictions"]},
            {"name": f"{E}{A}Run",     "table": f"{E.lower()}_{A.lower()}_runs", "key_fields": ["id: uuid", "model_id: uuid", "config: json", "status: str"],    "relationships": [f"belongs to {E}Model"]},
            {"name": f"{E}Prediction", "table": f"{E.lower()}_predictions", "key_fields": ["id: uuid", "model_id: uuid", "input: json", "latency_ms: int"],      "relationships": [f"belongs to {E}Model"]},
            {"name": f"{S}Alert",      "table": f"{S.lower()}_alerts",      "key_fields": ["id: uuid", "model_id: uuid", "type: str", "severity: str"],          "relationships": [f"belongs to {E}Model"]},
        ]

    elif is_data:
        pages = [
            {"name": f"{DL} Pipeline Dashboard", "path": "/",               "description": f"Overview of {DL.lower()} pipelines and run status",     "navigates_to": ["/pipelines", "/data"], "api_calls": ["GET /api/pipelines", "GET /api/health"],           "components": [f"{E}PipelineCard", "StatusBadge", "Navbar"],          "auth_required": False},
            {"name": f"{E} Pipeline Builder",    "path": "/pipelines/new",  "description": f"Configure {DL.lower()} pipeline sources and schedule",  "navigates_to": ["/pipelines"],          "api_calls": ["POST /api/pipelines", "GET /api/sources"],          "components": [f"{E}PipelineBuilder", f"{E}SourceSelector"],          "auth_required": True},
            {"name": f"{E} Pipeline Detail",     "path": "/pipelines/:id",  "description": f"Monitor runs and lineage for {DL.lower()} pipeline",    "navigates_to": [],                      "api_calls": ["GET /api/pipelines/:id", "GET /api/runs"],          "components": ["RunHistory", "LogViewer", f"{E}LineageGraph"],        "auth_required": True},
            {"name": f"{E} Data Explorer",       "path": "/data",           "description": f"Browse and query processed {E.lower()} datasets",       "navigates_to": [],                      "api_calls": ["GET /api/data", "POST /api/query"],                 "components": [f"{E}DataTable", "QueryEditor", "FilterPanel"],        "auth_required": True},
            {"name": f"{A} Quality Monitor",     "path": "/quality",        "description": f"Data quality metrics and anomaly detection",            "navigates_to": [],                      "api_calls": ["GET /api/quality", "GET /api/anomalies"],           "components": ["QualityChart", f"{E}AnomalyTable", "AlertPanel"],    "auth_required": True},
            {"name": "Settings",                 "path": "/settings",       "description": f"Configure {DL.lower()} sources and credentials",        "navigates_to": [],                      "api_calls": ["GET /api/settings", "PUT /api/settings"],           "components": ["ConnectionForm", "ScheduleConfig"],                   "auth_required": True},
        ]
        components = [
            {"name": f"{E}PipelineCard",    "description": f"{E} pipeline summary with last run status",         "used_by": [f"{DL} Pipeline Dashboard"],     "props": ["pipeline", "onEdit", "onRun"]},
            {"name": f"{E}PipelineBuilder", "description": f"Visual {DL.lower()} pipeline editor",               "used_by": [f"{E} Pipeline Builder"],        "props": ["sources", "transforms", "onSave"]},
            {"name": f"{E}DataTable",       "description": f"Paginated table for {E.lower()} records",           "used_by": [f"{E} Data Explorer"],           "props": ["data", "columns", "onFilter"]},
            {"name": "QualityChart",        "description": f"Time-series quality score for {DL.lower()}",        "used_by": [f"{A} Quality Monitor"],         "props": ["scores", "threshold", "metric"]},
            {"name": "LogViewer",           "description": f"Real-time streaming logs for {E.lower()} runs",     "used_by": [f"{E} Pipeline Detail"],         "props": ["runId", "autoScroll"]},
            {"name": "AlertPanel",          "description": f"{DL} quality and pipeline failure alerts",           "used_by": [f"{A} Quality Monitor", f"{DL} Pipeline Dashboard"], "props": ["alerts", "onAcknowledge"]},
            {"name": "Navbar",              "description": "Navigation with pipeline health indicator",           "used_by": [f"{DL} Pipeline Dashboard", f"{E} Data Explorer"],  "props": ["user", "pipelineHealth"]},
        ]
        routes = [
            {"method": "GET",  "path": "/api/pipelines",         "description": f"List {DL.lower()} pipelines",          "auth_required": True,  "input": "?status&page",           "output": "pipeline list",      "used_by_pages": [f"{DL} Pipeline Dashboard"]},
            {"method": "POST", "path": "/api/pipelines",         "description": f"Create {E.lower()} pipeline",          "auth_required": True,  "input": "pipeline config JSON",   "output": "created pipeline",   "used_by_pages": [f"{E} Pipeline Builder"]},
            {"method": "GET",  "path": "/api/pipelines/:id",     "description": f"Get {E.lower()} pipeline with runs",   "auth_required": True,  "input": "pipeline id",            "output": "pipeline + runs",    "used_by_pages": [f"{E} Pipeline Detail"]},
            {"method": "POST", "path": "/api/pipelines/:id/run", "description": f"Trigger {E.lower()} pipeline run",     "auth_required": True,  "input": "run config",             "output": "run object",         "used_by_pages": [f"{E} Pipeline Detail"]},
            {"method": "GET",  "path": "/api/data",              "description": f"Browse {E.lower()} dataset",           "auth_required": True,  "input": "?table&page&filters",    "output": "paginated rows",     "used_by_pages": [f"{E} Data Explorer"]},
            {"method": "POST", "path": "/api/query",             "description": f"Query {E.lower()} data",               "auth_required": True,  "input": "query string or filter", "output": "query results",      "used_by_pages": [f"{E} Data Explorer"]},
            {"method": "GET",  "path": "/api/quality",           "description": f"Get {DL.lower()} quality scores",      "auth_required": True,  "input": "?dataset&from&to",       "output": "quality metrics",    "used_by_pages": [f"{A} Quality Monitor"]},
            {"method": "GET",  "path": "/api/anomalies",         "description": f"Get {E.lower()} anomalies",            "auth_required": True,  "input": "?severity&dataset",      "output": "anomaly list",       "used_by_pages": [f"{A} Quality Monitor"]},
            {"method": "GET",  "path": "/api/health",            "description": "Pipeline health status",                "auth_required": False, "input": "none",                   "output": "health object",      "used_by_pages": [f"{DL} Pipeline Dashboard"]},
        ]
        models = [
            {"name": f"{E}Pipeline",     "table": f"{E.lower()}_pipelines",     "key_fields": ["id: uuid", "name: str", "config: json", "status: str"],                        "relationships": [f"has many {E}Runs", f"has many {E}Sources"]},
            {"name": f"{E}Run",          "table": f"{E.lower()}_runs",          "key_fields": ["id: uuid", "pipeline_id: uuid", "started_at: datetime", "rows_processed: int"],"relationships": [f"belongs to {E}Pipeline"]},
            {"name": f"{E}Source",       "table": f"{E.lower()}_sources",       "key_fields": ["id: uuid", "type: str", "connection_string: str", "schema: json"],             "relationships": [f"belongs to many {E}Pipelines"]},
            {"name": f"{A}QualityCheck", "table": f"{A.lower()}_quality_checks","key_fields": ["id: uuid", "dataset: str", "score: float", "issues: json"],                    "relationships": []},
        ]

    else:
        domain = " ".join(idea.split()[:3]).title()
        pages = [
            {"name": f"{DL} Home",     "path": "/",          "description": f"Landing page for {DL}",                       "navigates_to": ["/login", "/signup"],  "api_calls": [],                                           "components": ["Navbar", f"{E}HeroSection", "FeatureGrid"],      "auth_required": False},
            {"name": "Sign Up",        "path": "/signup",    "description": "New user registration",                        "navigates_to": ["/dashboard"],         "api_calls": ["POST /api/auth/register"],                   "components": ["AuthForm", "PasswordStrength"],                  "auth_required": False},
            {"name": "Login",          "path": "/login",     "description": "Returning user authentication",                "navigates_to": ["/dashboard"],         "api_calls": ["POST /api/auth/login"],                      "components": ["AuthForm", "SocialLogin"],                       "auth_required": False},
            {"name": f"{DL} Dashboard","path": "/dashboard", "description": f"Main {DL.lower()} workspace",                 "navigates_to": [f"/{E.lower()}s"],     "api_calls": ["GET /api/user/me", f"GET /api/{E.lower()}s"], "components": ["Navbar", f"{E}StatCard", f"{E}ActivityFeed"],    "auth_required": True},
            {"name": f"{E} Detail",    "path": f"/{E.lower()}s/:id", "description": f"Full detail for {E.lower()} record", "navigates_to": ["/dashboard"],         "api_calls": [f"GET /api/{E.lower()}s/:id"],                "components": [f"{E}DetailCard", f"{E}ActionPanel"],             "auth_required": True},
            {"name": "Settings",       "path": "/settings",  "description": "Account settings and preferences",            "navigates_to": [],                     "api_calls": ["GET /api/settings", "PUT /api/settings"],    "components": ["SettingsTabs", "DangerZone"],                    "auth_required": True},
        ]
        components = [
            {"name": "Navbar",           "description": f"Responsive navigation for {DL}",              "used_by": [f"{DL} Home", f"{DL} Dashboard"],       "props": ["user", "isAuthenticated"]},
            {"name": "AuthForm",         "description": "Shared login/signup form with validation",      "used_by": ["Sign Up", "Login"],                    "props": ["mode", "onSubmit", "isLoading"]},
            {"name": "AuthGuard",        "description": "HOC that redirects unauthenticated users",      "used_by": [f"{DL} Dashboard", f"{E} Detail"],      "props": ["children"]},
            {"name": f"{E}StatCard",     "description": f"KPI metric card for {DL.lower()}",             "used_by": [f"{DL} Dashboard"],                     "props": ["label", "value", "trend", "icon"]},
            {"name": f"{E}ActivityFeed", "description": f"Chronological feed of {DL.lower()} actions",  "used_by": [f"{DL} Dashboard"],                     "props": ["activities", "limit"]},
            {"name": f"{E}DetailCard",   "description": f"Full detail display for {E.lower()} record",  "used_by": [f"{E} Detail"],                         "props": ["item", "onEdit", "onDelete"]},
            {"name": "Toast",            "description": "Global notification system",                    "used_by": [f"{DL} Dashboard", f"{E} Detail"],      "props": ["message", "type", "duration"]},
        ]
        routes = [
            {"method": "POST", "path": "/api/auth/register",     "description": "Register new user",                      "auth_required": False, "input": "name, email, password",   "output": "user + JWT",           "used_by_pages": ["Sign Up"]},
            {"method": "POST", "path": "/api/auth/login",         "description": "Authenticate, return JWT",               "auth_required": False, "input": "email, password",         "output": "JWT token",            "used_by_pages": ["Login"]},
            {"method": "GET",  "path": "/api/auth/me",            "description": "Get current user",                       "auth_required": True,  "input": "JWT header",              "output": "user object",          "used_by_pages": [f"{DL} Dashboard"]},
            {"method": "GET",  "path": f"/api/{E.lower()}s",      "description": f"List {E.lower()} records",              "auth_required": True,  "input": "?page&limit&filter",      "output": f"{E.lower()} list",    "used_by_pages": [f"{DL} Dashboard"]},
            {"method": "POST", "path": f"/api/{E.lower()}s",      "description": f"Create {E.lower()} record",             "auth_required": True,  "input": f"{E.lower()} data JSON",  "output": f"created {E.lower()}", "used_by_pages": [f"{DL} Dashboard"]},
            {"method": "GET",  "path": f"/api/{E.lower()}s/:id",  "description": f"Get {E.lower()} detail",                "auth_required": True,  "input": f"{E.lower()} id",         "output": f"{E.lower()} object",  "used_by_pages": [f"{E} Detail"]},
            {"method": "PUT",  "path": f"/api/{E.lower()}s/:id",  "description": f"Update {E.lower()} record",             "auth_required": True,  "input": "partial update JSON",     "output": f"updated {E.lower()}", "used_by_pages": [f"{E} Detail"]},
            {"method": "DELETE","path": f"/api/{E.lower()}s/:id", "description": f"Delete {E.lower()} record",             "auth_required": True,  "input": f"{E.lower()} id",         "output": "success",              "used_by_pages": [f"{E} Detail"]},
            {"method": "GET",  "path": "/api/settings",           "description": "Get user settings",                      "auth_required": True,  "input": "JWT header",              "output": "settings object",      "used_by_pages": ["Settings"]},
        ]
        models = [
            {"name": "User",     "table": "users",     "key_fields": ["id: uuid", "email: str", "name: str", "created_at: datetime"], "relationships": [f"has many {E}s"]},
            {"name": E,          "table": f"{E.lower()}s", "key_fields": ["id: uuid", "user_id: uuid", "name: str", "status: str"],  "relationships": ["belongs to User", f"has many {S}s"]},
            {"name": S,          "table": f"{S.lower()}s", "key_fields": ["id: uuid", f"{E.lower()}_id: uuid", "type: str"],         "relationships": [f"belongs to {E}"]},
            {"name": "Settings", "table": "settings",  "key_fields": ["id: uuid", "user_id: uuid", "preferences: json"],            "relationships": ["belongs to User"]},
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
        "tech_decisions": _build_tech_decisions(tech_stack, idea),
    }