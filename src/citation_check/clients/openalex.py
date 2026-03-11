"""OpenAlex API client for searching academic papers by title."""

from __future__ import annotations

import httpx

from citation_check.clients import retry_on_rate_limit
from citation_check.models import SearchResult

_DOI_PREFIX = "https://doi.org/"


async def search_openalex(
    title: str,
    mailto: str | None = None,
    max_results: int = 3,
) -> list[SearchResult]:
    """Search OpenAlex for works matching *title*.

    Returns up to *max_results* :class:`SearchResult` objects.
    On any HTTP or parsing error the function returns an empty list.
    """
    params: dict[str, str | int] = {
        "search": title,
        "per_page": max_results,
    }
    if mailto:
        params["mailto"] = mailto

    @retry_on_rate_limit
    async def _fetch():
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.openalex.org/works", params=params
            )
            resp.raise_for_status()
            return resp

    try:
        resp = await _fetch()
        data = resp.json()
    except (httpx.HTTPError, ValueError):
        return []

    results: list[SearchResult] = []
    for work in data.get("results", []):
        # Authors
        authors: list[str] = []
        for authorship in work.get("authorships", []):
            author = authorship.get("author") or {}
            name = author.get("display_name")
            if name:
                authors.append(name)

        # DOI – strip the URL prefix if present
        doi_raw = work.get("doi")
        doi: str | None = None
        if doi_raw:
            if doi_raw.startswith(_DOI_PREFIX):
                doi = doi_raw.removeprefix(_DOI_PREFIX)
            else:
                doi = doi_raw

        # Venue – any level can be None
        venue: str | None = None
        primary_location = work.get("primary_location")
        if primary_location:
            source = primary_location.get("source")
            if source:
                venue = source.get("display_name")

        results.append(
            SearchResult(
                title=work.get("title", ""),
                authors=authors,
                year=work.get("publication_year"),
                venue=venue,
                doi=doi,
                source="openalex",
            )
        )

    return results
