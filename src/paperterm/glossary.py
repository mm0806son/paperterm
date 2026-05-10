"""Glossary YAML schema and loader (paperterm design doc §5 / §9).

This module defines the pydantic models that describe a paperterm
*glossary* — a set of *concepts* together with their *canonical* form,
*allowed forms*, and disallowed *aliases*. It also implements
``Glossary.from_yaml`` which transparently resolves the optional
``extends:`` chain and merges base glossaries into the calling file
following the algorithm in plan §5.3.

The schema deliberately leaves bootstrap-only fields (``found_forms``,
``confidence``) on the model so that draft glossaries produced by the
LLM bootstrap can round-trip; the linter is responsible for refusing
to run on a draft via :pyattr:`Glossary.is_draft` (see plan §5.2).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

# Allowed ``id`` slug pattern (plan §5.2 Concept table).
_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_ID_MAX_LEN = 30


class Category(str, Enum):
    """Top-level concept categories (plan §5.2)."""

    METRIC = "metric"
    DATASET = "dataset"
    MODEL = "model"
    PIPELINE = "pipeline"
    ABBREV_PAIR = "abbrev_pair"
    OTHER = "other"


class Context(str, Enum):
    """LaTeX context tags relevant to lint decisions (plan §3.4)."""

    PROSE = "prose"
    TABLE = "table"
    FIGURE = "figure"
    CAPTION = "caption"
    MATH = "math"
    VERBATIM = "verbatim"
    COMMENT = "comment"
    CITE_ARG = "cite_arg"


# ``contexts:`` may be either a list of ``Context`` values or the literal
# string ``"any"`` meaning unrestricted. We normalise both to ``None``
# (= unrestricted) at validation time.
_AnyOrContextList = list[Context] | None


class Form(BaseModel):
    """A single textual form (allowed or alias)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    form: str
    contexts: _AnyOrContextList = None
    case_sensitive: bool | None = None
    suggest: str | None = None  # only meaningful for aliases; "canonical" or explicit

    @model_validator(mode="before")
    @classmethod
    def _coerce_any_contexts(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("contexts") == "any":
            data = {**data, "contexts": None}
        return data


class FoundFormLocation(BaseModel):
    """A single occurrence location for a bootstrap-detected form."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    file: str
    line: int = Field(ge=0)


class FoundForm(BaseModel):
    """Bootstrap-only: a form actually observed in the corpus.

    ``count`` must equal ``len(locations)``; enforced here so
    malformed bootstrap drafts surface during loading.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    form: str
    count: int = Field(ge=1)
    locations: list[FoundFormLocation]

    @model_validator(mode="after")
    def _count_matches_locations(self) -> FoundForm:
        if self.count != len(self.locations):
            raise ValueError(
                f"FoundForm count={self.count} != len(locations)={len(self.locations)}"
            )
        return self


_CanonicalStr = Annotated[str, Field(min_length=1)]


class Concept(BaseModel):
    """A single semantic concept and all its known textual forms."""

    model_config = ConfigDict(extra="forbid")

    id: str
    category: Category
    canonical: _CanonicalStr
    case_sensitive: bool | None = None
    whole_word: bool | None = None
    allowed_forms: list[Form] = Field(default_factory=list)
    aliases: list[Form] = Field(default_factory=list)
    notes: str = ""
    # Bootstrap-only fields (plan §5.2). Their presence is the primary
    # draft signal that ``is_draft`` looks at.
    found_forms: list[FoundForm] | None = None
    confidence: float | None = None

    @model_validator(mode="after")
    def _validate_id(self) -> Concept:
        if not _ID_PATTERN.match(self.id):
            raise ValueError(f"Concept id {self.id!r} does not match {_ID_PATTERN.pattern}")
        if len(self.id) > _ID_MAX_LEN:
            raise ValueError(f"Concept id {self.id!r} exceeds {_ID_MAX_LEN} characters")
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Concept {self.id!r} confidence={self.confidence} outside [0, 1]")
        return self

    @property
    def is_draft_marker(self) -> bool:
        """Whether this concept carries any draft-only markers."""
        return self.canonical == "TBD" or bool(self.found_forms)


class Defaults(BaseModel):
    """Glossary-wide default values applied to every concept."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_sensitive: bool = False
    whole_word: bool = True


_VERSION = 1


class Glossary(BaseModel):
    """A paperterm glossary, fully resolved (no ``extends`` left to follow)."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(default=_VERSION)
    defaults: Defaults = Field(default_factory=Defaults)
    concepts: list[Concept] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> Glossary:
        if self.version != _VERSION:
            raise ValueError(f"Unsupported glossary version {self.version} (expected {_VERSION})")
        seen: set[str] = set()
        for concept in self.concepts:
            if concept.id in seen:
                raise ValueError(f"Duplicate concept id {concept.id!r}")
            seen.add(concept.id)
        return self

    @property
    def is_draft(self) -> bool:
        """``True`` iff any concept still carries draft-only markers."""
        return any(c.is_draft_marker for c in self.concepts)

    @classmethod
    def from_yaml(cls, path: str | Path) -> Glossary:
        """Load and fully resolve a glossary file, following ``extends:``."""
        return _load_resolved(Path(path), _CycleGuard())


# --------------------------------------------------------------------------- #
# extends resolution
# --------------------------------------------------------------------------- #


class _CycleGuard:
    """Tracks the chain of resolved files so ``extends:`` cycles are caught."""

    def __init__(self) -> None:
        self._stack: list[Path] = []

    def push(self, path: Path) -> None:
        if path in self._stack:
            chain = " -> ".join(str(p) for p in [*self._stack, path])
            raise ValueError(f"Glossary extends cycle: {chain}")
        self._stack.append(path)

    def pop(self) -> None:
        self._stack.pop()


def _load_raw(path: Path) -> dict[str, Any]:
    """Load raw YAML from a file, normalised to a dict."""
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Glossary {path} must be a YAML mapping at top level")
    return data


_PAPERTERM_URI_PREFIX = "paperterm:base/"


def _builtin_base_dir() -> Path:
    """Return the absolute path to ``paperterm/data/base/`` shipped in this package."""
    return Path(__file__).resolve().parent / "data" / "base"


def _resolve_extends(raw: dict[str, Any], base_path: Path) -> list[Path]:
    """Return the list of absolute paths referenced by ``raw['extends']``.

    Each entry is either a filesystem path (resolved relative to
    ``base_path``'s directory) or a built-in URI of the form
    ``paperterm:base/<file>`` which dispatches to the YAML files
    shipped under :func:`_builtin_base_dir` (plan §9.2).
    """
    extends = raw.get("extends", [])
    if isinstance(extends, str):
        extends = [extends]
    if not isinstance(extends, Iterable) or isinstance(extends, dict):
        raise ValueError(f"{base_path}: 'extends' must be a string or list of strings")
    resolved: list[Path] = []
    for entry in extends:
        if not isinstance(entry, str):
            raise ValueError(f"{base_path}: each 'extends' entry must be a string")
        if entry.startswith(_PAPERTERM_URI_PREFIX):
            relpath = entry[len(_PAPERTERM_URI_PREFIX) :]
            if not relpath or relpath.startswith("/") or ".." in Path(relpath).parts:
                raise ValueError(
                    f"{base_path}: invalid paperterm: URI {entry!r} "
                    "(must be paperterm:base/<file> with no leading '/' and no '..')"
                )
            candidate = (_builtin_base_dir() / relpath).resolve()
        else:
            candidate = (base_path.parent / entry).resolve()
        resolved.append(candidate)
    return resolved


def _load_resolved(path: Path, guard: _CycleGuard) -> Glossary:
    abs_path = path.resolve()
    guard.push(abs_path)
    try:
        raw = _load_raw(abs_path)
        ext_paths = _resolve_extends(raw, abs_path)

        merged_defaults: dict[str, Any] = {}
        merged_concepts: dict[str, dict[str, Any]] = {}

        for ext in ext_paths:
            base_glossary = _load_resolved(ext, guard)
            merged_defaults.update(base_glossary.defaults.model_dump())
            for concept in base_glossary.concepts:
                merged_concepts[concept.id] = concept.model_dump(exclude_none=True)

        # Now layer the current file on top.
        for key in ("extends",):
            raw.pop(key, None)
        if "defaults" in raw:
            if not isinstance(raw["defaults"], dict):
                raise ValueError(f"{abs_path}: 'defaults' must be a mapping")
            merged_defaults.update(raw["defaults"])
        for concept_data in raw.get("concepts", []) or []:
            if not isinstance(concept_data, dict) or "id" not in concept_data:
                raise ValueError(f"{abs_path}: each concept must be a mapping with 'id'")
            merged_concepts[concept_data["id"]] = concept_data

        merged_payload = {
            "version": raw.get("version", _VERSION),
            "defaults": merged_defaults,
            "concepts": list(merged_concepts.values()),
        }
        return Glossary.model_validate(merged_payload)
    finally:
        guard.pop()
