"""Crossref API client for searching academic papers by title."""

from __future__ import annotations

import logging

import httpx

from citation_check.clients import retry_on_rate_limit
from citation_check.models import SearchResult

logger = logging.getLogger(__name__)

CROSSREF_API_URL = "https://api.crossref.org/works"


async def search_crossref(
    title: str,
    mailto: str = "citation-check@example.com",
    max_results: int = 3,
) -> list[SearchResult]:
    """Search Crossref for papers matching the given title.

    Args:
        title: The paper title to search for.
        mailto: Email for Crossref polite pool (faster rate limits).
        max_results: Maximum number of results to return.

    Returns:
        A list of SearchResult objects, or an empty list on error.
    """
    params = {
        "query.bibliographic": title,
        "rows": str(max_results),
        "mailto": mailto,
    }

    @retry_on_rate_limit
    async def _fetch():
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(CROSSREF_API_URL, params=params)
            response.raise_for_status()
            return response

    try:
        response = await _fetch()
    except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError) as exc:
        logger.warning("Crossref search failed for %r: %s", title, exc)
        return []

    try:
        data = response.json()
        items = data["message"]["items"]
    except (ValueError, KeyError) as exc:
        logger.warning("Failed to parse Crossref response: %s", exc)
        return []

    results: list[SearchResult] = []
    for item in items:
        try:
            result_title = item["title"][0]
        except (KeyError, IndexError):
            continue  # skip items with no title

        authors: list[str] = []
        for author in item.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            name = f"{given} {family}".strip()
            if name:
                authors.append(name)

        year = _extract_year(item)
        venue_list = item.get("container-title", [])
        venue = venue_list[0] if venue_list else None
        doi = item.get("DOI")

        results.append(
            SearchResult(
                title=result_title,
                authors=authors,
                year=year,
                venue=venue,
                doi=doi,
                source="crossref",
            )
        )

    return results


def _extract_year(item: dict) -> int | None:
    """Extract publication year, preferring print over online."""
    for key in ("published-print", "published-online"):
        try:
            year = item[key]["date-parts"][0][0]
            if year is not None:
                return int(year)
        except (KeyError, IndexError, TypeError):
            continue
    return None
