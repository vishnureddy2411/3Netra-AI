# Performance Expert

You are building a performance-critical module. Apply every rule below exactly — no exceptions.

---

## Connection Management — Non-Negotiable

NEVER create a new httpx.AsyncClient, database connection, or Anthropic client inside a function body.
Every connection must come from app.state, created once at FastAPI startup and reused across all requests.

```python
# WRONG — creates new TCP connection on every call
async def fetch_github(query: str):
    async with httpx.AsyncClient() as client:
        return await client.get(...)

# CORRECT — reuses shared pool
async def fetch_github(query: str, request: Request):
    return await request.app.state.http_client.get(...)
```

---

## Async Patterns — Required

- ALWAYS use async/await for every I/O operation
- NEVER use time.sleep() → use await asyncio.sleep()
- NEVER use the requests library → use httpx.AsyncClient
- NEVER use blocking file I/O in a request handler → use aiofiles
- Run all independent operations in parallel:

```python
# WRONG — sequential, 3x slower
result1 = await fetch_github(query)
result2 = await fetch_hackernews(query)
result3 = await fetch_arxiv(query)

# CORRECT — parallel, same wall-clock time as the slowest one
result1, result2, result3 = await asyncio.gather(
    fetch_github(query),
    fetch_hackernews(query),
    fetch_arxiv(query)
)
```

---

## Caching Rules

Check Valkey BEFORE any database read that might repeat.

```python
cache_key = f"{entity_type}:{project_id}:{field}"

# Check cache first
cached = await valkey.get(cache_key)
if cached:
    return json.loads(cached)

# Miss: read from DB, write to cache
result = await db.query(...)
await valkey.set(cache_key, json.dumps(result), ex=3600)  # 1hr TTL
return result
```

TTL rules:
- Project graph: 7 days (changes rarely)
- Research report: 24 hours (stale after a day)
- Skill file content: infinite (loaded at startup, never expires)
- Agent verdicts: 30 days (immutable after creation)
- Query embeddings: 1 hour (same query reused in session)

---

## Database Query Rules

- NEVER use SELECT * — always specify exact columns needed
- ALWAYS add LIMIT N to list queries
- ALWAYS add indexes on columns you filter or sort by
- NEVER query in a loop — use JOIN or batch queries
- Use batch INSERT for multiple rows:

```python
# WRONG — N queries
for file in files:
    await db.execute("INSERT INTO files VALUES (?)", file)

# CORRECT — 1 query
await db.executemany("INSERT INTO files VALUES (?)", files)
```

---

## Token Efficiency

Count tokens before every Claude API call:

```python
import tiktoken
enc = tiktoken.get_encoding("cl100k_base")
token_count = len(enc.encode(prompt))

if token_count > 150_000:
    # Truncate least important context first
    # Never truncate: skill content, project graph, current module spec
    # Truncate first: previous message history, verbose diagram descriptions
    prompt = truncate_prompt(prompt, max_tokens=150_000)
```

Mark repeated context with prompt caching:
```python
{"type": "text", "text": diagram_content, "cache_control": {"type": "ephemeral"}}
```

---

## Response Time Logging

Log every operation that takes > 50ms:

```python
import time
start = time.monotonic()
result = await expensive_operation()
elapsed_ms = (time.monotonic() - start) * 1000
if elapsed_ms > 50:
    logger.info("operation_completed", extra={"op": "fetch_github", "ms": round(elapsed_ms)})
```
