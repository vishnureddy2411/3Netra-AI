"""
backend/services/council.py

PERMANENT FIX for pivot_suggestion never being null:
  Level 1: Chairman prompt explicitly forbids null
  Level 2: ensure_pivot_suggestion() runs as fallback
  Level 3: Emergency fallback in run_war_room

This means comparison card will ALWAYS have content to show.
"""

import asyncio
import json
import logging
import re
import time

logger = logging.getLogger(__name__)


def get_advisor_prompts(purpose: str, role: str) -> dict:
    purpose_context = {
        "portfolio": f"The user wants to get hired as {role or 'a software engineer'} and is building a portfolio project. Evaluate through the lens of what impresses hiring managers, passes ATS screening, and gets interviews.",
        "startup": "The user wants to build a real business. Evaluate through market opportunity and sustainable competitive advantage.",
        "learning": f"The user wants to learn{' for ' + role if role else ''}. Evaluate through the lens of the best skill-building path.",
    }.get(purpose, f"The user wants to build a project{' for ' + role + ' roles' if role else ''}.")

    return {
        "tech_lead": f"""{purpose_context}

You are a Senior Tech Lead with 15 years of production engineering experience.
Evaluate technical feasibility, build complexity, and stack appropriateness.
Name actual technologies. Be specific about build challenges and timelines.

Return ONLY this JSON:
{{
    "advisor": "tech_lead",
    "stance": "BUILD or PIVOT or ABANDON",
    "confidence": "high or medium or low",
    "key_finding": "one specific concrete technical finding about THIS exact project",
    "evidence": "specific technical reasoning naming actual technologies and patterns",
    "recommended_stack": ["tech1", "tech2", "tech3", "tech4", "tech5"],
    "missing_tech": ["missing technology for this purpose"],
    "timeline_weeks": 6,
    "risk": "one specific technical risk for THIS project",
    "recommendation": "one concrete actionable technical suggestion",
    "enhanced_version": "one sentence: a more impressive version of this project using specific technologies"
}}""",

        "market_analyst": f"""{purpose_context}

You are a Market Research Analyst specialized in developer tools and technical products.
Evaluate market size, competition, and opportunity with specific signals.
Name actual competing products and specific market dynamics.

Return ONLY this JSON:
{{
    "advisor": "market_analyst",
    "stance": "BUILD or PIVOT or ABANDON",
    "confidence": "high or medium or low",
    "key_finding": "one specific market insight about THIS project space",
    "evidence": "specific market signals — name actual competitors or trends",
    "competition_level": "low or medium or high",
    "specific_competitors": ["competitor1", "competitor2"],
    "market_gap": "specific unmet need this could address",
    "risk": "one specific market risk",
    "recommendation": "one concrete market positioning suggestion",
    "enhanced_version": "one sentence: a more differentiated version targeting the identified gap"
}}""",

        "risk_manager": f"""{purpose_context}

You are a Risk Manager who finds project failure modes before they happen.
Be pessimistic. Find what others miss. Name specific failure scenarios.

Return ONLY this JSON:
{{
    "advisor": "risk_manager",
    "stance": "BUILD or PIVOT or ABANDON",
    "confidence": "high or medium or low",
    "key_finding": "the single biggest risk for THIS specific project",
    "evidence": "specific reasoning about why this risk is real",
    "top_risks": [
        "specific risk 1 with concrete consequence",
        "specific risk 2 with concrete consequence",
        "specific risk 3 with concrete consequence"
    ],
    "fatal_flaw": "the one thing that could completely kill this project",
    "risk": "one specific execution risk",
    "recommendation": "one concrete risk mitigation suggestion",
    "enhanced_version": "one sentence: a version of this project that avoids the fatal flaw"
}}""",

        "ux_designer": f"""{purpose_context}

You are a Senior UX Designer and product strategist.
Think from the actual user's perspective. Be specific about who uses this and why.

Return ONLY this JSON:
{{
    "advisor": "ux_designer",
    "stance": "BUILD or PIVOT or ABANDON",
    "confidence": "high or medium or low",
    "key_finding": "one specific UX or product insight about THIS project",
    "evidence": "specific reasoning about users and value proposition",
    "target_user": "specific description of who would actually use this",
    "core_value_prop": "one sentence why someone chooses this over alternatives",
    "v1_features": [
        "essential MVP feature 1",
        "essential MVP feature 2",
        "essential MVP feature 3"
    ],
    "risk": "one specific UX or product risk",
    "recommendation": "one concrete product improvement suggestion",
    "enhanced_version": "one sentence: a version with stronger product differentiation"
}}""",

        "career_coach": f"""{purpose_context}

You are a Career Coach who has helped 500+ engineers get hired at top companies.
You know exactly what gets resumes shortlisted and what gets them ignored.

Return ONLY this JSON:
{{
    "advisor": "career_coach",
    "stance": "BUILD or PIVOT or ABANDON",
    "confidence": "high or medium or low",
    "key_finding": "one specific career insight about THIS project for {role}",
    "evidence": "specific reasoning about career impact and hiring signals",
    "skills_demonstrated": [
        "specific skill 1 this project proves",
        "specific skill 2 this project proves",
        "specific skill 3 this project proves"
    ],
    "skills_missing": [
        "important skill for {role} NOT demonstrated by this project"
    ],
    "career_value": "one sentence on career ROI of building this",
    "role_match_score": 72,
    "risk": "one specific career risk of building this project",
    "recommendation": "one concrete career-focused improvement suggestion",
    "enhanced_version": "one sentence: a version with stronger career signal for {role}"
}}""",
    }


