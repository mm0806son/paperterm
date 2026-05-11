"""Smoke tests for the ``paperterm version`` subcommand.

The tests pin the released version string in two places so the
single source of truth in ``src/paperterm/__init__.py`` cannot
silently drift away from what the CLI advertises.
"""

from __future__ import annotations

from click.testing import CliRunner

import paperterm
from paperterm.cli import main


def test_module_version_pinned() -> None:
    assert paperterm.__version__ == "1.0.0"


def test_cli_version_subcommand_prints_module_version() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["version"])
    assert result.exit_code == 0
    assert result.output == f"paperterm {paperterm.__version__}\n"
