import subprocess
import sys
from pathlib import Path
from typing import Callable

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
    print("Warming AI models before starting the app...")
    _warm_model("summary", ensure_summary_model_ready)
    _warm_model("sentiment", ensure_sentiment_model_ready)


def _warm_model(label: str, warmup: Callable[[], None]) -> None:
    try:
        print(f"Preparing {label} model...")
        warmup()
    except Exception as exc:
        print(
            f"Could not warm the {label} model: {exc}. "
            "The API will try the model again on request and use the fallback only if it still fails.",
            file=sys.stderr,
        )
    else:
        print(f"{label.title()} model ready.")


def main() -> None:
    ensure_models_ready()

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
