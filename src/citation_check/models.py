from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Reference:
    """A parsed reference from GROBID."""

    authors: list[str]
    title: str | None
    year: int | None
    venue: str | None
    doi: str | None
    raw_text: str
    index: int


@dataclass
class SearchResult:
    """Normalized result from any API client."""

    title: str
    authors: list[str]
    year: int | None
    venue: str | None
    doi: str | None
    source: str


@dataclass
class VerificationResult:
    """Result of verifying one reference."""

    reference: Reference
    best_match: SearchResult | None
    title_score: float
    author_score: float
    year_match: bool
    status: str
    details: str
