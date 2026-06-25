"""
backend/routes/quiz.py

Quiz API — Stage 7 endpoints

POST /api/quiz/start    — Generate first round of questions
POST /api/quiz/answer   — Evaluate a single answer
POST /api/quiz/next     — Generate next round of questions
POST /api/quiz/complete — Save all gaps and finish quiz
"""

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from middleware.auth import require_auth
from services.quiz_engine import (
    generate_questions,
    evaluate_answer,
    summarize_round,
    save_gaps_to_mcp,
    save_gaps_to_supabase,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request models ────────────────────────────────────────────────────────────

class QuizStartRequest(BaseModel):
    project_id:    str
    idea:          str
    role:          str
    project_graph: dict
    diagrams:      Optional[list] = []


class QuizAnswerRequest(BaseModel):
    project_id:    str
    idea:          str
    role:          str
    question:      dict
    user_answer:   str
    project_graph: dict


class QuizNextRequest(BaseModel):
    project_id:      str
    idea:            str
    role:            str
    project_graph:   dict
    diagrams:        Optional[list] = []
    round_number:    int
    asked_questions: list[str]


class QuizCompleteRequest(BaseModel):
    project_id:  str
    all_gaps:    list[str]
    all_rounds:  list[dict]
    idea:        str
    role:        str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/quiz/start")
async def start_quiz(request: Request, body: QuizStartRequest):
    """
    Generates the first round of 5 questions.
    Called when user clicks Start Quiz.
    """
    user = await require_auth(request)

    try:
        logger.info(f"Quiz starting — project: {body.project_id} | idea: {body.idea[:60]}")

        questions = await generate_questions(
            project_graph=body.project_graph,
            diagrams=body.diagrams or [],
            idea=body.idea,
            role=body.role,
            round_number=1,
            asked_questions=[],
            count=5,
        )

        logger.info(f"Quiz round 1 generated — {len(questions)} questions")

        return JSONResponse({
            "success":      True,
            "project_id":   body.project_id,
            "round_number": 1,
            "questions":    questions,
            "total":        len(questions),
        })

    except Exception as e:
        logger.error(f"Quiz start failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.post("/quiz/answer")
async def submit_answer(request: Request, body: QuizAnswerRequest):
    """
    Evaluates a single answer.
    Returns: correct/incorrect verdict + explanation + gap if wrong.
    """
    user = await require_auth(request)

    try:
        logger.info(
            f"Quiz answer — project: {body.project_id} | "
            f"question: {body.question.get('id')} | "
            f"answer length: {len(body.user_answer)}"
        )

        evaluation = await evaluate_answer(
            question=body.question,
            user_answer=body.user_answer,
            project_graph=body.project_graph,
            idea=body.idea,
            role=body.role,
        )

        return JSONResponse({
            "success":    True,
            "project_id": body.project_id,
            "question_id":body.question.get("id"),
            "evaluation": evaluation,
        })

    except Exception as e:
        logger.error(f"Quiz answer failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.post("/quiz/next")
async def next_round(request: Request, body: QuizNextRequest):
    """
    Generates next round of 5 questions.
    Never repeats questions from asked_questions list.
    """
    user = await require_auth(request)

    try:
        logger.info(
            f"Quiz next round — project: {body.project_id} | "
            f"round: {body.round_number} | "
            f"asked: {len(body.asked_questions)}"
        )

        questions = await generate_questions(
            project_graph=body.project_graph,
            diagrams=body.diagrams or [],
            idea=body.idea,
            role=body.role,
            round_number=body.round_number,
            asked_questions=body.asked_questions,
            count=5,
        )

        logger.info(
            f"Quiz round {body.round_number} generated — "
            f"{len(questions)} new questions"
        )

        return JSONResponse({
            "success":      True,
            "project_id":   body.project_id,
            "round_number": body.round_number,
            "questions":    questions,
            "total":        len(questions),
        })

    except Exception as e:
        logger.error(f"Quiz next round failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.post("/quiz/summarize")
async def summarize_quiz_round(request: Request):
    """
    Summarizes a completed round.
    Returns score, strengths, gaps, recommendation.
    """
    user = await require_auth(request)

    try:
        body_raw = await request.json()
        questions    = body_raw.get("questions", [])
        evaluations  = body_raw.get("evaluations", [])
        round_number = body_raw.get("round_number", 1)
        idea         = body_raw.get("idea", "")
        role         = body_raw.get("role", "Engineer")
        project_id   = body_raw.get("project_id", "")

        summary = await summarize_round(
            questions=questions,
            evaluations=evaluations,
            round_number=round_number,
            idea=idea,
            role=role,
        )

        return JSONResponse({
            "success":    True,
            "project_id": project_id,
            "summary":    summary,
        })

    except Exception as e:
        logger.error(f"Quiz summarize failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.post("/quiz/complete")
async def complete_quiz(request: Request, body: QuizCompleteRequest):
    """
    Called when user clicks Move to Next Stage.
    Saves all gaps to MCP + Supabase.
    """
    user = await require_auth(request)

    try:
        logger.info(
            f"Quiz completing — project: {body.project_id} | "
            f"gaps: {len(body.all_gaps)} | "
            f"rounds: {len(body.all_rounds)}"
        )

        # Build final summary across all rounds
        total_questions = sum(r.get("total", 0) for r in body.all_rounds)
        total_correct   = sum(r.get("correct", 0) for r in body.all_rounds)
        final_score     = round((total_correct / total_questions) * 100) if total_questions > 0 else 0

        final_summary = {
            "total_rounds":    len(body.all_rounds),
            "total_questions": total_questions,
            "total_correct":   total_correct,
            "final_score_pct": final_score,
            "knowledge_gaps":  body.all_gaps,
            "idea":            body.idea,
            "role":            body.role,
        }

        # Save to both MCP and Supabase
        await save_gaps_to_mcp(body.project_id, body.all_gaps, final_summary)
        await save_gaps_to_supabase(body.project_id, body.all_gaps, body.all_rounds)

        logger.info(
            f"Quiz complete — project: {body.project_id} | "
            f"score: {final_score}% | "
            f"gaps saved: {len(body.all_gaps)}"
        )

        return JSONResponse({
            "success":       True,
            "project_id":    body.project_id,
            "final_summary": final_summary,
            "message":       f"Quiz complete. {len(body.all_gaps)} knowledge gaps saved for Stage 8.",
        })

    except Exception as e:
        logger.error(f"Quiz complete failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )