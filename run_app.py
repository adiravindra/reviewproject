"""Launch and supervise the backend and dashboard as a single local application."""

import json
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path
from urllib.error import URLError

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_URL = "http://127.0.0.1:8000"
BACKEND_HEALTH_URL = f"{BACKEND_URL}/health"
DASHBOARD_URL = "http://127.0.0.1:8501"
DASHBOARD_HEALTH_URL = f"{DASHBOARD_URL}/_stcore/health"
READINESS_REQUEST_TIMEOUT_SECONDS = 0.25
STARTUP_TIMEOUT_SECONDS = 30.0
# A tenth-second poll notices peer failure promptly without busy-spinning while
# both long-lived services are healthy.
POLL_INTERVAL_SECONDS = 0.1
# Five seconds gives frameworks time for graceful cleanup but prevents a stuck
# child from hanging supervisor shutdown indefinitely.
SHUTDOWN_TIMEOUT_SECONDS = 5.0


def load_project_environment(*, loader=load_dotenv) -> None:
    """Load project settings without replacing the parent environment."""

    loader(PROJECT_ROOT / ".env", override=False)


def dashboard_is_ready(*, urlopen=urllib.request.urlopen) -> bool:
    """Return whether Streamlit's local health endpoint is ready."""

    try:
        with urlopen(
            DASHBOARD_HEALTH_URL,
            timeout=READINESS_REQUEST_TIMEOUT_SECONDS,
        ) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


def backend_is_ready(*, urlopen=urllib.request.urlopen) -> bool:
    """Return whether the backend health endpoint confirms it is ready."""

    try:
        with urlopen(
            BACKEND_HEALTH_URL,
            timeout=READINESS_REQUEST_TIMEOUT_SECONDS,
        ) as response:
            return response.status == 200 and json.load(response) == {"status": "ok"}
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return False


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
    monotonic=time.monotonic,
    python_executable=sys.executable,
    load_environment=load_project_environment,
    backend_ready=backend_is_ready,
    dashboard_ready=dashboard_is_ready,
    open_browser=webbrowser.open,
    report=print,
) -> int:
    """Supervise both peers, stop survivors, and return user-oriented exit status."""

    backend = None
    dashboard = None
    try:
        load_environment()
    except Exception:
        report(f"Could not load configuration from {PROJECT_ROOT / '.env'}.")
        return 1

    backend_command, dashboard_command = build_commands(python_executable)
    try:
        backend = popen(backend_command, cwd=PROJECT_ROOT)
        dashboard = popen(dashboard_command, cwd=PROJECT_ROOT)
        startup_started = monotonic()
        browser_attempted = False
        # Either peer is required for the app, so an early exit ends supervision
        # and the finally block shuts down its surviving counterpart.
        while True:
            for process in (backend, dashboard):
                returncode = process.poll()
                if returncode is not None:
                    return returncode or 1
            if not browser_attempted and backend_ready() and dashboard_ready():
                browser_attempted = True
                try:
                    browser_opened = open_browser(DASHBOARD_URL)
                except Exception:
                    browser_opened = False
                if not browser_opened:
                    report(
                        f"Open {DASHBOARD_URL} manually; "
                        "the default browser could not be started."
                    )
            if monotonic() - startup_started >= STARTUP_TIMEOUT_SECONDS:
                report("The application did not become ready within 30 seconds.")
                return 1
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
