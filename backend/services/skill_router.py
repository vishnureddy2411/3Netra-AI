"""
backend/services/skill_router.py

Maps module types to skill files and returns combined skill content
for injection into Developer agent system prompts.

Maestro composition order enforced:
  Layer 1 — Seniority (senior_backend, senior_frontend, etc.)
  Layer 2 — Domain    (rag_architect, security_auditor, etc.)
  Layer 3 — Process   (api_test_suite, a11y_audit, webapp_testing, etc.)

All skill files loaded into memory at FastAPI startup (see main.py @startup).
Zero disk I/O after startup.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

SKILLS_DIR = Path("prompts/skills")

# ── In-memory cache ───────────────────────────────────────────────────────────
# Populated once at startup via load_all_skills().
# Never read from disk inside a request handler.
SKILL_CACHE: dict[str, str] = {}


def load_all_skills() -> None:
    """
    Call once at FastAPI startup.
    Loads all .md files from prompts/skills/ into SKILL_CACHE.

    In main.py:
        @app.on_event("startup")
        async def startup():
            skill_router.load_all_skills()
    """
    if not SKILLS_DIR.exists():
        logger.warning("skills_dir_missing", extra={"path": str(SKILLS_DIR)})
        return

    loaded = 0
    for skill_file in SKILLS_DIR.glob("*.md"):
        skill_name = skill_file.stem  # filename without .md
        SKILL_CACHE[skill_name] = skill_file.read_text(encoding="utf-8")
        loaded += 1

    logger.info("skills_loaded", extra={"count": loaded, "skills": list(SKILL_CACHE.keys())})


# ── Module → Skill mapping ────────────────────────────────────────────────────
# Key = module_type string returned by classify_module()
# Value = ordered list of skill names (seniority → domain → process)
MODULE_SKILL_MAP: dict[str, list[str]] = {

    # Backend modules
    "auth":                ["senior_backend", "security_auditor", "observability", "api_test_suite"],
    "rest_api":            ["senior_backend", "api_design", "observability", "api_test_suite"],
    "rag_pipeline":        ["senior_backend", "rag_architect", "performance", "observability", "api_test_suite"],
    "database":            ["senior_backend", "database_designer", "performance", "observability"],
    "agent_pipeline":      ["senior_backend", "agent_workflow", "rag_architect", "observability"],
    "payment":             ["senior_backend", "security_auditor", "api_design", "observability"],
    "performance_critical":["senior_backend", "performance", "observability", "api_test_suite"],
    "existing_db_migration":["senior_backend", "database_designer", "migration", "observability"],

    # Frontend modules
    "frontend_page":       ["senior_frontend", "frontend_design", "a11y_audit", "observability", "webapp_testing"],
    "dashboard":           ["senior_frontend", "frontend_design", "a11y_audit", "observability"],
    "shared_components":   ["senior_fullstack", "frontend_design", "a11y_audit"],

    # Full-stack features
    "full_stack_feature":  ["senior_fullstack", "senior_backend", "frontend_design", "observability"],

    # Infrastructure
    "deployment":          ["senior_devops", "ci_cd", "observability"],

    # Special agents
    "career_output":       ["career_writer", "pr_review"],
    "quiz":                ["quiz_tutor"],

    # Fallback
    "unknown":             ["senior_fullstack", "observability"],
}


def get_skills(module_type: str) -> str:
    """
    Returns combined skill content for a module type.
    Skills merged in composition order with --- separator.
    If module_type not in map: falls back to senior_fullstack + observability.
    """
    skill_names = MODULE_SKILL_MAP.get(module_type, MODULE_SKILL_MAP["unknown"])

    if not SKILL_CACHE:
        logger.warning("skill_cache_empty_at_call_time", extra={"module_type": module_type})
        return ""

    sections = []
    for name in skill_names:
        content = SKILL_CACHE.get(name)
        if content:
            sections.append(content)
        else:
            logger.warning("skill_not_found", extra={"skill": name, "module_type": module_type})

    return "\n\n---\n\n".join(sections)


async def classify_module(module_name: str, tech_stack: list[str]) -> str:
    """
    Classify a module name into one of the MODULE_SKILL_MAP keys.
    Uses one cheap Haiku call.
    Falls back to keyword matching if Haiku call fails.

    Returns: module_type string (key in MODULE_SKILL_MAP)
    """
    # Fast keyword fallback — avoids API call for obvious cases
    name_lower = module_name.lower()
    keyword_map = {
        ("auth", "login", "register", "guard", "jwt", "session"): "auth",
        ("embed", "vector", "rag", "search", "semantic", "match"): "rag_pipeline",
        ("schema", "migration", "model", "table", "database"): "database",
        ("api", "route", "endpoint", "handler", "controller"): "rest_api",
        ("dashboard", "analytics", "chart", "graph", "report"): "dashboard",
        ("page", "ui", "component", "form", "modal", "layout"): "frontend_page",
        ("agent", "advisor", "council", "pipeline", "orchestrat"): "agent_pipeline",
        ("payment", "stripe", "checkout", "billing", "invoice"): "payment",
        ("deploy", "docker", "railway", "vercel", "ci", "cd"): "deployment",
        ("migrate", "alter", "backfill", "existing"): "existing_db_migration",
        ("navbar", "footer", "button", "card", "shared", "util"): "shared_components",
        ("readme", "linkedin", "resume", "career", "portfolio", "pr"): "career_output",
        ("quiz", "tutor", "question", "explain"): "quiz",
        ("performance", "cache", "pool", "optimiz"): "performance_critical",
    }

    for keywords, module_type in keyword_map.items():
        if any(kw in name_lower for kw in keywords):
            logger.info("module_classified_by_keyword", extra={
                "module": module_name,
                "type": module_type
            })
            return module_type

    # LLM classification for ambiguous cases
    try:
        from services.claude_client import call_haiku
        from models.agent_outputs import ModuleClassification

        system = (
            "You classify software module names into module types. "
            "Return ONLY valid JSON. No explanation.\n\n"
            f"Valid types: {list(MODULE_SKILL_MAP.keys())}"
        )
        user = (
            f"Module name: {module_name}\n"
            f"Tech stack: {', '.join(tech_stack)}\n\n"
            "Return: {\"module_type\": \"<type>\", \"confidence\": <0-100>, \"reasoning\": \"<one sentence>\"}"
        )
        raw = await call_haiku(system=system, user=user, max_tokens=100)
        result, error = ModuleClassification.parse_safe(raw)
        if result:
            logger.info("module_classified_by_llm", extra={
                "module": module_name,
                "type": result.module_type,
                "confidence": result.confidence
            })
            return result.module_type
    except Exception as e:
        logger.warning("llm_classification_failed", extra={"error": str(e)})

    return "unknown"


def get_skills_for_module(module_name: str, resolved_type: str) -> str:
    """
    Convenience function: given module name and already-resolved type,
    return the combined skill content. Use this in code_gen.py after
    classify_module() has already been awaited.
    """
    content = get_skills(resolved_type)
    logger.info("skills_injected", extra={
        "module": module_name,
        "type": resolved_type,
        "skills": MODULE_SKILL_MAP.get(resolved_type, ["unknown"]),
        "content_length": len(content),
    })
    return content
