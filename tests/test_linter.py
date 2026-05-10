"""Tests for paperterm.linter (rule matcher) and the CLI ``check`` glue."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from click.testing import CliRunner

from paperterm.cli import main as cli_main
from paperterm.glossary import Concept, Context, Form, Glossary
from paperterm.latex import TextSpan, iter_spans
from paperterm.linter import Linter


def _glossary(*concepts: Concept) -> Glossary:
    return Glossary.model_validate(
        {
            "version": 1,
            "concepts": [c.model_dump(exclude_none=True) for c in concepts],
        }
    )


def _spans(src: str, file: str = "x.tex") -> list[TextSpan]:
    return list(iter_spans(src, file=file))


# --------------------------------------------------------------------------- #
# core matcher
# --------------------------------------------------------------------------- #


def test_alias_in_prose_yields_violation() -> None:
    g = _glossary(
        Concept.model_validate(
            {
                "id": "f1",
                "category": "metric",
                "canonical": "F1 score",
                "aliases": [Form(form="F-1 score").model_dump()],
            }
        )
    )
    spans = _spans("We report F-1 score in Table 1.")
    vs = list(Linter(g).check_spans(spans))
    assert [v.matched_text for v in vs] == ["F-1 score"]
    assert vs[0].suggestion == "F1 score"
    assert vs[0].context is Context.PROSE
    assert vs[0].rule == "alias forbidden"


def test_canonical_form_does_not_violate() -> None:
    g = _glossary(
        Concept.model_validate(
            {
                "id": "f1",
                "category": "metric",
                "canonical": "F1 score",
                "aliases": [Form(form="F-1 score").model_dump()],
            }
        )
    )
    spans = _spans("We report F1 score in Table 1.")
    vs = list(Linter(g).check_spans(spans))
    assert vs == []


def test_alias_inside_math_block_is_ignored() -> None:
    g = _glossary(
        Concept.model_validate(
            {
                "id": "metric_a",
                "category": "metric",
                "canonical": "MetricA",
                "aliases": [Form(form="metricA").model_dump()],
            }
        )
    )
    src = "Pre $metricA = 0.5$ post."
    spans = _spans(src)
    vs = list(Linter(g).check_spans(spans))
    assert vs == []  # math block is opaque to the walker


def test_alias_inside_cite_arg_is_ignored() -> None:
    g = _glossary(
        Concept.model_validate(
            {
                "id": "f1",
                "category": "metric",
                "canonical": "F1 score",
                "aliases": [Form(form="F-1 score").model_dump()],
            }
        )
    )
    spans = _spans(r"See \cite{F-1 score} as a counter-example.")
    vs = list(Linter(g).check_spans(spans))
    assert vs == []


def test_explicit_suggest_overrides_canonical() -> None:
    g = _glossary(
        Concept.model_validate(
            {
                "id": "map_score",
                "category": "metric",
                "canonical": "mAP",
                "aliases": [
                    Form.model_validate({"form": "weighted mAP", "suggest": "mAP"}).model_dump(),
                    Form.model_validate({"form": "macro mAP"}).model_dump(),
                ],
            }
        )
    )
    spans = _spans("We report weighted mAP and the macro mAP across all variants.")
    vs = list(Linter(g).check_spans(spans))
    suggestions = {v.matched_text: v.suggestion for v in vs}
    assert suggestions == {
        "weighted mAP": "mAP",
        "macro mAP": "mAP",
    }


def test_case_sensitive_concept_distinguishes_case() -> None:
    g = _glossary(
        Concept.model_validate(
            {
                "id": "mscoco",
                "category": "dataset",
                "canonical": "MS-COCO",
                "case_sensitive": True,
                "aliases": [Form(form="Ms-Coco").model_dump()],
            }
        )
    )
    src = "Ms-Coco is wrong; MS-COCO is fine; ms-coco is unrelated."
    spans = _spans(src)
    vs = list(Linter(g).check_spans(spans))
    assert [v.matched_text for v in vs] == ["Ms-Coco"]


def test_whole_word_default_avoids_substring_matches() -> None:
    g = _glossary(
        Concept.model_validate(
            {
                "id": "rate",
                "category": "metric",
                "canonical": "learning rate",
                "aliases": [Form(form="lr").model_dump()],
            }
        )
    )
    # "lrx" should NOT match because whole_word=True is the default.
    spans = _spans("We tune lr; we also tune lrx.")
    vs = list(Linter(g).check_spans(spans))
    assert [v.matched_text for v in vs] == ["lr"]


def test_regex_form_supported() -> None:
    g = _glossary(
        Concept.model_validate(
            {
                "id": "ms",
                "category": "metric",
                "canonical": "millisecond",
                "aliases": [Form(form="regex:\\b\\d+ms\\b").model_dump()],
            }
        )
    )
    spans = _spans("Latency is 12ms in this run.")
    vs = list(Linter(g).check_spans(spans))
    assert [v.matched_text for v in vs] == ["12ms"]


def test_linter_refuses_draft_glossary() -> None:
    draft = Glossary.model_validate(
        {
            "version": 1,
            "concepts": [{"id": "x", "category": "metric", "canonical": "TBD"}],
        }
    )
    with pytest.raises(ValueError, match="refuses draft"):
        Linter(draft)


def test_violation_line_offset_inside_multi_line_chars() -> None:
    g = _glossary(
        Concept.model_validate(
            {
                "id": "foo",
                "category": "metric",
                "canonical": "Foo",
                "aliases": [Form(form="Bar").model_dump()],
            }
        )
    )
    src = dedent(
        """\
        first line is harmless prose
        second line mentions Bar here
        third line is harmless again
        """
    )
    spans = _spans(src, file="paper.tex")
    vs = list(Linter(g).check_spans(spans))
    assert len(vs) == 1
    v = vs[0]
    assert v.file == "paper.tex"
    assert v.line == 2  # absolute line in the source
    assert "second" not in v.matched_text


# --------------------------------------------------------------------------- #
# CLI integration
# --------------------------------------------------------------------------- #


def _make_paper(tmp_path: Path, glossary: str, sections: dict[str, str]) -> Path:
    (tmp_path / "glossary.yaml").write_text(glossary, encoding="utf-8")
    for name, body in sections.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return tmp_path


def test_check_subcommand_exit_code_one_on_violations(tmp_path: Path) -> None:
    paper = _make_paper(
        tmp_path,
        glossary=dedent(
            """\
            version: 1
            concepts:
              - id: f1
                category: metric
                canonical: "F1 score"
                aliases:
                  - form: "F-1 score"
            """
        ),
        sections={"section.tex": "We report F-1 score in Table 1.\n"},
    )
    runner = CliRunner()
    result = runner.invoke(cli_main, ["check", str(paper)])
    assert result.exit_code == 1
    assert "F-1 score" in result.output
    assert "F1 score" in result.output  # suggestion
    assert "1 violation" in result.output


def test_check_subcommand_exit_code_zero_when_clean(tmp_path: Path) -> None:
    paper = _make_paper(
        tmp_path,
        glossary=dedent(
            """\
            version: 1
            concepts:
              - id: f1
                category: metric
                canonical: "F1 score"
                aliases:
                  - form: "F-1 score"
            """
        ),
        sections={"section.tex": "We report F1 score in Table 1.\n"},
    )
    runner = CliRunner()
    result = runner.invoke(cli_main, ["check", str(paper)])
    assert result.exit_code == 0
    assert "no violations" in result.output


def test_check_subcommand_exit_code_two_on_draft(tmp_path: Path) -> None:
    paper = _make_paper(
        tmp_path,
        glossary=dedent(
            """\
            version: 1
            concepts:
              - id: f1
                category: metric
                canonical: TBD
                aliases:
                  - form: "F-1 score"
            """
        ),
        sections={"section.tex": "anything\n"},
    )
    runner = CliRunner()
    result = runner.invoke(cli_main, ["check", str(paper)])
    assert result.exit_code == 2
    assert "bootstrap draft" in result.output


def test_check_subcommand_exit_code_two_on_missing_glossary(tmp_path: Path) -> None:
    runner = CliRunner()
    (tmp_path / "section.tex").write_text("anything\n", encoding="utf-8")
    result = runner.invoke(cli_main, ["check", str(tmp_path)])
    assert result.exit_code == 2
    assert "glossary file not found" in result.output
