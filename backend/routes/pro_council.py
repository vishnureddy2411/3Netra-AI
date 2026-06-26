"""
backend/routes/pro_council.py

Professional Council — 3-Round Enterprise Problem Solving

Activates when userType = 'professional'.
Unlike student council which evaluates portfolio value,
this council focuses entirely on:
  - Technical architecture correctness
  - Security risks in the proposed solution
  - Delivery feasibility and team execution
  - Business ROI and stakeholder justification

5 Pro Agents + Pro Chairman:
  senior_architect, security_engineer, devops_engineer,
  backend_engineer, tech_lead → pro_chairman

3-Round Protocol:
  Round 1: All 5 agents analyze independently (parallel)
  Round 2: Circular cross-examination (A→B, B→C, C→D, D→E, E→A)
  Round 3: Pro Chairman arbitration → execution plan
"""

import asyncio
import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Agent roster ──────────────────────────────────────────────────────────────

PRO_AGENTS = [
    "senior_architect",
    "security_engineer",
    "devops_engineer",
    "backend_engineer",
    "tech_lead",
]

PRO_AGENT_DISPLAY = {
    "senior_architect":  "Senior Architect",
    "security_engineer": "Security Engineer",
    "devops_engineer":   "DevOps Engineer",
    "backend_engineer":  "Backend Engineer",
    "tech_lead":         "Tech Lead",
}

SKILLS_DIR = Path(__file__).parent.parent / "skills" / "agents" / "pro"


# ── Request model ─────────────────────────────────────────────────────────────

class ProCouncilRequest(BaseModel):
    project_id: str
    task: str
    role: str
    context: Optional[str] = ""


# ── YAML loader ───────────────────────────────────────────────────────────────

def load_pro_yaml(agent_name: str) -> dict:
    path = SKILLS_DIR / f"{agent_name}.yaml"
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Failed to load pro YAML {agent_name}: {e}")
        return {}


# ── Prompt composer ───────────────────────────────────────────────────────────

def compose_pro_agent_prompt(agent_data: dict, task: str, role: str) -> str:
    identity       = agent_data.get("identity", {})
    reasoning      = agent_data.get("reasoning_chain", [])
    anti_patterns  = agent_data.get("anti_patterns_to_catch", [])
    green_flags    = agent_data.get("green_flags", [])
    output_contract= agent_data.get("output_contract", {})
    json_schema    = output_contract.get("json_schema", "{}") if isinstance(output_contract, dict) else "{}"

    reasoning_str  = "\n".join(f"- {r}" for r in reasoning)
    anti_str       = "\n".join(f"- {p}" for p in anti_patterns)
    green_str      = "\n".join(f"- {g}" for g in green_flags)

    return f"""You are: {identity.get('role', 'Senior Engineer')}
Known for: {identity.get('known_for', '')}
Philosophy: {identity.get('philosophy', '')}
Adversarial stance: {identity.get('adversarial_stance', '')}

BUSINESS TASK: {task}
ENGINEER ROLE: {role}

REASONING CHAIN — apply these in order:
{reasoning_str}

ANTI-PATTERNS TO CATCH:
{anti_str}

GREEN FLAGS TO RECOGNIZE:
{green_str}

Return ONLY valid JSON matching this exact schema:
{json_schema}"""


# ── JSON parser ───────────────────────────────────────────────────────────────

def parse_pro_json(response: str, agent_name: str) -> dict:
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
            result = json.loads(raw)
            result["agent_name"] = PRO_AGENT_DISPLAY.get(agent_name, agent_name)
            return result
    except Exception as e:
        logger.warning(f"Pro JSON parse failed for {agent_name}: {e}")

    return {
        "agent_name": PRO_AGENT_DISPLAY.get(agent_name, agent_name),
        "position":   "PROCEED",
        "top_risk":   "Analysis incomplete — parse failed",
        "confidence": 5,
        "reasoning":  "Could not parse agent response",
    }


