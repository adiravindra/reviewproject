"""Orchestrate credential, agent, and deterministic metric stages."""

from backend.app.analyzer import analyze_reviews
from backend.app.credentials import validate_groq_credentials
from backend.app.models import (
    AnalysisRequest,
    AnalysisResponse,
    Metrics,
    Review,
    ReviewSentiment,
)


def calculate_metrics(reviews: list[Review], sentiments: list[ReviewSentiment]) -> Metrics:
    """Derive reproducible rating and sentiment aggregates without model inference."""

    ratings = [review.rating for review in reviews if review.rating is not None]
    counts = {"positive": 0, "neutral": 0, "negative": 0, "mixed": 0}
    for item in sentiments:
        counts[item.sentiment] += 1

    distribution = {str(star): 0 for star in range(1, 6)}
    for rating in ratings:
        distribution[str(rating)] += 1

    return Metrics(
        review_count=len(reviews),
        rated_count=len(ratings),
        average_rating=round(sum(ratings) / len(ratings), 1) if ratings else None,
        positive_percentage=round(100 * counts["positive"] / len(reviews), 1) if reviews else 0.0,
        sentiment_counts=counts,
        rating_distribution=distribution,
    )


def run_analysis(
    request: AnalysisRequest,
    *,
    credential_validator=validate_groq_credentials,
    analyzer=analyze_reviews,
) -> AnalysisResponse:
    """Validate Groq and analyze one previously collected evidence set."""

    # Credential preflight is deliberately first: invalid credentials must stop
    # before any generative provider invocation or deterministic metric work.
    credential_validator()
    insights = analyzer(request.reviews)
    metrics = calculate_metrics(request.reviews, insights.review_sentiments)
    return AnalysisResponse(
        source=request.source,
        metrics=metrics,
        insights=insights,
        reviews=request.reviews,
    )
