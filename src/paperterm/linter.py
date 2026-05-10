"""Rule matcher: turn (Glossary, list[TextSpan]) into a list of Violations.

This is the heart of ``paperterm check``. It takes a fully resolved
glossary (no draft markers; the caller is expected to refuse drafts via
:pyattr:`paperterm.glossary.Glossary.is_draft`) and a stream of LaTeX
:class:`TextSpan` records produced by :mod:`paperterm.latex`, and emits
one :class:`Violation` per occurrence of an alias form in a context the
form is not allowed in.

Allowed forms add positive-list entries that prevent matches; aliases
add negative-list entries that produce violations. Plain canonical
strings are *also* treated as allowed forms automatically — the user
never has to repeat the canonical inside ``allowed_forms``.

Matching is regex-based with optional word-boundary and
case-sensitivity controls; the per-form / per-concept / per-glossary
defaults flow downwards (``form.case_sensitive ?? concept.case_sensitive
?? defaults.case_sensitive``).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Final

from .glossary import Concept, Context, Form, Glossary
from .latex import TextSpan

# A "literal" form is *not* a regex unless it begins with this prefix
# (plan §5.2 Form table); we strip the prefix and use the rest verbatim
# as a regex source.
_REGEX_PREFIX: Final[str] = "regex:"


@dataclass(frozen=True)
class Violation:
    """A single offending occurrence detected in the corpus."""

    file: str
    line: int  # 1-based; the start_line of the chars span
    end_line: int
    column: int  # 1-based offset inside the chars span (best-effort)
    matched_text: str
    concept_id: str
    canonical: str
    suggestion: str  # what to replace ``matched_text`` with
    rule: str  # explanatory tag, e.g. "alias forbidden"
    context: Context


@dataclass(frozen=True)
class _CompiledForm:
    """A regex-compiled view of a form, plus the bookkeeping the matcher needs."""

    pattern: re.Pattern[str]
    raw_form: str
    contexts: frozenset[Context] | None  # None = any
    concept: Concept


class Linter:
    """Compile a glossary into a regex matcher and run it over text spans."""

    def __init__(self, glossary: Glossary) -> None:
        if glossary.is_draft:
            raise ValueError(
                "paperterm linter refuses draft glossaries; please review "
                "the bootstrap output (drop found_forms / pick a canonical) "
                "before running check"
            )
        self._glossary = glossary
        self._allowed: list[_CompiledForm] = []
        self._aliases: list[_CompiledForm] = []
        for concept in glossary.concepts:
            self._compile_concept(concept)

    # ----- compilation --------------------------------------------------- #

    def _compile_concept(self, concept: Concept) -> None:
        case_sensitive = self._concept_case_sensitive(concept)
        whole_word = self._concept_whole_word(concept)

        # The canonical name is implicitly an allowed form.
        canonical_form = Form(form=concept.canonical)
        self._allowed.append(_compile_form(canonical_form, concept, case_sensitive, whole_word))
        for f in concept.allowed_forms:
            self._allowed.append(_compile_form(f, concept, case_sensitive, whole_word))
        for f in concept.aliases:
            self._aliases.append(_compile_form(f, concept, case_sensitive, whole_word))

    def _concept_case_sensitive(self, concept: Concept) -> bool:
        if concept.case_sensitive is not None:
            return concept.case_sensitive
        return self._glossary.defaults.case_sensitive

    def _concept_whole_word(self, concept: Concept) -> bool:
        if concept.whole_word is not None:
            return concept.whole_word
        return self._glossary.defaults.whole_word

    # ----- matching ------------------------------------------------------ #

    def check_spans(self, spans: Iterable[TextSpan]) -> Iterator[Violation]:
        """Yield one :class:`Violation` per alias hit in a non-allowed context."""
        for span in spans:
            yield from self._check_span(span)

    def _check_span(self, span: TextSpan) -> Iterator[Violation]:
        for compiled in self._aliases:
            if not _context_allows(compiled.contexts, span.context):
                continue
            for hit in compiled.pattern.finditer(span.text):
                if _is_inside_allowed_form(hit, span, self._allowed):
                    continue
                concept = compiled.concept
                suggestion = _resolve_suggestion(compiled, concept)
                yield Violation(
                    file=span.file,
                    line=_line_for_offset(span, hit.start()),
                    end_line=_line_for_offset(span, hit.end() - 1),
                    column=_column_for_offset(span, hit.start()),
                    matched_text=hit.group(0),
                    concept_id=concept.id,
                    canonical=concept.canonical,
                    suggestion=suggestion,
                    rule="alias forbidden",
                    context=span.context,
                )


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _compile_form(
    form: Form,
    concept: Concept,
    concept_case_sensitive: bool,
    concept_whole_word: bool,
) -> _CompiledForm:
    case_sensitive = (
        form.case_sensitive if form.case_sensitive is not None else concept_case_sensitive
    )
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern_src = _form_to_pattern_source(form.form, concept_whole_word)
    return _CompiledForm(
        pattern=re.compile(pattern_src, flags),
        raw_form=form.form,
        contexts=_normalise_contexts(form),
        concept=concept,
    )


def _form_to_pattern_source(literal_or_regex: str, whole_word: bool) -> str:
    if literal_or_regex.startswith(_REGEX_PREFIX):
        return literal_or_regex[len(_REGEX_PREFIX) :]
    escaped = re.escape(literal_or_regex)
    if (
        whole_word
        and _ends_with_word_char(literal_or_regex)
        and _starts_with_word_char(literal_or_regex)
    ):
        return rf"\b{escaped}\b"
    return escaped


def _starts_with_word_char(s: str) -> bool:
    return bool(s) and bool(re.match(r"\w", s))


def _ends_with_word_char(s: str) -> bool:
    return bool(s) and bool(re.search(r"\w$", s))


def _normalise_contexts(form: Form) -> frozenset[Context] | None:
    if form.contexts is None:
        return None
    return frozenset(form.contexts)


def _context_allows(
    allowed: frozenset[Context] | None,
    actual: Context,
) -> bool:
    """Aliases run regardless of the form's ``contexts:`` field — *aliases
    are always forbidden* (plan §3.4 last paragraph). The ``contexts:``
    field on aliases is therefore ignored at matching time and we always
    return True here. The same helper is used by allowed-form lookups
    (see ``_is_inside_allowed_form``) where ``contexts:`` *does* matter."""
    del allowed
    del actual
    return True


def _is_inside_allowed_form(
    alias_hit: re.Match[str],
    span: TextSpan,
    allowed: list[_CompiledForm],
) -> bool:
    """Return True if the alias hit fully overlaps with an allowed form
    that *is* permitted in this span's context."""
    for af in allowed:
        if af.contexts is not None and span.context not in af.contexts:
            continue
        for af_hit in af.pattern.finditer(span.text):
            if af_hit.start() <= alias_hit.start() and af_hit.end() >= alias_hit.end():
                return True
    return False


def _resolve_suggestion(compiled: _CompiledForm, concept: Concept) -> str:
    # Locate the original Form object so we can read ``.suggest``.
    for f in concept.aliases:
        if f.form == compiled.raw_form:
            if f.suggest and f.suggest != "canonical":
                return f.suggest
            return concept.canonical
    return concept.canonical


def _line_for_offset(span: TextSpan, offset: int) -> int:
    """Map a character offset *inside the span* to an absolute line number."""
    nl_count = span.text[:offset].count("\n")
    return span.start_line + nl_count


def _column_for_offset(span: TextSpan, offset: int) -> int:
    """1-based column inside the line that contains ``offset``."""
    last_nl = span.text.rfind("\n", 0, offset)
    return offset - last_nl  # already 1-based: if no \n, last_nl=-1
