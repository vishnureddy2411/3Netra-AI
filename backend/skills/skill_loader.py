"""
backend/skills/skill_loader.py

Loads agent skill files and composes system prompts.

Architecture:
- Agent skill YAML files encode genuine domain expertise
- Founder rulebook is injected into EVERY agent prompt
- Domain knowledge is generated dynamically by LLM (not hardcoded files)
- Role matching is fuzzy — any engineering role maps correctly

Import: from skills.skill_loader import compose_agent_prompt
"""

import json
import logging
import os
import re
from functools import lru_cache
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "agents")
META_DIR   = os.path.join(os.path.dirname(__file__), "meta")

# In-memory caches
_domain_cache:    dict = {}
_rulebook_cache:  dict = {}

# ─────────────────────────────────────────────
# DOMAIN DETECTION
# ─────────────────────────────────────────────

DOMAIN_KEYWORDS = {
    "ml": [
        "machine learning", "deep learning", "neural", "model", "training",
        "inference", "rag", "llm", "embedding", "transformer", "classification",
        "regression", "clustering", "recommendation", "nlp", "computer vision",
        "reinforcement learning", "fine-tuning", "pytorch", "tensorflow",
        "scikit-learn", "huggingface", "langchain", "vector", "similarity",
        "generative", "diffusion", "gpt", "bert", "stable diffusion",
        "multimodal", "foundation model", "prompt engineering", "agent",
    ],
    "data": [
        "data pipeline", "etl", "data warehouse", "analytics", "dashboard",
        "streaming", "kafka", "spark", "airflow", "dbt", "snowflake", "bigquery",
        "data lake", "data quality", "data engineering", "real-time processing",
        "batch processing", "data lineage", "orchestration", "ingestion",
        "flink", "beam", "redshift", "databricks", "delta lake", "data mesh",
        "feature store", "data observability",
    ],
    "devops": [
        "kubernetes", "docker", "ci/cd", "infrastructure", "terraform",
        "ansible", "helm", "monitoring", "observability", "platform engineering",
        "site reliability", "deployment", "cloud native", "service mesh",
        "gitops", "chaos engineering", "incident response",
    ],
    "mobile": [
        "mobile app", "ios", "android", "react native", "flutter", "swift",
        "kotlin", "cross-platform", "push notification", "offline-first",
    ],
    "security": [
        "security", "penetration testing", "vulnerability", "zero trust",
        "soc", "siem", "threat modeling", "owasp", "devsecops", "appsec",
        "cryptography", "auth", "oauth", "zero knowledge",
    ],
    "web": [
        "web app", "saas", "platform", "marketplace", "portal", "api service",
        "rest api", "graphql", "microservice", "backend service", "crud",
        "authentication", "authorization", "multi-tenant", "subscription",
        "ecommerce", "cms", "blog", "social network",
    ],
}


def detect_domain(idea: str) -> str:
    """
    Detects the primary domain from the project idea.
    Scores every domain and returns the best match.
    Falls back to 'general' if no strong signal.
    """
    idea_lower = idea.lower()
    scores     = {domain: 0 for domain in DOMAIN_KEYWORDS}

    for domain, keywords in DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            if keyword in idea_lower:
                # Longer keyword = more specific = higher score
                scores[domain] += len(keyword.split())

    best_domain  = max(scores, key=scores.get)
    best_score   = scores[best_domain]

    if best_score == 0:
        logger.info(f"Domain: general (no signal found)")
        return "general"

    logger.info(f"Domain: {best_domain} (score={best_score}, all={scores})")
    return best_domain


# ─────────────────────────────────────────────
# SKILL FILE LOADING
# ─────────────────────────────────────────────

