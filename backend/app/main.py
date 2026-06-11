from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="ReviewInsight API")


class ReviewRequest(BaseModel):
    text: str


class ReviewAnalysis(BaseModel):
    sentiment: str
    topic: str
    urgency: str
    summary: str


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "project": "ReviewInsight"}


@app.post("/analyze", response_model=ReviewAnalysis)
def analyze_review(review: ReviewRequest) -> ReviewAnalysis:
    review_text = review.text.strip()

    if not review_text:
        return ReviewAnalysis(
            sentiment="neutral",
            topic="unknown",
            urgency="low",
            summary="No review text was provided.",
        )

    return ReviewAnalysis(
        sentiment="neutral",
        topic="general feedback",
        urgency="low",
        summary=f"Placeholder summary for: {review_text[:120]}",
    )
