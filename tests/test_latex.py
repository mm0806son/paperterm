"""Tests for the LaTeX-aware AST walker (paperterm.latex)."""

from __future__ import annotations

from pathlib import Path

import pytest

from paperterm.glossary import Context
from paperterm.latex import (
    CAPTION_MACROS,
    FIGURE_ENVIRONMENTS,
    MATH_ENVIRONMENTS,
    NON_LINTABLE_ARG_MACROS,
    TABLE_ENVIRONMENTS,
    VERBATIM_ENVIRONMENTS,
    TextSpan,
    iter_spans,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "tex"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _all_text(spans: list[TextSpan]) -> str:
    return "\n".join(s.text for s in spans)


def _by_context(spans: list[TextSpan]) -> dict[Context, list[TextSpan]]:
    out: dict[Context, list[TextSpan]] = {}
    for s in spans:
        out.setdefault(s.context, []).append(s)
    return out


# --------------------------------------------------------------------------- #
# Smoke / basic coverage
# --------------------------------------------------------------------------- #


def test_basic_prose_yields_spans_with_prose_context() -> None:
    spans = list(iter_spans(_load("basic_prose.tex"), file="basic_prose.tex"))
    assert spans, "basic prose must produce at least one span"
    assert all(s.context is Context.PROSE for s in spans)
    assert all(s.file == "basic_prose.tex" for s in spans)
    blob = _all_text(spans)
    assert "PolarityScore" in blob
    assert "GradientBoost" in blob


def test_chars_span_carries_line_range_covering_match() -> None:
    """PolarityScore lives on line 2 of the fixture; the chars span that
    contains it must report a line range whose closed interval includes 2.
    Spans may be wider than a single line because pylatexenc emits one
    chars node per contiguous run of plain text."""
    spans = list(iter_spans(_load("basic_prose.tex")))
    polarity = next(s for s in spans if "PolarityScore" in s.text)
    assert polarity.start_line <= 2 <= polarity.end_line


# --------------------------------------------------------------------------- #
# Skip rules — math / verbatim / cite / comment
# --------------------------------------------------------------------------- #


def test_math_blocks_are_fully_skipped() -> None:
    spans = list(iter_spans(_load("math_skip.tex")))
    blob = _all_text(spans)
    assert "Surrounding prose stays lintable" in blob
    assert "PolarityScore" not in blob  # was inside \begin{equation}
    assert "ForbiddenName" not in blob  # was inside \begin{align*}
    assert "Delta p" not in blob  # was inside inline $...$
    assert "mc^2" not in blob  # was inside \[...\]
    # No spans should claim math context — math blocks emit nothing.
    assert all(s.context is not Context.MATH for s in spans)


def test_verbatim_blocks_emit_nothing() -> None:
    spans = list(iter_spans(_load("verbatim_skip.tex")))
    blob = _all_text(spans)
    assert "ProseTerm" in blob
    assert "ForbiddenName inside verbatim" not in blob
    assert "forbidden_inside_lstlisting" not in blob


def test_cite_ref_label_url_args_are_dropped() -> None:
    spans = list(iter_spans(_load("cite_skip.tex")))
    blob = _all_text(spans)
    assert "LegitMetric" in blob
    for forbidden in (
        "ForbiddenCiteKey2020",
        "ForbiddenLabelKey",
        "ForbiddenInLabel",
        "ForbiddenAutoref",
        "ForbiddenURL",
    ):
        assert forbidden not in blob, f"{forbidden} leaked from a cite/ref/label/url arg"


def test_comments_and_multiline_commented_blocks_are_skipped() -> None:
    spans = list(iter_spans(_load("comment_skip.tex")))
    blob = _all_text(spans)
    assert "ProseAfterComment" in blob
    assert "ForbiddenInComment" not in blob
    assert "ForbiddenInsideCommentedFigure" not in blob, (
        "dogfood findings P2 (multi-line commented figure) regression"
    )


# --------------------------------------------------------------------------- #
# Context tagging — caption / table / figure
# --------------------------------------------------------------------------- #


def test_caption_inside_table_is_tagged_as_caption() -> None:
    spans = list(iter_spans(_load("table_caption.tex")))
    by_ctx = _by_context(spans)
    captions = by_ctx.get(Context.CAPTION, [])
    blob = "\n".join(s.text for s in captions)
    assert "Comparison of MetricA" in blob
    assert "architecture diagram of ModelX" in blob
    # The tabular body should appear under TABLE context (not CAPTION).
    table_blob = "\n".join(s.text for s in by_ctx.get(Context.TABLE, []))
    assert "Variant" in table_blob


def test_figure_env_propagates_figure_context_to_non_caption_chars() -> None:
    src = r"""
\begin{figure}
  Some inline figure caption-less prose.
\end{figure}
""".lstrip()
    spans = list(iter_spans(src))
    figure_spans = [s for s in spans if s.context is Context.FIGURE]
    assert any("inline figure caption-less prose" in s.text for s in figure_spans)


# --------------------------------------------------------------------------- #
# Centralised sets are non-empty (catches accidental refactor mistakes)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "container,member",
    [
        (MATH_ENVIRONMENTS, "equation"),
        (VERBATIM_ENVIRONMENTS, "verbatim"),
        (NON_LINTABLE_ARG_MACROS, "cite"),
        (NON_LINTABLE_ARG_MACROS, "ref"),
        (NON_LINTABLE_ARG_MACROS, "label"),
        (CAPTION_MACROS, "caption"),
        (TABLE_ENVIRONMENTS, "table"),
        (FIGURE_ENVIRONMENTS, "figure"),
    ],
)
def test_centralised_sets_contain_expected_member(container: frozenset[str], member: str) -> None:
    assert member in container
