import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
POLL_INTERVAL_SECONDS = 0.1
SHUTDOWN_TIMEOUT_SECONDS = 5.0


def build_commands(python_executable: str) -> tuple[list[str], list[str]]:
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
    backend = None
    dashboard = None
    backend_command, dashboard_command = build_commands(python_executable)
    try:
        backend = popen(backend_command, cwd=PROJECT_ROOT)
        dashboard = popen(dashboard_command, cwd=PROJECT_ROOT)
        while True:
            for process in (backend, dashboard):
                returncode = process.poll()
                if returncode is not None:
                    return returncode or 1
            sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        return 0
    except OSError:
        return 1
    finally:
        for process in (backend, dashboard):
            if process is not None:
                stop_process(process)


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
