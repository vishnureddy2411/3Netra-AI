"""
backend/services/council.py

War Room Council — 5 advisors debate the research report,
peer review each other, then Chairman delivers final verdict.

Flow:
  1. All 5 advisors read research report simultaneously (asyncio.gather)
  2. Peer review round — each advisor flags weak claims in others' outputs
  3. Chairman synthesizes everything into BUILD/PIVOT/ABANDON verdict

Why adversarial:
  One AI opinion = one bias. Five specialized opinions = balanced view.
  Peer review = weak claims removed before Chairman sees them.
  Result = higher quality verdict than any single model call.

Cost breakdown:
  5 advisors × Haiku = ~$0.02
  1 peer review × Haiku = ~$0.01
  1 Chairman × Sonnet = ~$0.04
  Total War Room = ~$0.07 per session
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════
# OUTPUT MODELS
# ════════════════════════════════════════════════════════════

class AdvisorOutput(BaseModel):
    """What each advisor returns after reading the research."""
    advisor_role: str
    recommendation: str        # BUILD, PIVOT, or ABANDON
    key_insight: str           # their most important point
    top_concern: str           # their biggest worry
    v1_suggestion: str         # what V1 should focus on
    confidence: int            # 1-10 how confident they are
    data_citations: list[str]  # specific numbers cited from research


class PeerReviewOutput(BaseModel):
    """Result of peer review round."""
    flags: list[str]           # unsupported claims found
    consensus_points: list[str]  # points all advisors agreed on
    major_disagreements: list[str]  # points advisors disagreed on


class ChairmanVerdict(BaseModel):
    """Final verdict from Chairman after synthesizing all inputs."""
    verdict: str               # BUILD, PIVOT, or ABANDON
    verdict_reasoning: str     # why this verdict
    role_match_score: int      # 0-100 how well idea matches target role
    role_match_reasoning: str  # why this score
    v1_scope: list[str]        # exactly what to build in V1 (3-5 items)
    v2_features: list[str]     # what to defer to V2
    recommended_stack: list[str]  # tech stack recommendation
    estimated_build_time: str  # realistic timeline
    career_value: str          # how this helps career
    pivot_suggestion: Optional[str]  # if PIVOT, what to pivot to
    top_risks: list[str]       # top 3 risks to address


# ════════════════════════════════════════════════════════════
# ADVISOR SYSTEM PROMPTS
# ════════════════════════════════════════════════════════════

ADVISOR_PROMPTS = {
    "tech_lead": """You are a Senior Tech Lead with 15 years experience.
You evaluate projects for technical feasibility and complexity.
Focus on: tech stack complexity, build timeline, technical debt risks,
infrastructure needs, scalability challenges, and what can realistically
be built by one developer in 4-6 weeks for a portfolio project.
Be direct and honest. Do not sugarcoat technical difficulty.""",

    "market_analyst": """You are a Market Research Analyst specialized in developer tools.
You evaluate market opportunity and competitive landscape.
Focus on: market size, existing competition strength, monetization potential,
user acquisition difficulty, and whether there is a real gap in the market.
Always cite specific data from the research. Be skeptical of crowded markets.""",

    "risk_manager": """You are a Risk Manager who identifies project failure modes.
You evaluate technical, market, legal, and execution risks.
Focus on: what could kill this project, regulatory risks, dependency risks,
API cost risks at scale, competition response, and founder single points of failure.
Be pessimistic by nature — your job is to find what others miss.""",

    "ux_designer": """You are a Senior UX Designer and product strategist.
You evaluate user experience and product-market fit.
Focus on: who the target user is, what their pain point is, how intuitive
the product would be, what the onboarding experience looks like, and
whether users would return after the first session.
Think from the user's perspective, not the builder's.""",

    "career_coach": """You are a Career Coach specialized in software engineering careers.
