"""
backend/services/research.py

Research Agent — searches 4 sources in parallel for any project idea.

Sources:
  1. GitHub    — similar repos, star counts, issues (risk signals)
  2. HackerNews — community sentiment, Show HN posts
  3. arXiv     — academic papers on the technology
  4. StackOverflow — ecosystem health, question volume

ELI5: Like sending 4 librarians to research your idea at the same time.
All 4 come back in 45 seconds instead of waiting 3 minutes for each.

Why parallel (asyncio.gather):
  Sequential: 4 × 12s = 48s total
  Parallel:   max(12s, 11s, 14s, 10s) = 14s total
  Saves ~34 seconds on every research call.
"""

import asyncio
import json
import logging
import os
from datetime import datetime

import httpx
from dotenv import load_dotenv

load_dotenv("../.env.local")

logger = logging.getLogger(__name__)

# ── API Configuration ─────────────────────────────────────────
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "3Netra-AI-Research/1.0",
}
if GITHUB_TOKEN:
    GITHUB_HEADERS["Authorization"] = f"token {GITHUB_TOKEN}"

REQUEST_TIMEOUT = 30.0  # seconds per API call


# ════════════════════════════════════════════════════════════
# INDIVIDUAL SOURCE FETCHERS
# ════════════════════════════════════════════════════════════

