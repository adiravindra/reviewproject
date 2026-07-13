"""Enforce descriptive docstrings across the retained Python source tree."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRECTORIES = {
    ".git",
    ".venv",
    ".codex_runtime",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
}


def _retained_python_files() -> list[Path]:
    """Return checked-in Python sources while ignoring environments and caches."""
    return sorted(
        path
        for path in PROJECT_ROOT.rglob("*.py")
        if not EXCLUDED_DIRECTORIES.intersection(path.relative_to(PROJECT_ROOT).parts)
    )


def _missing_docstrings(path: Path) -> list[str]:
    """Return qualified AST names whose docstrings are absent or blank."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    missing: list[str] = []

    if not (ast.get_docstring(tree, clean=False) or "").strip():
        missing.append("<module>")

    def inspect_scope(node: ast.AST, parents: tuple[str, ...] = ()) -> None:
        """Inspect documentable descendants while preserving lexical qualification."""
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                qualified_name = ".".join((*parents, child.name))
                if not (ast.get_docstring(child, clean=False) or "").strip():
                    missing.append(qualified_name)
                inspect_scope(child, (*parents, child.name))
            else:
                inspect_scope(child, parents)

    inspect_scope(tree)
    return missing


class DocumentationCoverageTests(unittest.TestCase):
    """Guard the repository-wide descriptive-docstring contract."""

    def test_every_retained_python_scope_has_a_docstring(self) -> None:
        """Report every undocumented module, class, function, and async function."""
        omissions = [
            f"{path.relative_to(PROJECT_ROOT)}: {qualified_name}"
            for path in _retained_python_files()
            for qualified_name in _missing_docstrings(path)
        ]

        self.assertFalse(
            omissions,
            "Missing or blank Python docstrings:\n" + "\n".join(omissions),
        )


if __name__ == "__main__":
    unittest.main()
