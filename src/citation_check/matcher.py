"""Fuzzy matching logic for comparing references against search results."""

from __future__ import annotations

import unicodedata

from rapidfuzz import fuzz

from citation_check.models import Reference, SearchResult, VerificationResult


def _try_strip_subtitle(a: str, b: str) -> float:
    """If one string has a colon and the other doesn't, strip the subtitle and re-score."""
    a_has = ":" in a
    b_has = ":" in b
    if a_has == b_has:
        return 0.0
    if a_has:
        prefix = a.split(":", 1)[0].strip()
        if len(prefix.split()) >= 4:
            return fuzz.token_sort_ratio(prefix, b)
    else:
        prefix = b.split(":", 1)[0].strip()
        if len(prefix.split()) >= 4:
            return fuzz.token_sort_ratio(a, prefix)
    return 0.0


def match_title(ref_title: str, result_title: str) -> float:
    """Return a 0-100 similarity score between two titles."""
    ref_lower = ref_title.lower()
    result_lower = result_title.lower()
    score = fuzz.token_sort_ratio(ref_lower, result_lower)

    # If one title has a subtitle (colon) and the other doesn't,
    # try matching without the subtitle.
    if score < 85:
        score = max(score, _try_strip_subtitle(ref_lower, result_lower))

    return score


def _normalize_last_name(name: str) -> str:
    """Extract the last name, lowercase it, and strip accents."""
    last = name.split()[-1] if name.split() else name
    last = last.lower()
    # Decompose unicode, strip combining characters (accents)
    nfkd = unicodedata.normalize("NFKD", last)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def match_authors(ref_authors: list[str], result_authors: list[str]) -> float:
    """Return a 0-100 author overlap score based on normalized last names."""
    if not ref_authors or not result_authors:
        return 100.0

    ref_set = {_normalize_last_name(a) for a in ref_authors}
    result_set = {_normalize_last_name(a) for a in result_authors}

    intersection = ref_set & result_set
    denominator = max(len(ref_set), len(result_set))
    return (len(intersection) / denominator) * 100


def match_year(ref_year: int | None, result_year: int | None) -> bool:
    """Check if years match within +-1 tolerance. None is treated as matching."""
    if ref_year is None or result_year is None:
        return True
    return abs(ref_year - result_year) <= 1


def score_match(reference: Reference, result: SearchResult) -> VerificationResult:
    """Score how well a SearchResult matches a Reference."""
    if not reference.title:
        return VerificationResult(
            reference=reference,
            best_match=result,
            title_score=0.0,
            author_score=0.0,
            year_match=False,
            status="not_found",
            details="Reference has no title",
        )

    title_score = match_title(reference.title, result.title)
    author_score = match_authors(reference.authors, result.authors)
    year_ok = match_year(reference.year, result.year)

    if title_score >= 85 and author_score >= 50 and year_ok:
        status = "verified"
    elif title_score >= 60:
        status = "close_match"
    else:
        status = "mismatch"

    details = (
        f"title={title_score:.1f}, authors={author_score:.1f}, "
        f"year_match={year_ok} -> {status}"
    )

    return VerificationResult(
        reference=reference,
        best_match=result,
        title_score=title_score,
        author_score=author_score,
        year_match=year_ok,
        status=status,
        details=details,
    )
