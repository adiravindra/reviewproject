from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from backend.app.errors import AppError, app_error_handler, request_validation_error_handler
from backend.app.routers.website import router as website_router


app = FastAPI(title="ReviewInsight API")

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, request_validation_error_handler)
app.include_router(website_router)
