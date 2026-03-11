"""Tests for the verifier module."""

from __future__ import annotations

import pytest

from citation_check.models import Reference
from citation_check.verifier import verify_reference


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ref(**kwargs) -> Reference:
    defaults = dict(
        authors=["Ashish Vaswani"],
        title="Attention Is All You Need",
        year=2017,
        venue="NeurIPS",
        doi=None,
        raw_text="Vaswani et al., Attention Is All You Need, 2017",
        index=0,
    )
    defaults.update(kwargs)
    return Reference(**defaults)


CROSSREF_GOOD_RESPONSE = {
    "message": {
        "items": [
            {
                "title": ["Attention Is All You Need"],
                "author": [
                    {"given": "Ashish", "family": "Vaswani"},
                    {"given": "Noam", "family": "Shazeer"},
                ],
                "published-print": {"date-parts": [[2017]]},
                "container-title": ["NeurIPS"],
                "DOI": "10.5555/3295222.3295349",
            }
        ]
    }
}

CROSSREF_EMPTY = {"message": {"items": []}}

SEMANTIC_SCHOLAR_GOOD_RESPONSE = {
    "data": [
        {
            "title": "Attention Is All You Need",
            "authors": [{"name": "Ashish Vaswani"}, {"name": "Noam Shazeer"}],
            "year": 2017,
            "venue": "NeurIPS",
            "externalIds": {"DOI": "10.5555/3295222.3295349"},
        }
    ]
}

SEMANTIC_SCHOLAR_EMPTY = {"data": []}

OPENALEX_EMPTY = {"results": []}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verified_by_crossref(httpx_mock):
    """When Crossref returns a strong match, no other API is queried."""
    httpx_mock.add_response(json=CROSSREF_GOOD_RESPONSE)

    ref = _make_ref()
    vr = await verify_reference(ref)

    assert vr.status == "verified"
    assert vr.best_match is not None
    assert vr.best_match.source == "crossref"
    # Only one HTTP request should have been made
    assert len(httpx_mock.get_requests()) == 1


@pytest.mark.asyncio
async def test_crossref_empty_semantic_scholar_succeeds(httpx_mock):
    """When Crossref has no results, Semantic Scholar is tried next."""
    # First call: Crossref returns empty
    httpx_mock.add_response(json=CROSSREF_EMPTY)
    # Second call: Semantic Scholar returns a good match
    httpx_mock.add_response(json=SEMANTIC_SCHOLAR_GOOD_RESPONSE)

    ref = _make_ref()
    vr = await verify_reference(ref)

    assert vr.status == "verified"
    assert vr.best_match is not None
    assert vr.best_match.source == "semantic_scholar"
    assert len(httpx_mock.get_requests()) == 2


@pytest.mark.asyncio
async def test_no_results_from_any_api(httpx_mock):
    """When all APIs return empty, status is not_found."""
    httpx_mock.add_response(json=CROSSREF_EMPTY)
    httpx_mock.add_response(json=SEMANTIC_SCHOLAR_EMPTY)
    httpx_mock.add_response(json=OPENALEX_EMPTY)

    ref = _make_ref()
    vr = await verify_reference(ref)

    assert vr.status == "not_found"
    assert vr.best_match is None
    assert len(httpx_mock.get_requests()) == 3


@pytest.mark.asyncio
async def test_no_title():
    """A reference with no title returns not_found immediately, no API calls."""
    ref = _make_ref(title=None)
    vr = await verify_reference(ref)

    assert vr.status == "not_found"
    assert vr.details == "No title to search for"