async def call_advisor(
    advisor_name: str,
    system_prompt: str,
    research_report: str,
    idea: str,
    target_role: str,
) -> dict:
    try:
        from services.llm_client import call_fast

        response = await call_fast(
            system=system_prompt,
            user=f"""IDEA TO EVALUATE: {idea}
TARGET ROLE: {target_role}
MARKET RESEARCH: {research_report[:1500] if research_report else 'No research data'}

Evaluate this specific idea. Return ONLY the JSON structure. No markdown, no explanation.""",
            max_tokens=600,
        )

        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*', '', cleaned).strip()
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)

        if match:
            data = json.loads(match.group())
            logger.info(f"{advisor_name}: {data.get('stance')} ({data.get('confidence')})")
            return data

        logger.warning(f"{advisor_name} returned unparseable response")
        return {
            "advisor": advisor_name,
            "stance": "PIVOT",
            "confidence": "low",
            "key_finding": "Could not parse response",
            "evidence": "",
            "risk": "Unknown",
            "recommendation": "",
            "enhanced_version": "",
        }

    except Exception as e:
        logger.error(f"Advisor {advisor_name} failed: {e}")
        return {
            "advisor": advisor_name,
            "stance": "PIVOT",
            "confidence": "low",
            "key_finding": f"Error: {str(e)[:100]}",
            "evidence": "",
            "risk": "Advisor unavailable",
            "recommendation": "",
            "enhanced_version": "",
        }


async def run_peer_review(advisor_outputs: list[dict], idea: str) -> str:
    try:
        from services.llm_client import call_fast

        stances = [
            f"{a.get('advisor')}: {a.get('stance')} — {a.get('key_finding', '')}"
            for a in advisor_outputs
        ]

        response = await call_fast(
            system="Synthesize expert advisor findings. Be concise and specific. Reference advisors by name.",
            user=f"""Idea: {idea}

Findings:
{chr(10).join(stances)}

In 2-3 sentences: where do advisors agree, where disagree, and what is the single most important finding?""",
            max_tokens=200,
        )
        return response.strip()
    except Exception as e:
        logger.error(f"Peer review failed: {e}")
        stances = [f"{a.get('advisor')}: {a.get('stance')}" for a in advisor_outputs]
        return f"Advisor stances: {', '.join(stances)}"


async def ensure_pivot_suggestion(
    idea: str,
    verdict: str,
    role: str,
    enhanced_versions: list[str],
) -> str:
    """
    PERMANENT GUARANTEE: pivot_suggestion is NEVER null.

    Priority order:
    1. Use advisor enhanced_version suggestions (already generated, free)
    2. Generate via Haiku call (cheap fallback)
    3. String concatenation (emergency fallback, never fails)
    """
    # Priority 1: Use advisor enhanced versions
    valid = [e for e in enhanced_versions if e and len(str(e).strip()) > 20]
    if valid:
        logger.info(f"Using advisor enhanced_version as pivot: {valid[0][:60]}")
        return valid[0].strip()

    # Priority 2: Generate via Haiku
    try:
        from services.llm_client import call_fast

        prompt = f"""Original project idea: {idea}
Expert verdict: {verdict}
Target role: {role}

Write ONE sentence describing a more impressive, differentiated, or enhanced version 
of this project that would be stronger for someone targeting {role}.
Be specific — name actual technologies or approaches.
Return ONLY the one sentence."""

        response = await call_fast(
            system="You suggest specific enhanced project ideas in one sentence.",
            user=prompt,
            max_tokens=100,
        )
        result = response.strip()
        if result and len(result) > 15:
            logger.info(f"Generated pivot via Haiku: {result[:60]}")
            return result
    except Exception as e:
        logger.error(f"Haiku pivot generation failed: {e}")

    # Priority 3: Emergency string fallback (never fails)
    logger.warning("Using emergency string fallback for pivot_suggestion")
    return (
        f"Enhanced {idea[:40].strip()}... with production-grade monitoring, "
        f"comprehensive test coverage, CI/CD pipeline, and Docker deployment "
        f"demonstrating senior {role} engineering practices"
    )


