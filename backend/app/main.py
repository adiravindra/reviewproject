from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from backend.app.errors import (
    AppError,
    app_error_handler,
    request_validation_error_handler,
    unexpected_error_handler,
)
from backend.app.routers.website import (
    get_analysis_dependencies,
    get_settings,
    router as website_router,
)
from backend.app.services.orchestration import AnalysisDependencies


def create_app(dependencies: AnalysisDependencies | None = None) -> FastAPI:
    application = FastAPI(title="ReviewInsight API")
    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(RequestValidationError, request_validation_error_handler)
    application.add_exception_handler(Exception, unexpected_error_handler)
    application.include_router(website_router)
    if dependencies is not None:
        application.dependency_overrides[get_settings] = lambda: dependencies.settings
        application.dependency_overrides[get_analysis_dependencies] = lambda: dependencies
    return application


app = create_app()
