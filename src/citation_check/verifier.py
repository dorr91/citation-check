"""Verification pipeline: query APIs and find the best match for each reference."""

from __future__ import annotations

from citation_check.clients.crossref import search_crossref
from citation_check.clients.openalex import search_openalex
from citation_check.clients.semantic_scholar import search_semantic_scholar
from citation_check.matcher import score_match
from citation_check.models import Reference, SearchResult, VerificationResult


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
            if vr_rank > best_rank or (vr_rank == best_rank and vr.title_score > best.title_score):
                best = vr
    return best


async def verify_reference(reference: Reference) -> VerificationResult:
    """Verify a single reference against Crossref, Semantic Scholar, and OpenAlex."""
    if not reference.title:
        return _not_found_result(reference, "No title to search for")

    title = reference.title

    # 1. Crossref
    crossref_results = await search_crossref(title)
    best = _pick_best(None, crossref_results, reference)
    if best and best.status == "verified":
        return best

    # 2. Semantic Scholar
    ss_results = await search_semantic_scholar(title)
    best = _pick_best(best, ss_results, reference)
    if best and best.status == "verified":
        return best

    # 3. OpenAlex
    oa_results = await search_openalex(title)
    best = _pick_best(best, oa_results, reference)

    if best is not None:
        return best

    return _not_found_result(reference, "No results from any API")


async def verify_all(references: list[Reference]) -> list[VerificationResult]:
    """Verify all references sequentially to respect rate limits."""
    results: list[VerificationResult] = []
    for ref in references:
        vr = await verify_reference(ref)
        results.append(vr)
    return results
