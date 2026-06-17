"""
backend/services/reward_engine.py

Reward signal collection and prompt memory for 3Netra-AI's RL-style learning.

ELI5: Think of this like a teacher grading papers.
  ✅ Approve = A grade (+1.0 reward)
  ✏️ Fix     = C grade (-0.3 reward)
  🔄 Rebuild = F grade (-1.0 reward)

Over time, the engine learns which prompts got A grades and uses
those as templates for future similar tasks.

When you have 10,000+ approved outputs, export them as a
fine-tuning dataset and train your own model:
  high_reward_sessions = SELECT * FROM rewards WHERE reward >= 0.8
  → Export as {"messages": [...]} JSONL format
  → Fine-tune Llama 3.1 8B on Together AI / Hugging Face
  → Point LLM_STRONG_MODEL at your endpoint
  → Zero API costs from that day forward
"""

import logging
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Database ──────────────────────────────────────────────────────────────────
REWARD_DB_PATH = Path("memory/rewards.db")

REWARD_SCHEMA = """
CREATE TABLE IF NOT EXISTS rewards (
    id           TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    session_id   TEXT NOT NULL,
    module_type  TEXT NOT NULL,
    module_name  TEXT,
    prompt_hash  TEXT NOT NULL,
    model        TEXT NOT NULL,
    reward       REAL NOT NULL CHECK(reward BETWEEN -1.0 AND 1.0),
    action       TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_rewards_module_type ON rewards(module_type);
CREATE INDEX IF NOT EXISTS idx_rewards_session     ON rewards(session_id);
CREATE INDEX IF NOT EXISTS idx_rewards_high        ON rewards(reward) WHERE reward >= 0.7;

CREATE TABLE IF NOT EXISTS prompt_memory (
    id            TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    module_type   TEXT NOT NULL,
    tier          TEXT NOT NULL CHECK(tier IN ('fast', 'strong')),
    prompt_hash   TEXT NOT NULL,
    prompt_excerpt TEXT NOT NULL,
    avg_reward    REAL NOT NULL,
    use_count     INTEGER DEFAULT 1,
    last_used_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pm_module_type ON prompt_memory(module_type, tier);

CREATE TABLE IF NOT EXISTS fine_tune_exports (
    id            TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    session_id    TEXT NOT NULL,
    module_type   TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    user_message  TEXT NOT NULL,
    agent_output  TEXT NOT NULL,
    reward        REAL NOT NULL,
    exported      INTEGER DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# ── Reward values ─────────────────────────────────────────────────────────────
REWARD_MAP = {
    "approve":  1.0,    # User clicked ✅ Continue — excellent output
    "fix":     -0.3,    # User clicked ✏️ Fix — acceptable but needed adjustment
    "rebuild": -1.0,    # User clicked 🔄 Rebuild — poor output, start over
}

# ── Threshold for storing in prompt_memory ────────────────────────────────────
HIGH_REWARD_THRESHOLD = 0.7  # only prompts that earned ≥0.7 become templates


def _get_conn() -> sqlite3.Connection:
    REWARD_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(REWARD_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(REWARD_SCHEMA)
    return conn


# ── Record functions ──────────────────────────────────────────────────────────

async def record_call(
    session_id: str,
    module_type: str,
    prompt_hash: str,
    model: str,
    module_name: Optional[str] = None,
) -> None:
    """
    Record an agent call. Reward is added later when user gives feedback.
    Called automatically by llm_client.call_fast() and call_strong().
    """
    with _get_conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO rewards
               (session_id, module_type, module_name, prompt_hash, model, reward, action)
               VALUES (?, ?, ?, ?, ?, 0.0, 'pending')""",
            (session_id, module_type, module_name, prompt_hash, model),
        )
    logger.debug("reward_call_recorded", extra={
        "session_id": session_id,
        "module_type": module_type,
        "prompt_hash": prompt_hash,
    })


