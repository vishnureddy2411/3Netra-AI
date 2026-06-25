"""
backend/services/quiz_engine.py

Quiz Engine — Stage 7

Generates dynamic questions from the actual project graph and diagrams.
Evaluates answers strictly but not offensively.
Tracks asked questions to avoid repetition across rounds.
Saves knowledge gaps to both MCP and Supabase.

Round progression:
  Round 1 — Basic understanding (architecture, tech choices)
  Round 2 — Deeper technical reasoning (data flow, failure modes)
  Round 3+ — Interview simulation level (explain to stakeholder, defend decisions)
"""

import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Question categories per round
ROUND_CATEGORIES = {
    1: ["architecture",     "tech_choice",   "data_flow",     "core_feature",    "stack_justification"],
    2: ["scalability",      "failure_modes", "security",      "database_design", "api_design"],
    3: ["interview_sim",    "trade_offs",    "improvements",  "production",      "stakeholder_explain"],
}

DEFAULT_CATEGORY_FALLBACK = [
    "architecture", "tech_choice", "data_flow",
    "scalability",  "failure_modes", "interview_sim",
    "security",     "trade_offs",    "improvements", "production",
]


# ── Question generator ────────────────────────────────────────────────────────

async def generate_questions(
    project_graph:    dict,
    diagrams:         list,
    idea:             str,
    role:             str,
    round_number:     int,
    asked_questions:  list[str],
    count:            int = 5,
) -> list[dict]:
    """
    Generates `count` questions dynamically from the actual project graph.
    Never repeats questions from asked_questions list.
    Round number controls difficulty.
    """
    from services.llm_client import call_strong

    # Extract project context from graph
    pages      = project_graph.get("pages", [])
    routes     = project_graph.get("api_routes", [])
    components = project_graph.get("shared_components", [])
    models     = project_graph.get("data_models", [])
    tech       = project_graph.get("tech_decisions", {})

    # Build diagram summary
    diagram_types = [d.get("diagram_type", "") for d in diagrams] if diagrams else []

    # Get categories for this round
    categories = ROUND_CATEGORIES.get(round_number, DEFAULT_CATEGORY_FALLBACK)

    # Determine difficulty descriptor
    difficulty = {
        1: "beginner — test basic understanding of what was built",
        2: "intermediate — test technical reasoning and design decisions",
    }.get(round_number, "advanced — simulate a real engineering interview")

    asked_str = "\n".join(f"- {q}" for q in asked_questions) if asked_questions else "None yet"

    prompt = f"""You are a senior engineering interviewer generating quiz questions for a developer who just built this project.

PROJECT: {idea}
ROLE BEING DEVELOPED FOR: {role}

PROJECT GRAPH:
Pages: {json.dumps([p.get('name') for p in pages[:8]])}
API Routes: {json.dumps([r.get('path') for r in routes[:10]])}
Components: {json.dumps([c.get('name') for c in components[:8]])}
Data Models: {json.dumps([m.get('name') for m in models[:6]])}
Tech Decisions: {json.dumps(tech)}
Diagram types generated: {json.dumps(diagram_types)}

ROUND: {round_number}
DIFFICULTY: {difficulty}
QUESTION CATEGORIES TO COVER: {json.dumps(categories[:count])}

QUESTIONS ALREADY ASKED (DO NOT REPEAT THESE):
{asked_str}

Generate exactly {count} questions. Rules:
1. Each question must reference SPECIFIC parts of THIS project — page names, route paths, model names, tech choices
2. Questions must be answerable from the project graph above
3. Never repeat any question from the already-asked list
4. Each question should cover a different category
5. Questions get progressively harder within this round
6. For interview_sim category: ask the user to explain as if talking to a hiring manager
7. Every question must have a clear correct answer derivable from the project

Return ONLY valid JSON:
{{
    "questions": [
        {{
            "id": "q_{round_number}_1",
            "category": "architecture",
            "difficulty": "beginner",
            "question": "Specific question referencing actual project components",
            "correct_answer": "The expected correct answer based on the project graph",
            "key_concepts": ["concept1", "concept2"],
            "why_it_matters": "Why a {role} hiring manager would ask this"
        }}
    ]
}}"""

    try:
        response = await call_strong(
            system=(
                "You are a strict but fair engineering interviewer. "
                "Generate questions that test real understanding of the specific project built. "
                "Every question must reference actual components from the project graph provided. "
                "Return only valid JSON."
            ),
            user=prompt,
            max_tokens=2000,
        )

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
            data = json.loads(raw)
            questions = data.get("questions", [])
            logger.info(f"Generated {len(questions)} questions for round {round_number}")
            return questions

    except Exception as e:
        logger.error(f"Question generation failed: {e}")

    # Fallback questions using project context
    return _fallback_questions(project_graph, idea, role, round_number, count)


# ── Answer evaluator ──────────────────────────────────────────────────────────

