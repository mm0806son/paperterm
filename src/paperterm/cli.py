"""Command-line interface for paperterm.

Phase 1 shipped the ``version`` subcommand; Phase 4 adds ``check`` (the
core lint workflow). ``bootstrap`` and ``print-prompt`` arrive in
later phases (see plan §6).
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import click
from rich.console import Console

from . import __version__
from .glossary import Glossary
from .latex import TextSpan, iter_spans
from .linter import Linter, Violation
from .report import render_violations


@click.group()
def main() -> None:
    """LaTeX-aware terminology consistency linter for academic papers."""


@main.command()
def version() -> None:
    """Print the installed paperterm version."""
    click.echo(f"paperterm {__version__}")


@main.command()
@click.argument(
    "paper_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--glossary",
    "glossary_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to glossary.yaml. Defaults to <paper_dir>/glossary.yaml.",
)
@click.option(
    "--include",
    "include_globs",
    multiple=True,
    default=("**/*.tex",),
    show_default=True,
    help="Glob (relative to paper_dir) of files to scan; repeatable.",
)
@click.option(
    "--exclude",
    "exclude_globs",
    multiple=True,
    default=("**/build/**",),
    show_default=True,
    help="Glob to exclude after include matching; repeatable.",
)
def check(
    paper_dir: Path,
    glossary_path: Path | None,
    include_globs: tuple[str, ...],
    exclude_globs: tuple[str, ...],
) -> None:
    """Lint <PAPER_DIR>'s .tex files against a glossary; exit non-zero on hits.

    Exit code 0 means no violation found, 1 means at least one violation,
    and 2 is reserved for hard errors (missing glossary, parse failure).
    """
    glossary_file = glossary_path or paper_dir / "glossary.yaml"
    if not glossary_file.is_file():
        _fail(
            f"glossary file not found: {glossary_file}\n"
            "  hint: pass --glossary or place glossary.yaml under <paper_dir>"
        )

    try:
        glossary = Glossary.from_yaml(glossary_file)
    except Exception as exc:
        _fail(f"failed to load glossary {glossary_file}: {exc}")

    if glossary.is_draft:
        _fail(
            f"glossary {glossary_file} is a bootstrap draft (contains "
            "found_forms or canonical: TBD); please review the draft and "
            "remove draft-only fields before running check"
        )

    linter = Linter(glossary)
    spans = _collect_spans(paper_dir, include_globs, exclude_globs)
    violations = list(linter.check_spans(spans))

    count = render_violations(violations, console=Console())
    if count > 0:
        sys.exit(1)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _collect_spans(
    paper_dir: Path,
    include_globs: tuple[str, ...],
    exclude_globs: tuple[str, ...],
) -> Iterator[TextSpan]:
    matched: set[Path] = set()
    for pattern in include_globs:
        for p in paper_dir.glob(pattern):
            if p.is_file():
                matched.add(p.resolve())
    excluded: set[Path] = set()
    for pattern in exclude_globs:
        for p in paper_dir.glob(pattern):
            if p.is_dir():
                for sub in p.rglob("*"):
                    if sub.is_file():
                        excluded.add(sub.resolve())
            else:
                excluded.add(p.resolve())
    for path in sorted(matched - excluded):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            _fail(f"failed to read {path}: {exc}")
        rel = path.relative_to(paper_dir.resolve())
        yield from iter_spans(text, file=str(rel))


def _fail(message: str) -> None:
    """Print an error message to stderr and exit with code 2."""
    click.echo(f"paperterm: error: {message}", err=True)
    sys.exit(2)


# Re-export ``Violation`` at module level so that downstream tests /
# scripts can import it from ``paperterm.cli`` without round-tripping.
__all__ = ["main", "version", "check", "Violation"]