You evaluate how well this project matches the user's career goals.
Focus on: does this project use technologies employers want to see,
will it stand out in a portfolio, what skills it demonstrates,
whether it matches the target role, and how to present it on a resume.
Be practical — think about what actually gets candidates hired.""",
}


# ════════════════════════════════════════════════════════════
# SINGLE ADVISOR CALL
# ════════════════════════════════════════════════════════════

async def call_advisor(
    advisor_role: str,
    system_prompt: str,
    research_report: str,
    idea: str,
    target_role: str,
) -> AdvisorOutput:
    """
    Calls one advisor with the research report.
    Returns structured AdvisorOutput.

    ELI5: One specialist reads the research and gives their expert opinion.
    Uses Haiku because this is opinion generation, not complex reasoning.
    """
    from services.llm_client import call_fast

    user_prompt = f"""PROJECT IDEA: {idea}
TARGET ROLE: {target_role}

RESEARCH REPORT:
{research_report[:6000]}

As the {advisor_role.replace('_', ' ').title()}, analyze this project idea.

Respond in this exact JSON format:
{{
    "advisor_role": "{advisor_role}",
    "recommendation": "BUILD or PIVOT or ABANDON",
    "key_insight": "your single most important insight in one sentence",
    "top_concern": "your biggest concern in one sentence",
    "v1_suggestion": "what V1 should focus on in one sentence",
    "confidence": 7,
    "data_citations": ["specific number or fact from research", "another specific fact"]
}}

Be specific. Cite exact numbers from the research. One sentence per field."""

    try:
        response = await call_fast(
            system=system_prompt,
            user=user_prompt,
            max_tokens=400,
        )

        # Parse JSON response
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return AdvisorOutput(**data)

        # Fallback if JSON parsing fails
        logger.warning(f"Advisor {advisor_role} returned non-JSON, using fallback")
        return AdvisorOutput(
            advisor_role=advisor_role,
            recommendation="PIVOT",
            key_insight=response[:200],
            top_concern="Could not parse structured response",
            v1_suggestion="Focus on core MVP features",
            confidence=5,
            data_citations=[],
        )

    except Exception as e:
        logger.error(f"Advisor {advisor_role} failed: {e}")
        return AdvisorOutput(
            advisor_role=advisor_role,
            recommendation="PIVOT",
            key_insight=f"Analysis failed: {str(e)}",
            top_concern="Advisor call failed",
            v1_suggestion="Retry analysis",
            confidence=1,
            data_citations=[],
        )


# ════════════════════════════════════════════════════════════
# PEER REVIEW ROUND
# ════════════════════════════════════════════════════════════

async def run_peer_review(
    advisor_outputs: list[AdvisorOutput],
    research_report: str,
) -> PeerReviewOutput:
    """
    Each advisor's output is reviewed for unsupported claims.
    Flags any claim not backed by research data.
    Identifies consensus points and major disagreements.

    ELI5: After all 5 advisors give their opinion, we check:
    - Did anyone make up facts not in the research?
    - What did everyone agree on?
    - Where did they strongly disagree?
    """
    from services.llm_client import call_fast

    outputs_text = "\n\n".join([
        f"ADVISOR {i+1} ({out.advisor_role}):\n"
        f"Recommendation: {out.recommendation}\n"
        f"Key Insight: {out.key_insight}\n"
        f"Top Concern: {out.top_concern}\n"
        f"Citations: {', '.join(out.data_citations)}"
        for i, out in enumerate(advisor_outputs)
    ])

    recommendations = [out.recommendation for out in advisor_outputs]
    build_count = recommendations.count("BUILD")
    pivot_count = recommendations.count("PIVOT")
    abandon_count = recommendations.count("ABANDON")

    user_prompt = f"""Review these 5 advisor outputs for a project.
Voting: BUILD={build_count}, PIVOT={pivot_count}, ABANDON={abandon_count}

ADVISOR OUTPUTS:
{outputs_text[:4000]}

RESEARCH DATA (ground truth):
{research_report[:2000]}

