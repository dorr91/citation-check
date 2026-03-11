"""CLI entry point for citation-check."""

from __future__ import annotations

import asyncio
import dataclasses
import json
from pathlib import Path

import click

from citation_check.grobid import check_grobid, extract_references
from citation_check.models import VerificationResult
from citation_check.report import print_batch_summary, print_report, write_batch_report
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
@click.option(
    "--skip-indices",
    default=None,
    help="Comma-separated list of reference indices to skip (e.g. 0,3,5)",
)
@click.option(
    "--mailto",
    required=True,
    help="Contact email for API polite pools (Crossref, OpenAlex)",
)
def verify(
    pdf_path, grobid_url, verbose, output_format, skip_indices, mailto,
):
    """Verify citations in a PDF paper."""
    asyncio.run(
        _verify(
            pdf_path, grobid_url, verbose,
            output_format, skip_indices, mailto,
        )
    )


async def _verify(
    pdf_path, grobid_url, verbose, output_format,
    skip_indices=None, mailto=None,
):
    # Parse skip indices
    skip_set: set[int] = set()
    if skip_indices:
        try:
            skip_set = {
                int(x.strip()) for x in skip_indices.split(",")
            }
        except ValueError:
            click.echo(
                "Error: --skip-indices must be"
                " comma-separated integers",
                err=True,
            )
            raise SystemExit(1)

    # 1. Check GROBID is running
    alive = await check_grobid(grobid_url)
    if not alive:
        click.echo(f"Error: GROBID is not running at {grobid_url}", err=True)
        raise SystemExit(1)

    # 2. Extract references
    click.echo(f"Extracting references from {pdf_path}...")
    references = await extract_references(pdf_path, grobid_url)
    click.echo(f"Found {len(references)} references.")

    if skip_set:
        references = [r for r in references if r.index not in skip_set]

    if not references:
        click.echo("No references found.")
        return

    # 3. Verify all references
    click.echo("Verifying references...")

    def _progress(done: int, total: int) -> None:
        click.echo(f"\r  {done}/{total} verified", nl=False)
        if done == total:
            click.echo()  # final newline

    results = await verify_all(references, mailto=mailto, on_progress=_progress)

    # 4. Output results
    if output_format == "json":
        data = [dataclasses.asdict(r) for r in results]
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        print_report(results, verbose=verbose)


@main.command("verify-dir")
@click.argument("dir_path", type=click.Path(exists=True, file_okay=False))
@click.option("--grobid-url", default="http://localhost:8070", help="GROBID server URL")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed match info")
@click.option(
    "--output-file",
    "-o",
    default="report.txt",
    help="Output file path for the full report (default: report.txt)",
)
@click.option(
    "--mailto",
    required=True,
    help="Contact email for API polite pools (Crossref, OpenAlex)",
)
def verify_dir(dir_path, grobid_url, verbose, output_file, mailto):
    """Verify citations in all PDFs within a directory."""
    asyncio.run(
        _verify_dir(dir_path, grobid_url, verbose, output_file, mailto)
    )


async def _verify_dir(dir_path, grobid_url, verbose, output_file, mailto):
    # 1. Check GROBID is running
    alive = await check_grobid(grobid_url)
    if not alive:
        click.echo(f"Error: GROBID is not running at {grobid_url}", err=True)
        raise SystemExit(1)

    # 2. Find all PDFs
    pdf_dir = Path(dir_path)
    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        click.echo(f"No PDF files found in {dir_path}")
        raise SystemExit(1)

    click.echo(f"Found {len(pdf_files)} PDF(s) in {dir_path}\n")

    # 3. Process each PDF
    all_paper_results: list[tuple[str, list[VerificationResult]]] = []
    errors: list[tuple[str, str]] = []

    for i, pdf_path in enumerate(pdf_files, 1):
        name = pdf_path.name
        click.echo(f"[{i}/{len(pdf_files)}] {name}")

        try:
            click.echo("  Extracting references...")
            references = await extract_references(str(pdf_path), grobid_url)
            click.echo(f"  Found {len(references)} references.")

            if not references:
                all_paper_results.append((name, []))
                continue

            click.echo("  Verifying...")

            def _progress(done: int, total: int) -> None:
                click.echo(f"\r    {done}/{total} verified", nl=False)
                if done == total:
                    click.echo()

            results = await verify_all(
                references, mailto=mailto, on_progress=_progress,
            )
            all_paper_results.append((name, results))
        except Exception as exc:
            click.echo(f"  Error: {exc}", err=True)
            errors.append((name, str(exc)))

    click.echo()

    # 4. Print summary table to stdout
    print_batch_summary(all_paper_results, errors)

    # 5. Write full report to file
    write_batch_report(
        all_paper_results, errors, output_file, verbose=verbose,
    )
    click.echo(f"\nFull report written to {output_file}")
