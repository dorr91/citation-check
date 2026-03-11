"""Verification pipeline: query APIs and find the best match for each reference."""

from __future__ import annotations

import asyncio
import logging

import httpx

from citation_check.clients.crossref import search_crossref
from citation_check.clients.openalex import search_openalex
from citation_check.clients.semantic_scholar import search_semantic_scholar
from citation_check.matcher import score_match
from citation_check.models import Reference, SearchResult, VerificationResult

logger = logging.getLogger(__name__)

_DELAY_BETWEEN_REFS = 0.2  # seconds between references to be polite to APIs


def _not_found_result(reference: Reference, details: str) -> VerificationResult:
    return VerificationResult(
        reference=reference,
        best_match=None,
        title_score=0.0,
        author_score=0.0,
        year_match=False,
        status="not_found",
        details=details,
    )


_STATUS_RANK = {"verified": 2, "close_match": 1, "mismatch": 0, "not_found": 0}


def _pick_best(
    current_best: VerificationResult | None,
    results: list[SearchResult],
    reference: Reference,
) -> VerificationResult | None:
    """Score all results and return the best match, preferring verified results."""
    best = current_best
    for result in results:
        vr = score_match(reference, result)
        if best is None:
            best = vr
        else:
            vr_rank = _STATUS_RANK.get(vr.status, 0)
            best_rank = _STATUS_RANK.get(best.status, 0)
            same_rank = vr_rank == best_rank
            if vr_rank > best_rank or (
                same_rank and vr.title_score > best.title_score
            ):
                best = vr
    return best


async def _lookup_doi_crossref(
    doi: str, mailto: str | None,
) -> list[SearchResult]:
    """Look up a specific DOI via Crossref."""
    url = f"https://api.crossref.org/works/{doi}"
    params = {}
    if mailto:
        params["mailto"] = mailto

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            item = data["message"]
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.warning("DOI lookup failed for %r: %s", doi, exc)
        return []

    try:
        result_title = item["title"][0]
    except (KeyError, IndexError):
        return []

    authors: list[str] = []
    for author in item.get("author", []):
        given = author.get("given", "")
        family = author.get("family", "")
        name = f"{given} {family}".strip()
        if name:
            authors.append(name)

    year = None
    for key in ("published-print", "published-online"):
        try:
            year = int(item[key]["date-parts"][0][0])
            break
        except (KeyError, IndexError, TypeError):
            continue

    venue_list = item.get("container-title", [])
    venue = venue_list[0] if venue_list else None

    return [
        SearchResult(
            title=result_title,
            authors=authors,
            year=year,
            venue=venue,
            doi=item.get("DOI"),
            source="crossref",
        )
    ]


async def verify_reference(
    reference: Reference, mailto: str | None = None
) -> VerificationResult:
    """Verify a single reference against Crossref, Semantic Scholar, and OpenAlex."""
    if not reference.title:
        return _not_found_result(reference, "No title to search for")

    title = reference.title

    # 0. Direct DOI lookup if available (fast and accurate)
    if reference.doi:
        doi_results = await _lookup_doi_crossref(reference.doi, mailto)
        best = _pick_best(None, doi_results, reference)
        if best and best.status == "verified":
            return best
    else:
        best = None

    # 1. Crossref
    kwargs = {"mailto": mailto} if mailto else {}
    crossref_results = await search_crossref(title, **kwargs)
    best = _pick_best(best, crossref_results, reference)
    if best and best.status == "verified":
        return best

    # 2. Semantic Scholar
    ss_results = await search_semantic_scholar(title)
    best = _pick_best(best, ss_results, reference)
    if best and best.status == "verified":
        return best

    # 3. OpenAlex
    oa_results = await search_openalex(title, **kwargs)
    best = _pick_best(best, oa_results, reference)

    if best is not None:
        return best

    return _not_found_result(reference, "No results from any API")


async def verify_all(
    references: list[Reference], mailto: str | None = None
) -> list[VerificationResult]:
    """Verify all references sequentially to respect rate limits."""
    results: list[VerificationResult] = []
    for i, ref in enumerate(references):
        if i > 0:
            await asyncio.sleep(_DELAY_BETWEEN_REFS)
        vr = await verify_reference(ref, mailto=mailto)
        results.append(vr)
    return results
