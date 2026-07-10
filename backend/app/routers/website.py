from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Query

from backend.app.errors import AppError
from backend.app.schemas.website import (
    WebsiteAnalysisRequest,
    WebsiteAnalysisResponse,
    WebsiteHistoryResponse,
)
from backend.app.services.history import get_website_analysis, list_website_analyses
from backend.app.services.orchestration import (
    AnalysisDependencies,
    build_analysis_dependencies,
    run_website_analysis,
)
from backend.app.settings import Settings


router = APIRouter(prefix="/analysis", tags=["website analysis"])


def get_settings() -> Settings:
    return Settings.from_env()


def get_analysis_dependencies(
    settings: Settings = Depends(get_settings),
) -> AnalysisDependencies:
    return build_analysis_dependencies(settings)


@router.post("/website", response_model=WebsiteAnalysisResponse)
def analyze_website(
    request: WebsiteAnalysisRequest,
    dependencies: AnalysisDependencies = Depends(get_analysis_dependencies),
) -> WebsiteAnalysisResponse:
    _validate_request_url(request.url)
    return run_website_analysis(request.url, dependencies)


@router.get("/history", response_model=WebsiteHistoryResponse)
def analysis_history(
    limit: int = Query(default=50, ge=1, le=200),
    settings: Settings = Depends(get_settings),
) -> WebsiteHistoryResponse:
    return list_website_analyses(limit=limit, path=settings.db_path)


@router.get("/history/{run_id}", response_model=WebsiteAnalysisResponse)
def analysis_history_item(
    run_id: str,
    settings: Settings = Depends(get_settings),
) -> WebsiteAnalysisResponse:
    result = get_website_analysis(run_id, path=settings.db_path)
    if result is None:
        raise AppError(
            code="analysis_not_found",
            message="The requested website analysis was not found.",
            stage="history",
            status_code=404,
            details={"analysis_id": run_id},
        )
    return result


def _validate_request_url(value: str) -> None:
    try:
        parsed = urlsplit(value.strip())
        _ = parsed.port
    except ValueError:
        raise _invalid_url_error(value) from None
    if (
        parsed.scheme.casefold() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise _invalid_url_error(value)


def _invalid_url_error(value: str) -> AppError:
    return AppError(
        code="invalid_url",
        message="Only public HTTP and HTTPS website URLs are supported.",
        stage="validation",
        status_code=422,
        details={"url": value},
    )
