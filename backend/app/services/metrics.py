from collections import Counter
from decimal import Decimal, ROUND_HALF_UP

from backend.app.schemas.website import (
    NormalizedReview,
    ReviewMetrics,
    SentimentCounts,
)


_SENTIMENTS = ("positive", "neutral", "negative")


def calculate_metrics(
    *,
    found_count: int,
    valid_count: int,
    reviews: list[NormalizedReview],
    sentiments: dict[str, str],
) -> ReviewMetrics:
    review_ids = {review.id for review in reviews}
    if set(sentiments) != review_ids or any(value not in _SENTIMENTS for value in sentiments.values()):
        raise ValueError("Sentiment classifications must cover every analyzed review exactly once.")

    ratings = [review.rating for review in reviews if review.rating is not None]
    distribution = {str(star): 0 for star in range(1, 6)}
    for rating in ratings:
        bucket = int(Decimal(str(rating)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        bucket = min(5, max(1, bucket))
        distribution[str(bucket)] += 1

    average_rating = None
    if ratings:
        average = sum(Decimal(str(rating)) for rating in ratings) / Decimal(len(ratings))
        average_rating = float(average.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    counts = Counter(sentiments.values())
    sentiment_counts = SentimentCounts(
        positive=counts["positive"],
        neutral=counts["neutral"],
        negative=counts["negative"],
    )
    highest = max(counts.values(), default=0)
    leaders = [sentiment for sentiment in _SENTIMENTS if counts[sentiment] == highest]
    overall_sentiment = leaders[0] if len(leaders) == 1 else "mixed"

    analyzed_count = len(reviews)
    return ReviewMetrics(
        reviews_found=found_count,
        reviews_valid=valid_count,
        reviews_analyzed=analyzed_count,
        reviews_skipped=max(0, found_count - analyzed_count),
        rated_reviews=len(ratings),
        average_rating=average_rating,
        rating_distribution=distribution,
        sentiment_counts=sentiment_counts,
        overall_sentiment=overall_sentiment,
    )
