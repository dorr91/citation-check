# citation-check

> Keep this file up to date when changing the repo.

PDF citation verifier: GROBID extracts references, then checks them against Crossref → Semantic Scholar → OpenAlex.

## Commands

- `uv run pytest tests/ -v` — tests
- `uv run ruff check src/ tests/` — lint
- `uv run citation-check verify <paper.pdf>` — run tool

## Testing

Uses `pytest-httpx` — do NOT use `url=` in `httpx_mock.add_response()` (exact match including query params). Use `@pytest.mark.asyncio`.

## External

Requires GROBID: `docker compose up`, default `localhost:8070`.
