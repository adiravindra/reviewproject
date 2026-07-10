import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# One tiny helper script to run the backend and frontend together.
BACKEND_COMMAND = [
    sys.executable,
    "-m",
    "uvicorn",
    "backend.app.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    "8000",
]
FRONTEND_COMMAND = [
    sys.executable,
    "-m",
    "streamlit",
    "run",
    "dashboard/streamlit_app.py",
    "--server.address",
    "127.0.0.1",
    "--server.port",
    "8501",
]


def main() -> None:
    backend = subprocess.Popen(BACKEND_COMMAND)
    frontend = subprocess.Popen(FRONTEND_COMMAND)

    print("Backend:  http://127.0.0.1:8000")
    print("Frontend: http://127.0.0.1:8501")
    print("Press Ctrl+C to stop both.")

    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        backend.terminate()
        frontend.terminate()


if __name__ == "__main__":
    main()
