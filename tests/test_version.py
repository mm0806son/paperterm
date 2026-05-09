"""Smoke tests for the ``paperterm version`` subcommand.

These tests pin the Phase 1 completion criterion from the design doc
(§12 Phase 1): ``paperterm version`` prints ``paperterm 0.1.0.dev0``,
and the package version string is the same Python-level
``paperterm.__version__``.
"""

from __future__ import annotations

from click.testing import CliRunner

import paperterm
from paperterm.cli import main


def test_module_version_is_dev0() -> None:
    assert paperterm.__version__ == "0.1.0.dev0"


def test_cli_version_subcommand_prints_module_version() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["version"])
    assert result.exit_code == 0
    assert result.output == f"paperterm {paperterm.__version__}\n"
