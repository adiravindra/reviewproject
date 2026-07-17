"""Enforce descriptive docstrings across the retained Python source tree."""

from __future__ import annotations

import ast
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RETAINED_SOURCE_ROOTS = ("backend", "dashboard", "tests")
EXCLUDED_DIRECTORIES = {
    ".git",
    ".venv",
    ".codex_runtime",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
}
CURRENT_CONFIGURATION_FILES = (
    Path(".env.example"),
    Path("requirements.txt"),
)
FORBIDDEN_GROQ_ONLY_TERMS = (
    "gemini",
    "google_api_key",
    "reviewinsight_google_model",
    "langchain_google_genai",
    "langchain-google-genai",
)
PROVIDER_SELECTION_PATTERNS = (
    re.compile(r"provider\s+(?:selection|selector)", re.IGNORECASE),
    re.compile(r"(?:select|choose)\s+(?:an?\s+)?(?:ai\s+)?provider", re.IGNORECASE),
    re.compile(r"st\.(?:radio|selectbox).*provider", re.IGNORECASE | re.DOTALL),
)


def _retained_python_files() -> list[Path]:
    """Return checked-in Python sources while ignoring environments and caches."""
    candidates = [PROJECT_ROOT / "run_app.py"]
    for source_root in RETAINED_SOURCE_ROOTS:
        candidates.extend((PROJECT_ROOT / source_root).rglob("*.py"))
    return sorted(
        path
        for path in candidates
        if path.is_file()
        and not EXCLUDED_DIRECTORIES.intersection(path.relative_to(PROJECT_ROOT).parts)
    )


def _groq_only_audit_files() -> list[Path]:
    """Return current runtime, configuration, and documentation files to audit."""

    runtime_files = [PROJECT_ROOT / "run_app.py"]
    for source_root in ("backend", "dashboard"):
        runtime_files.extend((PROJECT_ROOT / source_root).rglob("*.py"))
    documentation_files = [PROJECT_ROOT / "README.md"]
    documentation_files.extend((PROJECT_ROOT / "docs").glob("*.md"))
    configuration_files = [PROJECT_ROOT / path for path in CURRENT_CONFIGURATION_FILES]
    return sorted(runtime_files + documentation_files + configuration_files)


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

    def test_readme_documents_dotenv_precedence_and_automatic_browser_open(
        self,
    ) -> None:
        """Require startup documentation to match environment and browser behavior."""

        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn(".env", readme)
        self.assertIn("take precedence", readme)
        self.assertIn("automatically opens", readme)
        self.assertNotIn("does not load a `.env` file itself", readme)

    def test_readme_documents_staged_mvp_commands_and_demo_behavior(self) -> None:
        """Keep the public setup guide aligned with the staged Groq-only MVP."""

        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

        for expected in (
            ".\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt",
            ".\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v",
            ".\\.venv\\Scripts\\python.exe run_app.py",
            "GROQ_API_KEY",
            "REVIEWINSIGHT_GROQ_MODEL",
            "llama-3.3-70b-versatile",
            "POST /api/collect",
            "GET /api/demo",
            "POST /api/analyze",
            "GET /api/history",
            "data/review_history.db",
            "explicit",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, readme)

    def test_current_runtime_configuration_and_docs_are_groq_only(self) -> None:
        """Reject retired provider setup outside historical approved planning records."""

        violations: list[str] = []
        for path in _groq_only_audit_files():
            relative_path = path.relative_to(PROJECT_ROOT)
            text = path.read_text(encoding="utf-8")
            lowered = text.casefold()
            for forbidden in FORBIDDEN_GROQ_ONLY_TERMS:
                if forbidden in lowered:
                    violations.append(f"{relative_path}: {forbidden}")
            for pattern in PROVIDER_SELECTION_PATTERNS:
                if pattern.search(text):
                    violations.append(f"{relative_path}: {pattern.pattern}")

        self.assertFalse(
            violations,
            "Retired provider configuration or selection language remains:\n"
            + "\n".join(violations),
        )

    def test_provider_selection_audit_catches_multiline_streamlit_controls(self) -> None:
        """Keep line breaks from hiding a retired provider-selection control."""

        sample = 'st.radio(\n    "Provider",\n    options=["groq"],\n)'

        self.assertTrue(any(pattern.search(sample) for pattern in PROVIDER_SELECTION_PATTERNS))

    def test_discovery_is_limited_to_retained_source_roots(self) -> None:
        """Ignore unrelated root files, generated output, and peer worktrees."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            retained = {
                root / "backend" / "app.py",
                root / "dashboard" / "view.py",
                root / "tests" / "test_example.py",
                root / "run_app.py",
            }
            ignored = {
                root / "unrelated.py",
                root / "build" / "generated.py",
                root / ".worktrees" / "peer" / "module.py",
            }
            for path in retained | ignored:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('"""Temporary test module."""\n', encoding="utf-8")

            with patch(f"{__name__}.PROJECT_ROOT", root):
                discovered = set(_retained_python_files())

        self.assertEqual(discovered, retained)

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
