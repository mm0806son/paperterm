"""Tests for ``paperterm.prompts.BOOTSTRAP_PROMPT``.

These tests pin the *content* of the prompt — anchors that any future
edit must keep. Byte-equality with the checked-in
``prompts/glossary_bootstrap.md`` is enforced separately in the
P5.D-introduced ``test_checked_in_prompt_matches_module``.
"""

from __future__ import annotations

import re

import pytest

from paperterm.prompts import BOOTSTRAP_PROMPT

# --------------------------------------------------------------------------- #
# Anchor presence — the prompt must keep the structural sections that the
# rest of paperterm (and the user-facing instructions) refer to.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "anchor",
    [
        "## Role",
        "## Task",
        "## Skip rules",
        "## YAML schema",
        "## Worked examples",
        "## Output rules",
        "## Corpus",
        "## Chunked input mode",
        "=== BEGIN CORPUS ===",
        "=== END CORPUS ===",
        "=== CHUNK BREAK ===",
        "version: 1",
        "found_forms",
        "canonical",
    ],
)
def test_bootstrap_prompt_contains_anchor(anchor: str) -> None:
    assert anchor in BOOTSTRAP_PROMPT, f"prompt is missing required anchor {anchor!r}"


# --------------------------------------------------------------------------- #
# Anti-pollution — worked examples must not name any concept the dogfood
# corpus (Raw2Event paper) actually uses, otherwise users running the
# prompt against that paper would see seeded matches that look like real
# detections.
# --------------------------------------------------------------------------- #


_FORBIDDEN_KEYWORDS = (
    r"polarity deviation",
    r"per-pixel emd",
    r"davis346",
    r"raw2event",
    r"dvs[- ]?voltmeter",
    r"qkformer",
)


@pytest.mark.parametrize("keyword", _FORBIDDEN_KEYWORDS)
def test_bootstrap_prompt_has_no_dogfood_pollution(keyword: str) -> None:
    assert not re.search(keyword, BOOTSTRAP_PROMPT, re.IGNORECASE), (
        f"prompt contains dogfood-corpus keyword {keyword!r}; worked "
        "examples must use synthetic concepts only"
    )


# --------------------------------------------------------------------------- #
# Schema-field invariants — the prompt must not authorise any output
# field/structure that the paperterm linter then rejects.
# --------------------------------------------------------------------------- #


def test_bootstrap_prompt_does_not_introduce_top_level_bootstrap_field() -> None:
    """The draft schema is plan §5; there is no top-level ``bootstrap``
    field. plan §5.2 says draft is detected by ``canonical: TBD`` or
    presence of ``found_forms``."""
    assert not re.search(r"^\s*bootstrap:\s*", BOOTSTRAP_PROMPT, re.MULTILINE)


def test_bootstrap_prompt_does_not_use_suggested_canonical_field() -> None:
    """plan §5 schema field is named ``canonical``; some early prompt
    drafts called it ``suggested_canonical``, which the linter does
    not understand."""
    assert "suggested_canonical" not in BOOTSTRAP_PROMPT


# --------------------------------------------------------------------------- #
# Sanity — non-trivial size, no obvious placeholders left.
# --------------------------------------------------------------------------- #


def test_bootstrap_prompt_size_is_reasonable() -> None:
    line_count = BOOTSTRAP_PROMPT.count("\n") + 1
    assert 200 <= line_count <= 600, (
        f"prompt has {line_count} lines, outside the [200, 600] sanity range"
    )


def test_bootstrap_prompt_has_no_unfilled_placeholders() -> None:
    assert "{{" not in BOOTSTRAP_PROMPT, "found unresolved {{...}} placeholder"
    assert "TODO" not in BOOTSTRAP_PROMPT


# --------------------------------------------------------------------------- #
# Single-source-of-truth — the checked-in prompts/glossary_bootstrap.md
# (shipped at the repo root so users can read it on GitHub without
# installing paperterm) must be byte-equal to BOOTSTRAP_PROMPT.
# --------------------------------------------------------------------------- #


def test_checked_in_prompt_matches_module() -> None:
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    checked_in = repo_root / "prompts" / "glossary_bootstrap.md"
    assert checked_in.is_file(), (
        "prompts/glossary_bootstrap.md is missing; regenerate with "
        "`paperterm print-prompt > prompts/glossary_bootstrap.md`"
    )
    assert checked_in.read_text(encoding="utf-8") == BOOTSTRAP_PROMPT, (
        "prompts/glossary_bootstrap.md is out of sync with BOOTSTRAP_PROMPT; "
        "regenerate with `paperterm print-prompt > prompts/glossary_bootstrap.md`"
    )
