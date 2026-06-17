"""
backend/services/error_recovery.py

Structured error handling for every failure mode in 3Netra-AI.
Every function returns a dict that the SSE handler sends to the chat UI.
The chat UI renders it as a specific error card with the right recovery action.

Never let a raw Python exception reach the user. Every failure mode is here.
"""

import asyncio
import logging
import time
from typing import Literal

import anthropic
import httpx

logger = logging.getLogger(__name__)

# ── Error card types (chat UI renders differently per type) ───────────────────
ErrorType = Literal[
    "claude_rate_limit",
    "claude_timeout",
    "claude_invalid_response",
    "research_api_empty",
    "research_api_failed",
    "docker_start_failed",
    "docker_health_check_failed",
    "playwright_capture_failed",
    "mcp_server_unreachable",
    "database_write_failed",
    "session_expired",
    "unknown",
]


def _error_card(
    error_type: ErrorType,
    user_message: str,
    technical_detail: str,
    recoverable: bool,
    recovery_action: str,
    retry_after_seconds: int = 0,
) -> dict:
    """Build a structured error dict for the chat UI."""
    return {
        "type": "error_card",
        "error_type": error_type,
        "user_message": user_message,
        "technical_detail": technical_detail,
        "recoverable": recoverable,
        "recovery_action": recovery_action,
        "retry_after_seconds": retry_after_seconds,
    }


# ── Claude API failures ───────────────────────────────────────────────────────

def handle_claude_rate_limit(agent_name: str, retry_after: int = 30) -> dict:
    """429 or 529 from Anthropic API after all SDK retries exhausted."""
    logger.warning("claude_rate_limit", extra={"agent": agent_name, "retry_after": retry_after})
    return _error_card(
        error_type="claude_rate_limit",
        user_message=f"The {agent_name} hit a rate limit — retrying in {retry_after} seconds.",
        technical_detail=f"Anthropic API 429/529 after 3 SDK retries. Agent: {agent_name}",
        recoverable=True,
        recovery_action="auto_retry",
        retry_after_seconds=retry_after,
    )


def handle_claude_timeout(agent_name: str, timeout_s: float) -> dict:
    """Agent call exceeded timeout threshold."""
    logger.error("claude_timeout", extra={"agent": agent_name, "timeout_s": timeout_s})
    return _error_card(
        error_type="claude_timeout",
        user_message=f"The {agent_name} is taking longer than expected. Retrying once more.",
        technical_detail=f"Timeout after {timeout_s}s. Agent: {agent_name}",
        recoverable=True,
        recovery_action="retry_once",
        retry_after_seconds=5,
    )


def handle_claude_invalid_response(agent_name: str, raw_response: str, attempt: int) -> dict:
    """Agent returned malformed or invalid JSON."""
    preview = raw_response[:150].replace("\n", " ")
    logger.error("claude_invalid_response", extra={
        "agent": agent_name,
        "attempt": attempt,
        "response_preview": preview
    })

    if attempt < 2:
        return _error_card(
            error_type="claude_invalid_response",
            user_message=f"The {agent_name} returned an unexpected format — asking it to try again.",
            technical_detail=f"JSON validation failed on attempt {attempt}. Preview: {preview}",
            recoverable=True,
            recovery_action="retry_with_stricter_prompt",
            retry_after_seconds=2,
        )
    else:
        return _error_card(
            error_type="claude_invalid_response",
            user_message=(
                f"The {agent_name} couldn't produce a valid response after two attempts. "
                "You can try again or continue manually."
            ),
            technical_detail=f"JSON validation failed on both attempts. Preview: {preview}",
            recoverable=False,
            recovery_action="show_raw_and_continue",
        )


# ── Research API failures ─────────────────────────────────────────────────────

def handle_research_api_empty(source_name: str, query: str) -> dict:
    """Research API returned 0 results."""
    logger.warning("research_api_empty", extra={"source": source_name, "query": query[:50]})
    return _error_card(
        error_type="research_api_empty",
        user_message=f"{source_name} returned no results for this idea — using alternative signals.",
        technical_detail=f"Empty result set from {source_name}. Query: {query[:100]}",
        recoverable=True,
        recovery_action="skip_source_continue",
    )


def handle_research_api_failed(source_name: str, error: Exception) -> dict:
    """Research API call threw an exception."""
    logger.error("research_api_failed", extra={"source": source_name, "error": str(error)})
    return _error_card(
        error_type="research_api_failed",
        user_message=f"Couldn't reach {source_name} — the other sources will still run.",
        technical_detail=f"{type(error).__name__}: {str(error)[:200]}",
        recoverable=True,
        recovery_action="skip_source_continue",
    )