async def run_chairman(
    advisor_outputs: list[dict],
    peer_review: str,
    idea: str,
    target_role: str,
    purpose: str,
) -> dict:
    try:
        from services.llm_client import call_strong

        tech = next((a for a in advisor_outputs if a.get('advisor') == 'tech_lead'), {})
        mkt = next((a for a in advisor_outputs if a.get('advisor') == 'market_analyst'), {})
        risk = next((a for a in advisor_outputs if a.get('advisor') == 'risk_manager'), {})
        ux = next((a for a in advisor_outputs if a.get('advisor') == 'ux_designer'), {})
        career = next((a for a in advisor_outputs if a.get('advisor') == 'career_coach'), {})

        votes = {"BUILD": 0, "PIVOT": 0, "ABANDON": 0}
        for a in advisor_outputs:
            s = a.get("stance", "PIVOT").upper()
            if s in votes:
                votes[s] += 1

        findings = f"""
TECH LEAD ({tech.get('stance')}): {tech.get('key_finding')}
  Recommended stack: {', '.join(tech.get('recommended_stack', []))}
  Missing: {', '.join(tech.get('missing_tech', []))}
  Timeline: {tech.get('timeline_weeks')} weeks
  Enhanced version idea: {tech.get('enhanced_version')}

MARKET ({mkt.get('stance')}): {mkt.get('key_finding')}
  Competition: {mkt.get('competition_level')} | Competitors: {', '.join(mkt.get('specific_competitors', []))}
  Market gap: {mkt.get('market_gap')}
  Enhanced version idea: {mkt.get('enhanced_version')}

RISK ({risk.get('stance')}): {risk.get('key_finding')}
  Fatal flaw: {risk.get('fatal_flaw')}
  Top risks: {'; '.join(risk.get('top_risks', []))}
  Enhanced version idea: {risk.get('enhanced_version')}

UX ({ux.get('stance')}): {ux.get('key_finding')}
  Target user: {ux.get('target_user')}
  V1 features: {'; '.join(ux.get('v1_features', []))}

CAREER ({career.get('stance')}): {career.get('key_finding')}
  Skills shown: {', '.join(career.get('skills_demonstrated', []))}
  Skills missing: {', '.join(career.get('skills_missing', []))}
  Role match score: {career.get('role_match_score', 50)}
  Enhanced version idea: {career.get('enhanced_version')}

PEER REVIEW: {peer_review}
VOTES: BUILD={votes['BUILD']}, PIVOT={votes['PIVOT']}, ABANDON={votes['ABANDON']}"""

        response = await call_strong(
            system=f"""You are the Chairman of an expert engineering council.
Your verdict must be SPECIFIC — reference actual technologies and advisor names.

ABSOLUTE RULE — NO EXCEPTIONS:
pivot_suggestion is ALWAYS REQUIRED. It must NEVER be null, empty, or missing.
- For BUILD verdicts: pivot_suggestion = an enhanced next-level version of the approved idea
- For PIVOT verdicts: pivot_suggestion = a specific alternative that fixes the fatal flaw
- Minimum 15 words. Must name specific technologies or approaches.
If you cannot think of one, use the "Enhanced version idea" from any advisor above.""",
            user=f"""IDEA: {idea}
ROLE: {target_role}
PURPOSE: {purpose}

ADVISOR FINDINGS:
{findings}

Return ONLY this JSON. pivot_suggestion MUST be a specific project description, NEVER null:
{{
    "verdict": "BUILD or PIVOT or ABANDON",
    "verdict_reasoning": "2-3 sentences referencing at least 3 advisor names and their specific findings",
    "role_match_score": {career.get('role_match_score', 55)},
    "role_match_reasoning": "one sentence on this score referencing specific skills covered or missing",
    "v1_scope": {json.dumps(ux.get('v1_features', ['Core feature', 'REST API', 'Basic UI', 'Tests'])[:4])},
    "recommended_stack": {json.dumps(tech.get('recommended_stack', ['FastAPI', 'PostgreSQL', 'React', 'Docker']))},
    "estimated_build_time": "{tech.get('timeline_weeks', 6)} weeks",
    "career_value": "one specific sentence on career ROI from career coach findings",
    "pivot_suggestion": "REQUIRED ALWAYS: specific enhanced or alternative project — minimum 15 words, never null or empty",
    "top_risks": {json.dumps(risk.get('top_risks', [])[:3])}
}}""",
            max_tokens=800,
        )

        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*', '', cleaned).strip()
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)

        if match:
            data = json.loads(match.group())

            # LEVEL 2 GUARANTEE: Check and fix if chairman returned null anyway
            pivot = data.get('pivot_suggestion', '')
            if not pivot or len(str(pivot).strip()) < 15 or str(pivot).strip().upper() in ['NULL', 'NONE', 'N/A', 'REQUIRED ALWAYS']:
                logger.warning("Chairman returned invalid pivot_suggestion — running ensure_pivot_suggestion")
                enhanced_versions = [a.get('enhanced_version', '') for a in advisor_outputs]
                data['pivot_suggestion'] = await ensure_pivot_suggestion(
                    idea,
                    data.get('verdict', 'BUILD'),
                    target_role,
                    enhanced_versions,
                )

            logger.info(
                f"Chairman: {data.get('verdict')} | "
                f"pivot: {str(data.get('pivot_suggestion', ''))[:50]}"
            )
            return data

        raise ValueError("Could not parse chairman verdict JSON")

    except Exception as e:
        logger.error(f"Chairman failed: {e}")

        votes = {"BUILD": 0, "PIVOT": 0, "ABANDON": 0}
        for a in advisor_outputs:
            s = a.get("stance", "PIVOT").upper()
            if s in votes:
                votes[s] += 1
        majority = max(votes, key=lambda k: votes[k])

        # LEVEL 3 GUARANTEE: Emergency fallback
        enhanced_versions = [a.get('enhanced_version', '') for a in advisor_outputs]
        pivot = await ensure_pivot_suggestion(idea, majority, target_role, enhanced_versions)

        return {
            "verdict": majority,
            "verdict_reasoning": f"Based on advisor consensus: BUILD={votes['BUILD']}, PIVOT={votes['PIVOT']}, ABANDON={votes['ABANDON']}",
            "role_match_score": 55,
            "role_match_reasoning": "Estimated from advisor inputs — manual review recommended",
            "v1_scope": ["Core feature implementation", "REST API endpoints", "Basic UI", "Unit tests"],
            "recommended_stack": ["FastAPI", "PostgreSQL", "React", "Docker"],
            "estimated_build_time": "6 weeks",
            "career_value": "Demonstrates full-stack engineering and problem-solving capabilities",
            "pivot_suggestion": pivot,
            "top_risks": ["Scope creep risk", "Technical complexity underestimation", "Time constraints"],
        }


