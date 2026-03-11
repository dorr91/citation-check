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
    """Return (total, match, close_match, not_found) counts."""
    total = len(results)
    match = sum(1 for r in results if r.status == "verified")
    close = sum(1 for r in results if r.status == "close_match")
    not_found = total - match - close
    return total, match, close, not_found


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
    table.add_column("Exact", width=7, justify="right")
    table.add_column("Close", width=7, justify="right")
    table.add_column("Not Found", width=11, justify="right")

    total_refs = 0
    total_match = 0
    total_close = 0
    total_not_found = 0

    for name, results in paper_results:
        n_total, n_match, n_close, n_not_found = _paper_stats(results)
        total_refs += n_total
        total_match += n_match
        total_close += n_close
        total_not_found += n_not_found

        if n_total == 0:
            table.add_row(name, "0", "-", "-", "-")
        elif n_not_found == 0 and n_close == 0:
            table.add_row(
                name,
                str(n_total),
                f"[green]{n_match}[/green]",
                "0",
                "0",
            )
        else:
            table.add_row(
                name,
                str(n_total),
                f"[green]{n_match}[/green]",
                f"[yellow]{n_close}[/yellow]" if n_close else "0",
                f"[red]{n_not_found}[/red]" if n_not_found else "0",
            )

    for name, err in errors:
        table.add_row(f"[red]{name}[/red]", "[red]error[/red]", "", "", "")

    console.print(table)
    console.print(
        f"\nTotal: {total_match} exact, {total_close} close,"
        f" {total_not_found} not found across {len(paper_results)} paper(s)"
    )
    if errors:
        console.print(f"[red]{len(errors)} paper(s) failed to process[/red]")


PLAIN_STATUS = {
    "verified": "VERIFIED",
    "close_match": "CLOSE MATCH",
    "not_found": "NOT FOUND",
    "mismatch": "MISMATCH",
}

STATUS_CSS_CLASS = {
    "verified": "verified",
    "close_match": "close",
    "not_found": "not-found",
    "mismatch": "not-found",
}


