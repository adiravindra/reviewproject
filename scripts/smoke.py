from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass

from scripts.common import PROJECT_ROOT, project_path, python_command, terminate_process, wait_for_url


@dataclass(frozen=True)
class SmokeCommands:
    backend: list[str]
    streamlit: list[str]


def build_commands(
    host: str = "127.0.0.1",
    backend_port: int = 8000,
    streamlit_port: int = 8501,
) -> SmokeCommands:
    backend = python_command(
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        host,
        "--port",
        str(backend_port),
    )
    streamlit = python_command(
        "-m",
        "streamlit",
        "run",
        project_path("dashboard", "streamlit_app.py"),
        "--server.address",
        host,
        "--server.port",
        str(streamlit_port),
        "--server.headless",
        "true",
    )
    return SmokeCommands(backend=backend, streamlit=streamlit)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test ReviewInsight servers.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--streamlit-port", type=int, default=8501)
    parser.add_argument("--timeout", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    commands = build_commands(args.host, args.backend_port, args.streamlit_port)

    backend_url = f"http://{args.host}:{args.backend_port}/health"
    streamlit_url = f"http://{args.host}:{args.streamlit_port}/_stcore/health"

    backend = subprocess.Popen(commands.backend, cwd=PROJECT_ROOT)
    streamlit = subprocess.Popen(commands.streamlit, cwd=PROJECT_ROOT)

    try:
        wait_for_url(backend_url, timeout_seconds=args.timeout)
        print(f"FastAPI smoke check passed: {backend_url}")

        wait_for_url(streamlit_url, timeout_seconds=args.timeout)
        print(f"Streamlit smoke check passed: {streamlit_url}")

        print(f"Dashboard URL: http://{args.host}:{args.streamlit_port}")
        return 0
    finally:
        terminate_process(streamlit)
        terminate_process(backend)


if __name__ == "__main__":
    raise SystemExit(main())
