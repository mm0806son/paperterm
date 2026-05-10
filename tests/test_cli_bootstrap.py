"""CLI integration tests for ``paperterm print-prompt`` and ``paperterm bootstrap``."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from paperterm.bootstrap import DEFAULT_OUTPUT_NAME
from paperterm.cli import main as cli_main
from paperterm.prompts import BOOTSTRAP_PROMPT


def _write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# print-prompt
# --------------------------------------------------------------------------- #


def test_print_prompt_to_stdout_emits_full_prompt() -> None:
    runner = CliRunner()
    result = runner.invoke(cli_main, ["print-prompt"])
    assert result.exit_code == 0
    # Click strips the trailing newline of the last echo by default; allow a
    # trailing-newline tolerance.
    assert result.output.startswith(BOOTSTRAP_PROMPT[:200])
    assert "=== BEGIN CORPUS ===" in result.output


def test_print_prompt_to_file_writes_byte_equal_prompt(tmp_path: Path) -> None:
    target = tmp_path / "prompt.md"
    runner = CliRunner()
    result = runner.invoke(cli_main, ["print-prompt", "--output", str(target)])
    assert result.exit_code == 0
    assert "prompt written to" in result.output
    assert target.read_text(encoding="utf-8") == BOOTSTRAP_PROMPT


# --------------------------------------------------------------------------- #
# bootstrap
# --------------------------------------------------------------------------- #


def test_bootstrap_writes_default_output_and_prints_next_steps(tmp_path: Path) -> None:
    _write(tmp_path / "section.tex", "Real prose body.\n")
    runner = CliRunner()
    result = runner.invoke(cli_main, ["bootstrap", str(tmp_path)])
    assert result.exit_code == 0
    out_path = tmp_path / DEFAULT_OUTPUT_NAME
    assert out_path.is_file()
    payload = out_path.read_text(encoding="utf-8")
    assert payload.startswith(BOOTSTRAP_PROMPT.rstrip("\n"))
    assert "=== FILE: section.tex ===" in payload
    assert "1: Real prose body." in payload
    # CLI message must walk the user through the manual review step.
    assert "Paste the contents of" in result.output
    assert "Hand-promote" in result.output
    assert "glossary.draft.yaml" in result.output
    assert "glossary.yaml" in result.output


def test_bootstrap_explicit_output_path(tmp_path: Path) -> None:
    _write(tmp_path / "section.tex", "Hello.\n")
    explicit = tmp_path / "out" / "prompt.txt"
    runner = CliRunner()
    result = runner.invoke(cli_main, ["bootstrap", str(tmp_path), "--output", str(explicit)])
    assert result.exit_code == 0
    assert explicit.is_file()
    assert "Hello." in explicit.read_text(encoding="utf-8")


def test_bootstrap_include_exclude(tmp_path: Path) -> None:
    _write(tmp_path / "main.tex", "Main prose.\n")
    _write(tmp_path / "build" / "tmp.tex", "Build prose.\n")
    runner = CliRunner()
    result = runner.invoke(
        cli_main,
        [
            "bootstrap",
            str(tmp_path),
            "--include",
            "main.tex",
            "--exclude",
            "build/**",
        ],
    )
    assert result.exit_code == 0
    out = (tmp_path / DEFAULT_OUTPUT_NAME).read_text(encoding="utf-8")
    assert "Main prose." in out
    assert "Build prose." not in out


def test_bootstrap_does_not_leak_inline_math_or_cite_to_payload(tmp_path: Path) -> None:
    _write(
        tmp_path / "section.tex",
        r"prose start $E=mc^2$ middle \cite{HIDDEN_KEY} end" + "\n",
    )
    runner = CliRunner()
    result = runner.invoke(cli_main, ["bootstrap", str(tmp_path)])
    assert result.exit_code == 0
    payload = (tmp_path / DEFAULT_OUTPUT_NAME).read_text(encoding="utf-8")
    assert "prose start" in payload
    assert "middle" in payload
    assert "end" in payload
    assert "mc^2" not in payload
    assert "HIDDEN_KEY" not in payload
