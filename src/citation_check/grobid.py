from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

from citation_check.models import Reference

TEI_NS = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI_NS}


async def check_grobid(url: str = "http://localhost:8070") -> bool:
    """Health check: GET /api/isalive."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{url}/api/isalive")
            return resp.status_code == 200
    except httpx.HTTPError:
        return False


async def extract_references(
    pdf_path: str,
    grobid_url: str = "http://localhost:8070",
) -> list[Reference]:
    """Extract references from a PDF via GROBID's processReferences endpoint."""
    pdf_bytes = Path(pdf_path).read_bytes()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{grobid_url}/api/processReferences",
            files={"input": ("file.pdf", pdf_bytes, "application/pdf")},
            timeout=60.0,
        )
        resp.raise_for_status()

    return parse_tei_references(resp.text)


def parse_tei_references(xml_text: str) -> list[Reference]:
    """Parse TEI XML and return a list of Reference objects."""
    root = ET.fromstring(xml_text)
    bibl_structs = root.findall(f".//{{{TEI_NS}}}biblStruct")

    references: list[Reference] = []
    for idx, bib in enumerate(bibl_structs):
        title = _extract_title(bib)
        authors = _extract_authors(bib)
        year = _extract_year(bib)
        venue = _extract_venue(bib)
        doi = _extract_doi(bib)
        raw_text = _extract_raw_text(bib)

        references.append(
            Reference(
                authors=authors,
                title=title,
                year=year,
                venue=venue,
                doi=doi,
                raw_text=raw_text,
                index=idx,
            )
        )

    return references


def _extract_title(bib: ET.Element) -> str | None:
    """Extract article-level title, falling back to monograph-level."""
    # Article title first
    for title_el in bib.findall(f".//{{{TEI_NS}}}title"):
        level = title_el.get("level")
        if level == "a":
            text = _element_text(title_el)
            if text:
                return text

    # Monograph title as fallback
    for title_el in bib.findall(f".//{{{TEI_NS}}}title"):
        level = title_el.get("level")
        if level == "m":
            text = _element_text(title_el)
            if text:
                return text

    return None


def _extract_authors(bib: ET.Element) -> list[str]:
    """Extract author names from persName elements."""
    authors: list[str] = []
    for author_el in bib.findall(f".//{{{TEI_NS}}}author"):
        pers = author_el.find(f"{{{TEI_NS}}}persName")
        if pers is None:
            continue
        forename_el = pers.find(f"{{{TEI_NS}}}forename")
        surname_el = pers.find(f"{{{TEI_NS}}}surname")
        parts = []
        if forename_el is not None and forename_el.text:
            parts.append(forename_el.text.strip())
        if surname_el is not None and surname_el.text:
            parts.append(surname_el.text.strip())
        if parts:
            authors.append(" ".join(parts))
    return authors


def _extract_year(bib: ET.Element) -> int | None:
    """Extract publication year from date elements."""
    for date_el in bib.findall(f".//{{{TEI_NS}}}date"):
        when = date_el.get("when")
        if when:
            try:
                return int(when[:4])
            except (ValueError, IndexError):
                pass
        text = _element_text(date_el)
        if text:
            try:
                return int(text.strip()[:4])
            except (ValueError, IndexError):
                pass
    return None


def _extract_venue(bib: ET.Element) -> str | None:
    """Extract venue: journal title, or monograph title when article title exists."""
    has_article_title = any(
        t.get("level") == "a" for t in bib.findall(f".//{{{TEI_NS}}}title")
    )

    for title_el in bib.findall(f".//{{{TEI_NS}}}title"):
        level = title_el.get("level")
        if level == "j":
            text = _element_text(title_el)
            if text:
                return text
        if level == "m" and has_article_title:
            text = _element_text(title_el)
            if text:
                return text

    return None


def _extract_doi(bib: ET.Element) -> str | None:
    """Extract DOI from idno elements."""
    for idno in bib.findall(f".//{{{TEI_NS}}}idno"):
        if idno.get("type") == "DOI":
            text = _element_text(idno)
            if text:
                return text.strip()
    return None


def _extract_raw_text(bib: ET.Element) -> str:
    """Reconstruct raw text from the biblStruct element."""
    # Try to get text from a note element first
    note = bib.find(f"{{{TEI_NS}}}note")
    if note is not None:
        text = _element_text(note)
        if text:
            return text.strip()

    # Fall back to concatenating all text content
    return " ".join(bib.itertext()).strip()


def _element_text(el: ET.Element) -> str | None:
    """Get all text content of an element (including tail of children)."""
    text = "".join(el.itertext())
    return text.strip() if text.strip() else None
