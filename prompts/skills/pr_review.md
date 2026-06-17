# Pull Request Writer

You are writing GitHub Pull Request descriptions for a developer's portfolio. Every PR must tell a story that impresses a recruiter or technical interviewer who reads it. Generic PR descriptions are worse than none — they signal you don't know what you built.

---

## PR Title Format

```
[module-name]: brief description of what changed in plain English
```

Examples:
- `research-agent: add parallel 4-source search with 45s timeout`
- `council: add peer review round between advisors and chairman`
- `preview: replace E2B with local Docker warm pool`
- `memory: add Valkey embedding cache for decision recall`

Never: "fixed stuff", "updates", "WIP", "changes"

---

## PR Description Template — Use Exactly

```markdown
## What changed
[1-2 sentences. The module name, what it does now that it didn't before. 
Mention the specific technical change, not just "added a feature".]

Example:
"Added the peer review round to the War Room. After all 5 advisors complete, 
each advisor now reviews all other anonymized responses and flags unsupported claims 
before the Chairman sees them. Eliminates hallucinated GitHub stats from advisor outputs."

---

## Why this exists
[The problem this solves. If an ADR exists, link it.]

Example:
"Without peer review, advisors were citing invented GitHub star counts and made-up job statistics. 
The chairman was synthesizing unreliable data. This fix ensures every advisor claim is 
cross-validated before it reaches synthesis."

Related: `docs/decisions/ADR-003-council-peer-review.md`

---

## Technical decisions made here
[At least one specific decision with reasoning. This is what recruiters read.]

Example:
"Peer review uses anonymized responses (A through E) to prevent positional bias — 
advisors defer to whichever response appears first if they know who wrote it. 
The anonymization mapping is revealed in the chairman's context but not in the peer review round."

---

## How to verify this works
[Exact commands. Must be reproducible by someone who just cloned the repo.]

1. `cd 3netra-ai && docker compose up -d`
2. `curl -X POST http://localhost:8000/api/council -d '{"idea": "job matching API", "role": "ML Engineer"}'`
3. Expect: response JSON includes `peer_review_round: true` and `fact_checked_claims: [...]`
4. Verify: no advisor claim in the response cites a number without a source URL

---

## Test results
All existing tests: passing
New tests added: `tests/test_council.py::test_peer_review_eliminates_hallucinations`
Performance: peer review adds ~8s to council runtime (5 parallel Haiku calls)
```

---

## What Makes a PR Stand Out to a Recruiter

1. Mentions a specific tradeoff made ("chose X over Y because...")
2. Shows awareness of what could go wrong ("without this, [specific failure mode]")
3. Quantifies the change ("adds ~8s" not "adds some latency")
4. Includes a concrete verification step that actually works

---

## PR Size Rules

One PR = one module or one feature. Never combine unrelated changes.
If the PR touches more than 8 files: split it.
If the PR description needs more than 3 paragraphs: the PR is too large.

---

## ADR Reference Format

When a PR implements a decision documented in an ADR:
```markdown
Implements: docs/decisions/ADR-004-haiku-vs-sonnet-routing.md

Decision summary: Haiku for advisors (20x cheaper, sufficient quality for structured tasks).
Sonnet for Chairman + code gen (quality required, cost secondary).
```
