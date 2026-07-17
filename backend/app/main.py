"""Expose collection, analysis, demo, and local history through safe API routes."""

from fastapi import FastAPI, HTTPException

from backend.app.collector import CollectionError, collect_reviews
from backend.app.demo import load_demo_collection
from backend.app.errors import AnalysisError
from backend.app.history import HistoryStore
from backend.app.models import (
    AnalysisRequest,
    AnalysisResponse,
    CollectionRequest,
    CollectionResult,
    HistoryItem,
)
from backend.app.service import run_analysis


# Stable status mappings let clients distinguish user-correctable credentials,
# transient providers, and upstream analysis failures without internal details.
ANALYSIS_STATUS_CODES = {
    "missing_api_key": 400,
    "invalid_api_key": 401,
    "groq_unavailable": 503,
    "analysis_failed": 502,
    "model_output_invalid": 502,
    "history_failed": 500,
}

COLLECTION_STATUS_CODES = {
    "invalid_url": 422,
    "no_reviews": 422,
    "malformed_json_ld": 422,
    "site_blocked": 502,
    "collection_timeout": 504,
    "collection_failed": 502,
}


def _collection_http_error(error: CollectionError) -> HTTPException:
    """Convert a known collector failure into its small public envelope."""

    return HTTPException(
        status_code=COLLECTION_STATUS_CODES.get(error.code, 502),
        detail={"code": error.code, "message": error.public_message},
    )


def _analysis_http_error(error: AnalysisError) -> HTTPException:
    """Convert a known analysis or history failure into its small public envelope."""

    return HTTPException(
        status_code=ANALYSIS_STATUS_CODES.get(error.code, 502),
        detail={"code": error.code, "message": error.public_message},
    )


def create_app(
    collector=collect_reviews,
    analysis_service=run_analysis,
    demo_loader=load_demo_collection,
    history_store=None,
) -> FastAPI:
    """Build the API with injectable boundaries without eagerly opening history storage."""

    app = FastAPI(title="ReviewInsight MVP")
    store = history_store if history_store is not None else HistoryStore()

    @app.get("/health")
    def health():
        """Return the minimal process-readiness contract used by the dashboard."""

        return {"status": "ok"}

    @app.post("/api/collect", response_model=CollectionResult)
    def collect(request: CollectionRequest):
        """Collect normalized public reviews without invoking Groq or local history."""

        try:
            return collector(str(request.url))
        except CollectionError as error:
            raise _collection_http_error(error) from None
        except Exception:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "analysis_failed",
                    "message": "The analysis could not be completed.",
                },
            ) from None

    @app.get("/api/demo", response_model=CollectionResult)
    def demo():
        """Load the explicitly labeled bundled example collection on request only."""

        try:
            return demo_loader()
        except Exception:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "collection_failed",
                    "message": "Bundled demo data could not be loaded.",
                },
            ) from None

    @app.post("/api/analyze", response_model=AnalysisResponse)
    def analyze(request: AnalysisRequest):
        """Analyze submitted evidence once, save it once, and return its history ID."""

        try:
            report = analysis_service(request.to_collection())
            saved_id = store.save(report)
            return report.model_copy(update={"history_id": saved_id})
        except CollectionError as error:
            raise _collection_http_error(error) from None
        except AnalysisError as error:
            raise _analysis_http_error(error) from None
        except Exception:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "analysis_failed",
                    "message": "The analysis could not be completed.",
                },
            ) from None

    @app.get("/api/history", response_model=list[HistoryItem])
    def history():
        """Return newest-first safe summary rows from local history storage."""

        try:
            return store.list_runs()
        except AnalysisError as error:
            raise _analysis_http_error(error) from None
        except Exception:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "analysis_failed",
                    "message": "The analysis could not be completed.",
                },
            ) from None

    @app.get("/api/history/{run_id}", response_model=AnalysisResponse)
    def history_entry(run_id: int):
        """Return one saved report or the stable, non-sensitive absent-entry response."""

        try:
            report = store.get(run_id)
            if report is None:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "code": "history_not_found",
                        "message": "That history entry was not found.",
                    },
                )
            return report.model_copy(update={"history_id": run_id})
        except HTTPException:
            raise
        except AnalysisError as error:
            raise _analysis_http_error(error) from None
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
