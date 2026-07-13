from fastapi import FastAPI, HTTPException

from backend.app.analyzer import AnalysisError
from backend.app.collector import CollectionError
from backend.app.models import AnalysisRequest, AnalysisResponse
from backend.app.service import run_analysis


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
            status = 400 if exc.code == "missing_api_key" else 502
            raise HTTPException(
                status_code=status,
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
