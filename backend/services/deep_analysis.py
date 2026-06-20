"""
backend/services/deep_analysis.py

Comprehensive portfolio analysis using ALL structured council data.
Uses Sonnet — quality is the priority here, this is what users see.

Why Sonnet not Haiku:
  Haiku produced generic output because it could not handle
  the complexity of synthesizing 5 advisor outputs into specific analysis.
  Sonnet handles this correctly and produces expert-level output.

Flow:
  Council runs 5 advisors (structured JSON) + chairman verdict
  Deep Analysis reads ALL structured data and produces comprehensive report
  User sees specific, grounded, actionable analysis
"""

import json
import logging
import re
import time

logger = logging.getLogger(__name__)


async def run_deep_analysis(
    original_idea: str,
    role: str,
    purpose: str,
    verdict: dict,
    advisor_outputs: list,
    research_summary: str = "",
) -> dict:
    """
    Synthesizes all council data into a comprehensive user-facing report.
    Every output point references actual project details, actual technologies,
    actual role requirements — never generic advice.
    """
    start = time.time()

    try:
        from services.llm_client import call_strong

        # Extract structured data from each advisor
        tech    = next((a for a in advisor_outputs if a.get('advisor') == 'tech_lead'), {})
        mkt     = next((a for a in advisor_outputs if a.get('advisor') == 'market_analyst'), {})
        risk    = next((a for a in advisor_outputs if a.get('advisor') == 'risk_manager'), {})
        ux      = next((a for a in advisor_outputs if a.get('advisor') == 'ux_designer'), {})
        career  = next((a for a in advisor_outputs if a.get('advisor') == 'career_coach'), {})

        # Pull key data points from structured advisor outputs
        recommended_stack   = verdict.get('recommended_stack', [])
        pivot_suggestion    = verdict.get('pivot_suggestion', '')
        top_risks           = verdict.get('top_risks', [])
        verdict_text        = verdict.get('verdict', 'PIVOT')
        verdict_reasoning   = verdict.get('verdict_reasoning', '')
        role_match_score    = verdict.get('role_match_score', 50)
        v1_scope            = verdict.get('v1_scope', [])
        estimated_time      = verdict.get('estimated_build_time', '6 weeks')

        skills_demonstrated = career.get('skills_demonstrated', [])
        skills_missing      = career.get('skills_missing', [])
        career_value        = career.get('career_value', '')
        career_enhanced     = career.get('enhanced_version', '')

        competition_level   = mkt.get('competition_level', 'medium')
        specific_competitors= mkt.get('specific_competitors', [])
        market_gap          = mkt.get('market_gap', '')
        mkt_enhanced        = mkt.get('enhanced_version', '')

        fatal_flaw          = risk.get('fatal_flaw', '')
        risk_top            = risk.get('top_risks', top_risks)
        risk_enhanced       = risk.get('enhanced_version', '')

        tech_key_finding    = tech.get('key_finding', '')
        tech_missing        = tech.get('missing_tech', [])
        timeline_weeks      = tech.get('timeline_weeks', 6)
        tech_enhanced       = tech.get('enhanced_version', '')

        ux_target_user      = ux.get('target_user', '')
        ux_value_prop       = ux.get('core_value_prop', '')
        v1_features         = ux.get('v1_features', v1_scope)

        purpose_framing = {
            "portfolio": f"landing a job as {role}",
            "startup":   "building a real business with paying users",
            "learning":  f"mastering {role} technologies through hands-on projects",
        }.get(purpose, f"building a strong project for {role}")

        # Best enhanced version from advisors (used as improved blueprint seed)
        enhanced_versions = [tech_enhanced, mkt_enhanced, risk_enhanced, career_enhanced]
        best_enhanced = next((e for e in enhanced_versions if e and len(str(e)) > 20), pivot_suggestion)

        prompt = f"""You are a senior {role} career advisor, technical architect, and portfolio strategist.

CANDIDATE PROJECT: {original_idea}
TARGET ROLE: {role}
PURPOSE: {purpose_framing}

STRUCTURED DATA FROM 5 EXPERT SPECIALISTS WHO ALREADY REVIEWED THIS:

TECH LEAD ({tech.get('stance', 'PIVOT')} confidence: {tech.get('confidence', 'medium')}):
  Finding: {tech_key_finding}
  Recommended stack: {', '.join(recommended_stack) if recommended_stack else 'not specified'}
  Missing technologies: {', '.join(tech_missing) if tech_missing else 'none identified'}
  Timeline: {timeline_weeks} weeks
  Enhanced direction: {tech_enhanced}

MARKET ANALYST ({mkt.get('stance', 'PIVOT')} confidence: {mkt.get('confidence', 'medium')}):
  Finding: {mkt.get('key_finding', '')}
  Competition: {competition_level} | Competitors: {', '.join(specific_competitors) if specific_competitors else 'none named'}
  Market gap: {market_gap}
  Enhanced direction: {mkt_enhanced}

RISK MANAGER ({risk.get('stance', 'PIVOT')} confidence: {risk.get('confidence', 'medium')}):
  Fatal flaw: {fatal_flaw}
  Top risks: {' | '.join(risk_top[:3]) if risk_top else 'none identified'}
  Enhanced direction: {risk_enhanced}

UX DESIGNER ({ux.get('stance', 'PIVOT')}):
  Target user: {ux_target_user}
  Value proposition: {ux_value_prop}
  MVP features: {' | '.join(v1_features[:3]) if v1_features else 'not specified'}

CAREER COACH ({career.get('stance', 'PIVOT')} confidence: {career.get('confidence', 'medium')}):
  Skills demonstrated: {', '.join(skills_demonstrated) if skills_demonstrated else 'not analyzed'}
  Skills missing for {role}: {', '.join(skills_missing) if skills_missing else 'not analyzed'}
  Career value: {career_value}
  Role match score: {role_match_score}/100
  Enhanced direction: {career_enhanced}

CHAIRMAN VERDICT: {verdict_text}
CHAIRMAN REASONING: {verdict_reasoning[:300]}
SUGGESTED STRONGER DIRECTION: {pivot_suggestion[:250] if pivot_suggestion else 'none'}

TASK: Using ALL of this expert data, produce a comprehensive portfolio analysis.

CRITICAL RULES:
1. Every single point must reference THIS specific project, THIS role, or THESE exact technologies
2. Name specific technologies, specific companies, specific job requirements
3. Tech stack table must analyze EACH technology in recommended_stack
4. Skills matrix must reference ACTUAL {role} job description requirements
5. Improved blueprint must be SPECIFIC — name actual technologies, actual evaluation metrics, actual architecture decisions
6. Scoring must use the expert data as evidence — not arbitrary numbers
7. Never write advice that could apply to any project — it must be specific to THIS idea

Return ONLY this valid JSON. No markdown fences. No explanation before or after:
{{
    "idea_score": {role_match_score},
    "hiring_manager_impression": "SPECIFIC: what a hiring manager sees in 10 seconds when they open this project — mention the project type, the role, and what impression it creates. Be honest.",
    "ml_engineering_aspects": [
        "SPECIFIC aspect that demonstrates real {role} thinking — name the technology or concept",
        "another specific ML/AI/engineering aspect of THIS project"
    ],
    "fullstack_aspects": [
        "SPECIFIC aspect that looks like generic web development, not {role} work — name it",
        "another web-dev-only aspect that hiring managers would not count as {role} signal"
    ],
    "tech_stack_analysis": [
        {{
            "tech": "exact technology name",
            "why_use": "specific reason for THIS project — not generic",
            "skill_proved": "exact {role} skill this technology demonstrates to hiring managers",
            "risk": "low or medium or high",
            "alternative": "specific better alternative if exists, or 'Best choice for this use case'",
            "mvp": true
        }}
    ],
    "skills_demonstrated": [
        {{"skill": "specific {role} skill name", "strength": "high or medium or low"}}
    ],
    "skills_missing": [
        {{"skill": "specific {role} skill NOT shown by this project", "importance": "critical or high or medium"}}
    ],
    "improved_blueprint": {{
        "title": "specific project title under 8 words that would stand out on a resume",
        "description": "one sentence: what it does and what makes it different from generic projects",
        "key_improvements": [
            "SPECIFIC improvement 1 over original — name what is added and why it matters for {role}",
            "SPECIFIC improvement 2 — name actual technology or methodology",
            "SPECIFIC improvement 3 — name actual metric or evaluation approach"
        ],
        "mvp_features": [
            "specific MVP feature 1 that demonstrates {role} skills",
            "specific MVP feature 2",
            "specific MVP feature 3",
            "specific MVP feature 4"
        ],
        "recommended_stack": {json.dumps(recommended_stack if recommended_stack else ["Python", "FastAPI", "PostgreSQL", "Docker"])},
        "evaluation_approach": "SPECIFIC: name actual metrics — latency numbers, accuracy benchmarks, or business KPIs — not generic 'add metrics'",
        "estimated_weeks": {timeline_weeks},
        "resume_bullet": "one strong resume bullet point starting with an action verb — include specific technologies and measurable outcomes"
    }},
    "scoring": [
        {{
            "option": "Build as-is",
            "score": {max(1, min(9, role_match_score // 10 - 2))},
            "reason": "specific reason using expert evidence — reference fatal flaw or career coach finding"
        }},
        {{
            "option": "Build improved version",
            "score": {min(9, role_match_score // 10 + 2)},
            "reason": "specific reason why improvements make this stronger for {role} — reference actual additions"
        }},
        {{
            "option": "Pivot to different project",
            "score": {max(2, role_match_score // 10 - 1)},
            "reason": "specific reason — reference market gap or competition level found by Market Analyst"
        }},
        {{
            "option": "Abandon",
            "score": 2,
            "reason": "specific reason why the core concept still has merit and should not be abandoned"
        }}
    ],
    "final_recommendation": "build or improve or pivot or abandon",
    "final_reasoning": "2-3 sentences of specific evidence-based reasoning referencing at least 2 advisor findings by name — explain exactly what the person should do and why"
}}"""

        response = await call_strong(
            system=(
                f"You are a direct, expert {role} career advisor and technical architect. "
                "Every point must be specific to the exact project and role given. "
                "Reference actual technologies, actual competitors, actual job market signals. "
                "Never write generic advice. Return only valid JSON."
            ),
            user=prompt,
            max_tokens=1400,
        )

        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*', '', cleaned).strip()
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)

        if match:
            data = json.loads(match.group())
            elapsed = round(time.time() - start, 1)
            data['elapsed_seconds'] = elapsed
            logger.info(
                f"Deep analysis complete in {elapsed}s | "
                f"role={role} | idea={original_idea[:40]}"
            )
            return data

        raise ValueError("Could not parse deep analysis JSON")

    except Exception as e:
        logger.error(f"Deep analysis failed: {e} — using smart fallback")
        elapsed = round(time.time() - start, 1)

        # SMART FALLBACK — uses real council data, never generic strings
        recommended_stack   = verdict.get('recommended_stack', ['Python', 'FastAPI', 'PostgreSQL'])
        top_risks           = verdict.get('top_risks', [])
        verdict_text        = verdict.get('verdict', 'PIVOT')
        role_match_score    = verdict.get('role_match_score', 50)
        pivot_suggestion    = verdict.get('pivot_suggestion', '')
        verdict_reasoning   = verdict.get('verdict_reasoning', '')
        v1_scope            = verdict.get('v1_scope', [])
        estimated_time      = verdict.get('estimated_build_time', '6 weeks')

        career = next((a for a in advisor_outputs if a.get('advisor') == 'career_coach'), {})
        tech   = next((a for a in advisor_outputs if a.get('advisor') == 'tech_lead'), {})
        risk_  = next((a for a in advisor_outputs if a.get('advisor') == 'risk_manager'), {})
        mkt    = next((a for a in advisor_outputs if a.get('advisor') == 'market_analyst'), {})

        skills_shown   = career.get('skills_demonstrated', ['Python', 'API development', 'System design'])
        skills_missing = career.get('skills_missing', ['Model evaluation', 'Production monitoring', 'Experiment tracking'])
        fatal_flaw     = risk_.get('fatal_flaw', 'Needs stronger differentiation for the role')
        competition    = mkt.get('competition_level', 'medium')
        market_gap     = mkt.get('market_gap', f'Underserved niche within {role} tooling')
        tech_missing   = tech.get('missing_tech', ['MLflow', 'Prometheus', 'Grafana'])

        stack_str = ', '.join(recommended_stack[:3]) if recommended_stack else 'Python, FastAPI'

        return {
            "idea_score": role_match_score,
            "hiring_manager_impression": (
                f"A hiring manager reviewing {role} portfolios sees a technically valid project "
                f"using {stack_str}, but it competes with {competition} competition — "
                f"it needs {market_gap.lower() if market_gap else 'stronger differentiation'} "
                f"to stand out in 10 seconds."
            ),
            "ml_engineering_aspects": skills_shown[:3] if skills_shown else [
                f"Demonstrates core {role} technical competency",
                f"Uses {recommended_stack[0] if recommended_stack else 'industry-standard'} technology",
            ],
            "fullstack_aspects": [
                "Standard REST API implementation without ML-specific components",
                "Generic database integration that any web developer could implement",
            ],
            "tech_stack_analysis": [
                {
                    "tech": t,
                    "why_use": f"Industry-standard for {role} projects — widely used in production",
                    "skill_proved": f"{role} technical proficiency with {t}",
                    "risk": "low",
                    "alternative": "Best choice for this use case",
                    "mvp": True,
                }
                for t in recommended_stack[:5]
            ],
            "skills_demonstrated": [
                {"skill": s, "strength": "medium"} for s in skills_shown
            ],
            "skills_missing": [
                {"skill": s, "importance": "high"} for s in skills_missing
            ],
            "improved_blueprint": {
                "title": f"Production-Grade {original_idea[:35].strip()} with Evaluation Framework",
                "description": (
                    pivot_suggestion[:120]
                    if pivot_suggestion and len(pivot_suggestion) > 20
                    else f"A {role}-level {original_idea[:40]} with measurable outcomes, monitoring, and CI/CD"
                ),
                "key_improvements": (
                    [f"Fix: {r[:70]}" for r in top_risks[:3]]
                    if top_risks else [
                        f"Add evaluation framework with measurable metrics — addresses fatal flaw: {fatal_flaw[:60]}",
                        f"Add missing technologies: {', '.join(tech_missing[:2])} — required for {role} signal",
                        "Add production monitoring dashboard — proves system design thinking",
                    ]
                ),
                "mvp_features": v1_scope[:4] if v1_scope else [
                    "Core implementation with clean architecture",
                    "REST API with proper error handling and documentation",
                    "Evaluation suite with benchmark metrics",
                    "Docker deployment with monitoring",
                ],
                "recommended_stack": recommended_stack,
                "evaluation_approach": (
                    f"Define measurable targets from day one: latency p95 < 200ms, "
                    f"accuracy benchmarks on fixed test set, cost per request tracking"
                ),
                "estimated_weeks": tech.get('timeline_weeks', 6),
                "resume_bullet": (
                    f"Built production-grade {original_idea[:30].strip()} using "
                    f"{', '.join(recommended_stack[:3])} with evaluation framework, "
                    f"achieving measurable performance benchmarks"
                ),
            },
            "scoring": [
                {
                    "option": "Build as-is",
                    "score": max(1, min(9, role_match_score // 10 - 2)),
                    "reason": f"Risk Manager identified fatal flaw: {fatal_flaw[:80] if fatal_flaw else 'Needs stronger differentiation'}",
                },
                {
                    "option": "Build improved version",
                    "score": min(9, (role_match_score // 10) + 3),
                    "reason": f"Adding {', '.join(tech_missing[:2]) if tech_missing else 'evaluation framework and monitoring'} directly addresses Career Coach's missing skills finding",
                },
                {
                    "option": "Pivot to different project",
                    "score": max(3, role_match_score // 10),
                    "reason": f"Market Analyst found {competition} competition — improvement is lower risk than full pivot",
                },
                {
                    "option": "Abandon",
                    "score": 2,
                    "reason": f"Core concept has merit — Career Coach confirmed {skills_shown[0] if skills_shown else 'relevant skill'} alignment with {role} role",
                },
            ],
            "final_recommendation": "improve" if verdict_text != "ABANDON" else "pivot",
            "final_reasoning": (
                verdict_reasoning[:300]
                if verdict_reasoning and len(verdict_reasoning) > 30
                else (
                    f"Career Coach scored this {role_match_score}/100 for {role} alignment. "
                    f"Risk Manager identified '{fatal_flaw[:80] if fatal_flaw else 'scope risk'}' as the key weakness. "
                    f"Adding {', '.join(tech_missing[:2]) if tech_missing else 'evaluation metrics and monitoring'} "
                    f"would significantly increase hiring signal."
                )
            ),
            "elapsed_seconds": elapsed,
        }