Respond in this exact JSON format:
{{
    "flags": ["any claim not supported by research data", "another unsupported claim"],
    "consensus_points": ["point all advisors agreed on", "another consensus point"],
    "major_disagreements": ["area where advisors strongly disagreed", "another disagreement"]
}}

Keep each item to one clear sentence. Maximum 3 items per list."""

    try:
        response = await call_fast(
            system="You are a fact-checker. Only flag claims not supported by the provided research data.",
            user=user_prompt,
            max_tokens=400,
        )

        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return PeerReviewOutput(**data)

        return PeerReviewOutput(
            flags=[],
            consensus_points=["Peer review parsing failed"],
            major_disagreements=[],
        )

    except Exception as e:
        logger.error(f"Peer review failed: {e}")
        return PeerReviewOutput(
            flags=[],
            consensus_points=[],
            major_disagreements=[f"Peer review error: {str(e)}"],
        )


# ════════════════════════════════════════════════════════════
# CHAIRMAN SYNTHESIS
# ════════════════════════════════════════════════════════════

async def run_chairman(
    idea: str,
    target_role: str,
    advisor_outputs: list[AdvisorOutput],
    peer_review: PeerReviewOutput,
    research_report: str,
) -> ChairmanVerdict:
    """
    Chairman reads all advisor outputs + peer review and delivers final verdict.
    Uses Sonnet (not Haiku) because this requires deep reasoning and synthesis.

    ELI5: After all advisors debate, the CEO reads everything and makes
    the final decision. This is the most important call in the entire product.
    It determines whether the user builds, pivots, or abandons the idea.
    """
    from services.llm_client import call_strong

    recommendations = [out.recommendation for out in advisor_outputs]
    build_count = recommendations.count("BUILD")
    pivot_count = recommendations.count("PIVOT")
    abandon_count = recommendations.count("ABANDON")

    advisor_summary = "\n\n".join([
        f"{out.advisor_role.upper()}:\n"
        f"Vote: {out.recommendation} (confidence: {out.confidence}/10)\n"
        f"Key insight: {out.key_insight}\n"
        f"Top concern: {out.top_concern}\n"
        f"V1 suggestion: {out.v1_suggestion}"
        for out in advisor_outputs
    ])

    user_prompt = f"""You are the Chairman of a technical advisory board.
Make the final verdict on this project idea.

PROJECT: {idea}
TARGET ROLE: {target_role}

ADVISOR VOTES: BUILD={build_count}, PIVOT={pivot_count}, ABANDON={abandon_count}

ADVISOR INPUTS:
{advisor_summary}

PEER REVIEW FLAGS:
{json.dumps(peer_review.flags)}

CONSENSUS POINTS:
{json.dumps(peer_review.consensus_points)}

RESEARCH SUMMARY:
{research_report[:2000]}

Respond in this exact JSON format:
{{
    "verdict": "BUILD or PIVOT or ABANDON",
    "verdict_reasoning": "2-3 sentences explaining the verdict",
    "role_match_score": 85,
    "role_match_reasoning": "one sentence explaining score",
    "v1_scope": ["feature 1", "feature 2", "feature 3"],
    "v2_features": ["deferred feature 1", "deferred feature 2"],
    "recommended_stack": ["technology 1", "technology 2", "technology 3"],
    "estimated_build_time": "4-6 weeks for solo developer",
    "career_value": "one sentence on portfolio/career value",
    "pivot_suggestion": null,
    "top_risks": ["risk 1", "risk 2", "risk 3"]
}}

