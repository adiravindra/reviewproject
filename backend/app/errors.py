from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        stage: str,
        status_code: int,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.stage = stage
        self.status_code = status_code
        self.retryable = retryable
        self.details = details or {}

    def envelope(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "stage": self.stage,
                "retryable": self.retryable,
                "details": self.details,
            }
        }


async def app_error_handler(_: Request, error: AppError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content=error.envelope())


async def request_validation_error_handler(
    _: Request,
    __: RequestValidationError,
) -> JSONResponse:
    error = AppError(
        code="invalid_url",
        message="Provide one valid public website URL.",
        stage="validation",
        status_code=422,
    )
    return JSONResponse(status_code=error.status_code, content=error.envelope())