async def evaluate_answer(
    question:      dict,
    user_answer:   str,
    project_graph: dict,
    idea:          str,
    role:          str,
) -> dict:
    """
    Strictly evaluates a user's answer.
    Returns: correct/incorrect verdict + clear explanation + knowledge gap if wrong.
    Never offensive — always educational.
    """
    from services.llm_client import call_strong

    correct_answer = question.get("correct_answer", "")
    key_concepts   = question.get("key_concepts", [])
    category       = question.get("category", "")
    why_matters    = question.get("why_it_matters", "")

    tech = project_graph.get("tech_decisions", {})

    prompt = f"""You are a strict but fair engineering interviewer evaluating an answer.

PROJECT: {idea}
ROLE: {role}
TECH STACK: {json.dumps(tech)}

QUESTION: {question.get('question', '')}
CATEGORY: {category}
KEY CONCEPTS: {json.dumps(key_concepts)}

EXPECTED ANSWER: {correct_answer}

USER'S ANSWER: {user_answer}

EVALUATION RULES:
1. Be STRICT — partial credit is not a thing. Either they got the core concept or they did not.
2. Be FAIR — if they expressed the right idea in different words, that is correct.
3. Be EDUCATIONAL — always explain the correct answer clearly, even if they got it right.
4. Be RESPECTFUL — never condescending, never harsh. Teach, do not shame.
5. If wrong, clearly explain WHY their answer was incorrect and WHAT the correct concept is.
6. Reference specific parts of their project in the explanation.

Return ONLY valid JSON:
{{
    "is_correct": true,
    "verdict": "Correct" or "Incorrect" or "Partially Correct",
    "score": 1 or 0,
    "short_verdict": "One sentence — was it right or wrong and why",
    "explanation": "2-3 sentences explaining the correct answer clearly. Reference specific project components. Teach the concept properly.",
    "what_they_got_right": "Specific part of their answer that was correct — or null if completely wrong",
    "what_was_missing": "Specific concept or detail they missed — or null if completely correct",
    "knowledge_gap": "If incorrect — the specific topic they need to study. Null if correct.",
    "study_tip": "If incorrect — one specific thing to review. Null if correct."
}}"""

    try:
        response = await call_strong(
            system=(
                "You are a strict but kind engineering interviewer. "
                "Evaluate the answer fairly based on conceptual correctness, not exact wording. "
                "Always explain the correct concept clearly after evaluation. "
                "Return only valid JSON."
            ),
            user=prompt,
            max_tokens=800,
        )

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
            logger.info(
                f"Answer evaluated: "
                f"correct={result.get('is_correct')} "
                f"category={category}"
            )
            return result

    except Exception as e:
        logger.error(f"Answer evaluation failed: {e}")

    # Fallback evaluation
    return {
        "is_correct":       False,
        "verdict":          "Could not evaluate",
        "score":            0,
        "short_verdict":    "Evaluation failed — please try again",
        "explanation":      f"The correct answer was: {correct_answer}",
        "what_they_got_right": None,
        "what_was_missing": "Could not parse evaluation",
        "knowledge_gap":    category,
        "study_tip":        f"Review {category} concepts for {role} roles",
    }


# ── Round summarizer ──────────────────────────────────────────────────────────

async def summarize_round(
    questions:    list[dict],
    evaluations:  list[dict],
    round_number: int,
    idea:         str,
    role:         str,
) -> dict:
    """
    Summarizes a completed quiz round.
    Returns score, strengths, gaps, and recommendation.
    """
    from services.llm_client import call_fast

    total   = len(evaluations)
    correct = sum(1 for e in evaluations if e.get("is_correct", False))
    score   = round((correct / total) * 100) if total > 0 else 0

    gaps = [
        e.get("knowledge_gap")
        for e in evaluations
        if not e.get("is_correct") and e.get("knowledge_gap")
    ]

    strengths = [
        q.get("category")
        for q, e in zip(questions, evaluations)
        if e.get("is_correct")
    ]

    try:
        response = await call_fast(
            system="You are an engineering coach summarizing a quiz round. Return only valid JSON.",
            user=(
                f"Project: {idea}\nRole: {role}\nRound: {round_number}\n"
                f"Score: {correct}/{total} ({score}%)\n"
                f"Knowledge gaps: {json.dumps(gaps)}\n"
                f"Strong areas: {json.dumps(strengths)}\n\n"
                f"Return JSON: {{"
                f'"score_pct": {score}, '
                f'"correct": {correct}, '
                f'"total": {total}, '
                f'"performance_label": "Excellent or Good or Needs Work", '
                f'"summary": "2 sentences — what they know well and what needs work", '
                f'"strengths": {json.dumps(strengths[:3])}, '
                f'"gaps": {json.dumps(gaps[:3])}, '
                f'"recommendation": "Should they take another round or move to next stage?"'
                f"}}"
            ),
            max_tokens=400,
        )

        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*',     '', cleaned).strip()
        match   = re.search(r'\{.*\}',  cleaned, re.DOTALL)
        if match:
            raw = match.group()
            raw = re.sub(r',\s*([}\]])', r'\1', raw)
            return json.loads(raw)

    except Exception as e:
        logger.error(f"Round summary failed: {e}")

    return {
        "score_pct":         score,
        "correct":           correct,
        "total":             total,
        "performance_label": "Good" if score >= 60 else "Needs Work",
        "summary":           f"Answered {correct} of {total} correctly.",
        "strengths":         strengths[:3],
        "gaps":              gaps[:3],
        "recommendation":    "Take another round to reinforce weak areas." if score < 80 else "Ready for next stage.",
    }


