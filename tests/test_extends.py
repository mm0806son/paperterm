"""Tests for ``Glossary.from_yaml`` extends-resolution machinery."""

from __future__ import annotations

from pathlib import Path

import pytest

from paperterm.glossary import Glossary


def _write(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_single_extends_merges_concepts(tmp_path: Path) -> None:
    base = _write(
        tmp_path / "base.yaml",
        """
version: 1
concepts:
  - id: shared
    category: metric
    canonical: Shared
  - id: from_base_only
    category: model
    canonical: BaseOnly
""",
    )
    leaf = _write(
        tmp_path / "leaf.yaml",
        """
version: 1
extends:
  - base.yaml
concepts:
  - id: from_leaf
    category: dataset
    canonical: LeafOnly
""",
    )
    g = Glossary.from_yaml(leaf)
    ids = {c.id for c in g.concepts}
    assert ids == {"shared", "from_base_only", "from_leaf"}
    # The base file lives in the same dir as `leaf.yaml`.
    assert base.exists()


def test_same_id_in_leaf_completely_replaces_base(tmp_path: Path) -> None:
    _write(
        tmp_path / "base.yaml",
        """
version: 1
concepts:
  - id: shared
    category: metric
    canonical: BaseCanonical
    aliases:
      - form: Old
""",
    )
    leaf = _write(
        tmp_path / "leaf.yaml",
        """
version: 1
extends:
  - base.yaml
concepts:
  - id: shared
    category: metric
    canonical: LeafCanonical
""",
    )
    g = Glossary.from_yaml(leaf)
    assert len(g.concepts) == 1
    c = g.concepts[0]
    assert c.canonical == "LeafCanonical"
    # Plan §9.3: same id is *full replacement* — the base aliases must NOT carry over.
    assert c.aliases == []


def test_chain_extends_three_levels(tmp_path: Path) -> None:
    _write(
        tmp_path / "a.yaml",
        """
version: 1
concepts:
  - id: a_only
    category: metric
    canonical: A
""",
    )
    _write(
        tmp_path / "b.yaml",
        """
version: 1
extends:
  - a.yaml
concepts:
  - id: b_only
    category: metric
    canonical: B
""",
    )
    leaf = _write(
        tmp_path / "c.yaml",
        """
version: 1
extends:
  - b.yaml
concepts:
  - id: c_only
    category: metric
    canonical: C
""",
    )
    g = Glossary.from_yaml(leaf)
    assert sorted(c.id for c in g.concepts) == ["a_only", "b_only", "c_only"]


def test_cycle_detection(tmp_path: Path) -> None:
    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"
    _write(
        a,
        """
version: 1
extends:
  - b.yaml
concepts: []
""",
    )
    _write(
        b,
        """
version: 1
extends:
  - a.yaml
concepts: []
""",
    )
    with pytest.raises(ValueError, match="extends cycle"):
        Glossary.from_yaml(a)


def test_extends_string_form_accepted(tmp_path: Path) -> None:
    """`extends: <single-string>` should be treated as a one-element list."""
    _write(
        tmp_path / "base.yaml",
        """
version: 1
concepts:
  - id: only
    category: metric
    canonical: Only
""",
    )
    leaf = _write(
        tmp_path / "leaf.yaml",
        """
version: 1
extends: base.yaml
concepts: []
""",
    )
    g = Glossary.from_yaml(leaf)
    assert [c.id for c in g.concepts] == ["only"]


def test_paperterm_uri_resolves_to_builtin_base(tmp_path: Path) -> None:
    leaf = _write(
        tmp_path / "leaf.yaml",
        """
version: 1
extends:
  - paperterm:base/ml-common.yaml
concepts: []
""",
    )
    g = Glossary.from_yaml(leaf)
    ids = {c.id for c in g.concepts}
    assert {"f1_score", "accuracy"} <= ids


def test_paperterm_uri_rejects_traversal(tmp_path: Path) -> None:
    leaf = _write(
        tmp_path / "leaf.yaml",
        """
version: 1
extends:
  - paperterm:base/../../etc/passwd
concepts: []
""",
    )
    with pytest.raises(ValueError, match="invalid paperterm: URI"):
        Glossary.from_yaml(leaf)


def test_extends_non_string_entry_rejected(tmp_path: Path) -> None:
    leaf = _write(
        tmp_path / "leaf.yaml",
        """
version: 1
extends:
  - {not: "a string"}
concepts: []
""",
    )
    with pytest.raises(ValueError, match="each 'extends' entry must be a string"):
        Glossary.from_yaml(leaf)


def test_defaults_override_chain(tmp_path: Path) -> None:
    _write(
        tmp_path / "base.yaml",
        """
version: 1
defaults:
  case_sensitive: true
  whole_word: false
concepts: []
""",
    )
    leaf = _write(
        tmp_path / "leaf.yaml",
        """
version: 1
extends:
  - base.yaml
defaults:
  case_sensitive: false
concepts: []
""",
    )
    g = Glossary.from_yaml(leaf)
    # leaf flips case_sensitive back to false, but inherits whole_word=false from base.
    assert g.defaults.case_sensitive is False
    assert g.defaults.whole_word is False
