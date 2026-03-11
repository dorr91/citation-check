"""Edge case tests for Phase 5 robustness improvements."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from click.testing import CliRunner
from rich.console import Console

from citation_check.cli import main
from citation_check.clients.crossref import search_crossref
from citation_check.matcher import score_match
from citation_check.models import Reference, SearchResult, VerificationResult
from citation_check.report import print_report
from citation_check.verifier import verify_reference


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ref(**kwargs) -> Reference:
    defaults = dict(
        authors=["Author One"],
        title="Some Paper Title",
        year=2023,
        venue="Some Journal",
        doi=None,
        raw_text="Author One. Some Paper Title. Some Journal. 2023.",
        index=0,
    )
    defaults.update(kwargs)
    return Reference(**defaults)


CROSSREF_EMPTY = {"message": {"items": []}}
SEMANTIC_SCHOLAR_EMPTY = {"data": []}
OPENALEX_EMPTY = {"results": []}


# ---------------------------------------------------------------------------
# Test: Reference with no title -> "not_found" through full pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_title_reference_full_pipeline(httpx_mock):
    """A reference with no title should get status 'not_found' without any API calls."""
    ref = _make_ref(title=None, raw_text="Some unparseable reference text")
    vr = await verify_reference(ref)

    assert vr.status == "not_found"
    assert vr.details == "No title to search for"
    assert vr.best_match is None
    # No HTTP requests should have been made
    assert len(httpx_mock.get_requests()) == 0


# ---------------------------------------------------------------------------
# Test: Unicode/non-ASCII characters in title and authors
# ---------------------------------------------------------------------------


def test_unicode_title_and_authors_match():
    """Non-ASCII characters in title and authors should match correctly."""
    ref = _make_ref(
        title="Uber die Elektrolytische Leitung des Stromes",
        authors=["Muller", "Jorg Schroder"],
    )
    result = SearchResult(
        title="Uber die Elektrolytische Leitung des Stromes",
        authors=["Muller", "Jorg Schroder"],
        year=2023,
        venue="Some Journal",
        doi=None,
        source="crossref",
    )
    vr = score_match(ref, result)
    assert vr.status == "verified"
    assert vr.title_score >= 85


def test_unicode_accented_authors_match():
    """Authors with accents should match their unaccented equivalents."""
    ref = _make_ref(
        title="A Test Paper",
        authors=["Jose Garcia", "Francois Muller"],
    )
    result = SearchResult(
        title="A Test Paper",
        authors=["Jos\u00e9 Garc\u00eda", "Fran\u00e7ois M\u00fcller"],
        year=2023,
        venue=None,
        doi=None,
        source="crossref",
    )
    vr = score_match(ref, result)
    # The accent normalization should allow author matching
    assert vr.author_score >= 50
    assert vr.status == "verified"


# ---------------------------------------------------------------------------
# Test: All three APIs return empty results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_apis_empty_returns_not_found(httpx_mock):
    """When all three APIs return empty results, status should be 'not_found'."""
    httpx_mock.add_response(json=CROSSREF_EMPTY)
    httpx_mock.add_response(json=SEMANTIC_SCHOLAR_EMPTY)
    httpx_mock.add_response(json=OPENALEX_EMPTY)

    ref = _make_ref(title="A Paper That Does Not Exist Anywhere")
    vr = await verify_reference(ref)

    assert vr.status == "not_found"
    assert vr.best_match is None
    assert len(httpx_mock.get_requests()) == 3


# ---------------------------------------------------------------------------
# Test: Report renders correctly when reference has no title
# ---------------------------------------------------------------------------


def test_report_no_title_shows_raw_text():
    """When a reference has no title, the report should show raw_text."""
    ref = _make_ref(title=None, raw_text="Smith et al., Some unparseable ref, 2020")
    vr = VerificationResult(
        reference=ref,
        best_match=None,
        title_score=0.0,
        author_score=0.0,
        year_match=False,
        status="not_found",
        details="No title to search for",
    )

    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=120, highlight=False)
    print_report([vr], verbose=False, console=console)
    output = buf.getvalue()

    assert "[raw]" in output
    assert "Smith et al." in output


def test_report_no_title_no_raw_text():
    """When a reference has no title and empty raw_text, show '(no title)'."""
    ref = _make_ref(title=None, raw_text="")
    vr = VerificationResult(
        reference=ref,
        best_match=None,
        title_score=0.0,
        author_score=0.0,
        year_match=False,
        status="not_found",
        details="No title to search for",
    )

    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=120, highlight=False)
    print_report([vr], verbose=False, console=console)
    output = buf.getvalue()

    assert "(no title)" in output


# ---------------------------------------------------------------------------
# Test: --skip-indices CLI option
# ---------------------------------------------------------------------------


def test_skip_indices_filters_references(tmp_path):
    """--skip-indices should exclude references at given indices."""
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    refs = [
        _make_ref(index=0, title="Paper Zero"),
        _make_ref(index=1, title="Paper One"),
        _make_ref(index=2, title="Paper Two"),
    ]

    # We capture what verify_all receives
    captured_refs = []

    async def mock_verify_all(references):
        captured_refs.extend(references)
        return [
            VerificationResult(
                reference=r,
                best_match=None,
                title_score=0.0,
                author_score=0.0,
                year_match=False,
                status="not_found",
                details="test",
            )
            for r in references
        ]

    runner = CliRunner()
    with (
        patch(
            "citation_check.cli.check_grobid",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "citation_check.cli.extract_references",
            new_callable=AsyncMock,
            return_value=refs,
        ),
        patch(
            "citation_check.cli.verify_all",
            side_effect=mock_verify_all,
        ),
    ):
        result = runner.invoke(
            main, ["verify", str(pdf), "--skip-indices", "0,2"]
        )

    assert result.exit_code == 0
    # Only reference at index 1 should remain
    assert len(captured_refs) == 1
    assert captured_refs[0].index == 1


# ---------------------------------------------------------------------------
# Test: Retry logic on 429
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_on_429_then_success(httpx_mock):
    """Retry decorator should retry on 429 and succeed when API recovers."""
    # First two calls return 429, third succeeds
    httpx_mock.add_response(status_code=429)
    httpx_mock.add_response(status_code=429)
    httpx_mock.add_response(
        json={
            "message": {
                "items": [
                    {
                        "title": ["Attention Is All You Need"],
                        "author": [{"given": "Ashish", "family": "Vaswani"}],
                        "published-print": {"date-parts": [[2017]]},
                        "container-title": ["NeurIPS"],
                        "DOI": "10.5555/test",
                    }
                ]
            }
        }
    )

    with patch("citation_check.clients.asyncio.sleep", new_callable=AsyncMock):
        results = await search_crossref("Attention Is All You Need")

    assert len(results) == 1
    assert results[0].title == "Attention Is All You Need"
    # 3 requests total: 2 retries + 1 success
    assert len(httpx_mock.get_requests()) == 3


@pytest.mark.asyncio
async def test_retry_exhausted_on_429(httpx_mock):
    """When all retries are exhausted on 429, the function returns empty list."""
    # All 4 calls return 429 (initial + 3 retries)
    httpx_mock.add_response(status_code=429)
    httpx_mock.add_response(status_code=429)
    httpx_mock.add_response(status_code=429)
    httpx_mock.add_response(status_code=429)

    with patch("citation_check.clients.asyncio.sleep", new_callable=AsyncMock):
        results = await search_crossref("Some Title")

    # Should return empty list since the outer except catches the final HTTPStatusError
    assert results == []
    assert len(httpx_mock.get_requests()) == 4
