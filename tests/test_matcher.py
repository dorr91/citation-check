"""Tests for the matcher module."""

from __future__ import annotations

from citation_check.matcher import match_authors, match_title, match_year, score_match
from citation_check.models import Reference, SearchResult


# ---------------------------------------------------------------------------
# match_title
# ---------------------------------------------------------------------------


def test_match_title_exact():
    assert match_title("Attention Is All You Need", "Attention Is All You Need") == 100.0


def test_match_title_similar():
    score = match_title("Attention Is All You Need", "Attention is All You Need!")
    assert score > 80


def test_match_title_completely_different():
    score = match_title("Attention Is All You Need", "The Theory of Relativity")
    assert score < 40


# ---------------------------------------------------------------------------
# match_authors
# ---------------------------------------------------------------------------


def test_match_authors_exact():
    score = match_authors(["John Smith", "Jane Doe"], ["John Smith", "Jane Doe"])
    assert score == 100.0


def test_match_authors_subset():
    score = match_authors(["John Smith"], ["John Smith", "Jane Doe"])
    assert 0 < score < 100


def test_match_authors_no_overlap():
    score = match_authors(["John Smith"], ["Alice Cooper"])
    assert score == 0.0


def test_match_authors_both_empty():
    assert match_authors([], []) == 100.0


def test_match_authors_one_empty():
    assert match_authors([], ["John Smith"]) == 0.0
    assert match_authors(["John Smith"], []) == 0.0


def test_match_authors_accented_names():
    score = match_authors(["José García"], ["Jose Garcia"])
    assert score == 100.0


# ---------------------------------------------------------------------------
# match_year
# ---------------------------------------------------------------------------


def test_match_year_exact():
    assert match_year(2020, 2020) is True


def test_match_year_plus_one():
    assert match_year(2020, 2021) is True


def test_match_year_minus_one():
    assert match_year(2020, 2019) is True


def test_match_year_different():
    assert match_year(2020, 2023) is False


def test_match_year_none_ref():
    assert match_year(None, 2020) is True


def test_match_year_none_result():
    assert match_year(2020, None) is True


def test_match_year_both_none():
    assert match_year(None, None) is True


# ---------------------------------------------------------------------------
# score_match
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


def _make_result(**kwargs) -> SearchResult:
    defaults = dict(
        title="Attention Is All You Need",
        authors=["Ashish Vaswani", "Noam Shazeer"],
        year=2017,
        venue="NeurIPS",
        doi="10.5555/3295222.3295349",
        source="crossref",
    )
    defaults.update(kwargs)
    return SearchResult(**defaults)


def test_score_match_verified():
    ref = _make_ref()
    result = _make_result()
    vr = score_match(ref, result)
    assert vr.status == "verified"
    assert vr.title_score >= 85
    assert vr.best_match is result


def test_score_match_close_match():
    ref = _make_ref(title="Attention Is All You Need: A Survey")
    result = _make_result(title="Attention Mechanisms in Deep Learning: A Survey", authors=["Someone Else"], year=2021)
    vr = score_match(ref, result)
    assert vr.status in ("close_match", "mismatch")


def test_score_match_no_title():
    ref = _make_ref(title=None)
    result = _make_result()
    vr = score_match(ref, result)
    assert vr.status == "not_found"
    assert vr.title_score == 0.0
