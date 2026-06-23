"""
backend/routes/council.py

Council 2.0 — Structured Adversarial Debate System

The fundamental flaw in every "multi-agent" system today:
Five agents with the same training data reading each other's
outputs and converging to the same answer. This is sycophancy
with extra steps — not debate.

What actually fixes it (based on Irving et al. AI Debate 2018,
Constitutional AI Anthropic 2022, Reflexion Shinn 2023):
Agents must COMMIT to positions BEFORE seeing other agents' outputs.

The 5-Round Protocol:
─────────────────────────────────────────────────────────────
ROUND 0: DOMAIN + ROLE ANALYSIS (dynamic, LLM-generated)
  → Detect project domain and role
  → Generate domain-specific knowledge dynamically
  → No hardcoded domain files needed

ROUND 1: BLIND PARALLEL ANALYSIS
  → All 5 agents run simultaneously via asyncio.gather
  → Each agent sees: idea + their skill + intake data ONLY
  → Each commits: position + top risk + reasoning
  → No agent sees any other agent's output

ANTI-SYCOPHANCY GATE
  → Mathematical check: if agreement > 80% → adversarial injection
  → Inject devil's advocate perspective before Round 2
  → Disagreement score tracked throughout

ROUND 2: FORCED CROSS-EXAMINATION
  → Circular assignment: A attacks B, B attacks C, C attacks D,
    D attacks E, E attacks A
  → Each attack must cite ONE specific falsifiable claim
  → Vague attacks ("might not scale") rejected

ROUND 3: DEFENSE UNDER PRESSURE
  → Each agent reads the attack on their Round 1 output
  → Must defend or concede — cannot change fundamental position
  → Updates confidence score based on attack quality

ROUND 4: CHAIRMAN ARBITRATION
  → Reads ALL Round 1 + 2 + 3 outputs
  → Issues verdict with majority + minority dissent
  → Enforces anti-sycophancy threshold
  → Confidence = f(argument quality, not agreement level)
─────────────────────────────────────────────────────────────
"""

