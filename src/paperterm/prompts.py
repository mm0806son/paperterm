"""Single source of truth for paperterm's standalone bootstrap prompt.

The actual prompt text lives in ``src/paperterm/data/bootstrap_prompt.md``
so it ships with the wheel and so it stays editable as plain Markdown
(no Python escaping of backticks, no triple-quote conflicts). This
module loads that data file via :mod:`importlib.resources` and
re-exports it as :data:`BOOTSTRAP_PROMPT`.

Downstream:
- ``paperterm print-prompt`` writes :data:`BOOTSTRAP_PROMPT` verbatim.
- ``prompts/glossary_bootstrap.md`` (checked in at the repo root) is a
  byte-equal copy maintained by Phase 5 stage P5.D and verified by a
  test, so users browsing the GitHub repo see the same prompt without
  having to install paperterm first.
"""

from __future__ import annotations

from importlib import resources

_PROMPT_PACKAGE = "paperterm"
_PROMPT_RESOURCE = ("data", "bootstrap_prompt.md")


def _load() -> str:
    base = resources.files(_PROMPT_PACKAGE)
    for part in _PROMPT_RESOURCE:
        base = base.joinpath(part)
    return base.read_text(encoding="utf-8")


BOOTSTRAP_PROMPT: str = _load()


__all__ = ["BOOTSTRAP_PROMPT"]
