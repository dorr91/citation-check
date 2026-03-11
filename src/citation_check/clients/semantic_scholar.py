"""Semantic Scholar API client for citation verification."""

from __future__ import annotations

import httpx

from citation_check.clients import retry_on_rate_limit
from citation_check.models import SearchResult

_BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS = "title,authors,year,venue,externalIds"
_TIMEOUT = 15.0


async def search_semantic_scholar(
    title: str, max_results: int = 3
) -> list[SearchResult]:
    """Search Semantic Scholar for papers matching *title*.

    Returns up to *max_results* :class:`SearchResult` objects.
    On any network or API error an empty list is returned.
    """
    @retry_on_rate_limit
    async def _fetch():
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                _BASE_URL,
                params={
                    "query": title,
                    "limit": max_results,
                    "fields": _FIELDS,
                },
            )
            resp.raise_for_status()
            return resp

    try:
        resp = await _fetch()
        data = resp.json()
    except (httpx.HTTPError, ValueError):
        return []

    results: list[SearchResult] = []
    for paper in data.get("data", []):
        paper_title = paper.get("title")
        if not paper_title:
            continue
        authors = [a["name"] for a in paper.get("authors", []) if "name" in a]
        venue = paper.get("venue") or None
        doi = (paper.get("externalIds") or {}).get("DOI")
        results.append(
            SearchResult(
                title=paper_title,
                authors=authors,
                year=paper.get("year"),
                venue=venue,
                doi=doi,
                source="semantic_scholar",
            )
        )

    return results