import asyncio
import json
import logging
import re
import time
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from skills.skill_loader import (
    compose_agent_prompt,
    compose_chairman_prompt,
    detect_domain,
    load_domain_knowledge,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Agent roster ──────────────────────────────────────────────────────────────

AGENTS = [
    "systems_architect",
    "skeptical_interviewer",
    "career_strategist",
    "risk_engineer",
    "innovation_scout",
]

AGENT_DISPLAY_NAMES = {
    "systems_architect":    "Systems Architect",
    "skeptical_interviewer":"Skeptical Interviewer",
    "career_strategist":    "Career Strategist",
    "risk_engineer":        "Risk Engineer",
    "innovation_scout":     "Innovation Scout",
}


# ── Request model ─────────────────────────────────────────────────────────────

class CouncilRequest(BaseModel):
    project_id: str
    idea: str
    intake: dict
    research_summary: Optional[dict] = None
    advisor_outputs: Optional[list] = None


# ── JSON parsing ──────────────────────────────────────────────────────────────

def parse_agent_json(response: str, agent_name: str, fallback: dict) -> dict:
    """
    Parses agent JSON response with repair for common truncation.
    Never raises — always returns a valid dict.
    """
    try:
        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*',     '', cleaned).strip()
        match   = re.search(r'\{.*\}',  cleaned, re.DOTALL)

        if match:
            raw = match.group()
            # Repair truncation
            open_braces   = raw.count('{') - raw.count('}')
            open_brackets = raw.count('[') - raw.count(']')
            if open_braces > 0 or open_brackets > 0:
                raw = raw.rstrip(',\n\r\t ')
                raw += ']' * open_brackets
                raw += '}' * open_braces
            result = json.loads(raw)
            result["agent_name"] = AGENT_DISPLAY_NAMES.get(agent_name, agent_name)
            return result

    except Exception as e:
        logger.warning(f"JSON parse failed for {agent_name}: {e}")

    fallback["agent_name"] = AGENT_DISPLAY_NAMES.get(agent_name, agent_name)
    return fallback


# ── Round 1: Blind parallel analysis ─────────────────────────────────────────

async def run_round1_agent(
    agent_name: str,
    idea: str,
    intake: dict,
    domain: str,
) -> dict:
    """
    Runs a single agent in Round 1.
    Agent sees ONLY: their skill + idea + intake.
    Agent does NOT see: any other agent's output.
    """
    from services.llm_client import call_fast, call_strong

    display_name = AGENT_DISPLAY_NAMES.get(agent_name, agent_name)

    try:
        system_prompt = await compose_agent_prompt(
            agent_name=agent_name,
            idea=idea,
            intake=intake,
            domain=domain,
        )

        # Chairman and architect use strong model — others use fast
        if agent_name in ("systems_architect",):
            response = await call_strong(
                system=system_prompt,
                user=(
                    f"Analyze this project as {display_name}.\n\n"
                    f"Project: {idea}\n"
                    f"Role applying for: {intake.get('role', 'Engineer')}\n"
                    f"Purpose: {intake.get('purpose', 'portfolio')}\n\n"
                    f"You are in ROUND 1. Commit to your position independently. "
                    f"Return ONLY the JSON object specified in your output contract."
                ),
                max_tokens=1200,
            )
        else:
            response = await call_fast(
                system=system_prompt,
                user=(
                    f"Analyze this project as {display_name}.\n\n"
                    f"Project: {idea}\n"
                    f"Role applying for: {intake.get('role', 'Engineer')}\n"
                    f"Purpose: {intake.get('purpose', 'portfolio')}\n\n"
                    f"You are in ROUND 1. Commit to your position independently. "
                    f"Return ONLY the JSON object specified in your output contract."
                ),
                max_tokens=1000,
            )

        result = parse_agent_json(response, agent_name, {
            "position":   "BUILD",
            "top_risk":   "Analysis incomplete",
            "confidence": 5,
            "reasoning":  "Agent response could not be parsed",
        })

        logger.info(
            f"Round 1 — {display_name}: "
            f"position={result.get('position')} "
            f"confidence={result.get('confidence')}/10"
        )
        return result

    except Exception as e:
        logger.error(f"Round 1 failed for {agent_name}: {e}")
        return {
            "agent_name": display_name,
            "position":   "BUILD",
            "top_risk":   f"Agent {display_name} failed to respond: {str(e)[:100]}",
            "confidence": 3,
            "reasoning":  "Technical failure — treating as abstention",
        }


async def run_round1(
    idea: str,
    intake: dict,
    domain: str,
) -> list[dict]:
    """
    Runs all 5 agents in PARALLEL — true blind analysis.
    No agent waits for or sees another agent's output.
    """
    logger.info("Round 1 — Blind parallel analysis starting")
    start = time.time()

    tasks = [
        run_round1_agent(agent_name, idea, intake, domain)
        for agent_name in AGENTS
    ]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    elapsed = round(time.time() - start, 1)
    logger.info(f"Round 1 complete in {elapsed}s — {len(results)} agents responded")
    return list(results)


# ── Anti-sycophancy gate ──────────────────────────────────────────────────────

def calculate_agreement_score(round1_outputs: list[dict]) -> int:
    """
    Calculates what percentage of agents agreed on the same position.
    High agreement triggers adversarial injection in Round 2.
    """
    positions = [r.get("position", "BUILD") for r in round1_outputs]
    if not positions:
        return 0
    most_common   = max(set(positions), key=positions.count)
    agreement_pct = round((positions.count(most_common) / len(positions)) * 100)
    logger.info(
        f"Agreement score: {agreement_pct}% — "
        f"most common position: {most_common} "
        f"({'⚠️ sycophancy risk' if agreement_pct > 80 else '✓ healthy debate'})"
    )
    return agreement_pct


async def generate_adversarial_injection(
    idea: str,
    intake: dict,
    round1_outputs: list[dict],
) -> str:
    """
    When agreement is too high (>80%), generates a devil's advocate
    perspective to inject into Round 2 attacks.
    This prevents the council from rubber-stamping the obvious answer.
    """
    from services.llm_client import call_fast

    positions_summary = "\n".join([
        f"- {r.get('agent_name')}: {r.get('position')} — {r.get('top_risk', '')}"
        for r in round1_outputs
    ])

    try:
        response = await call_fast(
            system=(
                "You are a devil's advocate. Your job is to find the strongest possible "
                "argument AGAINST the majority position. Be specific and adversarial. "
                "Return 2-3 sentences only — a specific counter-argument."
            ),
            user=(
                f"Project: {idea}\n"
                f"All agents agreed on this direction:\n{positions_summary}\n\n"
                f"Generate the strongest possible counter-argument. "
                f"What specific evidence would prove them all wrong?"
            ),
            max_tokens=300,
        )
        logger.info("Adversarial injection generated for high-agreement council")
        return response.strip()

    except Exception as e:
        logger.warning(f"Adversarial injection failed: {e}")
        return ""


# ── Round 2: Forced cross-examination ────────────────────────────────────────

async def run_round2_attack(
    attacker_name: str,
    target_name: str,
    attacker_round1: dict,
    target_round1: dict,
    idea: str,
    intake: dict,
    adversarial_injection: str = "",
) -> dict:
    """
    One agent attacks another's Round 1 output.
    Attack must be specific and falsifiable — vague attacks are penalized.
    Circular assignment: A→B, B→C, C→D, D→E, E→A
    """
    from services.llm_client import call_fast

    attacker_display = AGENT_DISPLAY_NAMES.get(attacker_name, attacker_name)
    target_display   = AGENT_DISPLAY_NAMES.get(target_name,   target_name)

    injection_text = ""
    if adversarial_injection:
        injection_text = (
            f"\n\nADVERSARIAL CONTEXT (use this to strengthen your attack if relevant):\n"
            f"{adversarial_injection}"
        )

    try:
        response = await call_fast(
            system=(
                f"You are {attacker_display} conducting cross-examination. "
                f"Your job: find the single weakest specific claim in {target_display}'s analysis "
                f"and attack it with concrete counter-evidence. "
                f"Rules: "
                f"1. Cite ONE specific falsifiable claim from their output. "
                f"2. Provide specific counter-evidence — not vague concern. "
                f"3. Rate your attack strength 1-10. "
                f"4. Never be vague — 'it might not scale' is rejected. "
                f"Return ONLY valid JSON."
            ),
            user=(
                f"Project: {idea}\n"
                f"Role: {intake.get('role', 'Engineer')}\n\n"
                f"YOUR Round 1 position: {attacker_round1.get('position')} — "
                f"{attacker_round1.get('reasoning', '')[:300]}\n\n"
                f"TARGET ({target_display}) Round 1 output to attack:\n"
                f"Position: {target_round1.get('position')}\n"
                f"Top Risk: {target_round1.get('top_risk')}\n"
                f"Reasoning: {target_round1.get('reasoning', '')[:400]}"
                f"{injection_text}\n\n"
                f"Return JSON: {{"
                f'"attacker": "{attacker_display}", '
                f'"target": "{target_display}", '
                f'"specific_claim_attacked": "exact quote or paraphrase of their weakest claim", '
                f'"counter_evidence": "your specific counter-argument with evidence", '
                f'"attack_strength": 7, '
                f'"attack_verdict": "why this attack matters for the final decision"'
                f"}}"
            ),
            max_tokens=500,
        )

        result = parse_agent_json(response, attacker_name, {
            "attacker":               attacker_display,
            "target":                 target_display,
            "specific_claim_attacked":"Could not parse attack",
            "counter_evidence":       "Technical failure",
            "attack_strength":        1,
            "attack_verdict":         "Attack failed",
        })

        logger.info(
            f"Round 2 — {attacker_display} → {target_display}: "
            f"strength={result.get('attack_strength')}/10"
        )
        return result

    except Exception as e:
        logger.error(f"Round 2 attack failed {attacker_name}→{target_name}: {e}")
        return {
            "attacker":               attacker_display,
            "target":                 target_display,
            "specific_claim_attacked":"Attack failed due to technical error",
            "counter_evidence":       str(e)[:100],
            "attack_strength":        0,
            "attack_verdict":         "Technical failure",
        }


async def run_round2(
    round1_outputs: list[dict],
    idea: str,
    intake: dict,
    agreement_score: int,
) -> list[dict]:
    """
    Circular cross-examination: A→B, B→C, C→D, D→E, E→A
    If agreement too high: inject adversarial perspective first.
    """
    logger.info(f"Round 2 — Cross-examination starting (agreement={agreement_score}%)")

    # Generate adversarial injection if needed
    adversarial_injection = ""
    if agreement_score > 80:
        logger.warning(f"High agreement detected ({agreement_score}%) — generating adversarial injection")
        adversarial_injection = await generate_adversarial_injection(
            idea, intake, round1_outputs
        )

    # Circular attack assignment
    n = len(AGENTS)
    attack_pairs = [(AGENTS[i], AGENTS[(i + 1) % n]) for i in range(n)]

    round1_by_agent = {
        AGENTS[i]: round1_outputs[i]
        for i in range(min(n, len(round1_outputs)))
    }

    tasks = [
        run_round2_attack(
            attacker_name=attacker,
            target_name=target,
            attacker_round1=round1_by_agent.get(attacker, {}),
            target_round1=round1_by_agent.get(target, {}),
            idea=idea,
            intake=intake,
            adversarial_injection=adversarial_injection,
        )
        for attacker, target in attack_pairs
    ]

    results = await asyncio.gather(*tasks, return_exceptions=False)
    logger.info(f"Round 2 complete — {len(results)} attacks completed")
    return list(results)


# ── Round 3: Defense under pressure ──────────────────────────────────────────

async def run_round3_defense(
    agent_name: str,
    round1_output: dict,
    attack_on_agent: dict,
    idea: str,
    intake: dict,
) -> dict:
    """
    Each agent defends their Round 1 position against the specific attack.
    Can strengthen position or concede — cannot change fundamental position.
    Updates confidence score based on attack quality.
    """
    from services.llm_client import call_fast

    display_name = AGENT_DISPLAY_NAMES.get(agent_name, agent_name)

    try:
        response = await call_fast(
            system=(
                f"You are {display_name} defending your Round 1 analysis. "
                f"Rules: "
                f"1. You committed to {round1_output.get('position')} — you cannot change this unless the attack provides decisive evidence. "
                f"2. Address the SPECIFIC claim attacked — not the general topic. "
                f"3. If the attack is valid: concede that specific point while maintaining overall position. "
                f"4. If the attack is weak: explain specifically why it fails. "
                f"5. Update your confidence score based on the attack quality. "
                f"Return ONLY valid JSON."
            ),
            user=(
                f"Project: {idea}\n\n"
                f"YOUR Round 1 output:\n"
                f"Position: {round1_output.get('position')}\n"
                f"Top Risk: {round1_output.get('top_risk')}\n"
                f"Reasoning: {round1_output.get('reasoning', '')[:400]}\n\n"
                f"ATTACK ON YOU:\n"
                f"Attacker: {attack_on_agent.get('attacker')}\n"
                f"Claim Attacked: {attack_on_agent.get('specific_claim_attacked')}\n"
                f"Counter Evidence: {attack_on_agent.get('counter_evidence')}\n"
                f"Attack Strength: {attack_on_agent.get('attack_strength')}/10\n\n"
                f"Return JSON: {{"
                f'"agent_name": "{display_name}", '
                f'"position_maintained": true, '
                f'"defense": "your specific defense of the attacked claim", '
                f'"concession": "specific point you concede if attack was valid — or null", '
                f'"updated_confidence": 7, '
                f'"attack_quality_assessment": "was this attack strong or weak and why"'
                f"}}"
            ),
            max_tokens=500,
        )

        result = parse_agent_json(response, agent_name, {
            "agent_name":              display_name,
            "position_maintained":     True,
            "defense":                 "Defense could not be parsed",
            "concession":              None,
            "updated_confidence":      round1_output.get("confidence", 5),
            "attack_quality_assessment":"Unknown",
        })

        logger.info(
            f"Round 3 — {display_name} defense: "
            f"maintained={result.get('position_maintained')} "
            f"confidence={result.get('updated_confidence')}/10"
        )
        return result

    except Exception as e:
        logger.error(f"Round 3 defense failed for {agent_name}: {e}")
        return {
            "agent_name":              display_name,
            "position_maintained":     True,
            "defense":                 f"Technical failure: {str(e)[:100]}",
            "concession":              None,
            "updated_confidence":      round1_output.get("confidence", 5),
            "attack_quality_assessment":"Could not assess",
        }


async def run_round3(
    round1_outputs: list[dict],
    round2_attacks: list[dict],
    idea: str,
    intake: dict,
) -> list[dict]:
    """
    Each agent defends against the attack directed at them.
    Attack assignment is circular: agent[i] was attacked by agent[i-1].
    """
    logger.info("Round 3 — Defense under pressure starting")

    n = len(AGENTS)

    # Build attack lookup: target_agent → attack object
    attacks_by_target = {}
    for attack in round2_attacks:
        target_name = attack.get("target", "")
        for agent_display, agent_key in [
            (AGENT_DISPLAY_NAMES[a], a) for a in AGENTS
        ]:
            if target_name == agent_display:
                attacks_by_target[agent_key] = attack
                break

    tasks = [
        run_round3_defense(
            agent_name=AGENTS[i],
            round1_output=round1_outputs[i] if i < len(round1_outputs) else {},
            attack_on_agent=attacks_by_target.get(AGENTS[i], {
                "attacker": "Unknown",
                "specific_claim_attacked": "No attack found",
                "counter_evidence": "",
                "attack_strength": 0,
            }),
            idea=idea,
            intake=intake,
        )
        for i in range(n)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=False)
    logger.info(f"Round 3 complete — {len(results)} defenses submitted")
    return list(results)


# ── Round 4: Chairman arbitration ────────────────────────────────────────────

async def run_chairman(
    idea: str,
    intake: dict,
    round1_outputs: list[dict],
    round2_attacks: list[dict],
    round3_defenses: list[dict],
    agreement_score: int,
    domain: str,
) -> dict:
    """
    Chairman reads ALL rounds and issues final verdict.
    Not a synthesizer — a truth arbitrator.
    Cites specific agents. Issues minority dissent.
    Enforces anti-sycophancy.
    """
    from services.llm_client import call_strong

    logger.info("Round 4 — Chairman arbitration starting")

    try:
        chairman_prompt = await compose_chairman_prompt(
            idea=idea,
            intake=intake,
            round1_outputs=round1_outputs,
            round2_attacks=round2_attacks,
            round3_defenses=round3_defenses,
            domain=domain,
        )

        response = await call_strong(
            system=chairman_prompt,
            user=(
                f"Issue your final verdict for: {idea}\n\n"
                f"Agreement score was {agreement_score}%. "
                f"{'High agreement — weight dissenting views more heavily.' if agreement_score > 80 else 'Normal debate range.'}\n\n"
                f"Return ONLY the JSON verdict specified in your output contract."
            ),
            max_tokens=2000,
        )

        result = parse_agent_json(response, "chairman", {
            "verdict":           "BUILD",
            "confidence_score":  60,
            "verdict_reasoning": "Chairman analysis incomplete",
            "top_risk":          "Unknown",
            "recommended_stack": [],
            "estimated_build_time": "6 weeks",
            "career_value":      "Portfolio project",
            "pivot_suggestion":  None,
            "minority_dissent":  None,
            "sycophancy_warning": agreement_score > 80,
            "disagreement_score": 100 - agreement_score,
            "v1_scope":          [],
            "top_risks":         [],
        })

        result["agreement_score"]    = agreement_score
        result["sycophancy_warning"] = agreement_score > 80

        logger.info(
            f"Chairman verdict: {result.get('verdict')} "
            f"confidence={result.get('confidence_score')} "
            f"sycophancy={'⚠️ YES' if result.get('sycophancy_warning') else '✓ NO'}"
        )
        return result

    except Exception as e:
        logger.error(f"Chairman arbitration failed: {e}")
        return {
            "verdict":            "BUILD",
            "confidence_score":   50,
            "verdict_reasoning":  f"Chairman failed: {str(e)[:200]}",
            "top_risk":           "Technical failure in council",
            "recommended_stack":  [],
            "estimated_build_time":"6 weeks",
            "career_value":       "Portfolio project",
            "pivot_suggestion":   None,
            "minority_dissent":   None,
            "sycophancy_warning": False,
            "disagreement_score": 0,
            "agreement_score":    agreement_score,
            "v1_scope":           [],
            "top_risks":          [],
        }


# ── MCP save ──────────────────────────────────────────────────────────────────

async def save_verdict_to_mcp(project_id: str, verdict: dict):
    """Saves chairman verdict to MCP for future agent access."""
    try:
        from fastmcp import Client
        async with Client("http://localhost:8001/mcp") as mcp:
            await mcp.call_tool(
                "save_council_verdict",
                {
                    "project_id":    project_id,
                    "verdict_json":  json.dumps(verdict),
                },
            )
        logger.info(f"Verdict saved to MCP for: {project_id}")
    except Exception as e:
        logger.warning(f"Could not save verdict to MCP: {e}")


# ── Main endpoint ─────────────────────────────────────────────────────────────

@router.post("/council")
async def run_council(request: Request, body: CouncilRequest):
    """
    Runs the full 5-round adversarial debate council.

    Timeline:
    - Round 0 (domain analysis):    ~2s
    - Round 1 (5 agents parallel):  ~8-15s
    - Anti-sycophancy gate:         ~0.1s (+ ~3s if injection needed)
    - Round 2 (5 attacks parallel): ~8-10s
    - Round 3 (5 defenses parallel):~8-10s
    - Round 4 (chairman):           ~10-15s
    Total:                          ~40-55s
    """
    start = time.time()

    try:
        logger.info(f"Council starting for project: {body.project_id}")
        logger.info(f"Idea: {body.idea[:100]}")
        logger.info(f"Role: {body.intake.get('role')} | Purpose: {body.intake.get('purpose')}")

        # ── Round 0: Domain detection ──────────────────────────────────────
        domain = detect_domain(body.idea)
        logger.info(f"Domain detected: {domain}")

        # ── Round 1: Blind parallel analysis ──────────────────────────────
        round1_outputs = await run_round1(
            idea=body.idea,
            intake=body.intake,
            domain=domain,
        )

        # ── Anti-sycophancy gate ───────────────────────────────────────────
        agreement_score = calculate_agreement_score(round1_outputs)

        # ── Round 2: Cross-examination ────────────────────────────────────
        round2_attacks = await run_round2(
            round1_outputs=round1_outputs,
            idea=body.idea,
            intake=body.intake,
            agreement_score=agreement_score,
        )

        # ── Round 3: Defense ──────────────────────────────────────────────
        round3_defenses = await run_round3(
            round1_outputs=round1_outputs,
            round2_attacks=round2_attacks,
            idea=body.idea,
            intake=body.intake,
        )

        # ── Round 4: Chairman arbitration ─────────────────────────────────
        verdict = await run_chairman(
            idea=body.idea,
            intake=body.intake,
            round1_outputs=round1_outputs,
            round2_attacks=round2_attacks,
            round3_defenses=round3_defenses,
            agreement_score=agreement_score,
            domain=domain,
        )

        # ── Save to MCP ───────────────────────────────────────────────────
        await save_verdict_to_mcp(body.project_id, verdict)

        elapsed = round(time.time() - start, 1)
        logger.info(
            f"Council complete in {elapsed}s — "
            f"verdict={verdict.get('verdict')} "
            f"confidence={verdict.get('confidence_score')}"
        )

        return JSONResponse({
            "success":    True,
            "project_id": body.project_id,
            "result": {
                "verdict":          verdict,
                "advisor_outputs":  round1_outputs,
                "cross_examination":round2_attacks,
                "defenses":         round3_defenses,
                "agreement_score":  agreement_score,
                "domain":           domain,
                "elapsed_seconds":  elapsed,
                "rounds_completed": 4,
            },
        })

    except Exception as e:
        logger.error(f"Council failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error":   str(e),
                "message": "Council debate failed. Please try again.",
            }
        )