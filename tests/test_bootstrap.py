"""Tests for ``paperterm.bootstrap`` (manual mode prompt+corpus assembly)."""

from __future__ import annotations

from pathlib import Path

import pytest

from paperterm.bootstrap import (
    CORPUS_CLOSE,
    CORPUS_OPEN,
    DEFAULT_OUTPUT_NAME,
    build_prompt_file,
)
from paperterm.prompts import BOOTSTRAP_PROMPT


def _write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_default_output_path_is_under_paper_dir(tmp_path: Path) -> None:
    _write(tmp_path / "section.tex", "Hello World.\n")
    result = build_prompt_file(tmp_path)
    assert result.output_path == (tmp_path / DEFAULT_OUTPUT_NAME).resolve()
    assert result.output_path.is_file()


def test_payload_starts_with_full_prompt(tmp_path: Path) -> None:
    _write(tmp_path / "section.tex", "Hello World.\n")
    out = build_prompt_file(tmp_path).output_path.read_text(encoding="utf-8")
    assert out.startswith(BOOTSTRAP_PROMPT.rstrip("\n") + "\n")


def test_payload_contains_corpus_markers_and_file_header(tmp_path: Path) -> None:
    _write(tmp_path / "section.tex", "Hello World.\n")
    out = build_prompt_file(tmp_path).output_path.read_text(encoding="utf-8")
    assert CORPUS_OPEN in out
    assert CORPUS_CLOSE in out
    assert "=== FILE: section.tex ===" in out


def test_each_kept_line_is_prefixed_with_absolute_line_number(tmp_path: Path) -> None:
    _write(
        tmp_path / "section.tex",
        "First line of prose.\nSecond line of prose.\nThird line of prose.\n",
    )
    out = build_prompt_file(tmp_path).output_path.read_text(encoding="utf-8")
    assert "1: First line of prose." in out
    assert "2: Second line of prose." in out
    assert "3: Third line of prose." in out


def test_math_and_comment_lines_are_dropped_from_corpus(tmp_path: Path) -> None:
    _write(
        tmp_path / "section.tex",
        "Real prose A.\n% commented line that must not leak\n$E = mc^2$\nReal prose B.\n",
    )
    out = build_prompt_file(tmp_path).output_path.read_text(encoding="utf-8")
    assert "Real prose A." in out
    assert "Real prose B." in out
    assert "commented line" not in out
    # The math-only line might or might not appear depending on whether the
    # walker treats the whole line as math-only; at minimum its content
    # ($E = mc^2$) must not surface as a span.
    assert "mc^2" not in out


def test_files_with_no_lintable_content_are_skipped(tmp_path: Path) -> None:
    _write(tmp_path / "comments_only.tex", "% nothing real\n% just comments\n")
    _write(tmp_path / "with_prose.tex", "Real content here.\n")
    out = build_prompt_file(tmp_path).output_path.read_text(encoding="utf-8")
    assert "=== FILE: comments_only.tex ===" not in out
    assert "=== FILE: with_prose.tex ===" in out
    assert "Real content here." in out


def test_include_and_exclude_globs_are_respected(tmp_path: Path) -> None:
    _write(tmp_path / "main.tex", "Main prose.\n")
    _write(tmp_path / "build" / "draft.tex", "build draft prose.\n")
    _write(tmp_path / "appendix.tex", "Appendix prose.\n")
    out = build_prompt_file(
        tmp_path,
        include_globs=("**/*.tex",),
        exclude_globs=("**/build/**", "appendix.tex"),
    ).output_path.read_text(encoding="utf-8")
    assert "Main prose." in out
    assert "build draft prose." not in out
    assert "Appendix prose." not in out


def test_explicit_output_path_overrides_default(tmp_path: Path) -> None:
    _write(tmp_path / "section.tex", "Hi.\n")
    explicit = tmp_path / "out" / "custom.txt"
    result = build_prompt_file(tmp_path, output_path=explicit)
    assert result.output_path == explicit.resolve()
    assert explicit.is_file()
    assert not (tmp_path / DEFAULT_OUTPUT_NAME).exists()


def test_paper_dir_must_be_an_existing_directory(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist"
    with pytest.raises(ValueError, match="must be an existing directory"):
        build_prompt_file(missing)


# --------------------------------------------------------------------------- #
# AST-cleaned: same-line skipped material must not leak through.
# --------------------------------------------------------------------------- #


def test_inline_math_in_a_prose_line_is_dropped(tmp_path: Path) -> None:
    _write(tmp_path / "section.tex", "before $E = mc^2$ after\n")
    out = build_prompt_file(tmp_path).output_path.read_text(encoding="utf-8")
    assert "before" in out
    assert "after" in out
    assert "mc^2" not in out  # math span peeled by walker, must not reappear


def test_inline_cite_arg_in_a_prose_line_is_dropped(tmp_path: Path) -> None:
    _write(tmp_path / "section.tex", r"see \cite{SECRET_KEY} for details" + "\n")
    out = build_prompt_file(tmp_path).output_path.read_text(encoding="utf-8")
    assert "see" in out
    assert "for details" in out
    assert "SECRET_KEY" not in out


def test_trailing_comment_on_a_prose_line_is_dropped(tmp_path: Path) -> None:
    _write(tmp_path / "section.tex", "real prose body % HIDDEN_AUTHOR_NOTE\n")
    out = build_prompt_file(tmp_path).output_path.read_text(encoding="utf-8")
    assert "real prose body" in out
    assert "HIDDEN_AUTHOR_NOTE" not in out
