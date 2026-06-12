import sys
import unittest

from scripts import run_app, run_tests, smoke


class ScriptCommandTests(unittest.TestCase):
    def test_run_app_uses_current_python_for_backend_and_streamlit(self) -> None:
        commands = run_app.build_commands(host="127.0.0.1", backend_port=8000, streamlit_port=8501)

        self.assertEqual(commands.backend[0], sys.executable)
        self.assertEqual(commands.backend[1:4], ["-m", "uvicorn", "backend.app.main:app"])
        self.assertIn("--reload", commands.backend)
        self.assertEqual(commands.streamlit[0], sys.executable)
        self.assertEqual(commands.streamlit[1:4], ["-m", "streamlit", "run"])
        self.assertIn("dashboard/streamlit_app.py", commands.streamlit)

    def test_run_tests_builds_unittest_and_compile_commands(self) -> None:
        commands = run_tests.build_commands()

        self.assertEqual(commands.unittest, [sys.executable, "-m", "unittest", "discover", "-s", "tests"])
        self.assertEqual(commands.compile[0:3], [sys.executable, "-m", "py_compile"])
        self.assertIn("dashboard/streamlit_app.py", commands.compile)
        self.assertIn("backend/app/main.py", commands.compile)

    def test_smoke_uses_non_reload_backend_and_streamlit_commands(self) -> None:
        commands = smoke.build_commands(host="127.0.0.1", backend_port=8010, streamlit_port=8510)

        self.assertEqual(commands.backend[0:4], [sys.executable, "-m", "uvicorn", "backend.app.main:app"])
        self.assertNotIn("--reload", commands.backend)
        self.assertIn("8010", commands.backend)
        self.assertEqual(commands.streamlit[0:4], [sys.executable, "-m", "streamlit", "run"])
        self.assertIn("8510", commands.streamlit)


if __name__ == "__main__":
    unittest.main()
