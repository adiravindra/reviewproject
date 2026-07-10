from urllib.parse import urlsplit

from fastapi import APIRouter, status

from backend.app.errors import AppError
from backend.app.schemas.website import WebsiteAnalysisRequest


router = APIRouter(prefix="/analysis", tags=["website analysis"])


@router.post("/website")
def analyze_website(_: WebsiteAnalysisRequest) -> None:
    parsed = urlsplit(_.url)
    if (
        parsed.scheme.casefold() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise AppError(
            code="invalid_url",
            message="Only public HTTP and HTTPS website URLs are supported.",
            stage="validation",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            details={"url": _.url},
        )
    raise AppError(
        code="scrape_failed",
        message="Website analysis is not available yet.",
        stage="scraping",
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
    )
