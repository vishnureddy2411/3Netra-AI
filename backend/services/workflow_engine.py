"""
backend/services/workflow_engine.py

Workflow Engine — Loop Engineer Implementation

Reads the 10 agent skill YAMLs and executes each build stage.
Controls which agent activates at each stage.
Never builds more than one stage without user approval.

Stage sequence:
  planning → architecture → database_design → frontend_build
  → backend_build → integration → testing → deployment → final_review

Loop Engineer rules enforced here:
  - One stage at a time
  - Approved decisions from previous stages always carried forward
  - Security agent always active during architecture, testing, deployment
  - AI/ML agent activates when project contains ML/AI keywords
  - Never generate future stage work
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

AGENTS_DIR = Path(__file__).parent.parent / "skills" / "agents"

# ── Stage → Agent mapping ─────────────────────────────────────────────────────

STAGE_AGENT_MAP = {
    "planning":       "planning_agent",
    "architecture":   "review_agent",
    "database_design":"database_agent",
    "frontend_build": "frontend_agent",
    "backend_build":  "backend_agent",
    "integration":    "backend_agent",
    "testing":        "testing_agent",
    "deployment":     "devops_agent",
    "final_review":   "review_agent",
}

# Security agent is always active at these stages
SECURITY_ACTIVE_STAGES = {"architecture", "testing", "deployment"}

# ML/AI keywords that trigger aiml_agent in backend_build
AIML_KEYWORDS = [
    "ml", "machine learning", "ai", "artificial intelligence",
    "llm", "rag", "neural", "model training", "embedding",
    "recommendation", "nlp", "computer vision", "deep learning",
    "generative", "fine-tun", "inference", "vector", "classification",
    "detection", "prediction", "forecast", "sentiment",
]

# Ordered stage sequence
STAGE_ORDER = [
    "planning",
    "architecture",
    "database_design",
    "frontend_build",
    "backend_build",
    "integration",
    "testing",
    "deployment",
    "final_review",
]

# Stage display names
STAGE_DISPLAY = {
    "planning":        "Planning",
    "architecture":    "Architecture",
    "database_design": "Database Design",
    "frontend_build":  "Frontend Build",
    "backend_build":   "Backend Build",
    "integration":     "Integration",
    "testing":         "Testing",
    "deployment":      "Deployment",
    "final_review":    "Final Review",
}

# Engineering roles active per stage (from engineering_roles.yaml)
STAGE_ROLES = {
    "planning":        ["Product Engineer", "Tech Lead", "Software Architect"],
    "architecture":    ["Software Architect", "Backend Engineer", "Database Engineer", "Security Engineer", "DevOps Engineer"],
    "database_design": ["Database Engineer", "Data Engineer", "Data Architect", "Data Quality Engineer"],
    "frontend_build":  ["Frontend Engineer", "UI Engineer", "Design Systems Engineer", "Accessibility Engineer"],
    "backend_build":   ["Backend Engineer", "API Engineer", "Integration Engineer", "Platform Engineer"],
    "integration":     ["Full-Stack Engineer", "Integration Engineer", "QA Engineer"],
    "testing":         ["QA Engineer", "SDET", "Test Automation Engineer", "Security Testing Engineer", "Performance Test Engineer"],
    "deployment":      ["DevOps Engineer", "Cloud Engineer", "Site Reliability Engineer / SRE", "CI/CD Engineer"],
    "final_review":    ["Staff Engineer", "Principal Engineer", "Tech Lead", "Software Architect"],
}

# Approval prompts per stage
STAGE_APPROVAL_PROMPTS = {
    "planning":        "Review the project plan. Approve to begin architecture design.",
    "architecture":    "Review the system architecture. Approve to begin database design and coding.",
    "database_design": "Review the database schema. Approve to begin frontend development.",
    "frontend_build":  "Review this component. Approve to continue or request changes.",
    "backend_build":   "Review this endpoint. Approve to continue or request changes.",
    "integration":     "Confirm frontend and backend are connected. Approve to begin testing.",
    "testing":         "Review test results. Approve to proceed to deployment.",
    "deployment":      "Review deployment configuration. Approve to finalize.",
    "final_review":    "Final project review complete.",
}


# ── YAML loader ───────────────────────────────────────────────────────────────

def load_agent_yaml(agent_name: str) -> dict:
    path = AGENTS_DIR / f"{agent_name}.yaml"
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Failed to load agent YAML {agent_name}: {e}")
        return {}


# ── Project type detection ────────────────────────────────────────────────────

def is_ml_project(idea: str) -> bool:
    idea_lower = idea.lower()
    return any(kw in idea_lower for kw in AIML_KEYWORDS)


# ── Active agent resolution ───────────────────────────────────────────────────

def get_active_agents_for_stage(stage: str, idea: str) -> list[str]:
    """
    Returns list of agents to activate for this stage.
    Primary agent is first. Security and ML agents added where needed.
    """
    primary = STAGE_AGENT_MAP.get(stage, "planning_agent")
    agents  = [primary]

    # Security agent always active at these stages
    if stage in SECURITY_ACTIVE_STAGES and "security_agent" not in agents:
        agents.append("security_agent")

    # AI/ML agent activates on backend_build for ML projects
    if stage == "backend_build" and is_ml_project(idea):
        agents.append("aiml_agent")

    return agents


# ── System prompt composer ────────────────────────────────────────────────────

def compose_workflow_system_prompt(
    agent_data:       dict,
    stage:            str,
    project_context:  dict,
) -> str:
    identity        = agent_data.get("identity", {})
    core_rules      = agent_data.get("core_rules", [])
    reasoning_chain = agent_data.get("reasoning_chain", [])
    anti_patterns   = agent_data.get("anti_patterns_to_catch", [])
    green_flags     = agent_data.get("green_flags", [])
    output_contract = agent_data.get("output_contract", {})
    json_schema     = (
        output_contract.get("json_schema", "{}")
        if isinstance(output_contract, dict)
        else "{}"
    )

    rules_str   = "\n".join(f"- {r}" for r in core_rules[:5]) if core_rules else ""
    reason_str  = "\n".join(f"- {r}" for r in reasoning_chain[:8])
    anti_str    = "\n".join(f"- {p}" for p in anti_patterns[:8])
    green_str   = "\n".join(f"- {g}" for g in green_flags[:6])

    idea    = project_context.get("idea", "")
    role    = project_context.get("role", "Engineer")
    purpose = project_context.get("purpose", "portfolio")
    decisions = project_context.get("approved_decisions", {})

    decisions_str = ""
    if decisions:
        decisions_str = "\n\nAPPROVED DECISIONS — carry these forward:\n"
        for s_name, s_data in decisions.items():
            summary = str(s_data)[:400] if s_data else "No data"
            decisions_str += f"\n[{STAGE_DISPLAY.get(s_name, s_name).upper()}]\n{summary}\n"

    prompt = f"""You are: {identity.get('role', 'Senior Engineer')}