@lru_cache(maxsize=32)
def load_skill_file(skill_name: str) -> dict:
    """
    Loads a YAML skill file from backend/skills/agents/.
    Cached for the process lifetime — files do not change at runtime.
    """
    path = os.path.join(SKILLS_DIR, f"{skill_name}.yaml")
    if not os.path.exists(path):
        logger.warning(f"Skill file not found: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    logger.info(f"Skill loaded: {skill_name} v{data.get('skill', {}).get('version', '?')}")
    return data


def load_founder_rulebook() -> str:
    """
    Loads the founder rulebook YAML and converts it to a
    concise injected prompt section.
    Cached after first load.
    """
    global _rulebook_cache

    if _rulebook_cache:
        return _rulebook_cache.get("prompt", "")

    path = os.path.join(META_DIR, "founder_rulebook.yaml")
    if not os.path.exists(path):
        logger.warning(f"Founder rulebook not found: {path}")
        return ""

    with open(path, "r", encoding="utf-8") as f:
        rulebook = yaml.safe_load(f) or {}

    # Extract the most critical sections for prompt injection
    # We do not dump the entire 500-line YAML — we extract key decision rules
    dm    = rulebook.get("mental_models", {})
    gates = rulebook.get("quality_gates", {})
    reds  = rulebook.get("red_lines", {})
    decs  = rulebook.get("decision_algorithms", {})

    def fmt(items, indent="  - "):
        if isinstance(items, list):
            return "\n".join(f"{indent}{i}" for i in items[:6])
        return str(items)

    sections = []

    # Core decision framework
    framework = rulebook.get("decision_algorithms", {})
    bvb = framework.get("build_vs_buy", {})
    if bvb:
        sections.append(
            "BUILD vs BUY rule: Default to buy for infrastructure. "
            "Build only when it IS your competitive advantage."
        )

    # Reversibility test
    rev = dm.get("reversibility_test", {})
    if rev:
        sections.append(
            "REVERSIBILITY: Type 1 decisions (auth, DB schema, API design) "
            "require deep analysis. Type 2 decisions should take minutes."
        )

    # Boring technology
    bt = dm.get("boring_technology_principle", {})
    if bt:
        sections.append(
            "TECHNOLOGY: You have 3 innovation tokens per project. "
            "Spend them only on your competitive advantage. "
            "Everything else must be boring and battle-tested."
        )

    # Quality gates
    sg = gates.get("security_gate", {})
    if sg:
        never = sg.get("non_negotiable_checks", [])
        sections.append(
            f"SECURITY GATES (non-negotiable):\n" +
            "\n".join(f"  - {n}" for n in never[:5])
        )

    # Red lines
    red_never = reds.get("never_acceptable", {})
    security_reds = red_never.get("security", [])
    if security_reds:
        sections.append(
            f"RED LINES — automatic REJECT if any present:\n" +
            "\n".join(f"  - {r}" for r in security_reds[:5])
        )

    # Career framework
    cf = rulebook.get("career_framework", {})
    bullet = cf.get("the_resume_bullet_formula", {})
    if bullet:
        sections.append(
            f"RESUME BULLET FORMULA: "
            f"{bullet.get('formula', 'Built X using Y achieving Z metric')}"
        )

    # Scaling thresholds
    st = rulebook.get("scaling_thresholds", {})
    pr = st.get("portfolio_rule", {})
    if pr:
        sections.append(
            f"SCALING RULE: {pr.get('statement', 'Design for Tier 1. Show Tier 2 awareness.')}"
        )

    # Named anti-patterns summary
    ap = rulebook.get("named_anti_patterns", {})
    if ap:
        pattern_names = list(ap.keys())[:5]
        sections.append(
            f"NAMED ANTI-PATTERNS to detect: {', '.join(pattern_names)}"
        )

    prompt = """
## FOUNDER RULEBOOK (Governs All Decisions)
These rules override agent defaults when they conflict.

""" + "\n\n".join(sections) + """

FINAL CHECK before any recommendation:
1. Does this pass the security gate? (credentials, auth, input validation)
2. Is this the simplest strong solution — not the most impressive one?
3. What breaks at 10x users?
4. Would a senior engineer at Stripe be proud of this recommendation?
5. Does this decision serve the user's CAREER — not just their code?
"""

    _rulebook_cache["prompt"] = prompt.strip()
    logger.info("Founder rulebook loaded and compiled")
    return _rulebook_cache["prompt"]


# ─────────────────────────────────────────────
# ROLE SIGNAL MATCHING
# ─────────────────────────────────────────────

def get_role_signals(skill: dict, role: str) -> dict:
    """
    Fuzzy-matches the user's role to the closest role_specific_signals entry.
    Falls back to 'general' if no match found.

    Matching priority:
    1. Exact key match (ml_engineer → ml_engineer)
    2. Keyword substring match (longest keyword wins)
    3. Partial word intersection
    4. General fallback
    """
    role_signals = skill.get("role_specific_signals", {})
    if not role_signals or not role:
        return {}

    role_lower = role.lower()

    # 1. Exact key match
    key_attempt = role_lower.replace(" ", "_").replace("-", "_")
    if key_attempt in role_signals:
        logger.info(f"Role '{role}' exact-matched → '{key_attempt}'")
        return role_signals[key_attempt]

    # 2. Keyword match — longest match wins (most specific)
    best_key   = None
    best_score = 0

    for signal_key, signal_data in role_signals.items():
        if signal_key == "general":
            continue
        for keyword in signal_data.get("keywords", []):
            if keyword in role_lower:
                score = len(keyword)
                if score > best_score:
                    best_score = score
                    best_key   = signal_key

    if best_key:
        logger.info(f"Role '{role}' keyword-matched → '{best_key}' (score={best_score})")
        return role_signals[best_key]

    # 3. Partial word intersection
    role_words = set(role_lower.split())
    for signal_key, signal_data in role_signals.items():
        if signal_key == "general":
            continue
        for keyword in signal_data.get("keywords", []):
            if role_words & set(keyword.split()):
                logger.info(f"Role '{role}' partial-matched → '{signal_key}'")
                return signal_data

    # 4. General fallback
    logger.info(f"Role '{role}' → general fallback")
    return role_signals.get("general", {})


# ─────────────────────────────────────────────
# DYNAMIC DOMAIN KNOWLEDGE (LLM-generated)
# ─────────────────────────────────────────────

async def load_domain_knowledge(
    idea: str,
    role: str,
    domain: str,
) -> dict:
    """
    Dynamically generates domain-specific knowledge using LLM.
    Cached per (domain, role, idea_prefix) to avoid repeated calls.
    Falls back to empty dict if generation fails.

    No hardcoded domain files — everything generated from context.
    """
    cache_key = f"{domain}:{role[:30]}:{idea[:50]}"
    if cache_key in _domain_cache:
        return _domain_cache[cache_key]

    try:
        from services.llm_client import call_fast

        prompt = f"""Generate concise domain-specific knowledge for 5 AI advisor agents analyzing this project.

PROJECT: {idea}
ROLE: {role}
DOMAIN: {domain}

Return ONLY valid JSON — no markdown, no preamble:
{{
    "systems_architect": {{
        "specific_knowledge": [
            "Architectural fact specific to {domain} projects that most architects miss",
            "Performance consideration unique to this type of system",
            "Scalability pattern that applies specifically to {domain}",
            "Data flow concern specific to this domain",
            "Integration complexity unique to {domain} systems"
        ],
        "domain_failures": [
            "Most common production failure in {domain} systems",
            "Anti-pattern specific to {domain} that looks reasonable at first",
            "Scaling failure mode unique to this type of project"
        ]
    }},
    "skeptical_interviewer": {{
        "specific_knowledge": [
            "What hiring managers for {role} in {domain} specifically look for",
            "The interview question that separates junior from senior in {domain}",
            "What the top 10% of {domain} portfolios have that others do not"
        ],
        "domain_failures": [
            "Most common portfolio mistake for {role} in {domain}",
            "Red flag that reveals lack of production experience in {domain}"
        ]
    }},
    "career_strategist": {{
        "specific_knowledge": [
            "Technologies {role} job postings require for {domain} in 2026",
            "The metric that makes a {domain} project resume bullet impressive",
            "What {domain} project feature makes hiring managers remember a candidate"
        ],
        "domain_failures": [
            "Technology choice that signals outdated {domain} knowledge",
            "Scope mistake that kills career ROI for {domain} projects"
        ]
    }},
    "risk_engineer": {{
        "specific_knowledge": [
            "Security concern specific to {domain} systems that general advice misses",
            "Most likely demo failure mode for a {domain} project",
            "Compliance risk unique to {domain} that portfolio projects often ignore"
        ],
        "domain_failures": [
            "Security anti-pattern that is endemic to {domain} projects",
            "Risk that is unique to this exact type of {domain} system"
        ]
    }},
    "innovation_scout": {{
        "specific_knowledge": [
            "Emerging trend in {domain} in 2026 that makes a project forward-looking",
            "Novel combination of technologies specific to {domain} with high GitHub star potential",
            "Research paper or open problem in {domain} that has no good open source implementation yet"
        ],
        "domain_failures": [
            "Overused {domain} approach that signals lack of originality in 2026",
            "Technology choice in {domain} that was impressive in 2020 but is now expected baseline"
        ]
    }}
}}

Be SPECIFIC to this exact project and role. No generic advice."""

        response = await call_fast(
            system=(
                "You are a technical domain expert generating agent knowledge. "
                "Return ONLY valid JSON. Be specific to the exact project and role. "
                "Every item must be specific enough to be falsifiable — no vague generalities."
            ),
            user=prompt,
            max_tokens=2000,
        )

        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*',     '', cleaned).strip()
        match   = re.search(r'\{.*\}',  cleaned, re.DOTALL)

        if match:
            raw = match.group()
            # Repair truncation
            open_b = raw.count('{') - raw.count('}')
            open_k = raw.count('[') - raw.count(']')
            if open_b > 0 or open_k > 0:
                raw = raw.rstrip(',\n\r\t ')
                raw += ']' * open_k
                raw += '}' * open_b
            knowledge = json.loads(raw)
            _domain_cache[cache_key] = knowledge
            logger.info(f"Domain knowledge generated: {domain}/{role[:20]}")
            return knowledge

    except Exception as e:
        logger.warning(f"Dynamic domain knowledge failed ({type(e).__name__}): {e}")

    _domain_cache[cache_key] = {}
    return {}


# ─────────────────────────────────────────────
# PROMPT COMPOSITION
# ─────────────────────────────────────────────

async def compose_agent_prompt(
    agent_name: str,
    idea: str,
    intake: dict,
    domain: Optional[str] = None,
) -> str:
    """
    Composes a complete system prompt for an agent.

    Layers (in order of injection):
    1. Agent identity and optimization target
    2. Agent reasoning chain
    3. Agent anti-patterns and green flags
    4. Role-specific signals (fuzzy-matched)
    5. Dynamic domain knowledge (LLM-generated)
    6. Founder rulebook (governs all decisions)
    7. Output contract
    8. Non-negotiable rules
    """
    skill = load_skill_file(agent_name)
    if not skill:
        return _fallback_prompt(agent_name, idea, intake)

    domain       = domain or detect_domain(idea)
    role         = intake.get("role", "Engineer")
    purpose      = intake.get("purpose", "portfolio")

    # Load all layers
    domain_knowledge = await load_domain_knowledge(idea, role, domain)
    role_signals     = get_role_signals(skill, role)
    rulebook_prompt  = load_founder_rulebook()

    # Extract skill components
    identity      = skill.get("identity", {})
    reasoning     = skill.get("reasoning_chain", [])
    anti_patterns = skill.get("anti_patterns_to_catch", [])
    green_flags   = skill.get("green_flags", [])
    output        = skill.get("output_contract", {})
    meta          = skill.get("skill", {})

    # Role signals section
    role_section = ""
    if role_signals:
        req  = role_signals.get("required", [])
        imp  = role_signals.get("impressive", [])
        diff = role_signals.get("portfolio_differentiator", "")
        role_section = f"""
## Role-Specific Signals: {role}
What hiring managers REQUIRE to see:
{_fmt_list(req)}

What makes candidates stand out:
{_fmt_list(imp)}

Portfolio differentiator:
- {diff}
"""

    # Domain knowledge section
    domain_section = ""
    dk = domain_knowledge.get(agent_name, {})
    if dk:
        knowledge = dk.get("specific_knowledge", [])
        failures  = dk.get("domain_failures", [])
        domain_section = f"""
## Domain-Specific Knowledge ({domain.upper()})
Critical facts for this domain:
{_fmt_list(knowledge)}

Domain-specific failure modes:
{_fmt_list(failures)}
"""

    prompt = f"""You are {identity.get("role", "a senior technical advisor")}.

## Your Identity
Known for: {identity.get("known_for", "")}
Optimization target: {meta.get("optimization_target", "")}
Philosophy: {identity.get("philosophy", "")}
Adversarial stance: {identity.get("adversarial_stance", "")}

## Your Reasoning Framework
Work through these questions IN ORDER before forming any opinion:
{_fmt_numbered(reasoning)}

## Anti-Patterns You Are Trained to Catch
These are specific failure signatures — not vague concerns.
Flag EXPLICITLY if you find any:
{_fmt_list(anti_patterns)}

## Green Flags That Signal Quality
{_fmt_list(green_flags)}
{role_section}{domain_section}
{rulebook_prompt}

## Your Output Contract
Return ONLY valid JSON — no markdown, no preamble, no explanation:
{_fmt_output_contract(output)}

## Absolute Rules
- Every claim must be SPECIFIC and FALSIFIABLE
- Never say "it depends" — commit to a position
- Never say "might" or "could" — say "will" or "won't"
- Never say "consider" — say "do this" or "do not do this"
- Uncertain? Say: "I don't know because [specific missing information]"
- Your analysis is for: {idea[:200]}
- Role: {role} | Purpose: {purpose}
- You are in ROUND 1. You have NOT seen any other agent's output.
- Commit to your position independently. No hedging.
"""

    return prompt.strip()


async def compose_chairman_prompt(
    idea: str,
    intake: dict,
    round1_outputs: list,
    round2_attacks: list,
    round3_defenses: list,
    domain: Optional[str] = None,
) -> str:
    """
    Composes the chairman's arbitration prompt.
    Chairman reads ALL rounds and issues final verdict.
    Not a synthesizer — a truth arbitrator.
    """
    skill        = load_skill_file("chairman")
    identity     = skill.get("identity", {})
    framework    = skill.get("arbitration_framework", [])
    output       = skill.get("output_contract", {})
    rulebook     = load_founder_rulebook()

    # Calculate agreement score
    positions      = [r.get("position", "BUILD") for r in round1_outputs]
    most_common    = max(set(positions), key=positions.count) if positions else "BUILD"
    agreement_pct  = round((positions.count(most_common) / len(positions)) * 100) if positions else 0

    # Format agent verdicts summary
    verdicts_map = {
        r.get("agent_name", f"Agent {i+1}"): r.get("position", "BUILD")
        for i, r in enumerate(round1_outputs)
    }

    r1_section = "\n\n".join([
        f"### {r.get('agent_name', f'Agent {i+1}')} — Round 1\n"
        f"Position: **{r.get('position', 'unknown')}** | "
        f"Confidence: {r.get('confidence', 5)}/10\n"
        f"Top Risk: {r.get('top_risk', '')}\n"
        f"Reasoning: {str(r.get('reasoning', ''))[:400]}"
        for i, r in enumerate(round1_outputs)
    ])

    r2_section = "\n\n".join([
        f"### {r.get('attacker', f'Attacker {i+1}')} → {r.get('target', 'Target')}\n"
        f"Claim Attacked: {r.get('specific_claim_attacked', '')}\n"
        f"Counter Evidence: {r.get('counter_evidence', '')}\n"
        f"Attack Strength: {r.get('attack_strength', 0)}/10"
        for i, r in enumerate(round2_attacks)
    ])

    r3_section = "\n\n".join([
        f"### {r.get('agent_name', f'Agent {i+1}')} — Defense\n"
        f"Position Maintained: {r.get('position_maintained', True)}\n"
        f"Defense: {str(r.get('defense', ''))[:300]}\n"
        f"Concession: {r.get('concession', 'None')}\n"
        f"Updated Confidence: {r.get('updated_confidence', 5)}/10"
        for i, r in enumerate(round3_defenses)
    ])

    sycophancy_warning = (
        "⚠️ HIGH AGREEMENT DETECTED — Weight dissenting views 2x more heavily. "
        "High agreement in an AI council is a signal of sycophancy, not correctness."
        if agreement_pct > 80 else
        "Agreement level is within healthy debate range."
    )

    prompt = f"""You are {identity.get("role", "The Chairman — Truth Arbitrator")}.

## Your Mission
You are NOT a synthesizer. You are a TRUTH ARBITRATOR.
Find which agents are right, which are wrong, and cite specific evidence.
Issue minority dissent if any valid position was inadequately refuted.

## Arbitration Framework
{_fmt_numbered(framework)}

{rulebook}

## Agreement Score: {agreement_pct}%
{sycophancy_warning}

Agent verdicts: {json.dumps(verdicts_map)}

## ROUND 1 — Committed Positions (Formed Independently)
{r1_section}

## ROUND 2 — Cross-Examination Results
{r2_section}

## ROUND 3 — Defenses Under Pressure
{r3_section}

## Project
{idea}
Role: {intake.get("role", "Engineer")} | Purpose: {intake.get("purpose", "portfolio")}

## Output Contract
{_fmt_output_contract(output)}

## Chairman Rules
1. Cite SPECIFIC agent names in verdict_reasoning — not vague synthesis
2. Identify which attacks were valid and which were rhetorical
3. minority_dissent is NOT optional — document the strongest losing argument
4. If agreement > 80%: set sycophancy_warning: true and reduce confidence by 15
5. confidence_score starts at 100 - (agreement_score * 0.3) — adjust by argument quality
6. pivot_suggestion must be a SPECIFIC real project with title + one-line description or null
7. v1_scope must be 3-5 specific buildable features — not vague goals
8. Before issuing BUILD: verify no red lines are crossed (check the rulebook above)
9. This person's career depends on your verdict. Treat it with that weight.
"""

    return prompt.strip()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _fmt_list(items: list) -> str:
    if not items:
        return "- None specified"
    return "\n".join(f"- {item}" for item in items)


def _fmt_numbered(items: list) -> str:
    if not items:
        return "1. Analyze the project carefully"
    return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))


def _fmt_output_contract(output: dict) -> str:
    if not output:
        return 'Return JSON with: agent_name, position, top_risk, reasoning, confidence'
    required = output.get("required_fields", [])
    schema   = output.get("json_schema", "")
    return f"Required fields: {', '.join(required)}\n\n{schema}"


def _fallback_prompt(agent_name: str, idea: str, intake: dict) -> str:
    rulebook = load_founder_rulebook()
    return (
        f"You are a senior technical advisor analyzing: {idea}\n"
        f"Role: {intake.get('role', 'Engineer')} | "
        f"Purpose: {intake.get('purpose', 'portfolio')}\n\n"
        f"{rulebook}\n\n"
        f"Return JSON: agent_name, position (BUILD/REDESIGN/REJECT), "
        f"top_risk, reasoning, confidence (1-10)"
    )