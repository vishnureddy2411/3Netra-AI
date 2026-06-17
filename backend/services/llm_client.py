"""
backend/services/llm_client.py

Model-agnostic LLM client for 3Netra-AI.
Every agent call goes through here. Swap LLMs by changing one env var.

Install: pip install litellm

Supported models (set LLM_MODEL in .env.local):
  Claude:     claude-sonnet-4-6 / claude-haiku-4-5
  GPT:        gpt-4o / gpt-4o-mini
  Gemini:     gemini/gemini-1.5-pro
  Groq:       groq/llama-3.1-70b-versatile (fast + cheap)
  Ollama:     ollama/llama3.1 (local, $0)
  Together:   together_ai/mistral-7b-instruct
  vLLM:       hosted_vllm/your-model (self-hosted)
  Your model: openai/your-fine-tuned-model (OpenAI-compatible endpoint)

ELI5: litellm is a translator. Claude, GPT, and Gemini all speak
different "languages" in their APIs. litellm lets you write one set
of code that works with all of them. Changing models = changing one
word in your .env.local file.
"""

import asyncio
import hashlib
import logging
import os
import time
from typing import AsyncGenerator, Optional

import litellm
from litellm import acompletion

logger = logging.getLogger(__name__)

# ── Model routing ─────────────────────────────────────────────────────────────
# Two model tiers — cheap for simple tasks, powerful for quality tasks.
# Override individually for fine-grained cost control.

LLM_FAST   = os.getenv("LLM_FAST_MODEL",  "claude-haiku-4-5")     # advisors, quiz, annotations
LLM_STRONG = os.getenv("LLM_STRONG_MODEL", "claude-sonnet-4-6")   # chairman, code gen, diagrams
LLM_EMBED  = os.getenv("LLM_EMBED_MODEL",  None)                  # None = local sentence-transformers

# Timeouts
FAST_TIMEOUT   = float(os.getenv("LLM_FAST_TIMEOUT",   "30"))
STRONG_TIMEOUT = float(os.getenv("LLM_STRONG_TIMEOUT", "60"))

# Silence litellm's verbose logging (it's noisy)
litellm.set_verbose = False

# ── Semaphore — cap concurrent LLM calls ─────────────────────────────────────
_SEMAPHORE = asyncio.Semaphore(int(os.getenv("LLM_MAX_CONCURRENT", "10")))


# ── Core call functions ───────────────────────────────────────────────────────

async def call_fast(
    system: str,
    user: str,
    max_tokens: int = 1000,
    session_id: Optional[str] = None,
    module_type: Optional[str] = None,
) -> str:
    """
    Fast/cheap model call. Use for: advisors, quiz, annotations,
    diagram planner, module classifier, career posts, cost tracking.

    Automatically retrieves best historical prompt if PromptMemory
    has high-reward examples for this module_type.
    """
    enhanced_system = await _enhance_with_memory(system, module_type, "fast")
    result = await _call(LLM_FAST, enhanced_system, user, max_tokens, FAST_TIMEOUT)

    # Store for reward tracking (session_id + prompt hash)
    if session_id and module_type:
        from services.reward_engine import record_call
        await record_call(
            session_id=session_id,
            module_type=module_type,
            prompt_hash=_hash_prompt(system + user),
            model=LLM_FAST,
        )

    return result


async def call_strong(
    system: str,
    user: str,
    max_tokens: int = 4000,
    session_id: Optional[str] = None,
    module_type: Optional[str] = None,
) -> str:
    """
    Strong/quality model call. Use for: Chairman verdict,
    architecture diagrams, code generation, README generation.

    Retrieves best historical prompt from PromptMemory if available.
    """
    enhanced_system = await _enhance_with_memory(system, module_type, "strong")
    result = await _call(LLM_STRONG, enhanced_system, user, max_tokens, STRONG_TIMEOUT)

    if session_id and module_type:
        from services.reward_engine import record_call
        await record_call(
            session_id=session_id,
            module_type=module_type,
            prompt_hash=_hash_prompt(system + user),
            model=LLM_STRONG,
        )

    return result


async def call_fast_parallel(calls: list[dict]) -> list[str]:
    """
    Run multiple fast calls in parallel — for War Room advisors.
    Each call: {"system": str, "user": str, "max_tokens": int,
                "session_id": str, "module_type": str}
    """
    tasks = [
        call_fast(
            system=c["system"],
            user=c["user"],
            max_tokens=c.get("max_tokens", 1000),
            session_id=c.get("session_id"),
            module_type=c.get("module_type"),
        )
        for c in calls
    ]
    return list(await asyncio.gather(*tasks))


async def stream_strong(
    system: str,
    user: str,
    max_tokens: int = 4000,
) -> AsyncGenerator[str, None]:
    """
    Streaming strong model call for SSE — yields tokens as they arrive.
    Use for: real-time chat responses, code generation display.

    ELI5: Instead of waiting 30 seconds for the full response, you see
    each word appear one at a time, like watching someone type.
    """
    async with _SEMAPHORE:
        response = await acompletion(
            model=LLM_STRONG,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _call(
    model: str,
    system: str,
    user: str,
    max_tokens: int,
    timeout: float,
) -> str:
    """Core litellm call with semaphore + timeout + logging."""
    start = time.monotonic()
    logger.info("llm_call_start", extra={"model": model, "max_tokens": max_tokens})

    async with _SEMAPHORE:
        try:
            response = await asyncio.wait_for(
                acompletion(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user},
                    ],
                    max_tokens=max_tokens,
                    num_retries=3,        # litellm built-in retry with backoff
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.error("llm_timeout", extra={"model": model, "timeout": timeout})
            raise TimeoutError(f"{model} timed out after {timeout}s")

    elapsed = round((time.monotonic() - start) * 1000)
    tokens_out = response.usage.completion_tokens if response.usage else "?"
    logger.info("llm_call_complete", extra={
        "model": model,
        "ms": elapsed,
        "tokens_out": tokens_out,
    })

    return response.choices[0].message.content


async def _enhance_with_memory(
    system: str,
    module_type: Optional[str],
    tier: str,
) -> str:
    """
    Retrieves top-performing historical prompts for this module_type
    and appends them as examples to the system prompt.

    ELI5: If the agent built 50 auth modules and some got ✅ Approve,
    we look up what made those prompts work and include those examples
    in the next auth module prompt. The agent learns from past successes.
    """
    if not module_type:
        return system

    try:
        from services.reward_engine import get_best_prompts
        examples = await get_best_prompts(module_type=module_type, tier=tier, limit=2)
        if examples:
            examples_text = "\n\n".join([
                f"## Example that earned user approval:\n{ex['prompt_excerpt']}"
                for ex in examples
            ])
            return system + f"\n\n---\n\n## Historical patterns that worked well:\n{examples_text}"
    except Exception as e:
        logger.warning("prompt_memory_retrieval_failed", extra={"error": str(e)})

    return system


def _hash_prompt(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]