Be decisive. Give a clear verdict with specific reasoning."""

    try:
        response = await call_strong(
            system="You are a decisive technical chairman. Make clear, specific recommendations.",
            user=user_prompt,
            max_tokens=800,
        )

        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return ChairmanVerdict(**data)

        logger.error("Chairman returned non-JSON response")
        return _fallback_verdict(idea, build_count, pivot_count, abandon_count)

    except Exception as e:
        logger.error(f"Chairman failed: {e}")
        return _fallback_verdict(idea, build_count, pivot_count, abandon_count)


def _fallback_verdict(
    idea: str,
    build_count: int,
    pivot_count: int,
    abandon_count: int,
) -> ChairmanVerdict:
    """Returns a basic verdict based on advisor vote counts if Chairman fails."""
    if build_count >= 3:
        verdict = "BUILD"
    elif abandon_count >= 3:
        verdict = "ABANDON"
    else:
        verdict = "PIVOT"

    return ChairmanVerdict(
        verdict=verdict,
        verdict_reasoning=f"Based on advisor votes: BUILD={build_count}, PIVOT={pivot_count}, ABANDON={abandon_count}",
        role_match_score=50,
        role_match_reasoning="Could not generate detailed analysis",
        v1_scope=["Core MVP feature", "Basic authentication", "Simple dashboard"],
        v2_features=["Advanced features", "Analytics"],
        recommended_stack=["Python", "FastAPI", "Next.js"],
        estimated_build_time="4-6 weeks",
        career_value="Demonstrates full-stack development skills",
        pivot_suggestion=None,
        top_risks=["Technical complexity", "Market competition", "Time constraints"],
    )


# ════════════════════════════════════════════════════════════
# MAIN WAR ROOM FUNCTION
# ════════════════════════════════════════════════════════════

async def run_war_room(
    idea: str,
    target_role: str,
    research_report: str,
) -> dict:
    """
    Main War Room function. Runs the complete council process.

    Step 1: All 5 advisors run simultaneously (asyncio.gather)
    Step 2: Peer review round
    Step 3: Chairman synthesis

    Returns complete War Room result with all outputs and final verdict.

    ELI5: Assembles the full expert panel, runs the debate,
    and returns the Chairman's final decision with full reasoning.
    """
    logger.info(f"War Room started for: '{idea[:60]}'")
    start_time = datetime.utcnow()

    # Step 1: Run all 5 advisors simultaneously
    logger.info("Step 1: Running 5 advisors in parallel...")
    advisor_outputs = await asyncio.gather(
        call_advisor("tech_lead", ADVISOR_PROMPTS["tech_lead"], research_report, idea, target_role),
        call_advisor("market_analyst", ADVISOR_PROMPTS["market_analyst"], research_report, idea, target_role),
        call_advisor("risk_manager", ADVISOR_PROMPTS["risk_manager"], research_report, idea, target_role),
        call_advisor("ux_designer", ADVISOR_PROMPTS["ux_designer"], research_report, idea, target_role),
        call_advisor("career_coach", ADVISOR_PROMPTS["career_coach"], research_report, idea, target_role),
    )
    logger.info(f"Advisors complete. Votes: {[o.recommendation for o in advisor_outputs]}")

    # Step 2: Peer review round
    logger.info("Step 2: Running peer review...")
    peer_review = await run_peer_review(advisor_outputs, research_report)
    logger.info(f"Peer review complete. Flags: {len(peer_review.flags)}")

    # Step 3: Chairman synthesis
    logger.info("Step 3: Chairman synthesizing verdict...")
    verdict = await run_chairman(
        idea=idea,
        target_role=target_role,
        advisor_outputs=advisor_outputs,
        peer_review=peer_review,
        research_report=research_report,
    )
    logger.info(f"Chairman verdict: {verdict.verdict}")

    elapsed = (datetime.utcnow() - start_time).total_seconds()

    return {
        "idea": idea,
        "target_role": target_role,
        "elapsed_seconds": round(elapsed, 1),
        "advisor_outputs": [o.model_dump() for o in advisor_outputs],
        "peer_review": peer_review.model_dump(),
        "verdict": verdict.model_dump(),
        "votes": {
            "BUILD": sum(1 for o in advisor_outputs if o.recommendation == "BUILD"),
            "PIVOT": sum(1 for o in advisor_outputs if o.recommendation == "PIVOT"),
            "ABANDON": sum(1 for o in advisor_outputs if o.recommendation == "ABANDON"),
        },
    }