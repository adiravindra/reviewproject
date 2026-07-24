"""Expose collection, analysis, demo, and local history through safe API routes."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.app.collector import CollectionError, collect_reviews
from backend.app.demo import load_demo_collection
from backend.app.errors import AnalysisError
from backend.app.history import HistoryStore
from backend.app.import_cache import ImportCacheStore
from backend.app.imports.contracts import ReviewImportError
from backend.app.imports.registry import build_default_registry
from backend.app.imports.service import ReviewImportService
from backend.app.models import (
    AnalysisRequest,
    AnalysisResponse,
    CollectionRequest,
    CollectionResult,
    HistoryItem,
    ImportOptions,
    ImportRequest,
)
from backend.app.service import run_analysis


# Stable status mappings let clients distinguish user-correctable credentials,
# transient providers, and upstream analysis failures without internal details.
ANALYSIS_ERRORS = {
    "missing_api_key": (400, "Set GROQ_API_KEY before analyzing reviews."),
    "invalid_api_key": (401, "Groq rejected the configured credential. Check the key and its permissions."),
    (
        "groq_unavailable"
    ): (
        503,
        "Groq credentials could not be validated. Analysis did not start; try again when Groq is reachable.",
    ),
    "analysis_failed": (
        502,
        "Groq could not complete the analysis. Your reviews are still available; try again.",
    ),
    "model_output_invalid": (
        502,
        "Groq returned an invalid analysis result. Your reviews are still available; try again.",
    ),
    "history_failed": (500, "Local analysis history could not be updated."),
}

COLLECTION_ERRORS = {
    "invalid_url": (422, "Use a public http or https review-page URL."),
    "no_reviews": (422, "At least two public reviews are required."),
    "malformed_json_ld": (422, "Review data on this page is malformed and could not be read."),
    "site_blocked": (502, "The website blocked automated access. Try another public review page."),
    "collection_timeout": (504, "The website took too long to respond. Try again or use another page."),
    "collection_failed": (502, "The page could not be read. Try another public review page."),
}

IMPORT_ERRORS = {
    "invalid_import_url": (
        422,
        "Use an HTTPS Amazon product or Google Maps place URL matching the selected source.",
    ),
    "unsupported_import_platform": (422, "Select Amazon or Google Maps."),
    "unsupported_import_limit": (422, "Choose one of the limits shown for the selected source."),
    "missing_provider_key": (
        400,
        "Set the selected provider API credential before importing reviews.",
    ),
    "provider_auth_failed": (
        401,
        "The review provider rejected its configured backend credential.",
    ),
    "provider_quota_exhausted": (
        429,
        "The review provider quota or configured spending capacity is exhausted.",
    ),
    "no_reviews": (422, "At least two usable written reviews are required."),
    "provider_response_invalid": (
        502,
        "The review provider returned an unsupported response.",
    ),
    "import_failed": (502, "The review provider could not complete the import."),
    "provider_unavailable": (
        503,
        "The review provider is temporarily unavailable. Try again later.",
    ),
    "import_timeout": (504, "The review provider took too long to complete the import."),
    "cache_failed": (500, "The local review import cache could not be updated."),
}

GENERIC_ANALYSIS_DETAIL = {
    "code": "analysis_failed",
    "message": "The analysis could not be completed.",
}

HISTORY_FAILURE_DETAIL = {
    "code": "history_failed",
    "message": "Local analysis history could not be updated.",
}


def _collection_http_error(error: CollectionError) -> HTTPException:
    """Convert a known collector failure into its small public envelope."""

    mapped = COLLECTION_ERRORS.get(error.code)
    if mapped is None:
        return _generic_analysis_http_error()
    status_code, message = mapped
    return HTTPException(
        status_code=status_code,
        detail={"code": error.code, "message": message},
    )


def _analysis_http_error(error: AnalysisError) -> HTTPException:
    """Convert a known analysis or history failure into its small public envelope."""

    mapped = ANALYSIS_ERRORS.get(error.code)
    if mapped is None:
        return _generic_analysis_http_error()
    status_code, message = mapped
    return HTTPException(
        status_code=status_code,
        detail={"code": error.code, "message": message},
    )


def _import_http_error(error: ReviewImportError) -> HTTPException:
    """Convert an import failure into its exact safe public envelope."""

    mapped = IMPORT_ERRORS.get(error.code)
    if mapped is None:
        return _generic_import_http_error()
    status_code, message = mapped
    return HTTPException(
        status_code=status_code,
        detail={"code": error.code, "message": message},
    )


def _generic_import_http_error() -> HTTPException:
    """Return the generic envelope for unexpected import failures."""

    status_code, message = IMPORT_ERRORS["import_failed"]
    return HTTPException(
        status_code=status_code,
        detail={"code": "import_failed", "message": message},
    )


def _generic_analysis_http_error() -> HTTPException:
    """Return the one generic envelope permitted for unexpected API failures."""

    return HTTPException(status_code=500, detail=GENERIC_ANALYSIS_DETAIL)


def _history_failure_http_error() -> HTTPException:
    """Return the stable envelope used when local history persistence fails."""

    return HTTPException(status_code=500, detail=HISTORY_FAILURE_DETAIL)


def create_app(
    collector=collect_reviews,
    analysis_service=run_analysis,
    demo_loader=load_demo_collection,
    history_store=None,
    import_service=None,
) -> FastAPI:
    """Build the API with injectable boundaries without eagerly opening history storage."""

    app = FastAPI(title="ReviewInsight MVP")
    store = history_store if history_store is not None else HistoryStore()
    importer = (
        import_service
        if import_service is not None
        else ReviewImportService(build_default_registry(), ImportCacheStore())
    )

    @app.exception_handler(RequestValidationError)
    async def collection_validation_error(request: Request, error: RequestValidationError):
        """Hide invalid collection input details behind the documented URL envelope."""

        if request.url.path == "/api/collect":
            status_code, message = COLLECTION_ERRORS["invalid_url"]
            return JSONResponse(
                status_code=status_code,
                content={"detail": {"code": "invalid_url", "message": message}},
            )
        if request.url.path == "/api/import":
            fields = {
                str(item)
                for issue in error.errors()
                for item in issue.get("loc", ())
            }
            if "platform" in fields:
                code = "unsupported_import_platform"
            elif "limit" in fields:
                code = "unsupported_import_limit"
            else:
                code = "invalid_import_url"
            status_code, message = IMPORT_ERRORS[code]
            return JSONResponse(
                status_code=status_code,
                content={"detail": {"code": code, "message": message}},
            )
        return await request_validation_exception_handler(request, error)

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
            raise _generic_analysis_http_error() from None

    @app.get("/api/import/options", response_model=ImportOptions)
    def import_options():
        """Return registered source choices without checking credentials."""

        try:
            return importer.options()
        except ReviewImportError as error:
            raise _import_http_error(error) from None
        except Exception:
            raise _generic_import_http_error() from None

    @app.post("/api/import", response_model=CollectionResult)
    def import_reviews(request: ImportRequest):
        """Import normalized reviews without invoking analysis or history."""

        try:
            return importer.import_reviews(request)
        except ReviewImportError as error:
            raise _import_http_error(error) from None
        except Exception:
            raise _generic_import_http_error() from None

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
            report = analysis_service(request)
        except CollectionError as error:
            raise _collection_http_error(error) from None
        except AnalysisError as error:
            raise _analysis_http_error(error) from None
        except Exception:
            raise _generic_analysis_http_error() from None

        try:
            saved_id = store.save(report)
        except AnalysisError as error:
            raise _analysis_http_error(error) from None
        except Exception:
            raise _history_failure_http_error() from None
        return report.model_copy(update={"history_id": saved_id})

    @app.get("/api/history", response_model=list[HistoryItem])
    def history():
        """Return newest-first safe summary rows from local history storage."""

        try:
            return store.list_runs()
        except AnalysisError as error:
            raise _analysis_http_error(error) from None
        except Exception:
            raise _generic_analysis_http_error() from None

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
            raise _generic_analysis_http_error() from None

    return app


app = create_app()
