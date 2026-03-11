# citation-check

A CLI tool that verifies whether citations in academic papers are real or hallucinated. Given a PDF, it extracts references using [GROBID](https://github.com/kermitt2/grobid) and checks each one against three academic databases: [Crossref](https://www.crossref.org/), [Semantic Scholar](https://www.semanticscholar.org/), and [OpenAlex](https://openalex.org/).

This is useful for catching fabricated references in AI-generated or AI-assisted academic writing.

## How It Works

### Pipeline

1. **Reference extraction** — The PDF is sent to a local GROBID service, which uses machine learning to parse the reference section and return structured data (title, authors, year, venue, DOI) as TEI XML.

2. **Database lookup** — Each reference is searched against academic databases in sequence: Crossref first, then Semantic Scholar, then OpenAlex. The search short-circuits as soon as a verified match is found, saving API calls.

3. **Fuzzy matching** — For each search result, the tool scores the match across three dimensions:
   - **Title**: fuzzy string similarity using `token_sort_ratio` (word-order independent, 0–100 scale)
   - **Authors**: normalized last-name overlap (accent-insensitive, handles Unicode)
   - **Year**: must match within ±1 year tolerance

4. **Classification** — Based on the scores, each reference is classified:
   - **Verified** — title >= 85%, authors >= 50%, year matches
   - **Close Match** — title >= 60% but doesn't meet full verification threshold
   - **Mismatch** — best result has title similarity < 60%
   - **Not Found** — no results from any database

5. **Report** — Results are displayed as a colored terminal table or exported as JSON.

### Architecture

```
src/citation_check/
├── cli.py              # Click CLI entry point
├── models.py           # Reference, SearchResult, VerificationResult dataclasses
├── grobid.py           # GROBID client and TEI XML parser
├── verifier.py         # Orchestrates the verification pipeline
├── matcher.py          # Fuzzy matching logic (title, authors, year)
├── report.py           # Rich terminal table and JSON output
└── clients/
    ├── __init__.py     # Shared retry-on-rate-limit decorator
    ├── crossref.py     # Crossref API client
    ├── semantic_scholar.py  # Semantic Scholar API client
    └── openalex.py     # OpenAlex API client
```

API clients use `httpx` for async HTTP, with automatic retry (exponential backoff) on rate limiting (HTTP 429). All clients gracefully degrade — if an API is down or returns errors, verification continues with the remaining sources.

## Setup

**Requirements:** Python 3.12+, Docker

```bash
# Install dependencies
uv sync

# Start GROBID (required for PDF parsing)
docker compose up
```

GROBID must be running at `http://localhost:8070` before you can verify papers.

## Usage

```bash
uv run citation-check verify paper.pdf
```

### Options

| Flag | Description |
|---|---|
| `--verbose` / `-v` | Show detailed match scores (author similarity, year match) |
| `--output json` | Machine-readable JSON instead of the default colored table |
| `--grobid-url URL` | Custom GROBID server URL (default: `http://localhost:8070`) |
| `--skip-indices 0,3,5` | Skip specific references by 0-based index |

### Examples

```bash
# Verbose table output
uv run citation-check verify paper.pdf -v

# JSON output for scripting
uv run citation-check verify paper.pdf --output json

# Skip references 1 and 4 (0-indexed)
uv run citation-check verify paper.pdf --skip-indices 0,3
```

### Understanding the Output

Each reference gets a color-coded status:

- **Verified** (green) — title match >= 85%, author match >= 50%, year within ±1
- **Close Match** (yellow) — title match >= 60% but below verification threshold
- **Not Found** (red) — no results from any API
- **Mismatch** (red) — best match has title similarity < 60%

A summary line shows `X/Y references verified, Z flagged`.

## Development

```bash
# Run tests
uv run pytest tests/ -v

# Lint
uv run ruff check src/ tests/
```