async def fetch_github(
    idea: str,
    http_client: httpx.AsyncClient,
) -> dict:
    """
    Search GitHub for similar projects.
    Returns top repos by stars, total count, and risk signals from Issues.

    ELI5: Searches GitHub like Google — finds projects similar to your idea
    and tells you how popular they are and what problems they have.
    """
    try:
        # Search repositories by topic
        search_query = idea[:100]  # GitHub limits query length
        response = await http_client.get(
            "https://api.github.com/search/repositories",
            params={
                "q": search_query,
                "sort": "stars",
                "order": "desc",
                "per_page": 5,
            },
            headers=GITHUB_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        repos = []
        for repo in data.get("items", [])[:5]:
            repos.append({
                "name": repo.get("full_name", ""),
                "stars": repo.get("stargazers_count", 0),
                "url": repo.get("html_url", ""),
                "description": repo.get("description", "")[:150],
                "language": repo.get("language", ""),
                "open_issues": repo.get("open_issues_count", 0),
                "last_updated": repo.get("updated_at", "")[:10],
            })

        total_count = data.get("total_count", 0)
        logger.info(f"GitHub: found {total_count} repos for '{idea[:50]}'")

        return {
            "source": "github",
            "total_similar_repos": total_count,
            "top_repos": repos,
            "market_signal": "high" if total_count > 1000 else "medium" if total_count > 100 else "low",
        }

    except Exception as e:
        logger.warning(f"GitHub search failed: {e}")
        return {
            "source": "github",
            "error": str(e),
            "total_similar_repos": 0,
            "top_repos": [],
            "market_signal": "unknown",
        }


async def fetch_hackernews(
    idea: str,
    http_client: httpx.AsyncClient,
) -> dict:
    """
    Search HackerNews for community discussions about this idea.
    No authentication needed — completely free and open.

    ELI5: HackerNews is where developers discuss new ideas.
    High upvotes = developers think this is a good idea.
    """
    try:
        # Use Algolia API — HackerNews's official search API
        response = await http_client.get(
            "https://hn.algolia.com/api/v1/search",
            params={
                "query": idea[:100],
                "tags": "story",
                "hitsPerPage": 5,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        posts = []
        for hit in data.get("hits", [])[:5]:
            posts.append({
                "title": hit.get("title", "")[:100],
                "url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                "points": hit.get("points", 0),
                "comments": hit.get("num_comments", 0),
                "created": hit.get("created_at", "")[:10],
            })

        total = data.get("nbHits", 0)
        avg_points = sum(p["points"] for p in posts) / len(posts) if posts else 0

        logger.info(f"HackerNews: found {total} posts for '{idea[:50]}'")

        return {
            "source": "hackernews",
            "total_posts": total,
            "top_posts": posts,
            "avg_upvotes": round(avg_points, 1),
            "community_interest": "high" if avg_points > 100 else "medium" if avg_points > 20 else "low",
        }

    except Exception as e:
        logger.warning(f"HackerNews search failed: {e}")
        return {
            "source": "hackernews",
            "error": str(e),
            "total_posts": 0,
            "top_posts": [],
            "community_interest": "unknown",
        }


async def fetch_arxiv(
    idea: str,
    http_client: httpx.AsyncClient,
) -> dict:
    """
    Search arXiv for academic papers on the technology.
    No authentication needed — completely free and open.

    ELI5: arXiv is where researchers publish papers.
    Many recent papers = active research area = cutting edge technology.
    Old papers only = mature but not trendy = may be harder to differentiate.
    """
    try:
        import xml.etree.ElementTree as ET

        response = await http_client.get(
            "https://export.arxiv.org/api/query",
            params={
                "search_query": f"all:{idea[:80]}",
                "start": 0,
                "max_results": 5,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        # Parse XML response
        root = ET.fromstring(response.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        papers = []
        for entry in root.findall("atom:entry", ns)[:5]:
            title = entry.find("atom:title", ns)
            summary = entry.find("atom:summary", ns)
            published = entry.find("atom:published", ns)
            link = entry.find("atom:id", ns)

            papers.append({
                "title": title.text.strip()[:100] if title is not None else "",
                "summary": summary.text.strip()[:200] if summary is not None else "",
                "published": published.text[:10] if published is not None else "",
                "url": link.text.strip() if link is not None else "",
            })

        total_results = root.find(
            "{http://a9.com/-/spec/opensearch/1.1/}totalResults"
        )
        total = int(total_results.text) if total_results is not None else 0

        logger.info(f"arXiv: found {total} papers for '{idea[:50]}'")

        return {
            "source": "arxiv",
            "total_papers": total,
            "recent_papers": papers,
            "research_activity": "high" if total > 100 else "medium" if total > 10 else "low",
        }

    except Exception as e:
        logger.warning(f"arXiv search failed: {e}")
        return {
            "source": "arxiv",
            "error": str(e),
            "total_papers": 0,
            "recent_papers": [],
            "research_activity": "unknown",
        }


async def fetch_stackoverflow(
    idea: str,
    http_client: httpx.AsyncClient,
) -> dict:
    """
    Search StackOverflow for questions about this technology.
    No authentication needed for basic usage (300 req/day free).

    ELI5: Many StackOverflow questions = many developers using this tech.
    High answer rate = good community support = easier to find help.
    Low answer rate = niche tech = harder to get unstuck.
    """
    try:
        response = await http_client.get(
            "https://api.stackexchange.com/2.3/search",
            params={
                "order": "desc",
                "sort": "votes",
                "intitle": idea[:80],
                "site": "stackoverflow",
                "pagesize": 5,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        questions = []
        for item in data.get("items", [])[:5]:
            questions.append({
                "title": item.get("title", "")[:100],
                "score": item.get("score", 0),
                "answers": item.get("answer_count", 0),
                "views": item.get("view_count", 0),
                "is_answered": item.get("is_answered", False),
                "url": item.get("link", ""),
            })

        total = data.get("total", 0)
        answered = sum(1 for q in questions if q["is_answered"])
        answer_rate = (answered / len(questions) * 100) if questions else 0

        logger.info(f"StackOverflow: found {total} questions for '{idea[:50]}'")

        return {
            "source": "stackoverflow",
            "total_questions": total,
            "top_questions": questions,
            "answer_rate_percent": round(answer_rate, 1),
            "ecosystem_health": "good" if answer_rate > 70 else "moderate" if answer_rate > 40 else "poor",
        }

    except Exception as e:
        logger.warning(f"StackOverflow search failed: {e}")
        return {
            "source": "stackoverflow",
            "error": str(e),
            "total_questions": 0,
            "top_questions": [],
            "ecosystem_health": "unknown",
        }


# ════════════════════════════════════════════════════════════
# MAIN RESEARCH FUNCTION
# ════════════════════════════════════════════════════════════

async def run_research(
    idea: str,
    http_client: httpx.AsyncClient,
) -> dict:
    """
    Main research function — runs all 4 sources in parallel.
    This is what the FastAPI route calls.

    Args:
        idea: the user's project idea as a string
        http_client: shared httpx client from FastAPI app state

    Returns:
        Complete research report as a dict ready to store in MCP server.

    ELI5: Sends all 4 librarians at the same time.
    Waits for the slowest one. Returns everything combined.
    """
    logger.info(f"Research started for: '{idea[:80]}'")
    start_time = datetime.utcnow()

    # Run all 4 sources simultaneously — this is the key performance trick
    # asyncio.gather() starts all 4 at the same time
    # Total time = slowest source (not sum of all sources)
    github_result, hn_result, arxiv_result, so_result = await asyncio.gather(
        fetch_github(idea, http_client),
        fetch_hackernews(idea, http_client),
        fetch_arxiv(idea, http_client),
        fetch_stackoverflow(idea, http_client),
    )

    elapsed = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"Research completed in {elapsed:.1f}s")

    # Combine all results into one research report
    report = {
        "idea": idea,
        "researched_at": datetime.utcnow().isoformat(),
        "elapsed_seconds": round(elapsed, 1),
        "sources": {
            "github": github_result,
            "hackernews": hn_result,
            "arxiv": arxiv_result,
            "stackoverflow": so_result,
        },
        "summary": {
            "similar_repos": github_result.get("total_similar_repos", 0),
            "community_posts": hn_result.get("total_posts", 0),
            "academic_papers": arxiv_result.get("total_papers", 0),
            "so_questions": so_result.get("total_questions", 0),
            "market_signal": github_result.get("market_signal", "unknown"),
            "community_interest": hn_result.get("community_interest", "unknown"),
            "research_activity": arxiv_result.get("research_activity", "unknown"),
            "ecosystem_health": so_result.get("ecosystem_health", "unknown"),
        },
    }

    return report