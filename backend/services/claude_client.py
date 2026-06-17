"""
backend/services/claude_client.py

Centralised Claude API client for 3Netra-AI.
All agent calls go through here — never create anthropic.Anthropic() elsewhere.

Handles:
- Retry with exponential backoff (max_retries=3 via SDK)
- Global semaphore to cap concurrent API calls (max 10)
- Per-model timeout (Haiku: 30s, Sonnet: 60s)
- Structured streaming via SSE
- Token counting before every call
"""

import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Optional

import anthropic
import tiktoken

logger = logging.getLogger(__name__)

# ── Models ────────────────────────────────────────────────────────────────────
HAIKU_MODEL  = "claude-haiku-4-5"
SONNET_MODEL = "claude-sonnet-4-6"

HAIKU_TIMEOUT  = 30.0   # seconds — advisors, quiz, annotations
SONNET_TIMEOUT = 60.0   # seconds — chairman, code gen, diagrams

# ── Rate limiting ─────────────────────────────────────────────────────────────
# Max 10 concurrent Claude calls regardless of user count.
# Prevents rate-limit cascade when multiple users hit War Room simultaneously.
CLAUDE_SEMAPHORE = asyncio.Semaphore(10)

# ── Shared client — instantiated once at import time ─────────────────────────
# max_retries=3 → SDK handles 429 and 529 with exponential backoff automatically.
# Never create anthropic.Anthropic() outside this file.
_client = anthropic.Anthropic(max_retries=3)

# ── Token counting ────────────────────────────────────────────────────────────
_enc = tiktoken.get_encoding("cl100k_base")
MAX_TOKENS_BEFORE_TRUNCATION = 150_000

def count_tokens(text: str) -> int:
    return len(_enc.encode(text))

def truncate_if_needed(system: str, user: str) -> tuple[str, str]:
    """Truncate user prompt if total tokens exceed safe limit."""
    total = count_tokens(system) + count_tokens(user)
    if total <= MAX_TOKENS_BEFORE_TRUNCATION:
        return system, user

    # Truncate user content only — never truncate system/skill content
    budget = MAX_TOKENS_BEFORE_TRUNCATION - count_tokens(system) - 500  # 500 buffer
    tokens = _enc.encode(user)
    truncated = _enc.decode(tokens[:budget])
    logger.warning(
        "prompt_truncated",
        extra={"original_tokens": total, "truncated_to": budget}
    )
    return system, truncated + "\n\n[Context truncated to fit token limit]"


# ── Core call functions ───────────────────────────────────────────────────────

async def call_haiku(
    system: str,
    user: str,
    max_tokens: int = 1000,
    cache_system: bool = False,
) -> str:
    """
    Single Haiku call. Use for: advisors, quiz, annotations, classification,
    diagram planning, career posts, cost tracking.

    Args:
        system: System prompt (skill content + role definition)
        user: User message
        max_tokens: Max response tokens
        cache_system: If True, marks system content for prompt caching
    Returns:
        Response text string
    """
    system_content = _build_system_content(system, cache_system)
    system, user = truncate_if_needed(system, user)

    logger.info("haiku_call_start", extra={"max_tokens": max_tokens})
    start = time.monotonic()

    async with CLAUDE_SEMAPHORE:
        try:
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: _client.messages.create(
                        model=HAIKU_MODEL,
                        max_tokens=max_tokens,
                        system=system_content,
                        messages=[{"role": "user", "content": user}],
                    )
                ),
                timeout=HAIKU_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error("haiku_timeout", extra={"timeout_s": HAIKU_TIMEOUT})
            raise TimeoutError(f"Haiku call timed out after {HAIKU_TIMEOUT}s")

    elapsed = round((time.monotonic() - start) * 1000)
    logger.info("haiku_call_complete", extra={"ms": elapsed, "tokens_out": response.usage.output_tokens})
    return response.content[0].text


async def call_sonnet(
    system: str,
    user: str,
    max_tokens: int = 4000,
    cache_system: bool = True,
) -> str:
    """
    Single Sonnet call. Use for: Chairman verdict, architecture diagrams,
    code generation, README generation. Cache system by default — diagrams
    and project graph injected here are expensive and repeated.

    Args:
        system: System prompt (skill content + cached project context)
        user: User message (current module spec)
        max_tokens: Max response tokens (4000 default, 8000 for code gen)
        cache_system: If True, marks system for prompt caching
    Returns:
        Response text string
    """
    system_content = _build_system_content(system, cache_system)
    system, user = truncate_if_needed(system, user)

    logger.info("sonnet_call_start", extra={"max_tokens": max_tokens})
    start = time.monotonic()

    async with CLAUDE_SEMAPHORE:
        try:
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: _client.messages.create(
                        model=SONNET_MODEL,
                        max_tokens=max_tokens,
                        system=system_content,
                        messages=[{"role": "user", "content": user}],
                    )
                ),
                timeout=SONNET_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error("sonnet_timeout", extra={"timeout_s": SONNET_TIMEOUT})
            raise TimeoutError(f"Sonnet call timed out after {SONNET_TIMEOUT}s")

    elapsed = round((time.monotonic() - start) * 1000)
    logger.info("sonnet_call_complete", extra={"ms": elapsed, "tokens_out": response.usage.output_tokens})
    return response.content[0].text


async def stream_sonnet(
    system: str,
    user: str,
    max_tokens: int = 4000,
) -> AsyncGenerator[str, None]:
    """
    Streaming Sonnet call for SSE — yields token chunks as they arrive.
    Use for: real-time chat UI responses, code generation display.

    Usage in FastAPI SSE endpoint:
        async for chunk in stream_sonnet(system, user):
            yield f"data: {json.dumps({'token': chunk})}\n\n"
    """
    system, user = truncate_if_needed(system, user)

    async with CLAUDE_SEMAPHORE:
        with _client.messages.stream(
            model=SONNET_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            for text in stream.text_stream:
                yield text


async def call_haiku_parallel(calls: list[dict]) -> list[str]:
    """
    Run multiple Haiku calls in parallel — used for War Room advisors.
    Each call dict: {"system": str, "user": str, "max_tokens": int}

    Example:
        results = await call_haiku_parallel([
            {"system": advisor1_prompt, "user": research_json},
            {"system": advisor2_prompt, "user": research_json},
            ...
        ])
    """
    tasks = [
        call_haiku(
            system=c["system"],
            user=c["user"],
            max_tokens=c.get("max_tokens", 1000),
            cache_system=c.get("cache_system", False),
        )
        for c in calls
    ]
    return list(await asyncio.gather(*tasks))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_system_content(system: str, cache: bool) -> list | str:
    """If cache=True, wraps system text in cache_control block."""
    if not cache:
        return system
    return [
        {
            "type": "text",
            "text": system,
            "cache_control": {"type": "ephemeral"},
        }
    ]
