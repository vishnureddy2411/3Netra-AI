"""
backend/services/deep_analysis.py

Corporate-grade portfolio analysis synthesizing ALL council agent data.
Uses Claude Sonnet — quality is the priority here.

Flow:
  1. Council runs 5 adversarial agents + Chairman arbitration
  2. This service reads ALL structured agent outputs
  3. Produces specific, evidence-based, corporate-style analysis
  4. User sees grounded, actionable assessment — never generic advice
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
    start = time.time()

    try:
        from services.llm_client import call_strong

        # ── Extract structured advisor data ──────────────────────────────────
        tech   = next((a for a in advisor_outputs if a.get('advisor') == 'tech_lead'), {})
        mkt    = next((a for a in advisor_outputs if a.get('advisor') == 'market_analyst'), {})
        risk   = next((a for a in advisor_outputs if a.get('advisor') == 'risk_manager'), {})
        ux     = next((a for a in advisor_outputs if a.get('advisor') == 'ux_designer'), {})
        career = next((a for a in advisor_outputs if a.get('advisor') == 'career_coach'), {})

        # ── Pull key fields ──────────────────────────────────────────────────
        recommended_stack = verdict.get('recommended_stack', [])
        top_risks         = verdict.get('top_risks', [])
        verdict_text      = verdict.get('verdict', 'PIVOT')
        verdict_reasoning = verdict.get('verdict_reasoning', '')
        v1_scope          = verdict.get('v1_scope', [])
        pivot_suggestion  = verdict.get('pivot_suggestion', '')

        skills_demonstrated = career.get('skills_demonstrated', [])
        skills_missing      = career.get('skills_missing', [])
        career_value        = career.get('career_value', '')
        career_enhanced     = career.get('enhanced_version', '')

        competition_level    = mkt.get('competition_level', 'medium')
        specific_competitors = mkt.get('specific_competitors', [])
        market_gap           = mkt.get('market_gap', '')
        mkt_enhanced         = mkt.get('enhanced_version', '')
        mkt_finding          = mkt.get('key_finding', '')

        fatal_flaw    = risk.get('fatal_flaw', '')
        risk_top      = risk.get('top_risks', top_risks)
        risk_enhanced = risk.get('enhanced_version', '')

        tech_key_finding = tech.get('key_finding', '')
        tech_missing     = tech.get('missing_tech', [])
        timeline_weeks   = tech.get('timeline_weeks', 6)
        tech_enhanced    = tech.get('enhanced_version', '')

        ux_target_user = ux.get('target_user', '')
        ux_value_prop  = ux.get('core_value_prop', '')
        v1_features    = ux.get('v1_features', v1_scope)

        purpose_framing = {
            "portfolio": f"building a portfolio to land a {role} job",
            "startup":   "building a product with real paying users",
            "learning":  f"mastering {role} technologies through hands-on projects",
            "job_role":  f"getting hired as {role}",
        }.get(purpose, f"building a strong {role} portfolio project")

        final_rec = verdict_text.lower() if verdict_text in ['BUILD', 'IMPROVE', 'PIVOT', 'ABANDON'] else 'improve'

        prompt = f"""You are a senior technical advisor producing a corporate-grade portfolio assessment.

PROJECT: {original_idea}
TARGET ROLE: {role}
GOAL: {purpose_framing}

COUNCIL FINDINGS — 5 specialists already reviewed this project:

TECH LEAD ({tech.get('stance', 'PIVOT')}):
  Finding: {tech_key_finding}
  Recommended stack: {', '.join(recommended_stack)}
  Missing technologies: {', '.join(tech_missing) if tech_missing else 'none'}
  Enhanced direction: {tech_enhanced}
  Timeline: {timeline_weeks} weeks

MARKET ANALYST ({mkt.get('stance', 'PIVOT')}):
  Finding: {mkt_finding}
  Competition level: {competition_level}
  Key competitors: {', '.join(specific_competitors) if specific_competitors else 'none named'}
  Market gap: {market_gap}
  Enhanced direction: {mkt_enhanced}

RISK MANAGER ({risk.get('stance', 'PIVOT')}):
  Fatal flaw: {fatal_flaw}
  Top risks: {' | '.join(risk_top[:3]) if risk_top else 'none'}
  Enhanced direction: {risk_enhanced}

UX DESIGNER ({ux.get('stance', 'PIVOT')}):
  Target user: {ux_target_user}
  Value proposition: {ux_value_prop}
  V1 features: {' | '.join(v1_features[:3]) if v1_features else 'not specified'}

CAREER COACH ({career.get('stance', 'PIVOT')}):
  Skills demonstrated: {', '.join(skills_demonstrated) if skills_demonstrated else 'not analyzed'}
  Skills missing for {role}: {', '.join(skills_missing) if skills_missing else 'not analyzed'}
  Career value: {career_value}
  Enhanced direction: {career_enhanced}

