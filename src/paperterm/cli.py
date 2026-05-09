"""Command-line interface for paperterm.

Phase 1 ships only the ``version`` subcommand — bootstrap, check, and
print-prompt are added in subsequent phases (see plan §6).
"""

from __future__ import annotations

import click

from . import __version__


@click.group()
def main() -> None:
    """LaTeX-aware terminology consistency linter for academic papers."""


@main.command()
def version() -> None:
    """Print the installed paperterm version."""
    click.echo(f"paperterm {__version__}")