# ── Docker / Preview failures ─────────────────────────────────────────────────

def handle_docker_start_failed(module_name: str, error: Exception) -> dict:
    """Docker container failed to start for preview."""
    logger.error("docker_start_failed", extra={"module": module_name, "error": str(error)})
    return _error_card(
        error_type="docker_start_failed",
        user_message=(
            f"Preview couldn't start for {module_name} — showing the generated code instead. "
            "You can review it and decide to continue or fix."
        ),
        technical_detail=f"docker-py error: {str(error)[:200]}",
        recoverable=True,
        recovery_action="show_code_fallback",
    )


def handle_docker_health_check_failed(module_name: str, port: int, attempts: int) -> dict:
    """Container started but servers didn't respond to health checks."""
    logger.error("docker_health_check_failed", extra={
        "module": module_name, "port": port, "attempts": attempts
    })
    return _error_card(
        error_type="docker_health_check_failed",
        user_message=(
            f"The {module_name} preview started but the server didn't respond. "
            "This usually means a startup error in the generated code."
        ),
        technical_detail=f"Health check failed after {attempts} attempts on port {port}",
        recoverable=True,
        recovery_action="show_startup_logs_and_offer_fix",
    )


def handle_playwright_capture_failed(module_name: str, error: Exception) -> dict:
    """Playwright couldn't take a screenshot."""
    logger.error("playwright_capture_failed", extra={"module": module_name, "error": str(error)})
    return _error_card(
        error_type="playwright_capture_failed",
        user_message=(
            f"Screenshot of {module_name} failed — the server is running but the page "
            "didn't render. The code is still available to review."
        ),
        technical_detail=f"Playwright error: {str(error)[:200]}",
        recoverable=True,
        recovery_action="show_code_fallback",
    )


# ── Infrastructure failures ───────────────────────────────────────────────────

def handle_mcp_server_unreachable(tool_name: str, error: Exception) -> dict:
    """MCP server didn't respond to a tool call."""
    logger.error("mcp_unreachable", extra={"tool": tool_name, "error": str(error)})
    return _error_card(
        error_type="mcp_server_unreachable",
        user_message="Project memory is temporarily unavailable — retrying connection.",
        technical_detail=f"MCP tool {tool_name} failed: {str(error)[:200]}",
        recoverable=True,
        recovery_action="retry_mcp_connection",
        retry_after_seconds=5,
    )


def handle_database_write_failed(table: str, error: Exception) -> dict:
    """Supabase or SQLite write failed."""
    logger.error("db_write_failed", extra={"table": table, "error": str(error)})
    return _error_card(
        error_type="database_write_failed",
        user_message="Saving your progress hit an issue — your session data may not be fully saved.",
        technical_detail=f"DB write to {table} failed: {str(error)[:200]}",
        recoverable=False,
        recovery_action="warn_user_data_risk",
    )


# ── Generic fallback ──────────────────────────────────────────────────────────

def handle_unknown_error(context: str, error: Exception) -> dict:
    """Catch-all for unexpected errors."""
    logger.error("unknown_error", extra={"context": context, "error": str(error)})
    return _error_card(
        error_type="unknown",
        user_message="Something unexpected happened. You can try again or refresh the page.",
        technical_detail=f"Context: {context}. Error: {type(error).__name__}: {str(error)[:300]}",
        recoverable=True,
        recovery_action="offer_retry_or_refresh",
    )


# ── Async retry wrapper ───────────────────────────────────────────────────────

async def retry_with_backoff(
    fn,
    max_attempts: int = 2,
    initial_delay: float = 2.0,
    context: str = "unknown",
):
    """
    Retry an async function with exponential backoff.
    Returns result on success, raises on final failure.

    Usage:
        result = await retry_with_backoff(
            lambda: call_haiku(system, user),
            max_attempts=2,
            context="chairman_synthesis"
        )
    """
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except (anthropic.RateLimitError, anthropic.APIStatusError) as e:
            last_error = e
            if attempt < max_attempts:
                delay = initial_delay * (2 ** (attempt - 1))
                logger.warning(
                    "retry_attempt",
                    extra={"attempt": attempt, "delay_s": delay, "context": context}
                )
                await asyncio.sleep(delay)
        except Exception as e:
            raise  # Non-retryable errors bubble up immediately

    raise last_error
