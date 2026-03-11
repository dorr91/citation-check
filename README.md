# citation-check

Verifies whether citations in a PDF are real or potentially hallucinated by
looking them up in academic databases (Crossref, Semantic Scholar, OpenAlex).

## Setup

Requires Python 3.12+ and a running [GROBID](https://github.com/kermitt2/grobid)
instance for PDF reference extraction.

```bash
# Start GROBID
docker compose up -d

# Install
uv sync
```

## Usage

```bash
citation-check verify paper.pdf --mailto you@example.com
```

The `--mailto` flag is **required**. Crossref and OpenAlex offer faster "polite
pool" access to clients that identify themselves with a contact email. Providing
a real email is how we respect their terms of use — they provide these APIs for
free, and identifying ourselves lets them contact us if our usage causes
problems.

### Options

| Flag | Description |
|------|-------------|
| `--mailto EMAIL` | **(required)** Contact email sent to Crossref and OpenAlex |
| `--grobid-url URL` | GROBID server URL (default: `http://localhost:8070`) |
| `--output table\|json` | Output format (default: `table`) |
| `--verbose, -v` | Show detailed match scores |
| `--skip-indices 0,3,5` | Skip specific reference indices |

### How it works

1. Sends the PDF to GROBID to extract structured references
2. For each reference, looks it up in Crossref, Semantic Scholar, and OpenAlex
3. Uses fuzzy title matching, author overlap, and year comparison to score matches
4. Reports each reference as **verified**, **close match**, **mismatch**, or **not found**

A "not found" result means the reference wasn't found in any of the databases —
this could indicate hallucination, but could also mean the work is a book,
thesis, or very recent publication not yet indexed.
