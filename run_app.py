"""Launch and supervise the backend and dashboard as a single local application."""

import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
POLL_INTERVAL_SECONDS = 0.1
SHUTDOWN_TIMEOUT_SECONDS = 5.0


def build_commands(python_executable: str) -> tuple[list[str], list[str]]:
    """Build argument-list commands that reuse the current Python interpreter."""

    # Lists avoid shell parsing and quoting ambiguity while sys.executable keeps
    # both peers in the same environment as this supervisor.
    backend = [
        python_executable,
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    dashboard = [
        python_executable,
        "-m",
        "streamlit",
        "run",
        "dashboard/streamlit_app.py",
        "--server.address",
        "127.0.0.1",
        "--server.port",
        "8501",
        "--server.headless",
        "true",
    ]
    return backend, dashboard


def stop_process(process, *, timeout: float = SHUTDOWN_TIMEOUT_SECONDS) -> None:
    """Stop one child gracefully, forcing termination only after the deadline."""

    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def run(
    *,
    popen=subprocess.Popen,
    sleep=time.sleep,
    python_executable=sys.executable,
) -> int:
    """Supervise both peers, stop survivors, and return user-oriented exit status."""

    backend = None
    dashboard = None
    backend_command, dashboard_command = build_commands(python_executable)
    try:
        backend = popen(backend_command, cwd=PROJECT_ROOT)
        dashboard = popen(dashboard_command, cwd=PROJECT_ROOT)
        # Either peer is required for the app, so an early exit ends supervision
        # and the finally block shuts down its surviving counterpart.
        while True:
            for process in (backend, dashboard):
                returncode = process.poll()
                if returncode is not None:
                    return returncode or 1
            sleep(POLL_INTERVAL_SECONDS)
    # User-requested shutdown is successful; startup and unexpected peer exits
    # remain nonzero so scripts can distinguish them from a clean Ctrl+C.
    except KeyboardInterrupt:
        return 0
    except OSError:
        return 1
    finally:
        for process in (backend, dashboard):
            if process is not None:
                stop_process(process)


def main() -> int:
    """Return the supervisor exit code for propagation through SystemExit."""

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
