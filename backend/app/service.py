"""Orchestrate credential, collection, agent, and deterministic metric stages."""

from backend.app.analyzer import analyze_reviews
from backend.app.collector import collect_reviews
from backend.app.credentials import validate_provider_credentials
from backend.app.models import AnalysisResponse, Metrics, Provider, Review, ReviewSentiment


def calculate_metrics(reviews: list[Review], sentiments: list[ReviewSentiment]) -> Metrics:
    """Derive reproducible rating and sentiment aggregates without model inference."""

    ratings = [review.rating for review in reviews if review.rating is not None]
    counts = {"positive": 0, "neutral": 0, "negative": 0}
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
    url: str,
    provider: Provider,
    *,
    credential_validator=validate_provider_credentials,
    collector=collect_reviews,
    analyzer=analyze_reviews,
) -> AnalysisResponse:
    """Run preflight first, then collect and analyze evidence into one response."""

    # Credential preflight is deliberately first: invalid credentials must stop
    # before network collection and before any generative provider invocation.
    credential_validator(provider)
    collection = collector(url)
    insights = analyzer(collection.reviews, provider)
    metrics = calculate_metrics(collection.reviews, insights.review_sentiments)
    return AnalysisResponse(
        source=collection.source,
        metrics=metrics,
        insights=insights,
        reviews=collection.reviews,
    )
