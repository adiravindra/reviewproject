from __future__ import annotations

import subprocess
from dataclasses import dataclass

from scripts.common import PROJECT_ROOT, project_path, python_command


PYTHON_FILES = [
    project_path("backend", "app", "main.py"),
    project_path("dashboard", "api_client.py"),
    project_path("dashboard", "streamlit_app.py"),
    project_path("dashboard", "ui.py"),
    project_path("dashboard", "pages", "1_Sentiment_Analysis.py"),
    project_path("dashboard", "pages", "2_Topic_Category_Analysis.py"),
    project_path("dashboard", "pages", "3_Urgency_Priority.py"),
    project_path("dashboard", "pages", "4_GenAI_Summary_Insights.py"),
    project_path("dashboard", "pages", "5_Overall_Dashboard.py"),
    project_path("dashboard", "pages", "6_History.py"),
    project_path("dashboard", "pages", "7_API_Health.py"),
]


@dataclass(frozen=True)
class TestCommands:
    unittest: list[str]
    compile: list[str]


def build_commands() -> TestCommands:
    return TestCommands(
        unittest=python_command("-m", "unittest", "discover", "-s", "tests"),
        compile=python_command("-m", "py_compile", *PYTHON_FILES),
    )


def run_command(command: list[str]) -> int:
    print(f"Running: {' '.join(command)}")
    return subprocess.run(command, cwd=PROJECT_ROOT).returncode


def main() -> int:
    commands = build_commands()

    unittest_code = run_command(commands.unittest)
    if unittest_code != 0:
        return unittest_code

    return run_command(commands.compile)


if __name__ == "__main__":
    raise SystemExit(main())
