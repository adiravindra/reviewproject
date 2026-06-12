from fastapi import APIRouter

from backend.app.schemas.reviews import HealthResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", project="ReviewInsight", version="0.1.0")