Known for: {identity.get('known_for', '')}
Philosophy: {identity.get('philosophy', '')}
Adversarial stance: {identity.get('adversarial_stance', '')}

PROJECT: {idea}
ENGINEER ROLE BEING BUILT FOR: {role}
PURPOSE: {purpose}
CURRENT BUILD STAGE: {STAGE_DISPLAY.get(stage, stage)}{decisions_str}"""

    if rules_str:
        prompt += f"\n\nCORE RULES — NEVER violate these:\n{rules_str}"

    prompt += f"""

REASONING CHAIN — apply in order:
{reason_str}

ANTI-PATTERNS TO CATCH AND AVOID:
{anti_str}

GREEN FLAGS TO AIM FOR:
{green_str}

Return ONLY valid JSON matching this exact schema:
{json_schema}

CRITICAL CONSTRAINTS:
1. Build ONLY what belongs to the {STAGE_DISPLAY.get(stage, stage)} stage
2. Never include work from future stages
3. Every output must be specific to THIS project — no generic boilerplate
4. Reference and follow all approved decisions from previous stages
5. The next stage agent will read your output — make it clear and complete"""

    return prompt


# ── Core stage executor ───────────────────────────────────────────────────────

async def execute_stage(
    stage:           str,
    project_context: dict,
    max_tokens:      int = 2500,
) -> dict:
    """
    Executes a single build stage using the correct agent skill YAML.
    Called by workflow.py for each stage transition.
    Returns structured output with workflow metadata attached.
    """
    from services.llm_client import call_strong

    idea          = project_context.get("idea", "")
    active_agents = get_active_agents_for_stage(stage, idea)
    primary_agent = active_agents[0]

    logger.info(
        f"Workflow Engine — Stage: {stage} | "
        f"Agent: {primary_agent} | "
        f"Supporting: {active_agents[1:]} | "
        f"Project: {idea[:50]}"
    )

    agent_data    = load_agent_yaml(primary_agent)
    system_prompt = compose_workflow_system_prompt(agent_data, stage, project_context)

    try:
        response = await call_strong(
            system=system_prompt,
            user=(
                f"Execute the {STAGE_DISPLAY.get(stage, stage)} stage for this project.\n\n"
                f"Project: {idea}\n"
                f"Engineer Role: {project_context.get('role', 'Engineer')}\n"
                f"Purpose: {project_context.get('purpose', 'portfolio')}\n\n"
                f"Build ONLY what belongs to the {STAGE_DISPLAY.get(stage, stage)} stage. "
                f"Be specific to this project. "
                f"Return ONLY valid JSON as specified in your output contract."
            ),
            max_tokens=max_tokens,
        )

        # Parse with repair
        result = _parse_json_with_repair(response)

    except Exception as e:
        logger.error(f"Stage {stage} LLM call failed: {e}")
        result = {
            "_error": str(e)[:200],
            "_fallback": True,
            "message": f"Stage {stage} encountered an error. Please try again.",
        }

    # Attach workflow metadata — always present regardless of LLM output
    result["_stage"]             = stage
    result["_stage_display"]     = STAGE_DISPLAY.get(stage, stage)
    result["_agent"]             = primary_agent
    result["_active_roles"]      = STAGE_ROLES.get(stage, ["Software Engineer"])
    result["_supporting_agents"] = active_agents[1:]
    result["_approval_prompt"]   = STAGE_APPROVAL_PROMPTS.get(stage, "Review and approve to continue.")
    result["_next_stage"]        = get_next_stage(stage)

    logger.info(f"Stage {stage} complete — agent: {primary_agent}")
    return result


# ── JSON parser with repair ───────────────────────────────────────────────────

def _parse_json_with_repair(response: str) -> dict:
    try:
        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*',     '', cleaned).strip()
        match   = re.search(r'\{.*\}',  cleaned, re.DOTALL)

        if match:
            raw = match.group()
            open_braces   = raw.count('{') - raw.count('}')
            open_brackets = raw.count('[') - raw.count(']')
            if open_braces > 0 or open_brackets > 0:
                raw = raw.rstrip(',\n\r\t ')
                raw += ']' * open_brackets
                raw += '}' * open_braces
            raw = re.sub(r',\s*([}\]])', r'\1', raw)

            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                # Try truncating at last valid position
                pos_match = re.search(r'char (\d+)', str(Exception))
                if pos_match:
                    char_pos = int(pos_match.group(1))
                    raw = raw[:char_pos - 1].rstrip(',\n\r\t ')
                    open_braces   = raw.count('{') - raw.count('}')
                    open_brackets = raw.count('[') - raw.count(']')
                    raw += ']' * open_brackets
                    raw += '}' * open_braces
                    return json.loads(raw)
                raise

    except Exception as e:
        logger.warning(f"JSON parse failed in workflow engine: {e}")
        return {}


# ── Stage navigation helpers ──────────────────────────────────────────────────

def get_next_stage(current_stage: str) -> Optional[str]:
    try:
        idx = STAGE_ORDER.index(current_stage)
        return STAGE_ORDER[idx + 1] if idx + 1 < len(STAGE_ORDER) else None
    except ValueError:
        return None


def get_stage_display(stage: str) -> str:
    return STAGE_DISPLAY.get(stage, stage.replace("_", " ").title())


def get_stage_roles(stage: str) -> list[str]:
    return STAGE_ROLES.get(stage, ["Software Engineer"])


def get_approval_prompt(stage: str) -> str:
    return STAGE_APPROVAL_PROMPTS.get(stage, "Review and approve to continue.")


def is_final_stage(stage: str) -> bool:
    return stage == STAGE_ORDER[-1]