# citation-check

> Keep this file up to date when changing the repo.

PDF citation verifier: GROBID extracts references, then checks them against Crossref → Semantic Scholar → OpenAlex.

## Commands

- `uv run pytest tests/ -v` — tests
- `uv run ruff check src/ tests/` — lint
- `uv run citation-check verify <paper.pdf> --mailto user@example.com` — run tool

## Testing

Uses `pytest-httpx` — do NOT use exact string `url=` in `httpx_mock.add_response()` (brittle with query param ordering). Regex patterns (`url=re.compile(...)`) are fine. Use `@pytest.mark.asyncio`.

## External

Requires GROBID: `docker compose up`, default `localhost:8070`.
