from __future__ import annotations

from citation_check.models import Reference, SearchResult, VerificationResult


class TestReference:
    def test_basic_instantiation(self):
        ref = Reference(
            authors=["John Smith", "Jane Doe"],
            title="A Great Paper",
            year=2023,
            venue="Nature",
            doi="10.1234/example",
            raw_text="Smith, Doe. A Great Paper. Nature, 2023.",
            index=0,
        )
        assert ref.authors == ["John Smith", "Jane Doe"]
        assert ref.title == "A Great Paper"
        assert ref.year == 2023
        assert ref.venue == "Nature"
        assert ref.doi == "10.1234/example"
        assert ref.index == 0

    def test_optional_fields_none(self):
        ref = Reference(
            authors=[],
            title=None,
            year=None,
            venue=None,
            doi=None,
            raw_text="Some raw text",
            index=5,
        )
        assert ref.title is None
        assert ref.year is None
        assert ref.venue is None
        assert ref.doi is None
        assert ref.authors == []


class TestSearchResult:
    def test_basic_instantiation(self):
        result = SearchResult(
            title="A Great Paper",
            authors=["John Smith"],
            year=2023,
            venue="Nature",
            doi="10.1234/example",
            source="crossref",
        )
        assert result.title == "A Great Paper"
        assert result.source == "crossref"

    def test_optional_fields_none(self):
        result = SearchResult(
            title="Paper",
            authors=[],
            year=None,
            venue=None,
            doi=None,
            source="semantic_scholar",
        )
        assert result.year is None
        assert result.venue is None
        assert result.doi is None


class TestVerificationResult:
    def test_basic_instantiation(self):
        ref = Reference(
            authors=["John Smith"],
            title="A Paper",
            year=2023,
            venue="Nature",
            doi=None,
            raw_text="raw",
            index=0,
        )
        match = SearchResult(
            title="A Paper",
            authors=["John Smith"],
            year=2023,
            venue="Nature",
            doi="10.1234/x",
            source="crossref",
        )
        vr = VerificationResult(
            reference=ref,
            best_match=match,
            title_score=95.0,
            author_score=90.0,
            year_match=True,
            status="verified",
            details="High confidence match",
        )
        assert vr.status == "verified"
        assert vr.title_score == 95.0
        assert vr.best_match is not None

    def test_no_match(self):
        ref = Reference(
            authors=["Unknown"],
            title="Missing Paper",
            year=2020,
            venue=None,
            doi=None,
            raw_text="raw",
            index=1,
        )
        vr = VerificationResult(
            reference=ref,
            best_match=None,
            title_score=0.0,
            author_score=0.0,
            year_match=False,
            status="not_found",
            details="No matching results found",
        )
        assert vr.best_match is None
        assert vr.status == "not_found"
