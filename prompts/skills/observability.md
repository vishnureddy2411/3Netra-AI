# Observability Standards

Every module you build must have structured logging and clean error handling baked in from the first line.
Not added later. Not optional. Built in.

---

## Logger Setup — One Line Per File

```python
import logging
logger = logging.getLogger(__name__)
```

Use __name__ so log output shows exactly which file the message came from.
Never use print() in any module — it goes nowhere in production.

---

## Log Levels — Use Exactly

| Level   | When to use                                                  |
|---------|--------------------------------------------------------------|
| DEBUG   | Internal state during development. Never in production paths.|
| INFO    | Operation started, operation completed with duration.        |
| WARNING | Expected failure handled gracefully (retry, cache miss).     |
| ERROR   | Unexpected failure that reached the user or lost data.       |

---

## Required Log Points — Every External Call

Every function that calls Claude API, a database, an external API, or Docker MUST have:

```python
async def call_research_api(query: str, project_id: str) -> dict:
    logger.info("research_api_start", extra={"query": query[:50], "project_id": project_id})
    start = time.monotonic()
    try:
        result = await _do_the_call(query)
        elapsed = round((time.monotonic() - start) * 1000)
        logger.info("research_api_complete", extra={"ms": elapsed, "project_id": project_id})
        return result
    except Exception as e:
        logger.error("research_api_failed", extra={"error": str(e), "project_id": project_id})
        raise
```

---

## Never Log These

- Passwords, API keys, secret tokens (any value from env vars)
- Full request or response bodies (log shape: keys only, not values)
- User PII: emails, names, phone numbers in raw form
- Full stack traces at INFO level (only at ERROR level)

---

## Error Return Shape — Always Structured

Every function that can fail must return a structured error, never raise unhandled exceptions to the caller:

```python
# WRONG — unhandled exception crashes the pipeline 3 stages later
result = json.loads(claude_response)

# CORRECT — structured error returned immediately
try:
    result = json.loads(claude_response)
except json.JSONDecodeError as e:
    logger.error("json_parse_failed", extra={"error": str(e), "response_preview": claude_response[:100]})
    return {
        "success": False,
        "error": "Agent returned malformed response",
        "code": "PARSE_ERROR",
        "recoverable": True,
        "retry_suggestion": "Retrying with stricter JSON instruction"
    }
```

---

## Request Tracing — Include in Every Log

Generate a short request ID at the start of every user session and pass it through:

```python
import uuid
session_id = str(uuid.uuid4())[:8]  # e.g., "a3f2b1c9"
# Pass session_id to every function, include in every log extra={}
```

This lets you grep all logs for one user's session: `grep "session_id: a3f2b1c9" app.log`

---

## Health Check Endpoint — Required in Every Service

Every FastAPI backend MUST have:

```python
@app.get("/health")
async def health():
    return {"status": "ok", "service": "3netra-backend", "timestamp": datetime.utcnow().isoformat()}
```

Railway and Docker health checks call this. If it's missing, deployments fail silently.
