from backend.app.analyzer import analyze_reviews
from backend.app.collector import collect_reviews
from backend.app.models import AnalysisResponse, Metrics, Provider, Review, ReviewSentiment


def calculate_metrics(reviews: list[Review], sentiments: list[ReviewSentiment]) -> Metrics:
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
    collector=collect_reviews,
    analyzer=analyze_reviews,
) -> AnalysisResponse:
    collection = collector(url)
    insights = analyzer(collection.reviews, provider)
    metrics = calculate_metrics(collection.reviews, insights.review_sentiments)
    return AnalysisResponse(
        source=collection.source,
        metrics=metrics,
        insights=insights,
        reviews=collection.reviews,
    )