# ── Gap saver ─────────────────────────────────────────────────────────────────

async def save_gaps_to_mcp(project_id: str, gaps: list[str], summary: dict):
    """Saves knowledge gaps to MCP for Stage 8 Code Generation to reference."""
    try:
        from fastmcp import Client
        async with Client("http://localhost:8001/mcp") as mcp:
            await mcp.call_tool("save_quiz_gaps", {
                "project_id": project_id,
                "gaps_json":  json.dumps({
                    "knowledge_gaps": gaps,
                    "quiz_summary":   summary,
                }),
            })
        logger.info(f"Quiz gaps saved to MCP for: {project_id}")
    except Exception as e:
        logger.warning(f"Could not save gaps to MCP: {e}")


async def save_gaps_to_supabase(project_id: str, gaps: list[str], all_rounds: list[dict]):
    """Saves quiz results to project_artifacts for permanent storage."""
    try:
        from services.supabase_client import get_supabase
        supabase = get_supabase()
        await supabase.table("project_artifacts").upsert({
            "project_id":    project_id,
            "artifact_type": "quiz_results",
            "content":       json.dumps({
                "knowledge_gaps": gaps,
                "rounds":         all_rounds,
                "total_rounds":   len(all_rounds),
            }),
        }).execute()
        logger.info(f"Quiz results saved to Supabase for: {project_id}")
    except Exception as e:
        logger.warning(f"Could not save quiz to Supabase: {e}")


# ── Fallback questions ────────────────────────────────────────────────────────

def _fallback_questions(
    project_graph: dict,
    idea:          str,
    role:          str,
    round_number:  int,
    count:         int,
) -> list[dict]:
    """Fallback questions when LLM generation fails — uses project context."""
    pages  = project_graph.get("pages", [{}])
    routes = project_graph.get("api_routes", [{}])
    tech   = project_graph.get("tech_decisions", {})
    models = project_graph.get("data_models", [{}])

    page_name  = pages[0].get("name", "main page") if pages else "main page"
    route_path = routes[0].get("path", "/api/main") if routes else "/api/main"
    db         = tech.get("database", "the database") if tech else "the database"
    model_name = models[0].get("name", "main model") if models else "main model"
    frontend   = tech.get("frontend", "the frontend framework") if tech else "the frontend"

    fallback_pool = [
        {
            "id":            f"q_{round_number}_fb_1",
            "category":      "architecture",
            "difficulty":    "beginner",
            "question":      f"Explain the overall architecture of {idea}. What are the main layers?",
            "correct_answer":f"The system has a frontend ({frontend}), backend API, and {db} layer. Each layer has a specific responsibility.",
            "key_concepts":  ["separation of concerns", "layered architecture"],
            "why_it_matters":"Architecture explanation is the first question in most system design interviews.",
        },
        {
            "id":            f"q_{round_number}_fb_2",
            "category":      "tech_choice",
            "difficulty":    "beginner",
            "question":      f"Why did you choose {db} as the database for this project?",
            "correct_answer":f"{db} was chosen for its reliability, ACID compliance, and fit with the data model of {idea}.",
            "key_concepts":  ["database selection", "data modeling"],
            "why_it_matters":"Technology justification shows engineering judgment, not just execution.",
        },
        {
            "id":            f"q_{round_number}_fb_3",
            "category":      "data_flow",
            "difficulty":    "beginner",
            "question":      f"Walk me through what happens when a user visits the {page_name} page.",
            "correct_answer":f"The frontend makes a request to {route_path}, the backend queries {db} for {model_name} data, and returns it to render the page.",
            "key_concepts":  ["request lifecycle", "data flow"],
            "why_it_matters":"Tracing data flow shows full-stack understanding.",
        },
        {
            "id":            f"q_{round_number}_fb_4",
            "category":      "scalability",
            "difficulty":    "intermediate",
            "question":      f"What is the first thing that would break in {idea} if user traffic increased 10x?",
            "correct_answer":f"The database would likely be the bottleneck — {db} queries would slow down without proper indexing and connection pooling.",
            "key_concepts":  ["scalability", "database optimization", "bottleneck analysis"],
            "why_it_matters":"Scalability thinking separates senior engineers from junior engineers.",
        },
        {
            "id":            f"q_{round_number}_fb_5",
            "category":      "interview_sim",
            "difficulty":    "intermediate",
            "question":      f"Explain {idea} to a hiring manager in 2 minutes. What problem does it solve and what technical decisions are you most proud of?",
            "correct_answer":f"The project solves [problem]. The key technical decisions were choosing {frontend} for the UI, {db} for data persistence, and structuring the API around {route_path} endpoints.",
            "key_concepts":  ["communication", "project narrative", "technical storytelling"],
            "why_it_matters":"This is literally the first question in every portfolio interview.",
        },
    ]

    return fallback_pool[:count]