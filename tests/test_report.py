"""Tests for the report module."""

from __future__ import annotations

from io import StringIO

from rich.console import Console

from citation_check.models import Reference, SearchResult, VerificationResult
from citation_check.report import print_report


def _make_reference(index: int = 0, title: str = "Test Paper") -> Reference:
    return Reference(
        authors=["Author One"],
        title=title,
        year=2023,
        venue="Some Journal",
        doi=None,
        raw_text="Author One. Test Paper. Some Journal. 2023.",
        index=index,
    )


def _make_result(
    status: str = "verified",
    title: str = "Test Paper",
    index: int = 0,
    title_score: float = 95.0,
) -> VerificationResult:
    ref = _make_reference(index=index, title=title)
    match = SearchResult(
        title="Test Paper Match",
        authors=["Author One"],
        year=2023,
        venue="Some Journal",
        doi="10.1234/test",
        source="crossref",
    )
    return VerificationResult(
        reference=ref,
        best_match=match if status != "not_found" else None,
        title_score=title_score,
        author_score=80.0,
        year_match=True,
        status=status,
        details=f"Status is {status}",
    )


def _capture_report(results: list[VerificationResult], verbose: bool = False) -> str:
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=120, highlight=False)
    print_report(results, verbose=verbose, console=console)
    return buf.getvalue()


def test_print_report_produces_output():
    results = [_make_result()]
    output = _capture_report(results)
    assert len(output) > 0
    assert "Test Paper" in output


def test_summary_line():
    results = [
        _make_result(status="verified", index=0),
        _make_result(status="not_found", index=1),
        _make_result(status="close_match", index=2),
    ]
    output = _capture_report(results)
    assert "1/3 references verified" in output
    assert "2 flagged" in output


def test_all_statuses_render():
    statuses = ["verified", "close_match", "not_found", "mismatch"]
    results = [_make_result(status=s, index=i) for i, s in enumerate(statuses)]
    output = _capture_report(results)
    assert "Verified" in output
    assert "Close Match" in output
    assert "Not Found" in output
    assert "Mismatch" in output


def test_verbose_mode_shows_details():
    results = [_make_result()]
    output = _capture_report(results, verbose=True)
    assert "Author score" in output
    assert "Year match" in output


def test_no_results():
    output = _capture_report([])
    assert "0/0 references verified" in output
    assert "0 flagged" in output
