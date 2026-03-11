"""Rich-formatted terminal report for citation verification results."""

from __future__ import annotations

from pathlib import Path

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


def _paper_stats(
    results: list[VerificationResult],
) -> tuple[int, int, int, int]:
    """Return (total, verified, close_match, flagged) counts."""
    total = len(results)
    verified = sum(1 for r in results if r.status == "verified")
    close = sum(1 for r in results if r.status == "close_match")
    flagged = total - verified
    return total, verified, close, flagged


def print_batch_summary(
    paper_results: list[tuple[str, list[VerificationResult]]],
    errors: list[tuple[str, str]],
    console: Console | None = None,
) -> None:
    """Print a summary table across all papers to the terminal."""
    if console is None:
        console = Console()

    table = Table(title="Batch Summary")
    table.add_column("Paper", min_width=30)
    table.add_column("Refs", width=6, justify="right")
    table.add_column("Verified", width=10, justify="right")
    table.add_column("Flagged", width=10, justify="right")

    total_refs = 0
    total_verified = 0
    total_flagged = 0

    for name, results in paper_results:
        n_total, n_verified, _, n_flagged = _paper_stats(results)
        total_refs += n_total
        total_verified += n_verified
        total_flagged += n_flagged

        if n_total == 0:
            table.add_row(name, "0", "-", "-")
        elif n_flagged == 0:
            table.add_row(
                name,
                str(n_total),
                f"[green]{n_verified}[/green]",
                "0",
            )
        else:
            table.add_row(
                name,
                str(n_total),
                f"[green]{n_verified}[/green]",
                f"[red]{n_flagged}[/red]",
            )

    for name, err in errors:
        table.add_row(f"[red]{name}[/red]", "[red]error[/red]", "", "")

    console.print(table)
    console.print(
        f"\nTotal: {total_verified}/{total_refs} verified,"
        f" {total_flagged} flagged across {len(paper_results)} paper(s)"
    )
    if errors:
        console.print(f"[red]{len(errors)} paper(s) failed to process[/red]")


PLAIN_STATUS = {
    "verified": "VERIFIED",
    "close_match": "CLOSE MATCH",
    "not_found": "NOT FOUND",
    "mismatch": "MISMATCH",
}


def write_batch_report(
    paper_results: list[tuple[str, list[VerificationResult]]],
    errors: list[tuple[str, str]],
    output_path: str,
    verbose: bool = False,
) -> None:
    """Write a full plain-text report to a file."""
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("CITATION VERIFICATION REPORT")
    lines.append("=" * 72)
    lines.append("")

    # Summary table
    lines.append("SUMMARY")
    lines.append("-" * 72)
    lines.append(f"{'Paper':<40} {'Refs':>6} {'OK':>6} {'Flag':>6}")
    lines.append("-" * 72)

    total_refs = 0
    total_verified = 0
    total_flagged = 0

    for name, results in paper_results:
        n_total, n_verified, _, n_flagged = _paper_stats(results)
        total_refs += n_total
        total_verified += n_verified
        total_flagged += n_flagged
        display_name = name if len(name) <= 38 else name[:35] + "..."
        if n_total == 0:
            lines.append(f"{display_name:<40} {'0':>6} {'-':>6} {'-':>6}")
        else:
            lines.append(
                f"{display_name:<40} {n_total:>6} {n_verified:>6} {n_flagged:>6}"
            )

    for name, _ in errors:
        display_name = name if len(name) <= 38 else name[:35] + "..."
        lines.append(f"{display_name:<40} {'ERROR':>6}")

    lines.append("-" * 72)
    lines.append(
        f"{'TOTAL':<40} {total_refs:>6} {total_verified:>6} {total_flagged:>6}"
    )
    lines.append("")

    # Per-paper details
    for name, results in paper_results:
        lines.append("=" * 72)
        lines.append(f"PAPER: {name}")
        lines.append("=" * 72)

        if not results:
            lines.append("  No references found.")
            lines.append("")
            continue

        for vr in results:
            idx = vr.reference.index + 1
            status = PLAIN_STATUS.get(vr.status, vr.status)
            title = vr.reference.title or vr.reference.raw_text or "(no title)"
            lines.append(f"  [{idx}] {status}: {title}")

            if vr.best_match:
                bm = vr.best_match
                lines.append(
                    f"      Match: {bm.title} [{bm.source}]"
                )
                lines.append(
                    f"      Score: title={vr.title_score:.0f}%"
                    f" author={vr.author_score:.0f}%"
                    f" year={'yes' if vr.year_match else 'no'}"
                )

            if verbose:
                if vr.reference.authors:
                    lines.append(
                        f"      Authors: {', '.join(vr.reference.authors)}"
                    )
                if vr.reference.year:
                    lines.append(f"      Year: {vr.reference.year}")
                if vr.reference.doi:
                    lines.append(f"      DOI: {vr.reference.doi}")
                if vr.best_match and vr.best_match.authors:
                    lines.append(
                        f"      Match authors: {', '.join(vr.best_match.authors)}"
                    )
                lines.append(f"      Details: {vr.details}")

        lines.append("")

    # Errors section
    if errors:
        lines.append("=" * 72)
        lines.append("ERRORS")
        lines.append("=" * 72)
        for name, err in errors:
            lines.append(f"  {name}: {err}")
        lines.append("")

    Path(output_path).write_text("\n".join(lines) + "\n")
