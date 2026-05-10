"""Manual bootstrap: assemble a single prompt-plus-corpus file the user
can paste into any LLM (Claude.ai, ChatGPT, Gemini, ...) without
needing paperterm to talk to that LLM directly.

The corpus injected into the file is *AST-cleaned*: each .tex file is
walked through :mod:`paperterm.latex` and only lintable text spans
(prose / caption / table / figure context) survive. Math, verbatim,
comment, citation/ref/label/url contexts are dropped before reaching
the LLM, eliminating the easiest source of false positives in the
draft yaml.

The on-disk format matches the ``Corpus`` section of
:data:`paperterm.prompts.BOOTSTRAP_PROMPT`: each line of every file is
prefixed with its absolute 1-based line number so that the LLM can
fill ``locations.line`` by copying instead of counting.

This module deliberately ships *no* network code: paperterm v0.1
does not bundle any provider-specific API path. Users run their
own LLM and paste the reply back as ``glossary.draft.yaml``.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .glossary import Context
from .latex import TextSpan, iter_spans
from .prompts import BOOTSTRAP_PROMPT

CORPUS_OPEN = "=== BEGIN CORPUS ==="
CORPUS_CLOSE = "=== END CORPUS ==="
DEFAULT_OUTPUT_NAME = ".paperterm_prompt.txt"

# Contexts that contribute to the corpus the LLM sees. Math / verbatim /
# comment / cite_arg are dropped silently because they are skipped by the
# walker upstream; we list the lintable contexts here so the policy is
# explicit and easy to audit.
_CORPUS_CONTEXTS: frozenset[Context] = frozenset(
    {Context.PROSE, Context.CAPTION, Context.TABLE, Context.FIGURE}
)


@dataclass(frozen=True)
class BootstrapResult:
    """Outcome of a bootstrap run, returned by :func:`build_prompt_file`."""

    output_path: Path
    files_scanned: int
    bytes_written: int


def build_prompt_file(
    paper_dir: Path,
    *,
    include_globs: Iterable[str] = ("**/*.tex",),
    exclude_globs: Iterable[str] = ("**/build/**",),
    output_path: Path | None = None,
) -> BootstrapResult:
    """Scan ``paper_dir`` and write the prompt-plus-corpus file.

    The file is overwritten if it already exists. The caller (CLI) is
    responsible for printing the next-step instructions to the user.
    """
    paper_dir = paper_dir.resolve()
    if not paper_dir.is_dir():
        raise ValueError(f"paper_dir must be an existing directory: {paper_dir}")
    target = (output_path or paper_dir / DEFAULT_OUTPUT_NAME).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    matched = _select_files(paper_dir, include_globs, exclude_globs)
    corpus = _assemble_corpus(paper_dir, matched)
    payload = _compose_payload(corpus)
    target.write_text(payload, encoding="utf-8")
    return BootstrapResult(
        output_path=target,
        files_scanned=len(matched),
        bytes_written=len(payload.encode("utf-8")),
    )


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _select_files(
    paper_dir: Path,
    include_globs: Iterable[str],
    exclude_globs: Iterable[str],
) -> list[Path]:
    matched: set[Path] = set()
    for pattern in include_globs:
        for p in paper_dir.glob(pattern):
            if p.is_file():
                matched.add(p.resolve())
    excluded: set[Path] = set()
    for pattern in exclude_globs:
        for p in paper_dir.glob(pattern):
            if p.is_dir():
                # When the exclude pattern resolves to a directory,
                # treat it as recursively excluding every file under it.
                # Plain ``Path.glob`` does not descend into ``**`` after
                # a directory match, so we expand here.
                for sub in p.rglob("*"):
                    if sub.is_file():
                        excluded.add(sub.resolve())
            else:
                excluded.add(p.resolve())
    return sorted(matched - excluded)


def _assemble_corpus(paper_dir: Path, files: list[Path]) -> str:
    chunks: list[str] = []
    for path in files:
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ValueError(f"failed to read {path}: {exc}") from exc
        rel = str(path.relative_to(paper_dir))
        spans = [s for s in iter_spans(raw, file=rel) if s.context in _CORPUS_CONTEXTS]
        if not spans:
            continue
        chunks.append(_format_chunk(rel, raw, spans))
    return "\n\n".join(chunks)


def _format_chunk(rel: str, raw: str, spans: list[TextSpan]) -> str:
    """Emit a ``=== FILE: ... ===`` header followed by, for each line that
    the walker emitted any non-whitespace text on, the *cleaned* content
    of that line — built from span text only, never from the raw .tex.

    Building each line from span chars (rather than copying the raw
    file line) is what keeps the AST-cleaned promise: if a line in the
    source contains both lintable prose and skipped material (inline
    math, ``\\cite{}`` argument, trailing ``%`` comment), only the
    prose halves survive in the corpus the LLM sees.
    """
    del raw  # the .tex file content is intentionally unused now
    line_parts: dict[int, list[str]] = defaultdict(list)
    for span in spans:
        for offset, line_text in enumerate(span.text.split("\n")):
            stripped = line_text.strip()
            if stripped:
                line_parts[span.start_line + offset].append(stripped)
    body_lines: list[str] = []
    for ln in sorted(line_parts):
        cleaned = " ".join(line_parts[ln])
        body_lines.append(f"{ln}: {cleaned}")
    header = f"=== FILE: {rel} ==="
    return f"{header}\n" + "\n".join(body_lines)


def _compose_payload(corpus: str) -> str:
    prompt = BOOTSTRAP_PROMPT
    if not prompt.endswith("\n"):
        prompt += "\n"
    return f"{prompt}\n{CORPUS_OPEN}\n{corpus}\n{CORPUS_CLOSE}\n"


__all__ = [
    "BootstrapResult",
    "CORPUS_CLOSE",
    "CORPUS_OPEN",
    "DEFAULT_OUTPUT_NAME",
    "build_prompt_file",
]
