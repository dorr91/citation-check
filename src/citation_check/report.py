"""Rich-formatted terminal report for citation verification results."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from citation_check.models import VerificationResult

STATUS_ICONS = {
    "verified": "[green]\u2713 Verified[/green]",
    "close_match": "[yellow]~ Close Match[/yellow]",
    "not_found": "[red]\u2717 Not Found[/red]",
    "mismatch": "[red]\u2717 Mismatch[/red]",
}

STATUS_STYLES = {
    "verified": "green",
    "close_match": "yellow",
    "not_found": "red",
    "mismatch": "red",
}


def _truncate(text: str, max_len: int = 60) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def print_report(
    results: list[VerificationResult],
    verbose: bool = False,
    console: Console | None = None,
) -> None:
    """Print a colored table of verification results."""
    if console is None:
        console = Console()

    table = Table(title="Citation Verification Report")
    table.add_column("#", style="dim", width=4)
    table.add_column("Status", width=16)
    table.add_column("Title", min_width=20)
    table.add_column("Best Match", min_width=20)
    table.add_column("Score", width=8)

    for vr in results:
        style = STATUS_STYLES.get(vr.status, "")
        status_text = STATUS_ICONS.get(vr.status, vr.status)

        if vr.reference.title:
            ref_title = _truncate(vr.reference.title)
        elif vr.reference.raw_text:
            ref_title = _truncate(f"\\[raw] {vr.reference.raw_text}")
        else:
            ref_title = "(no title)"

        if vr.best_match:
            match_text = _truncate(vr.best_match.title)
            if vr.best_match.source:
                match_text += f" [{vr.best_match.source}]"
        else:
            match_text = "-"

        score_text = f"{vr.title_score:.0f}%"

        table.add_row(
            str(vr.reference.index + 1),
            status_text,
            f"[{style}]{ref_title}[/{style}]",
            match_text,
            score_text,
        )

        if verbose:
            detail_parts = [
                f"Author score: {vr.author_score:.0f}%",
                f"Year match: {vr.year_match}",
                f"Details: {vr.details}",
            ]
            table.add_row(
                "",
                "",
                f"[dim]{' | '.join(detail_parts)}[/dim]",
                "",
                "",
            )

    console.print(table)

    verified_count = sum(1 for r in results if r.status == "verified")
    flagged_count = len(results) - verified_count
    console.print(
        f"\n{verified_count}/{len(results)} references verified, {flagged_count} flagged"
    )

    # Detail section for non-verified citations
    flagged = [r for r in results if r.status != "verified"]
    if flagged:
        console.print("\n[bold]Flagged Citations Detail[/bold]\n")
        for vr in flagged:
            idx = vr.reference.index + 1
            status_text = STATUS_ICONS.get(vr.status, vr.status)
            console.print(f"[bold]#{idx}[/bold] {status_text}")

            # Original reference info
            console.print(f"  [dim]Title:[/dim]   {vr.reference.title or '(none)'}")
            if vr.reference.authors:
                console.print(
                    f"  [dim]Authors:[/dim] {', '.join(vr.reference.authors)}"
                )
            if vr.reference.year:
                console.print(f"  [dim]Year:[/dim]    {vr.reference.year}")
            if vr.reference.doi:
                console.print(f"  [dim]DOI:[/dim]     {vr.reference.doi}")

            # Best match info (if any)
            if vr.best_match:
                console.print(f"  [dim]Found:[/dim]   {vr.best_match.title} [{vr.best_match.source}]")
                if vr.best_match.authors:
                    console.print(
                        f"  [dim]         Authors: {', '.join(vr.best_match.authors)}[/dim]"
                    )
                if vr.best_match.year:
                    console.print(
                        f"  [dim]         Year: {vr.best_match.year}[/dim]"
                    )
                console.print(
                    f"  [dim]Scores:[/dim]  title={vr.title_score:.0f}% author={vr.author_score:.0f}% year={'✓' if vr.year_match else '✗'}"
                )
            else:
                console.print("  [dim]Found:[/dim]   (no results from any source)")

            console.print()