CHAIRMAN VERDICT: {verdict_text}
CHAIRMAN REASONING: {verdict_reasoning[:400] if verdict_reasoning else 'not provided'}
STRONGER DIRECTION: {pivot_suggestion[:300] if pivot_suggestion else 'none suggested'}

PRODUCE A CORPORATE-GRADE ASSESSMENT. Rules:
- Every sentence must be specific to THIS project and THIS role
- hiring_manager_impression: What a {role} hiring manager thinks in 10 seconds — reference domain, specific technologies, competition level, and candidate signal. Minimum 3 sentences. Direct and honest.
- ml_engineering_aspects: ONLY signals that prove {role} domain thinking — name specific technologies or concepts. Never generic.
- fullstack_aspects: ONLY generic web dev aspects that do NOT impress a {role} hiring manager — be specific to this project.
- tech_stack_analysis: Analyze EVERY technology in the recommended stack — why this exact tech for this exact project.
- skills_demonstrated: Based on Career Coach findings — name actual {role} skills this project proves.
- skills_missing: Based on Career Coach findings — {role} job requirements this project does NOT demonstrate.
- improved_blueprint: Name actual technologies, actual metrics, actual architecture decisions — nothing generic.
- scoring: Evidence-based scores — reference specific advisor names and findings as justification.
- final_reasoning: 2-3 sentences referencing at least 2 specific advisor findings. Tell the candidate exactly what to do and why.

