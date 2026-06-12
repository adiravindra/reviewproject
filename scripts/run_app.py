from __future__ import annotations

import argparse
import subprocess
import time
from dataclasses import dataclass

from scripts.common import PROJECT_ROOT, project_path, python_command, terminate_process


@dataclass(frozen=True)
class AppCommands:
    backend: list[str]
    streamlit: list[str]


def build_commands(
    host: str = "127.0.0.1",
    backend_port: int = 8000,
    streamlit_port: int = 8501,
) -> AppCommands:
    backend = python_command(
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        host,
        "--port",
        str(backend_port),
        "--reload",
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
    )
    return AppCommands(backend=backend, streamlit=streamlit)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ReviewInsight FastAPI and Streamlit together.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--streamlit-port", type=int, default=8501)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    commands = build_commands(args.host, args.backend_port, args.streamlit_port)

    print(f"Starting FastAPI at http://{args.host}:{args.backend_port}")
    backend = subprocess.Popen(commands.backend, cwd=PROJECT_ROOT)

    print(f"Starting Streamlit at http://{args.host}:{args.streamlit_port}")
    streamlit = subprocess.Popen(commands.streamlit, cwd=PROJECT_ROOT)

    print("Press Ctrl+C to stop both servers.")
    try:
        while True:
            backend_code = backend.poll()
            streamlit_code = streamlit.poll()
            if backend_code is not None:
                print(f"FastAPI stopped with exit code {backend_code}.")
                return backend_code
            if streamlit_code is not None:
                print(f"Streamlit stopped with exit code {streamlit_code}.")
                return streamlit_code
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping ReviewInsight servers...")
        terminate_process(streamlit)
        terminate_process(backend)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
