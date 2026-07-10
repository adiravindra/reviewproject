from fastapi import APIRouter, HTTPException, status

from backend.app.schemas.website import WebsiteAnalysisRequest


router = APIRouter(prefix="/analysis", tags=["website analysis"])


@router.post("/website")
def analyze_website(_: WebsiteAnalysisRequest) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Website analysis is not implemented yet.",
    )
