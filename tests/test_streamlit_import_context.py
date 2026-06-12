import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"


class StreamlitImportContextTests(unittest.TestCase):
    def test_dashboard_modules_import_from_dashboard_working_directory(self) -> None:
        script = """
import importlib.util
from pathlib import Path

import streamlit_app

for page_path in sorted(Path("pages").glob("*.py")):
    spec = importlib.util.spec_from_file_location(page_path.stem, page_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
"""

        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=DASHBOARD_DIR,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
