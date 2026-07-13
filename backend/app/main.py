from fastapi import FastAPI, HTTPException

from backend.app.collector import CollectionError
from backend.app.errors import AnalysisError
from backend.app.models import AnalysisRequest, AnalysisResponse
from backend.app.service import run_analysis


ANALYSIS_STATUS_CODES = {
    "missing_api_key": 400,
    "invalid_api_key": 401,
    "provider_unavailable": 503,
    "analysis_failed": 502,
}


def create_app(analysis_service=run_analysis) -> FastAPI:
    app = FastAPI(title="ReviewInsight MVP")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/analyze", response_model=AnalysisResponse)
    def analyze(request: AnalysisRequest):
        try:
            return analysis_service(str(request.url), request.provider)
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
