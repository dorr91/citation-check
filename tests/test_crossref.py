"""Tests for the Crossref API client."""

from __future__ import annotations

import pytest

from citation_check.clients.crossref import search_crossref

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

TYPICAL_RESPONSE = {
    "message": {
        "items": [
            {
                "title": ["Attention Is All You Need"],
                "author": [
                    {"given": "Ashish", "family": "Vaswani"},
                    {"given": "Noam", "family": "Shazeer"},
                ],
                "published-print": {"date-parts": [[2017, 6, 12]]},
                "container-title": ["Advances in Neural Information Processing Systems"],
                "DOI": "10.5555/3295222.3295349",
            },
            {
                "title": ["Attention is All You Need (workshop version)"],
                "author": [{"given": "Ashish", "family": "Vaswani"}],
                "published-print": {"date-parts": [[2017]]},
                "container-title": ["ICML Workshop"],
                "DOI": "10.1234/fake",
            },
        ]
    }
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_successful_search(httpx_mock):
    """A typical two-result response is parsed correctly."""
    httpx_mock.add_response(json=TYPICAL_RESPONSE)

    results = await search_crossref("Attention Is All You Need")

    assert len(results) == 2

    first = results[0]
    assert first.title == "Attention Is All You Need"
    assert first.authors == ["Ashish Vaswani", "Noam Shazeer"]
    assert first.year == 2017
    assert first.venue == "Advances in Neural Information Processing Systems"
    assert first.doi == "10.5555/3295222.3295349"
    assert first.source == "crossref"

    second = results[1]
    assert second.title == "Attention is All You Need (workshop version)"
    assert second.authors == ["Ashish Vaswani"]
    assert second.doi == "10.1234/fake"


@pytest.mark.asyncio
async def test_missing_and_empty_fields(httpx_mock):
    """Papers with missing or empty optional fields are handled gracefully."""
    response = {
        "message": {
            "items": [
                {
                    "title": ["Some Paper"],
                    # no author key
                    # no published-print or published-online
                    # no container-title
                    # no DOI
                }
            ]
        }
    }
    httpx_mock.add_response(json=response)

    results = await search_crossref("Some Paper")

    assert len(results) == 1
    paper = results[0]
    assert paper.title == "Some Paper"
    assert paper.authors == []
    assert paper.year is None
    assert paper.venue is None
    assert paper.doi is None
    assert paper.source == "crossref"


@pytest.mark.asyncio
async def test_api_error_returns_empty_list(httpx_mock):
    """A non-200 status code results in an empty list, not an exception."""
    httpx_mock.add_response(status_code=500)

    results = await search_crossref("anything")

    assert results == []


@pytest.mark.asyncio
async def test_empty_results(httpx_mock):
    """An API response with no matching papers returns an empty list."""
    httpx_mock.add_response(json={"message": {"items": []}})

    results = await search_crossref("xyzzy nonexistent paper title")

    assert results == []


@pytest.mark.asyncio
async def test_item_with_no_title_is_skipped(httpx_mock):
    """Items missing the title field are silently skipped."""
    response = {
        "message": {
            "items": [
                {
                    # no title key at all
                    "author": [{"given": "Jane", "family": "Doe"}],
                    "DOI": "10.9999/notitle",
                },
                {
                    "title": [],  # empty title list
                    "DOI": "10.9999/emptytitle",
                },
                {
                    "title": ["Valid Paper"],
                    "DOI": "10.9999/valid",
                },
            ]
        }
    }
    httpx_mock.add_response(json=response)

    results = await search_crossref("some query")

    assert len(results) == 1
    assert results[0].title == "Valid Paper"


@pytest.mark.asyncio
async def test_year_extraction_falls_back_to_published_online(httpx_mock):
    """When published-print is absent, year is taken from published-online."""
    response = {
        "message": {
            "items": [
                {
                    "title": ["Online-First Paper"],
                    "published-online": {"date-parts": [[2023, 1, 15]]},
                    # no published-print
                }
            ]
        }
    }
    httpx_mock.add_response(json=response)

    results = await search_crossref("Online-First Paper")

    assert len(results) == 1
    assert results[0].year == 2023