# ── Round 1: Blind parallel analysis ─────────────────────────────────────────

async def run_pro_round1_agent(agent_name: str, task: str, role: str) -> dict:
    from services.llm_client import call_fast, call_strong

    agent_data = load_pro_yaml(agent_name)
    system     = compose_pro_agent_prompt(agent_data, task, role)

    try:
        # Architect uses strong model — others use fast
        if agent_name in ("senior_architect", "security_engineer"):
            response = await call_strong(
                system=system,
                user=(
                    f"Analyze this business problem independently as {PRO_AGENT_DISPLAY[agent_name]}.\n\n"
                    f"Task: {task}\n"
                    f"Engineer Role: {role}\n\n"
                    f"Commit to your position. Do not wait for other agents. "
                    f"Return ONLY the JSON object specified in your output contract."
                ),
                max_tokens=1200,
            )
        else:
            response = await call_fast(
                system=system,
                user=(
                    f"Analyze this business problem independently as {PRO_AGENT_DISPLAY[agent_name]}.\n\n"
                    f"Task: {task}\n"
                    f"Engineer Role: {role}\n\n"
                    f"Commit to your position. Do not wait for other agents. "
                    f"Return ONLY the JSON object specified in your output contract."
                ),
                max_tokens=1000,
            )

        result = parse_pro_json(response, agent_name)
        logger.info(
            f"Pro Round 1 — {PRO_AGENT_DISPLAY[agent_name]}: "
            f"position={result.get('position')} "
            f"confidence={result.get('confidence')}/10"
        )
        return result

    except Exception as e:
        logger.error(f"Pro Round 1 failed for {agent_name}: {e}")
        return {
            "agent_name": PRO_AGENT_DISPLAY.get(agent_name, agent_name),
            "position":   "PROCEED",
            "top_risk":   f"Agent failed: {str(e)[:100]}",
            "confidence": 3,
            "reasoning":  "Technical failure — treating as abstention",
        }


async def run_pro_round1(task: str, role: str) -> list[dict]:
    logger.info("Pro Round 1 — Blind parallel analysis starting")
    start  = time.time()
    tasks  = [run_pro_round1_agent(a, task, role) for a in PRO_AGENTS]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    logger.info(f"Pro Round 1 complete in {round(time.time()-start,1)}s")
    return list(results)


# ── Round 2: Cross-examination ────────────────────────────────────────────────

async def run_pro_round2_attack(
    attacker_name: str,
    target_name:   str,
    attacker_r1:   dict,
    target_r1:     dict,
    task:          str,
    role:          str,
) -> dict:
    from services.llm_client import call_fast

    attacker_display = PRO_AGENT_DISPLAY.get(attacker_name, attacker_name)
    target_display   = PRO_AGENT_DISPLAY.get(target_name, target_name)

    try:
        response = await call_fast(
            system=(
                f"You are {attacker_display} conducting a technical cross-examination. "
                f"Find the single weakest specific claim in {target_display}'s analysis "
                f"and attack it with concrete counter-evidence from your engineering perspective. "
                f"Rules: cite one specific falsifiable claim. Give specific counter-evidence. "
                f"Return ONLY valid JSON."
            ),
            user=(
                f"Task: {task}\n"
                f"Role: {role}\n\n"
                f"TARGET ({target_display}) analysis:\n"
                f"Position: {target_r1.get('position')}\n"
                f"Top Risk: {target_r1.get('top_risk')}\n"
                f"Reasoning: {str(target_r1.get('reasoning', ''))[:300]}\n\n"
                f"Return JSON: {{"
                f'"attacker": "{attacker_display}", '
                f'"target": "{target_display}", '
                f'"claim_attacked": "specific claim from their analysis", '
                f'"counter_evidence": "your specific counter-argument", '
                f'"attack_strength": 7, '
                f'"why_it_matters": "how this affects the business decision"'
                f"}}"
            ),
            max_tokens=400,
        )
        result = parse_pro_json(response, attacker_name)
        logger.info(
            f"Pro Round 2 — {attacker_display} → {target_display}: "
            f"strength={result.get('attack_strength')}/10"
        )
        return result

    except Exception as e:
        logger.error(f"Pro Round 2 attack failed {attacker_name}→{target_name}: {e}")
        return {
            "attacker":       attacker_display,
            "target":         target_display,
            "claim_attacked": "Attack failed",
            "counter_evidence": str(e)[:100],
            "attack_strength": 0,
            "why_it_matters":  "Technical failure",
        }


