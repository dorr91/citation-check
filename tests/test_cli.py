"""Tests for the CLI module."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from citation_check.cli import main
from citation_check.models import Reference, SearchResult, VerificationResult


def _make_reference(index: int = 0) -> Reference:
    return Reference(
        authors=["Author One"],
        title="Test Paper Title",
        year=2023,
        venue="Test Journal",
        doi=None,
        raw_text="Author One. Test Paper Title. Test Journal. 2023.",
        index=index,
    )


def _make_verification_result(index: int = 0) -> VerificationResult:
    ref = _make_reference(index=index)
    match = SearchResult(
        title="Test Paper Title",
        authors=["Author One"],
        year=2023,
        venue="Test Journal",
        doi="10.1234/test",
        source="crossref",
    )
    return VerificationResult(
        reference=ref,
        best_match=match,
        title_score=95.0,
        author_score=80.0,
        year_match=True,
        status="verified",
        details="Good match via crossref",
    )


def test_verify_fails_when_grobid_not_running(tmp_path):
    """Test that verify command fails gracefully when GROBID is not available."""
    # Create a dummy PDF file so click.Path(exists=True) passes
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    runner = CliRunner()
    with patch(
        "citation_check.cli.check_grobid", new_callable=AsyncMock, return_value=False
    ):
        result = runner.invoke(
            main, ["verify", str(pdf), "--mailto", "test@test.com"],
        )

    assert result.exit_code != 0
    assert "GROBID is not running" in result.output or "GROBID is not running" in (result.stderr or "")


def test_json_output_with_mocked_data(tmp_path):
    """Test JSON output mode with mocked references and results."""
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    refs = [_make_reference(0), _make_reference(1)]
    results = [_make_verification_result(0), _make_verification_result(1)]

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
            new_callable=AsyncMock,
            return_value=results,
        ),
    ):
        result = runner.invoke(
            main, ["verify", str(pdf), "--output", "json", "--mailto", "test@test.com"],
        )

    assert result.exit_code == 0
    data = json.loads(result.output.split("\n", 3)[3])  # skip the echo lines
    assert len(data) == 2
    assert data[0]["status"] == "verified"
    assert data[0]["reference"]["title"] == "Test Paper Title"


def test_table_output_with_mocked_data(tmp_path):
    """Test table output mode (default) works without errors."""
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    refs = [_make_reference()]
    results = [_make_verification_result()]

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
            new_callable=AsyncMock,
            return_value=results,
        ),
    ):
        result = runner.invoke(
            main, ["verify", str(pdf), "--mailto", "test@test.com"],
        )

    assert result.exit_code == 0
    assert "references verified" in result.output
