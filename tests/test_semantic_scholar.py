"""Tests for the Semantic Scholar API client."""

from __future__ import annotations

import pytest

from citation_check.clients.semantic_scholar import search_semantic_scholar

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

TYPICAL_RESPONSE = {
    "total": 2,
    "offset": 0,
    "data": [
        {
            "paperId": "abc123",
            "title": "Attention Is All You Need",
            "authors": [
                {"authorId": "1", "name": "Ashish Vaswani"},
                {"authorId": "2", "name": "Noam Shazeer"},
            ],
            "year": 2017,
            "venue": "NeurIPS",
            "externalIds": {"DOI": "10.5555/3295222.3295349", "ArXiv": "1706.03762"},
        },
        {
            "paperId": "def456",
            "title": "Attention is All You Need (workshop version)",
            "authors": [{"authorId": "1", "name": "Ashish Vaswani"}],
            "year": 2017,
            "venue": "ICML Workshop",
            "externalIds": {"ArXiv": "1706.99999"},
        },
    ],
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_successful_search(httpx_mock):
    """A typical two-result response is parsed correctly."""
    httpx_mock.add_response(json=TYPICAL_RESPONSE)

    results = await search_semantic_scholar("Attention Is All You Need")

    assert len(results) == 2

    first = results[0]
    assert first.title == "Attention Is All You Need"
    assert first.authors == ["Ashish Vaswani", "Noam Shazeer"]
    assert first.year == 2017
    assert first.venue == "NeurIPS"
    assert first.doi == "10.5555/3295222.3295349"
    assert first.source == "semantic_scholar"

    second = results[1]
    assert second.doi is None  # no DOI in externalIds


@pytest.mark.asyncio
async def test_missing_and_empty_fields(httpx_mock):
    """Papers with missing or empty optional fields are handled gracefully."""
    response = {
        "data": [
            {
                "paperId": "xyz",
                "title": "Some Paper",
                # no authors key
                # no year key
                "venue": "",  # empty string → should become None
                # no externalIds key
            }
        ]
    }
    httpx_mock.add_response(json=response)

    results = await search_semantic_scholar("Some Paper")

    assert len(results) == 1
    paper = results[0]
    assert paper.title == "Some Paper"
    assert paper.authors == []
    assert paper.year is None
    assert paper.venue is None
    assert paper.doi is None
    assert paper.source == "semantic_scholar"


@pytest.mark.asyncio
async def test_api_error_returns_empty_list(httpx_mock):
    """A non-200 status code results in an empty list, not an exception."""
    httpx_mock.add_response(status_code=500)

    results = await search_semantic_scholar("anything")

    assert results == []


@pytest.mark.asyncio
async def test_empty_results(httpx_mock):
    """An API response with no matching papers returns an empty list."""
    httpx_mock.add_response(json={"total": 0, "offset": 0, "data": []})

    results = await search_semantic_scholar("xyzzy nonexistent paper title")

    assert results == []
