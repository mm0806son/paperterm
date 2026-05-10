"""Human-readable line-format report for ``paperterm check`` output."""

from __future__ import annotations

from collections.abc import Iterable

from rich.console import Console
from rich.text import Text

from .linter import Violation


def render_violations(
    violations: Iterable[Violation],
    *,
    console: Console | None = None,
) -> int:
    """Print a one-line-per-violation report. Returns the number of violations."""
    console = console or Console()
    count = 0
    for v in violations:
        count += 1
        line = Text()
        line.append(f"{v.file}:{v.line}:{v.column}", style="bold")
        line.append("  ")
        line.append(f"[{v.context.value}]", style="dim")
        line.append("  ")
        line.append(repr(v.matched_text), style="yellow")
        line.append("  →  ")
        line.append(repr(v.suggestion), style="green")
        line.append("  ")
        line.append(f"({v.concept_id})", style="dim cyan")
        console.print(line)
    if count == 0:
        console.print("[green]paperterm: no violations[/green]")
    else:
        console.print(f"\n[red]paperterm: {count} violation(s)[/red]")
    return count