async def record_reward(
    session_id: str,
    module_name: str,
    action: str,  # "approve" | "fix" | "rebuild"
    system_prompt: Optional[str] = None,
    user_message: Optional[str] = None,
    agent_output: Optional[str] = None,
) -> float:
    """
    Called when user clicks ✅ / ✏️ / 🔄 in the chat UI.
    Records the reward signal and updates prompt memory if reward is high.

    Returns the reward value for logging.
    """
    reward = REWARD_MAP.get(action, 0.0)

    with _get_conn() as conn:
        # Update reward in rewards table
        conn.execute(
            """UPDATE rewards
               SET reward = ?, action = ?
               WHERE session_id = ?
               ORDER BY created_at DESC
               LIMIT 1""",
            (reward, action, session_id),
        )

        # Store full interaction for fine-tuning export if high reward
        if reward >= HIGH_REWARD_THRESHOLD and all([system_prompt, user_message, agent_output]):
            conn.execute(
                """INSERT INTO fine_tune_exports
                   (session_id, module_type, system_prompt, user_message, agent_output, reward)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (session_id, module_name, system_prompt, user_message, agent_output, reward),
            )

    logger.info("reward_recorded", extra={
        "session_id": session_id,
        "module": module_name,
        "action": action,
        "reward": reward,
    })

    # Update prompt memory for high-reward prompts
    if reward >= HIGH_REWARD_THRESHOLD:
        await _update_prompt_memory(session_id, module_name, reward)

    return reward


async def _update_prompt_memory(
    session_id: str,
    module_type: str,
    reward: float,
) -> None:
    """
    When a prompt earns high reward, store it in prompt_memory.
    Future calls to the same module_type will retrieve this as a template.
    """
    with _get_conn() as conn:
        # Get the prompt hash for this session's last call
        row = conn.execute(
            "SELECT prompt_hash FROM rewards WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
            (session_id,)
        ).fetchone()

        if not row:
            return

        prompt_hash = row["prompt_hash"]

        # Check if this prompt is already in memory
        existing = conn.execute(
            "SELECT id, avg_reward, use_count FROM prompt_memory WHERE prompt_hash = ?",
            (prompt_hash,)
        ).fetchone()

        if existing:
            # Update running average reward
            new_avg = (existing["avg_reward"] * existing["use_count"] + reward) / (existing["use_count"] + 1)
            conn.execute(
                "UPDATE prompt_memory SET avg_reward = ?, use_count = use_count + 1 WHERE prompt_hash = ?",
                (new_avg, prompt_hash)
            )
        else:
            # Insert new high-reward prompt
            # We store only an excerpt (first 500 chars) to save space
            conn.execute(
                """INSERT INTO prompt_memory (module_type, tier, prompt_hash, prompt_excerpt, avg_reward)
                   VALUES (?, 'strong', ?, ?, ?)""",
                (module_type, prompt_hash, f"[prompt_hash:{prompt_hash}]", reward)
            )

    logger.info("prompt_memory_updated", extra={
        "module_type": module_type,
        "prompt_hash": prompt_hash,
        "reward": reward,
    })


# ── Retrieval functions ───────────────────────────────────────────────────────

async def get_best_prompts(
    module_type: str,
    tier: str = "strong",
    limit: int = 2,
    min_reward: float = 0.7,
) -> list[dict]:
    """
    Retrieve top-performing prompts for a module type.
    Called by llm_client before building each module.

    ELI5: "Show me the 2 best examples of auth module prompts
    that users approved without asking for fixes."
    """
    with _get_conn() as conn:
        rows = conn.execute(
            """SELECT prompt_excerpt, avg_reward, use_count
               FROM prompt_memory
               WHERE module_type = ? AND tier = ? AND avg_reward >= ?
               ORDER BY avg_reward DESC, use_count DESC
               LIMIT ?""",
            (module_type, tier, min_reward, limit)
        ).fetchall()

    return [dict(row) for row in rows]


# ── Fine-tuning export ────────────────────────────────────────────────────────

def export_fine_tune_dataset(output_path: str = "fine_tune_data.jsonl") -> int:
    """
    Export all high-reward (prompt, output) pairs as a JSONL fine-tuning dataset.
    Run this when you're ready to train your own model.

    Format: {"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}

    Next steps after export:
    1. Upload to Hugging Face / Together AI
    2. Fine-tune Llama 3.1 8B (8B params, good balance of quality vs cost)
    3. Host on vLLM or Ollama
    4. Set LLM_STRONG_MODEL=your-endpoint in .env.local
    5. Zero API costs

    Returns: number of examples exported
    """
    import json

    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM fine_tune_exports WHERE exported = 0 AND reward >= 0.7 ORDER BY reward DESC"
        ).fetchall()

    if not rows:
        logger.info("no_fine_tune_data_available")
        return 0

    count = 0
    with open(output_path, "w") as f:
        for row in rows:
            example = {
                "messages": [
                    {"role": "system",    "content": row["system_prompt"]},
                    {"role": "user",      "content": row["user_message"]},
                    {"role": "assistant", "content": row["agent_output"]},
                ]
            }
            f.write(json.dumps(example) + "\n")
            count += 1

    # Mark as exported
    with _get_conn() as conn:
        conn.execute("UPDATE fine_tune_exports SET exported = 1 WHERE exported = 0")

    logger.info("fine_tune_export_complete", extra={"examples": count, "output": output_path})
    return count


# ── Analytics ─────────────────────────────────────────────────────────────────

def get_reward_stats() -> dict:
    """
    Session analytics — how many approvals vs fixes vs rebuilds.
    Useful for identifying which module types have the worst quality.
    """
    with _get_conn() as conn:
        stats = conn.execute("""
            SELECT
                module_type,
                COUNT(*) as total_calls,
                AVG(reward) as avg_reward,
                SUM(CASE WHEN action='approve' THEN 1 ELSE 0 END) as approvals,
                SUM(CASE WHEN action='fix' THEN 1 ELSE 0 END) as fixes,
                SUM(CASE WHEN action='rebuild' THEN 1 ELSE 0 END) as rebuilds
            FROM rewards
            WHERE action != 'pending'
            GROUP BY module_type
            ORDER BY avg_reward ASC
        """).fetchall()

        total_for_export = conn.execute(
            "SELECT COUNT(*) as n FROM fine_tune_exports WHERE reward >= 0.7 AND exported = 0"
        ).fetchone()["n"]

    return {
        "module_stats": [dict(r) for r in stats],
        "ready_for_export": total_for_export,
        "export_threshold": "10,000 examples recommended for fine-tuning",
    }
