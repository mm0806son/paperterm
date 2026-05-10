"""Command-line interface for paperterm.

Phase 1 shipped the ``version`` subcommand; Phase 4 added ``check``
(the core lint workflow); Phase 5 adds ``print-prompt`` and
``bootstrap`` so users can prepare a glossary draft using their own
LLM (Claude.ai, ChatGPT, ...) without handing paperterm an API key.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import click
from rich.console import Console

from . import __version__
from .bootstrap import DEFAULT_OUTPUT_NAME, build_prompt_file
from .glossary import Glossary
from .latex import TextSpan, iter_spans
from .linter import Linter, Violation
from .prompts import BOOTSTRAP_PROMPT
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


@main.command("print-prompt")
@click.option(
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write the prompt to this path instead of stdout.",
)
def print_prompt(output_path: Path | None) -> None:
    """Print paperterm's standalone bootstrap prompt.

    The prompt is paper-agnostic: paste it into any LLM (Claude.ai,
    ChatGPT, ...) followed by your own .tex content between the
    `=== BEGIN CORPUS ===` / `=== END CORPUS ===` markers, then save
    the YAML reply.
    """
    if output_path is None:
        click.echo(BOOTSTRAP_PROMPT, nl=False)
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(BOOTSTRAP_PROMPT, encoding="utf-8")
    click.echo(f"paperterm: prompt written to {output_path}")


@main.command()
@click.argument(
    "paper_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help=f"Output file (default: <paper_dir>/{DEFAULT_OUTPUT_NAME}).",
)
@click.option(
    "--include",
    "include_globs",
    multiple=True,
    default=("**/*.tex",),
    show_default=True,
    help="Glob (relative to paper_dir) of files to include; repeatable.",
)
@click.option(
    "--exclude",
    "exclude_globs",
    multiple=True,
    default=("**/build/**",),
    show_default=True,
    help="Glob to exclude after include matching; repeatable.",
)
def bootstrap(
    paper_dir: Path,
    output_path: Path | None,
    include_globs: tuple[str, ...],
    exclude_globs: tuple[str, ...],
) -> None:
    """Prepare a single prompt+corpus file you can paste into your LLM.

    paperterm will not contact any external service. The output is a
    plain text file containing the standalone prompt followed by your
    paper's lintable text (math, comments, citations, etc. already
    stripped). Paste the file into Claude.ai / ChatGPT / your editor
    of choice and capture the YAML reply.
    """
    try:
        result = build_prompt_file(
            paper_dir,
            include_globs=include_globs,
            exclude_globs=exclude_globs,
            output_path=output_path,
        )
    except (OSError, ValueError) as exc:
        _fail(str(exc))

    out = result.output_path
    rel_paper = paper_dir.resolve()
    click.echo(
        f"paperterm: prompt written to {out}\n"
        f"  scanned {result.files_scanned} .tex file(s), wrote "
        f"{result.bytes_written} bytes\n"
        "\n"
        "Next steps:\n"
        f"  1. Paste the contents of {out} into any LLM (Claude.ai, "
        "ChatGPT, ...) and capture its YAML reply.\n"
        f"  2. Save the reply as {rel_paper}/glossary.draft.yaml "
        "(this is a draft).\n"
        f"  3. Hand-promote the draft to {rel_paper}/glossary.yaml:\n"
        "       - drop every found_forms / confidence field\n"
        '       - choose a canonical (replace any "TBD")\n'
        "       - move remaining forms into aliases / allowed_forms\n"
        f"  4. Run `paperterm check {rel_paper}`."
    )


# Re-export ``Violation`` at module level so that downstream tests /
# scripts can import it from ``paperterm.cli`` without round-tripping.
__all__ = ["main", "version", "check", "print_prompt", "bootstrap", "Violation"]