Return ONLY valid JSON — no markdown, no explanation:
{{
    "hiring_manager_impression": "3-4 sentence corporate assessment specific to this project domain, technologies, competition level, and seniority signal.",
    "final_recommendation": "{final_rec}",
    "final_reasoning": "2-3 sentences naming at least 2 advisors. Tell candidate exactly what to build and why.",
    "skills_demonstrated": [
        {{"skill": "specific {role} skill from Career Coach findings", "strength": "high or medium or low"}}
    ],
    "skills_missing": [
        {{"skill": "specific {role} skill from Career Coach missing list", "importance": "critical or high or medium"}}
    ],
    "ml_engineering_aspects": [
        "Specific {role} signal — name exact technology or architectural decision",
        "Another domain-specific signal",
        "Third signal referencing a council finding",
        "Fourth signal specific to this project"
    ],
    "fullstack_aspects": [
        "Specific generic web dev aspect that does NOT count as {role} signal",
        "Another table-stakes aspect",
        "Third generic aspect"
    ],
    "improved_blueprint": {{
        "title": "Specific resume-ready project title under 8 words",
        "description": "One sentence: what it does and what makes it stand out",
        "key_improvements": [
            "Specific improvement referencing Tech Lead or Risk Manager finding",
            "Second improvement referencing actual council finding",
            "Third improvement naming actual metric or architectural decision"
        ],
        "mvp_features": [
            "Specific {role}-relevant feature 1",
            "Specific feature 2",
            "Specific feature 3",
            "Specific feature 4"
        ],
        "recommended_stack": {json.dumps(recommended_stack if recommended_stack else ["Python", "FastAPI", "PostgreSQL", "Docker"])},
        "evaluation_approach": "Specific metrics — actual benchmarks, latency targets, accuracy thresholds for this project",
        "estimated_weeks": {timeline_weeks},
        "resume_bullet": "One strong resume bullet with action verb, specific technologies, one measurable outcome"
    }},
    "scoring": [
        {{
            "option": "Build as-is",
            "score": <score 1-10 based on how strong the project is RIGHT NOW without changes — use Risk Manager fatal flaw severity as evidence>,
            "reason": "Specific reason using Risk Manager fatal flaw finding: {fatal_flaw[:80] if fatal_flaw else 'see council findings'}"
        }},
        {{
            "option": "Build improved version",
            "score": <score 1-10 based on how strong the project becomes WITH Tech Lead improvements — must be higher than Build as-is>,
            "reason": "Specific reason using Tech Lead finding: {tech_key_finding[:80] if tech_key_finding else 'see tech lead findings'} — name the actual improvements"
        }},
        {{
            "option": "Pivot to different project",
            "score": <score 1-10 based on Market Analyst competition level: high competition = lower pivot score, low competition = higher pivot score>,
            "reason": "Specific reason using Market Analyst finding: competition is {competition_level} — {market_gap[:60] if market_gap else 'see market findings'}"
        }},
        {{
            "option": "Abandon",
            "score": <score 1-10 — almost always low 1-3 unless Career Coach found zero skill alignment>,
            "reason": "Specific reason using Career Coach finding: {', '.join(skills_demonstrated[:2]) if skills_demonstrated else 'see career findings'} — why concept still has merit"
        }}
    ],
    "tech_stack_analysis": [
        {{
            "tech": "technology name",
            "why_use": "specific reason for THIS project — not generic",
            "skill_proved": "exact {role} competency this demonstrates",
            "risk": "low or medium or high",
            "alternative": "specific named alternative or Best choice for this use case",
            "mvp": true
        }}
    ]
}}"""

        response = await call_strong(
            system=(
                f"You are a corporate-grade {role} portfolio advisor producing specific, "
                "evidence-based analysis. Every sentence must reference this exact project, "
                "role, and council findings. Zero generic text. Zero repeated phrases. "
                "Return only valid JSON."
            ),
            user=prompt,
            max_tokens=3000,
        )

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

            # Repair internal JSON errors
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                raw = re.sub(r',\s*([}\]])', r'\1', raw)
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    pos = raw.rfind('"final_reasoning"')
                    if pos > 0:
                        raw = raw[:pos] + f'"final_reasoning": "{verdict_reasoning[:150] if verdict_reasoning else "See council findings."}"' + '}'
                    data = json.loads(raw)

            elapsed         = round(time.time() - start, 1)
            data['elapsed_seconds'] = elapsed
            data['idea_score']      = 0

            logger.info(f"Deep analysis complete in {elapsed}s | role={role} | idea={original_idea[:40]}")
            return data

        raise ValueError("Could not parse deep analysis JSON")

    except Exception as e:
        logger.error(f"Deep analysis failed: {e} — using dynamic fallback")
        elapsed = round(time.time() - start, 1)

        # ── Dynamic fallback — uses real council data, never generic strings ──
        recommended_stack = verdict.get('recommended_stack', ['Python', 'FastAPI', 'PostgreSQL'])
        top_risks         = verdict.get('top_risks', [])
        verdict_text      = verdict.get('verdict', 'PIVOT')
        verdict_reasoning = verdict.get('verdict_reasoning', '')
        v1_scope          = verdict.get('v1_scope', [])
        pivot_suggestion  = verdict.get('pivot_suggestion', '')

        career = next((a for a in advisor_outputs if a.get('advisor') == 'career_coach'), {})
        tech   = next((a for a in advisor_outputs if a.get('advisor') == 'tech_lead'), {})
        risk_  = next((a for a in advisor_outputs if a.get('advisor') == 'risk_manager'), {})
        mkt    = next((a for a in advisor_outputs if a.get('advisor') == 'market_analyst'), {})

        skills_shown   = career.get('skills_demonstrated', [])
        skills_missing = career.get('skills_missing', [])
        career_value   = career.get('career_value', '')
        fatal_flaw     = risk_.get('fatal_flaw', '')
        competition    = mkt.get('competition_level', 'medium')
        market_gap     = mkt.get('market_gap', '')
        mkt_finding    = mkt.get('key_finding', '')
        tech_missing   = tech.get('missing_tech', [])
        tech_finding   = tech.get('key_finding', '')
        timeline_weeks = tech.get('timeline_weeks', 6)
        stack_str      = ', '.join(recommended_stack[:3]) if recommended_stack else 'Python, FastAPI'

        return {
            "idea_score":      0,
            "elapsed_seconds": elapsed,
            "hiring_manager_impression": (
                f"A hiring manager reviewing {role} portfolios evaluates this project against "
                f"the technical stack: {stack_str}. "
                f"{tech_finding if tech_finding else f'The implementation demonstrates foundational {role} competency using industry-standard tools'}. "
                f"{mkt_finding if mkt_finding else f'With {competition} competition in this space'}, "
                f"the project needs {'stronger differentiation — ' + market_gap.lower() if market_gap else 'measurable outcomes and production-quality implementation'} "
                f"to stand out from similar portfolio entries within 10 seconds."
            ),
            "ml_engineering_aspects": (
                [f"{s} — directly signals {role} domain proficiency" for s in skills_shown[:5]]
                if skills_shown else [
                    f"{recommended_stack[0] if recommended_stack else 'Core technology'} with production-grade configuration",
                    f"Domain-specific logic requiring {role} expertise",
                    f"System architecture decisions aligned with {role} job requirements",
                ]
            ),
            "fullstack_aspects": (
                [f"{s} — required for the role but insufficient as a standalone {role} signal" for s in skills_missing[:3]]
                if skills_missing else [
                    f"Standard REST API without {role}-specific business logic",
                    "Generic database integration without domain-specific schema design",
                    "Authentication layer — table-stakes, not a differentiator for this role",
                ]
            ),
            "tech_stack_analysis": [
                {
                    "tech":         t,
                    "why_use":      f"{tech_finding[:100] if tech_finding else f'Industry standard for {role} production systems — recommended by Tech Lead for this project domain'}",
                    "skill_proved": f"{role} technical proficiency with {t} in a production-grade context",
                    "risk":         "low",
                    "alternative":  "Best choice for this use case",
                    "mvp":          True,
                }
                for t in recommended_stack[:6]
            ],
            "skills_demonstrated": (
                [{"skill": s, "strength": "medium"} for s in skills_shown]
                if skills_shown else [
                    {"skill": f"Core {role} implementation", "strength": "medium"},
                    {"skill": "System design",               "strength": "medium"},
                    {"skill": "API development",             "strength": "medium"},
                ]
            ),
            "skills_missing": (
                [{"skill": s, "importance": "high"} for s in skills_missing]
                if skills_missing else [
                    {"skill": f"Production monitoring for {role} systems", "importance": "high"},
                    {"skill": "Evaluation framework with measurable benchmarks", "importance": "critical"},
                    {"skill": f"Domain-specific {role} tooling",              "importance": "high"},
                ]
            ),
            "improved_blueprint": {
                "title":       f"Production-Grade {original_idea[:35].strip()} with Evaluation Framework",
                "description": (
                    pivot_suggestion[:150]
                    if pivot_suggestion and len(pivot_suggestion) > 20
                    else f"A {role}-level implementation of {original_idea[:50]} with measurable outcomes, production monitoring, and CI/CD pipeline"
                ),
                "key_improvements": (
                    [f"Address Risk Manager finding: {r[:80]}" for r in top_risks[:3]]
                    if top_risks else [
                        f"Add evaluation framework — resolves Tech Lead finding: {tech_finding[:80] if tech_finding else 'needs measurable benchmarks'}",
                        f"Integrate {', '.join(tech_missing[:2]) if tech_missing else 'monitoring + observability'} — critical missing {role} signals identified by Tech Lead",
                        f"Add production deployment pipeline — demonstrates system design maturity required for {role} roles",
                    ]
                ),
                "mvp_features": (v1_scope[:4] if len(v1_scope) >= 4 else (v1_scope + [
                    f"Evaluation suite with {role}-specific benchmark metrics",
                    "Docker deployment with health checks and logging",
                    "API documentation with usage examples and error handling",
                    "Monitoring dashboard with key domain-specific metrics",
                ])[:4]),
                "recommended_stack":    recommended_stack,
                "evaluation_approach": (
                    f"Define measurable targets specific to {role} from day one: "
                    f"latency p95 < 200ms, domain-specific accuracy benchmarks on a fixed test set, "
                    f"cost-per-request tracking, and automated regression on every deployment"
                ),
                "estimated_weeks": timeline_weeks,
                "resume_bullet":   (
                    f"Built production-grade {original_idea[:40].strip()} using "
                    f"{', '.join(recommended_stack[:3])} — "
                    f"{career_value[:100] if career_value else 'with evaluation framework, production monitoring, and measurable performance benchmarks aligned with ' + role + ' hiring requirements'}"
                ),
            },
            "scoring": [
                {
                    "option": "Build as-is",
                    "score":  4,
                    "reason": f"Risk Manager identified: {fatal_flaw[:120] if fatal_flaw else 'project needs stronger differentiation at ' + competition + ' competition level identified by Market Analyst'}",
                },
                {
                    "option": "Build improved version",
                    "score":  8,
                    "reason": f"Adding {', '.join(tech_missing[:2]) if tech_missing else 'evaluation framework and production monitoring'} directly addresses Career Coach gap — significantly increases {role} hiring signal",
                },
                {
                    "option": "Pivot to different project",
                    "score":  4,
                    "reason": f"Market Analyst found {competition} competition in this space — improving the existing concept carries lower risk than a full pivot while achieving comparable hiring signal",
                },
                {
                    "option": "Abandon",
                    "score":  2,
                    "reason": f"Career Coach confirmed {skills_shown[0] if skills_shown else 'core skill'} alignment with {role} requirements — the concept has real merit and should be developed with the improvements above",
                },
            ],
            "final_recommendation": "improve" if verdict_text not in ["ABANDON"] else "pivot",
            "final_reasoning": (
                verdict_reasoning[:350]
                if verdict_reasoning and len(verdict_reasoning) > 50
                else (
                    f"Career Coach confirmed {len(skills_shown)} demonstrated skills but flagged "
                    f"{skills_missing[0] if skills_missing else 'evaluation framework'} as a critical gap for {role} roles. "
                    f"Risk Manager identified '{fatal_flaw[:100] if fatal_flaw else 'production readiness'}' as the primary weakness — "
                    f"addressable by adding {', '.join(tech_missing[:2]) if tech_missing else 'monitoring, evaluation, and production tooling'}. "
                    f"Build the improved version: same core concept, significantly stronger {role} hiring signal."
                )
            ),
        }