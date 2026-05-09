"""paperterm — LaTeX-aware terminology consistency linter for academic papers.

This module exposes the package version as :data:`__version__`. It is the
single source of truth for the version string: the build backend
(``hatchling``, configured in ``pyproject.toml``) reads this same value
into the wheel metadata, and the CLI re-imports it at runtime.
"""

from __future__ import annotations

__version__ = "0.1.0.dev0"

__all__ = ["__version__"]