async def run_pro_round2(
    task:           str,
    role:           str,
    round1_outputs: list[dict],
) -> list[dict]:
    logger.info("Pro Round 2 — Cross-examination starting")

    n = len(PRO_AGENTS)
    attack_pairs = [(PRO_AGENTS[i], PRO_AGENTS[(i + 1) % n]) for i in range(n)]
    r1_by_agent  = {PRO_AGENTS[i]: round1_outputs[i] for i in range(min(n, len(round1_outputs)))}

    tasks = [
        run_pro_round2_attack(
            attacker_name=attacker,
            target_name=target,
            attacker_r1=r1_by_agent.get(attacker, {}),
            target_r1=r1_by_agent.get(target, {}),
            task=task,
            role=role,
        )
        for attacker, target in attack_pairs
    ]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    logger.info(f"Pro Round 2 complete — {len(results)} attacks")
    return list(results)


# ── Round 3: Pro Chairman arbitration ────────────────────────────────────────

async def run_pro_chairman(
    task:           str,
    role:           str,
    round1_outputs: list[dict],
    round2_attacks: list[dict],
) -> dict:
    from services.llm_client import call_strong

    logger.info("Pro Chairman — Arbitration starting")

    chairman_data  = load_pro_yaml("pro_chairman")
    identity       = chairman_data.get("identity", {})
    reasoning      = chairman_data.get("reasoning_chain", [])
    anti_patterns  = chairman_data.get("anti_patterns_to_catch", [])
    output_contract= chairman_data.get("output_contract", {})
    json_schema    = output_contract.get("json_schema", "{}") if isinstance(output_contract, dict) else "{}"

    reasoning_str  = "\n".join(f"- {r}" for r in reasoning)
    anti_str       = "\n".join(f"- {p}" for p in anti_patterns)

    r1_summary = "\n".join([
        f"{o.get('agent_name')}: {o.get('position')} — confidence={o.get('confidence')}/10\n"
        f"  Top Risk: {o.get('top_risk', '')}\n"
        f"  Reasoning: {str(o.get('reasoning', ''))[:200]}"
        for o in round1_outputs
    ])

    r2_summary = "\n".join([
        f"{a.get('attacker')} → {a.get('target')} (strength={a.get('attack_strength')}/10): "
        f"{str(a.get('counter_evidence', ''))[:150]}"
        for a in round2_attacks
    ])

    try:
        response = await call_strong(
            system=f"""You are: {identity.get('role', 'VP of Engineering')}
Known for: {identity.get('known_for', '')}
Philosophy: {identity.get('philosophy', '')}
Adversarial stance: {identity.get('adversarial_stance', '')}

REASONING CHAIN:
{reasoning_str}

ANTI-PATTERNS IN ARBITRATION:
{anti_str}

Return ONLY valid JSON matching this exact schema:
{json_schema}""",
            user=(
                f"Business Task: {task}\n"
                f"Engineer Role: {role}\n\n"
                f"ROUND 1 — Agent Analyses:\n{r1_summary}\n\n"
                f"ROUND 2 — Cross-Examinations:\n{r2_summary}\n\n"
                f"Produce the final execution plan.\n\n"
            f"CRITICAL RULE: blocking_issues must only contain things the USER needs to provide "
            f"that the agents cannot decide for themselves — such as missing business requirements "
            f"(peak load numbers, budget, compliance requirements, existing infrastructure details).\n"
            f"NEVER put architectural decisions in blocking_issues. "
            f"Idempotency strategy, queue choice, failover design, security approach — "
            f"these are YOUR decisions. Put them in the execution_plan, not in blocking_issues.\n"
            f"If you have enough information to make a technical decision, MAKE IT. "
            f"Only block when you genuinely cannot proceed without input from the user.\n\n"
            f"Cite at least 2 specific agents by name in your reasoning.\n\n"
            f"CRITICAL: If the context contains 'BLOCKER RESOLUTIONS' or agent-made assumptions, "
            f"extract each assumption into the 'resolved_assumptions' field as a list of objects "
            f"with 'blocker' and 'assumption' keys. This shows users exactly what was decided "
            f"on their behalf.\n\n"
            f"Return ONLY valid JSON."
            ),
            max_tokens=2500,
        )
        result = parse_pro_json(response, "pro_chairman")
        logger.info(
            f"Pro Chairman verdict: {result.get('verdict')} "
            f"confidence={result.get('confidence_score')}"
        )
        return result

    except Exception as e:
        logger.error(f"Pro Chairman failed: {e}")
        return {
            "verdict":               "PROCEED_WITH_CONDITIONS",
            "primary_recommendation":"Analysis failed — please retry",
            "executive_summary":     f"Technical error: {str(e)[:150]}",
            "execution_plan":        [],
            "blocking_issues":       [],
            "conditions":            [],
            "key_tradeoffs":         [],
            "confidence_score":      50,
            "minority_dissent":      None,
            "clarifying_questions":  [],
            "first_action":          "Retry the analysis",
        }


