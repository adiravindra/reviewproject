"""Expose the validated analysis service through a small, stable FastAPI boundary."""

from fastapi import FastAPI, HTTPException

from backend.app.collector import CollectionError
from backend.app.errors import AnalysisError
from backend.app.models import AnalysisRequest, AnalysisResponse


# Stable status mappings let clients distinguish user-correctable credentials,
# transient providers, and upstream analysis failures without internal details.
ANALYSIS_STATUS_CODES = {
    "missing_api_key": 400,
    "invalid_api_key": 401,
    "provider_unavailable": 503,
    "analysis_failed": 502,
}


def _run_analysis_service(collection):
    """Import the transitioning service lazily after staged request validation."""

    from backend.app.service import run_analysis

    return run_analysis(collection)


def create_app(analysis_service=_run_analysis_service) -> FastAPI:
    """Build the API with an injectable service for boundary-focused tests."""

    app = FastAPI(title="ReviewInsight MVP")

    @app.get("/health")
    def health():
        """Return the minimal process-readiness contract used by the dashboard."""

        return {"status": "ok"}

    @app.post("/api/analyze", response_model=AnalysisResponse)
    def analyze(request: AnalysisRequest):
        """Translate validated requests and safe domain failures into HTTP results."""

        try:
            return analysis_service(request.to_collection())
        except CollectionError as exc:
            status = 422 if exc.code in {"invalid_url", "no_reviews"} else 502
            raise HTTPException(
                status_code=status,
                detail={"code": exc.code, "message": exc.public_message},
            ) from None
        except AnalysisError as exc:
            raise HTTPException(
                status_code=ANALYSIS_STATUS_CODES.get(exc.code, 502),
                detail={"code": exc.code, "message": exc.public_message},
            ) from None
        except Exception:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "analysis_failed",
                    "message": "The analysis could not be completed.",
                },
            ) from None

    return app


app = create_app()
