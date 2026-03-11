# Citation Verification Tool — Implementation Plan

## Overview

A Python CLI tool that reads a conference paper PDF, extracts its references using GROBID, and verifies each citation against academic databases (Crossref, Semantic Scholar, OpenAlex) to detect hallucinated or incorrect references.

---

## Phase 1: Project Scaffolding & GROBID Integration

**Goal:** Set up the project and get structured references out of a PDF.

### Steps

1. Initialize project structure:
   - `pyproject.toml` with dependencies
   - `src/citation_check/` package
   - Entry point: `src/citation_check/cli.py`
2. Core dependencies: `pymupdf`, `httpx`, `rapidfuzz`, `click` (CLI)
3. Write a `grobid.py` module:
   - Check that GROBID is running locally (health check on `localhost:8070`)
   - POST full PDF to `/api/processReferences`
   - Parse the TEI XML response into a list of `Reference` dataclass instances (authors, title, year, venue, DOI if present, raw text)
4. Write a `models.py` with the `Reference` dataclass
5. Test with a real paper PDF

**Subagent opportunity:** None yet — this phase is sequential and foundational.

---

## Phase 2: Academic Database Clients

**Goal:** Build query clients for Crossref, Semantic Scholar, and OpenAlex.

### Steps

1. Write `clients/crossref.py`:
   - Query by title using `habanero` or raw `httpx` to `api.crossref.org/works`
   - Return top N results as normalized matches (title, authors, year, venue, DOI)
   - Respect rate limiting (polite pool: set `mailto` parameter)
2. Write `clients/semantic_scholar.py`:
   - Query by title via `api.semanticscholar.org/graph/v1/paper/search`
   - Return normalized matches
   - Throttle to stay under free tier limits
3. Write `clients/openalex.py`:
   - Query by title via `api.openalex.org/works`
   - Return normalized matches
   - Set `mailto` for polite pool
4. Define a common `SearchResult` dataclass in `models.py` for normalized API responses
5. Add a shared throttle/rate-limiter (simple `asyncio.Semaphore` + delay, or `httpx` transport-level)

**Subagent opportunity:** The three API clients are independent. Launch 3 subagents in parallel, one per client, each with the `SearchResult` schema and API docs/examples. Merge results.

---

## Phase 3: Matching & Scoring

**Goal:** Compare extracted references against API results and assign confidence scores.

### Steps

1. Write `matcher.py`:
   - Fuzzy title match using `rapidfuzz.fuzz.token_sort_ratio` (threshold ~85 for "match", ~60 for "close")
   - Author comparison: normalize names (last name extraction, unicode handling), compare sets with partial matching
   - Year match: exact or ±1 tolerance
   - Venue match: fuzzy, optional (venues have many abbreviation variants)
2. Define a `VerificationResult` dataclass:
   - Reference (original)
   - Best match (if any) with similarity scores
   - Status: `verified` | `close_match` | `not_found` | `mismatch`
   - Details: which fields matched/differed
3. Write `verifier.py` — orchestrates the full pipeline per reference:
   - Query Crossref first
   - If no strong match, query Semantic Scholar
   - If still no strong match, query OpenAlex
   - Return the best `VerificationResult`

**Subagent opportunity:** `matcher.py` and `verifier.py` are tightly coupled, best done by one agent. Could split out name normalization utilities to a subagent if the logic gets complex.

---

## Phase 4: CLI & Report Output

**Goal:** Wire everything together with a CLI and readable output.

### Steps

1. Write `cli.py` using `click`:
   - `citation-check verify <paper.pdf>`
   - Options: `--grobid-url` (default `http://localhost:8070`), `--verbose`, `--output json`
2. Write `report.py`:
   - CLI table output (use `rich` for colored terminal output)
   - Color-coded status per reference: green (verified), yellow (close match), red (not found/mismatch)
   - Show closest match details for yellow/red entries
   - Summary line: "X/Y references verified, Z flagged"
3. Optional JSON output mode for programmatic use

**Subagent opportunity:** Report formatting (`report.py`) is independent from CLI wiring — can be built by a subagent while another wires up `cli.py`.

---

## Phase 5: End-to-End Testing & Edge Cases

**Goal:** Validate against real papers and handle failure modes.

### Steps

1. Test with 2-3 real conference papers with known-good references
2. Test with a paper that has a deliberately inserted fake reference
3. Handle edge cases:
   - GROBID fails to parse a reference (fall back to raw text display, mark as "unparseable")
   - All APIs return no results (could be a very new or niche paper — flag but don't assume hallucination)
   - Non-English references
   - References to books, theses, technical reports (less coverage in Crossref)
   - Rate limit errors (retry with backoff)
4. Add a `--skip-indices` option to skip known-good references and speed up re-runs

**Subagent opportunity:** Testing against different papers can be parallelized across subagents, each running the tool against a different PDF and reporting results.

---

## Dependency Summary

```
pymupdf          # PDF text extraction (fallback if GROBID fails)
httpx            # HTTP client for GROBID + APIs
rapidfuzz        # Fuzzy string matching
click            # CLI framework
rich             # Terminal output formatting
```

Optional:
```
habanero         # Crossref Python client (or just use httpx directly)
```

External:
```
docker           # To run GROBID locally
```

## Architecture

```
src/citation_check/
├── cli.py              # Entry point, argument parsing
├── models.py           # Reference, SearchResult, VerificationResult
├── grobid.py           # PDF → structured references
├── clients/
│   ├── crossref.py     # Crossref API
│   ├── semantic_scholar.py  # Semantic Scholar API
│   └── openalex.py     # OpenAlex API
├── matcher.py          # Fuzzy matching logic
├── verifier.py         # Orchestrates verification pipeline
└── report.py           # CLI output formatting
```
