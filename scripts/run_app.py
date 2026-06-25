import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.model_sentiment import ensure_sentiment_model_ready  # noqa: E402
from backend.app.services.model_summarizer import ensure_summary_model_ready  # noqa: E402


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


def ensure_models_ready() -> None:
    print("Checking local AI models before starting the app...")
    print("Preparing summary model...")
    ensure_summary_model_ready()
    print("Preparing sentiment model...")
    ensure_sentiment_model_ready()
    print("Model check complete.")


def main() -> None:
    try:
        ensure_models_ready()
    except Exception as exc:
        print(f"Could not prepare the AI models: {exc}", file=sys.stderr)
        print("The app was not started. Check your network connection or set REVIEWINSIGHT_MODEL_LOCAL_ONLY=1 if the models are already cached.", file=sys.stderr)
        raise SystemExit(1) from exc

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
