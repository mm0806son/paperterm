"""LaTeX-aware AST walker — yields lintable text spans tagged by context.

This is the engine that lets paperterm avoid the false positives that
trip up word-level prose linters: it walks the LaTeX AST produced by
pylatexenc, ignores the contexts where matching is meaningless
(comments, math, verbatim, citation arguments, labels, refs, URLs),
and tags every emitted text span with one of the lintable contexts
from plan §3.4 (``prose`` / ``caption`` / ``table`` / ``figure``).

The walker is intentionally pure: it consumes a raw .tex source
string and yields :class:`TextSpan` records — it does not touch the
filesystem nor cross file boundaries (``\input{}`` is *not* expanded
in v0.1; callers iterate file by file).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from pylatexenc.latexwalker import (
    LatexCharsNode,
    LatexCommentNode,
    LatexEnvironmentNode,
    LatexGroupNode,
    LatexMacroNode,
    LatexMathNode,
    LatexNode,
    LatexSpecialsNode,
    LatexWalker,
    get_default_latex_context_db,
)
from pylatexenc.macrospec import MacroSpec

from .glossary import Context

# --------------------------------------------------------------------------- #
# Sets that drive the context decisions. Centralised so that future
# refinements (more cite-like macros etc.) only need to touch one place.
# --------------------------------------------------------------------------- #

#: Math environments — entire body is skipped (returns no spans).
MATH_ENVIRONMENTS: frozenset[str] = frozenset(
    {
        "equation",
        "equation*",
        "align",
        "align*",
        "eqnarray",
        "eqnarray*",
        "multline",
        "multline*",
        "gather",
        "gather*",
        "displaymath",
        "math",
    }
)

#: Verbatim-like environments — entire body is skipped.
VERBATIM_ENVIRONMENTS: frozenset[str] = frozenset(
    {"verbatim", "verbatim*", "lstlisting", "minted", "listing", "Verbatim"}
)

#: Macros whose argument(s) are *labels / cite keys / URLs / file paths*
#: and therefore must not contribute lintable text. Star variants are
#: handled by stripping a trailing ``*``.
NON_LINTABLE_ARG_MACROS: frozenset[str] = frozenset(
    {
        # citations
        "cite",
        "citep",
        "citet",
        "citealt",
        "citealp",
        "citeauthor",
        "citeyear",
        "citeyearpar",
        # cross references
        "ref",
        "eqref",
        "autoref",
        "cref",
        "Cref",
        "pageref",
        "label",
        # urls / file paths
        "url",
        "href",
        "input",
        "include",
        "includegraphics",
        # bibliographic keys
        "bibitem",
    }
)

#: Macros whose first mandatory argument *is* prose-like content tagged
#: as :class:`Context.CAPTION`.
CAPTION_MACROS: frozenset[str] = frozenset({"caption", "subcaption"})

#: Environments that flip the surrounding context (lintable, but the
#: caller may choose to allow extra forms here — see plan §3.4).
TABLE_ENVIRONMENTS: frozenset[str] = frozenset(
    {"table", "table*", "tabular", "tabular*", "tabularx", "longtable"}
)

FIGURE_ENVIRONMENTS: frozenset[str] = frozenset({"figure", "figure*", "subfigure", "wrapfigure"})


# --------------------------------------------------------------------------- #
# Public data type
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class TextSpan:
    """A contiguous run of raw LaTeX characters worth showing the matcher."""

    text: str
    file: str
    start_line: int  # 1-based, inclusive
    end_line: int  # 1-based, inclusive
    context: Context


# --------------------------------------------------------------------------- #
# Walker
# --------------------------------------------------------------------------- #


def _build_latex_context() -> object:
    """Augment the default pylatexenc macro DB with paperterm-specific
    macros whose argument structure isn't part of the bundled spec but
    matters for context tagging (e.g. ``\\caption{...}``)."""
    ctx = get_default_latex_context_db()
    ctx.add_context_category(
        "paperterm-extras",
        prepend=True,
        macros=[
            MacroSpec("caption", "{"),
            MacroSpec("subcaption", "{"),
        ],
    )
    return ctx


_LATEX_CONTEXT = _build_latex_context()


def iter_spans(source: str, *, file: str = "<input>") -> Iterator[TextSpan]:
    """Walk a LaTeX source string and yield one :class:`TextSpan` per
    contiguous prose-like chars node, tagged by context.

    Args:
        source: raw .tex contents (already decoded as UTF-8).
        file:   identifier carried into each span's ``file`` attribute;
                callers usually pass the relative path of the source file.
    """
    line_starts = _line_starts(source)
    walker = LatexWalker(source, latex_context=_LATEX_CONTEXT)
    nodes, _, _ = walker.get_latex_nodes()
    yield from _walk(nodes, source, line_starts, file, Context.PROSE)


def _walk(
    nodes: list[LatexNode],
    source: str,
    line_starts: list[int],
    file: str,
    context: Context,
) -> Iterator[TextSpan]:
    for node in nodes:
        if node is None:
            continue
        yield from _visit(node, source, line_starts, file, context)


def _visit(
    node: LatexNode,
    source: str,
    line_starts: list[int],
    file: str,
    context: Context,
) -> Iterator[TextSpan]:
    if isinstance(node, LatexCommentNode):
        # comments never reach the matcher
        return

    if isinstance(node, LatexMathNode):
        # entire math span (inline or display) is opaque to paperterm
        return

    if isinstance(node, LatexCharsNode):
        chars = node.chars
        if chars and chars.strip():
            start_line, end_line = _line_range(node.pos, len(chars), line_starts)
            yield TextSpan(
                text=chars,
                file=file,
                start_line=start_line,
                end_line=end_line,
                context=context,
            )
        return

    if isinstance(node, LatexGroupNode):
        # plain { ... } group — recurse without changing context
        yield from _walk(node.nodelist or [], source, line_starts, file, context)
        return

    if isinstance(node, LatexEnvironmentNode):
        env = (node.environmentname or "").strip()
        if env in MATH_ENVIRONMENTS:
            return
        if env in VERBATIM_ENVIRONMENTS:
            return
        if env in TABLE_ENVIRONMENTS:
            inner_context = Context.TABLE
        elif env in FIGURE_ENVIRONMENTS:
            inner_context = Context.FIGURE
        else:
            inner_context = context
        yield from _walk(node.nodelist or [], source, line_starts, file, inner_context)
        return

    if isinstance(node, LatexMacroNode):
        macro = node.macroname or ""
        macro_root = macro.rstrip("*")
        if macro_root in NON_LINTABLE_ARG_MACROS:
            return
        if macro_root in CAPTION_MACROS:
            yield from _walk_macro_args(node, source, line_starts, file, Context.CAPTION)
            return
        # generic macro: recurse into args under the surrounding context
        yield from _walk_macro_args(node, source, line_starts, file, context)
        return

    if isinstance(node, LatexSpecialsNode):
        # things like ``~`` or ``--`` — no prose worth matching
        return

    # Unknown node types are silently ignored to stay forward-compatible
    # with future pylatexenc additions.
    return


def _walk_macro_args(
    node: LatexMacroNode,
    source: str,
    line_starts: list[int],
    file: str,
    context: Context,
) -> Iterator[TextSpan]:
    args = getattr(node, "nodeargd", None)
    if args is None:
        return
    for arg in args.argnlist or []:
        if arg is None:
            continue
        yield from _visit(arg, source, line_starts, file, context)


# --------------------------------------------------------------------------- #
# Line-number helpers
# --------------------------------------------------------------------------- #


def _line_starts(source: str) -> list[int]:
    """Return a list whose i-th element is the byte offset of line i+1."""
    starts = [0]
    for idx, ch in enumerate(source):
        if ch == "\n":
            starts.append(idx + 1)
    return starts


def _line_range(pos: int, length: int, line_starts: list[int]) -> tuple[int, int]:
    """Map a (pos, length) span in *source* to (start_line, end_line) 1-based."""
    start = _line_for(pos, line_starts)
    end = _line_for(max(pos, pos + length - 1), line_starts) if length > 0 else start
    return start, end


def _line_for(pos: int, line_starts: list[int]) -> int:
    """Return 1-based line index containing ``pos``."""
    # binary search; line_starts is monotonically increasing
    lo, hi = 0, len(line_starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if line_starts[mid] <= pos:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1
