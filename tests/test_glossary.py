"""Tests for ``paperterm.glossary`` (schema-only behaviour, no extends)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from paperterm.glossary import (
    Category,
    Concept,
    Defaults,
    Form,
    FoundForm,
    FoundFormLocation,
    Glossary,
)


def _write(tmp_path: Path, body: str, name: str = "g.yaml") -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


# --------------------------------------------------------------------------- #
# Direct model construction
# --------------------------------------------------------------------------- #


def test_minimal_glossary_loads_empty() -> None:
    g = Glossary.model_validate({"version": 1, "concepts": []})
    assert g.version == 1
    assert g.concepts == []
    assert g.defaults == Defaults()
    assert not g.is_draft


def test_concept_id_must_be_snake_case_slug() -> None:
    with pytest.raises(ValidationError):
        Concept.model_validate({"id": "BadID", "category": "metric", "canonical": "x"})
    with pytest.raises(ValidationError):
        Concept.model_validate({"id": "1leading_digit", "category": "metric", "canonical": "x"})


def test_concept_id_length_capped() -> None:
    with pytest.raises(ValidationError):
        Concept.model_validate({"id": "a" * 31, "category": "metric", "canonical": "x"})


def test_unknown_category_rejected() -> None:
    with pytest.raises(ValidationError):
        Concept.model_validate({"id": "x", "category": "weapon", "canonical": "x"})


def test_canonical_must_be_non_empty() -> None:
    with pytest.raises(ValidationError):
        Concept.model_validate({"id": "x", "category": "metric", "canonical": ""})


def test_form_extra_field_forbidden() -> None:
    with pytest.raises(ValidationError):
        Form.model_validate({"form": "x", "weight": 0.5})


def test_form_contexts_any_normalised_to_none() -> None:
    f = Form.model_validate({"form": "x", "contexts": "any"})
    assert f.contexts is None


def test_found_form_count_must_match_locations() -> None:
    with pytest.raises(ValidationError):
        FoundForm.model_validate(
            {
                "form": "X",
                "count": 2,
                "locations": [{"file": "a.tex", "line": 1}],
            }
        )

    ff = FoundForm.model_validate(
        {
            "form": "X",
            "count": 2,
            "locations": [
                {"file": "a.tex", "line": 1},
                {"file": "a.tex", "line": 9},
            ],
        }
    )
    assert ff.locations[0] == FoundFormLocation(file="a.tex", line=1)


def test_glossary_rejects_duplicate_ids() -> None:
    payload = {
        "version": 1,
        "concepts": [
            {"id": "x", "category": "metric", "canonical": "Foo"},
            {"id": "x", "category": "model", "canonical": "Bar"},
        ],
    }
    with pytest.raises(ValidationError):
        Glossary.model_validate(payload)


def test_unsupported_version_rejected() -> None:
    with pytest.raises(ValidationError):
        Glossary.model_validate({"version": 2, "concepts": []})


# --------------------------------------------------------------------------- #
# Draft markers
# --------------------------------------------------------------------------- #


def test_concept_with_canonical_tbd_is_draft_marker() -> None:
    c = Concept.model_validate({"id": "x", "category": "metric", "canonical": "TBD"})
    assert c.is_draft_marker


def test_concept_with_found_forms_is_draft_marker() -> None:
    c = Concept.model_validate(
        {
            "id": "x",
            "category": "metric",
            "canonical": "Foo",
            "found_forms": [
                {
                    "form": "Foo",
                    "count": 1,
                    "locations": [{"file": "a.tex", "line": 1}],
                }
            ],
            "confidence": 0.9,
        }
    )
    assert c.is_draft_marker


def test_glossary_is_draft_propagates() -> None:
    g = Glossary.model_validate(
        {
            "version": 1,
            "concepts": [
                {"id": "x", "category": "metric", "canonical": "TBD"},
                {"id": "y", "category": "metric", "canonical": "OK"},
            ],
        }
    )
    assert g.is_draft


# --------------------------------------------------------------------------- #
# from_yaml smoke + builtin base
# --------------------------------------------------------------------------- #


def test_from_yaml_loads_minimal_file(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
version: 1
concepts:
  - id: foo
    category: metric
    canonical: Foo
""",
    )
    g = Glossary.from_yaml(p)
    assert [c.id for c in g.concepts] == ["foo"]
    assert g.concepts[0].category is Category.METRIC


def test_from_yaml_rejects_non_mapping(tmp_path: Path) -> None:
    p = _write(tmp_path, "- just a list\n")
    with pytest.raises(ValueError, match="must be a YAML mapping"):
        Glossary.from_yaml(p)


def test_builtin_base_glossaries_load_clean() -> None:
    """Both built-in base files load with sane shape and no draft markers."""
    base = Path(__file__).resolve().parent.parent / "src" / "paperterm" / "data" / "base"
    for name in ("ml-common.yaml", "event-camera.yaml"):
        g = Glossary.from_yaml(base / name)
        assert not g.is_draft
        assert len(g.concepts) >= 5
        for c in g.concepts:
            assert c.canonical and c.canonical != "TBD"
