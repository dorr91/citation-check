# citation-check

Python CLI tool that extracts references from academic PDFs via GROBID and verifies them against Crossref, Semantic Scholar, and OpenAlex.

## Commands

- `uv run pytest tests/ -v` — run tests
- `uv run ruff check src/ tests/` — lint
- `uv run citation-check verify <paper.pdf>` — run the tool

## Architecture

```
src/citation_check/
├── cli.py          # Click CLI entry point
├── models.py       # Reference, SearchResult, VerificationResult dataclasses
├── grobid.py       # PDF → references via GROBID TEI XML
├── clients/        # API clients (crossref.py, semantic_scholar.py, openalex.py)
├── matcher.py      # Fuzzy matching (rapidfuzz title, author set overlap, year ±1)
├── verifier.py     # Orchestrates: Crossref → Semantic Scholar → OpenAlex, early return on verified
└── report.py       # Rich colored table output
```

## Testing

All async. Uses `pytest-httpx` for HTTP mocking — do NOT use `url=` param in `httpx_mock.add_response()` (it does exact match including query params). Use `@pytest.mark.asyncio`.

## Dependencies

Runtime: httpx, rapidfuzz, click, rich, pymupdf. Dev: pytest, pytest-asyncio, pytest-httpx, ruff.

## External

Requires GROBID running locally (`docker compose up` via compose.yaml, default `localhost:8070`).
