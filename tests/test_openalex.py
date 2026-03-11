"""Tests for the OpenAlex API client."""
from __future__ import annotations

import httpx
import pytest
from pytest_httpx import HTTPXMock

from citation_check.clients.openalex import search_openalex
from citation_check.models import SearchResult


def _openalex_work(
    *,
    title: str = "Some Paper Title",
    doi: str | None = "https://doi.org/10.1234/test",
    publication_year: int | None = 2023,
    authorships: list[dict] | None = None,
    primary_location: dict | None = None,
) -> dict:
    """Build a minimal OpenAlex work object."""
    work: dict = {"title": title}
    if doi is not None:
        work["doi"] = doi
    if publication_year is not None:
        work["publication_year"] = publication_year
    if authorships is not None:
        work["authorships"] = authorships
    if primary_location is not None:
        work["primary_location"] = primary_location
    return work


@pytest.mark.asyncio
async def test_successful_search(httpx_mock: HTTPXMock) -> None:
    """Typical response with authors, venue, DOI prefix stripped, and year."""
    work = _openalex_work(
        title="Deep Learning for NLP",
        doi="https://doi.org/10.1234/deep",
        publication_year=2021,
        authorships=[
            {"author": {"display_name": "Alice Smith"}},
            {"author": {"display_name": "Bob Jones"}},
        ],
        primary_location={
            "source": {"display_name": "Journal of AI"},
        },
    )
    httpx_mock.add_response(
        url=httpx.URL(
            "https://api.openalex.org/works",
            params={"search": "deep learning", "per_page": "3", "mailto": "citation-check@example.com"},
        ),
        json={"results": [work]},
    )

    results = await search_openalex("deep learning")

    assert len(results) == 1
    r = results[0]
    assert r == SearchResult(
        title="Deep Learning for NLP",
        authors=["Alice Smith", "Bob Jones"],
        year=2021,
        venue="Journal of AI",
        doi="10.1234/deep",
        source="openalex",
    )


@pytest.mark.asyncio
async def test_missing_optional_fields(httpx_mock: HTTPXMock) -> None:
    """Work with no authorships, no primary_location, and no DOI."""
    work = _openalex_work(
        title="Minimal Paper",
        doi=None,
        publication_year=None,
    )
    httpx_mock.add_response(
        json={"results": [work]},
    )

    results = await search_openalex("minimal paper")

    assert len(results) == 1
    r = results[0]
    assert r.title == "Minimal Paper"
    assert r.authors == []
    assert r.year is None
    assert r.venue is None
    assert r.doi is None
    assert r.source == "openalex"


@pytest.mark.asyncio
async def test_api_error_returns_empty_list(httpx_mock: HTTPXMock) -> None:
    """HTTP errors should be caught and return an empty list."""
    httpx_mock.add_response(status_code=500)

    results = await search_openalex("anything")

    assert results == []


@pytest.mark.asyncio
async def test_empty_results(httpx_mock: HTTPXMock) -> None:
    """An empty results array from the API returns an empty list."""
    httpx_mock.add_response(json={"results": []})

    results = await search_openalex("nonexistent paper xyz")

    assert results == []


@pytest.mark.asyncio
async def test_doi_without_prefix_kept_as_is(httpx_mock: HTTPXMock) -> None:
    """A DOI that does not start with the https://doi.org/ prefix is kept unchanged."""
    work = _openalex_work(
        title="Paper With Plain DOI",
        doi="10.5678/plain",
        publication_year=2020,
        authorships=[],
    )
    httpx_mock.add_response(json={"results": [work]})

    results = await search_openalex("plain doi paper")

    assert len(results) == 1
    assert results[0].doi == "10.5678/plain"