def _html_escape(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_batch_report(
    paper_results: list[tuple[str, list[VerificationResult]]],
    errors: list[tuple[str, str]],
    output_path: str,
    verbose: bool = False,
) -> None:
    """Write a full HTML report to a file."""
    parts: list[str] = []

    parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Citation Verification Report</title>
<style>
  :root {
    --green: #22863a;
    --yellow: #b08800;
    --red: #cb2431;
    --bg: #ffffff;
    --bg-alt: #f6f8fa;
    --border: #d0d7de;
    --text: #1f2328;
    --text-dim: #656d76;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    color: var(--text);
    background: var(--bg);
    line-height: 1.5;
    max-width: 960px;
    margin: 0 auto;
    padding: 2rem 1rem;
  }
  h1 { font-size: 1.5rem; margin-bottom: 1.5rem; }
  h2 { font-size: 1.2rem; margin: 2rem 0 0.75rem; border-bottom: 1px solid var(--border); padding-bottom: 0.4rem; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 1rem; font-size: 0.9rem; }
  th, td { text-align: left; padding: 0.4rem 0.75rem; border-bottom: 1px solid var(--border); }
  th { background: var(--bg-alt); font-weight: 600; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  .badge {
    display: inline-block;
    padding: 0.1rem 0.5rem;
    border-radius: 1rem;
    font-size: 0.8rem;
    font-weight: 600;
  }
  .badge.verified { background: #dafbe1; color: var(--green); }
  .badge.close { background: #fff8c5; color: var(--yellow); }
  .badge.not-found { background: #ffebe9; color: var(--red); }
  .match-info { color: var(--text-dim); font-size: 0.85rem; }
  .score { font-size: 0.85rem; color: var(--text-dim); }
  .totals td { font-weight: 600; border-top: 2px solid var(--border); }
  .error-row td { color: var(--red); }
  details { margin-bottom: 0.5rem; }
  details summary { cursor: pointer; font-weight: 500; padding: 0.25rem 0; }
  .toggle-btn {
    background: var(--bg-alt);
    border: 1px solid var(--border);
    border-radius: 0.375rem;
    padding: 0.25rem 0.75rem;
    font-size: 0.8rem;
    cursor: pointer;
    color: var(--text-dim);
    margin-bottom: 0.5rem;
  }
  .toggle-btn:hover { background: #eaeef2; }
  .row-ok { display: none; }
  .show-all .row-ok { display: table-row; }
  .detail-row td { padding-top: 0; }
  .detail-columns { display: flex; gap: 1.5rem; }
  .detail-section { flex: 1; font-size: 0.85rem; color: var(--text-dim); line-height: 1.6; padding: 0.4rem 0.6rem; border-radius: 0.375rem; background: var(--bg-alt); }
  .detail-section h4 { font-size: 0.8rem; color: var(--text); margin: 0 0 0.2rem; text-transform: uppercase; letter-spacing: 0.03em; }
  .detail-section dl { margin: 0; }
  .detail-section dt { display: inline; font-weight: 600; }
  .detail-section dt::after { content: " "; }
  .detail-section dd { display: inline; margin: 0; }
  .detail-section dd::after { content: ""; display: block; }
  .detail-section.match-section { border-left: 3px solid var(--border); }
</style>
</head>
<body>
<h1>Citation Verification Report</h1>
""")

    # Summary table
    parts.append("<h2>Summary</h2>\n<table>\n<tr>")
    parts.append("<th>Paper</th><th class='num'>Refs</th>")
    parts.append("<th class='num'>Exact</th><th class='num'>Close</th>")
    parts.append("<th class='num'>Not Found</th></tr>\n")

    total_refs = 0
    total_match = 0
    total_close = 0
    total_not_found = 0

    for name, results in paper_results:
        n_total, n_match, n_close, n_not_found = _paper_stats(results)
        total_refs += n_total
        total_match += n_match
        total_close += n_close
        total_not_found += n_not_found
        esc_name = _html_escape(name)

        parts.append(f"<tr><td>{esc_name}</td><td class='num'>{n_total}</td>")
        if n_total == 0:
            parts.append(
                "<td class='num'>-</td><td class='num'>-</td>"
                "<td class='num'>-</td></tr>\n"
            )
        else:
            parts.append(
                f"<td class='num'>{n_match}</td>"
                f"<td class='num'>{n_close}</td>"
                f"<td class='num'>{n_not_found}</td></tr>\n"
            )

    for name, _ in errors:
        esc_name = _html_escape(name)
        parts.append(
            f"<tr class='error-row'><td>{esc_name}</td>"
            "<td class='num'>ERROR</td>"
            "<td></td><td></td><td></td></tr>\n"
        )

    parts.append(
        f"<tr class='totals'><td>Total</td>"
        f"<td class='num'>{total_refs}</td>"
        f"<td class='num'>{total_match}</td>"
        f"<td class='num'>{total_close}</td>"
        f"<td class='num'>{total_not_found}</td></tr>\n"
    )
    parts.append("</table>\n")

    # Per-paper details
    for paper_idx, (name, results) in enumerate(paper_results):
        esc_name = _html_escape(name)
        parts.append(f"<h2>{esc_name}</h2>\n")

        if not results:
            parts.append("<p>No references found.</p>\n")
            continue

        n_not_found = sum(
            1 for r in results if r.status in ("not_found", "mismatch")
        )
        n_ok = len(results) - n_not_found

        if n_ok > 0:
            parts.append(
                f"<button class='toggle-btn' onclick=\""
                f"var t=document.getElementById('paper-{paper_idx}');"
                f"var on=t.classList.toggle('show-all');"
                f"this.textContent=on"
                f"?'Hide {n_ok} verified/close match'"
                f":'Show {n_ok} verified/close match';"
                f"\">Show {n_ok} verified/close match</button>\n"
            )

        parts.append(f"<table id='paper-{paper_idx}'>\n<tr><th>#</th><th>Status</th>")
        parts.append("<th>Reference</th><th>Best Match</th><th>Score</th></tr>\n")

        for vr in results:
            idx = vr.reference.index + 1
            status_label = PLAIN_STATUS.get(vr.status, vr.status)
            css_class = STATUS_CSS_CLASS.get(vr.status, "")
            is_problem = vr.status in ("not_found", "mismatch")
            row_class = "" if is_problem else " class='row-ok'"
            title = _html_escape(
                vr.reference.title or vr.reference.raw_text or "(no title)"
            )

            match_cell = "-"
            score_cell = ""
            if vr.best_match:
                bm = vr.best_match
                match_cell = _html_escape(bm.title)
                if bm.source:
                    match_cell += (
                        f" <span class='match-info'>[{_html_escape(bm.source)}]</span>"
                    )
                score_cell = (
                    f"<span class='score'>"
                    f"title {vr.title_score:.0f}%"
                    f" &middot; author {vr.author_score:.0f}%"
                    f" &middot; year {'&#10003;' if vr.year_match else '&#10007;'}"
                    f"</span>"
                )

            parts.append(
                f"<tr{row_class}><td>{idx}</td>"
                f"<td><span class='badge {css_class}'>{status_label}</span></td>"
                f"<td>{title}</td>"
                f"<td>{match_cell}</td>"
                f"<td>{score_cell}</td></tr>\n"
            )

            # Always show full details for not-found/mismatch citations
            if is_problem:
                parts.append(
                    f"<tr class='detail-row'><td></td><td colspan='4'>"
                    f"<div class='detail-columns'>"
                )
                # Source citation section
                parts.append("<div class='detail-section'><h4>Source</h4><dl>")
                if vr.reference.authors:
                    parts.append(
                        f"<dt>Authors:</dt><dd>{_html_escape(', '.join(vr.reference.authors))}</dd>"
                    )
                if vr.reference.year:
                    parts.append(
                        f"<dt>Year:</dt><dd>{vr.reference.year}</dd>"
                    )
                if vr.reference.doi:
                    parts.append(
                        f"<dt>DOI:</dt><dd>{_html_escape(vr.reference.doi)}</dd>"
                    )
                if vr.reference.raw_text:
                    parts.append(
                        f"<dt>Raw text:</dt><dd>{_html_escape(vr.reference.raw_text)}</dd>"
                    )
                parts.append("</dl></div>")
                # Best match section
                if vr.best_match:
                    bm = vr.best_match
                    parts.append(
                        "<div class='detail-section match-section'>"
                        "<h4>Best Match</h4><dl>"
                    )
                    parts.append(
                        f"<dt>Title:</dt><dd>{_html_escape(bm.title)}"
                        f" [{_html_escape(bm.source)}]</dd>"
                    )
                    if bm.authors:
                        parts.append(
                            f"<dt>Authors:</dt><dd>{_html_escape(', '.join(bm.authors))}</dd>"
                        )
                    if bm.year:
                        parts.append(
                            f"<dt>Year:</dt><dd>{bm.year}</dd>"
                        )
                    parts.append(
                        f"<dt>Scores:</dt><dd>"
                        f"title {vr.title_score:.0f}%"
                        f" &middot; author {vr.author_score:.0f}%"
                        f" &middot; year {'&#10003;' if vr.year_match else '&#10007;'}"
                        f"</dd>"
                    )
                    parts.append("</dl></div>")
                else:
                    parts.append(
                        "<div class='detail-section match-section'>"
                        "<h4>Best Match</h4>"
                        "<p>No results from any source</p></div>"
                    )
                parts.append(
                    f"</div>"
                    f"<div class='match-info' style='margin-top:0.3rem'>"
                    f"{_html_escape(vr.details)}</div>"
                    f"</td></tr>\n"
                )
            elif verbose:
                detail_parts = []
                if vr.reference.authors:
                    detail_parts.append(
                        f"Authors: {_html_escape(', '.join(vr.reference.authors))}"
                    )
                if vr.reference.year:
                    detail_parts.append(f"Year: {vr.reference.year}")
                if vr.reference.doi:
                    detail_parts.append(
                        f"DOI: {_html_escape(vr.reference.doi)}"
                    )
                if vr.best_match and vr.best_match.authors:
                    detail_parts.append(
                        f"Match authors: "
                        f"{_html_escape(', '.join(vr.best_match.authors))}"
                    )
                detail_parts.append(
                    f"Details: {_html_escape(vr.details)}"
                )
                detail_html = "<br>".join(detail_parts)
                parts.append(
                    f"<tr class='row-ok'><td></td><td colspan='4'>"
                    f"<span class='match-info'>{detail_html}</span>"
                    f"</td></tr>\n"
                )

        parts.append("</table>\n")

    # Errors section
    if errors:
        parts.append("<h2>Errors</h2>\n<table>\n")
        parts.append("<tr><th>Paper</th><th>Error</th></tr>\n")
        for name, err in errors:
            parts.append(
                f"<tr class='error-row'>"
                f"<td>{_html_escape(name)}</td>"
                f"<td>{_html_escape(err)}</td></tr>\n"
            )
        parts.append("</table>\n")

    parts.append("</body>\n</html>\n")

    Path(output_path).write_text("".join(parts))