async def run_war_room(
    idea: str,
    target_role: str,
    research_report: str,
    purpose: str = "portfolio",
) -> dict:
    start = time.time()
    logger.info(f"War Room starting | purpose={purpose} | role={target_role} | idea={idea[:50]}")

    prompts = get_advisor_prompts(purpose, target_role)

    # 5 advisors in parallel
    advisor_outputs = await asyncio.gather(
        call_advisor("tech_lead", prompts["tech_lead"], research_report, idea, target_role),
        call_advisor("market_analyst", prompts["market_analyst"], research_report, idea, target_role),
        call_advisor("risk_manager", prompts["risk_manager"], research_report, idea, target_role),
        call_advisor("ux_designer", prompts["ux_designer"], research_report, idea, target_role),
        call_advisor("career_coach", prompts["career_coach"], research_report, idea, target_role),
    )

    logger.info(f"All 5 advisors done in {time.time() - start:.1f}s")

    peer_review = await run_peer_review(list(advisor_outputs), idea)
    logger.info(f"Peer review done in {time.time() - start:.1f}s")

    verdict = await run_chairman(
        list(advisor_outputs),
        peer_review,
        idea,
        target_role,
        purpose,
    )

    # LEVEL 3 GUARANTEE: Final check before returning
    if not verdict.get('pivot_suggestion') or len(str(verdict.get('pivot_suggestion', '')).strip()) < 15:
        logger.error("CRITICAL: pivot_suggestion still null after all guarantees — running final fallback")
        enhanced_versions = [a.get('enhanced_version', '') for a in advisor_outputs]
        verdict['pivot_suggestion'] = await ensure_pivot_suggestion(
            idea, verdict.get('verdict', 'BUILD'), target_role, enhanced_versions
        )

    votes = {"BUILD": 0, "PIVOT": 0, "ABANDON": 0}
    for a in advisor_outputs:
        s = a.get("stance", "PIVOT").upper()
        if s in votes:
            votes[s] += 1

    elapsed = round(time.time() - start, 1)
    logger.info(
        f"War Room done: {verdict.get('verdict')} in {elapsed}s | "
        f"pivot_suggestion present: {bool(verdict.get('pivot_suggestion'))}"
    )

    return {
        "verdict": verdict,
        "votes": votes,
        "advisor_outputs": list(advisor_outputs),
        "peer_review": peer_review,
        "elapsed_seconds": elapsed,
    }