# ── MCP save ──────────────────────────────────────────────────────────────────

async def save_pro_verdict_to_mcp(project_id: str, verdict: dict):
    try:
        from fastmcp import Client
        async with Client("http://localhost:8001/mcp") as mcp:
            await mcp.call_tool("save_council_verdict", {
                "project_id":   project_id,
                "verdict_json": json.dumps(verdict),
            })
        logger.info(f"Pro verdict saved to MCP for: {project_id}")
    except Exception as e:
        logger.warning(f"Could not save pro verdict to MCP: {e}")


# ── Main endpoint ─────────────────────────────────────────────────────────────

@router.post("/pro-council")
async def run_pro_council(request: Request, body: ProCouncilRequest):
    """
    Runs the 3-round professional council for business problem analysis.

    Timeline:
    - Round 1 (5 agents parallel): ~10-15s
    - Round 2 (5 attacks parallel): ~8-10s
    - Round 3 (chairman):           ~15-20s
    Total: ~35-45s
    """
    start = time.time()

    try:
        logger.info(f"Pro Council starting — project: {body.project_id}")
        logger.info(f"Task: {body.task[:100]} | Role: {body.role}")

        # Round 1 — Blind parallel analysis
        round1_outputs = await run_pro_round1(body.task, body.role)

        # Round 2 — Cross-examination
        round2_attacks = await run_pro_round2(body.task, body.role, round1_outputs)

        # Round 3 — Chairman arbitration
        verdict = await run_pro_chairman(body.task, body.role, round1_outputs, round2_attacks)

        # Save to MCP for workflow engine access
        await save_pro_verdict_to_mcp(body.project_id, verdict)

        elapsed = round(time.time() - start, 1)
        logger.info(f"Pro Council complete in {elapsed}s")

        return JSONResponse({
            "success":    True,
            "project_id": body.project_id,
            "result": {
                "verdict":          verdict,
                "agent_outputs":    round1_outputs,
                "cross_examination":round2_attacks,
                "elapsed_seconds":  elapsed,
                "rounds_completed": 3,
                "mode":             "professional",
            },
        })

    except Exception as e:
        logger.error(f"Pro Council failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e), "message": "Pro Council failed. Please retry."},
        )