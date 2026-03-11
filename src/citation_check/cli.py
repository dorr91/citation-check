"""CLI entry point for citation-check."""

from __future__ import annotations

import asyncio
import dataclasses
import json

import click

from citation_check.grobid import check_grobid, extract_references
from citation_check.report import print_report
from citation_check.verifier import verify_all


@click.group()
def main():
    """Citation verification tool."""
    pass


@main.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option("--grobid-url", default="http://localhost:8070", help="GROBID server URL")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed match info")
@click.option(
    "--output",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
)
def verify(pdf_path, grobid_url, verbose, output_format):
    """Verify citations in a PDF paper."""
    asyncio.run(_verify(pdf_path, grobid_url, verbose, output_format))


async def _verify(pdf_path, grobid_url, verbose, output_format):
    # 1. Check GROBID is running
    alive = await check_grobid(grobid_url)
    if not alive:
        click.echo(f"Error: GROBID is not running at {grobid_url}", err=True)
        raise SystemExit(1)

    # 2. Extract references
    click.echo(f"Extracting references from {pdf_path}...")
    references = await extract_references(pdf_path, grobid_url)
    click.echo(f"Found {len(references)} references.")

    if not references:
        click.echo("No references found.")
        return

    # 3. Verify all references
    click.echo("Verifying references...")
    results = await verify_all(references)

    # 4. Output results
    if output_format == "json":
        data = [dataclasses.asdict(r) for r in results]
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        print_report(results, verbose=verbose)
