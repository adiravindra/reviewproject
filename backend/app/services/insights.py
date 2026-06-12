from backend.app.services.keywords import (
    extract_common_complaints,
    extract_themes,
)
from backend.app.services.sentiment import (
    analyze_sentiment,
    overall_sentiment,
    sentiment_breakdown,
)
from backend.app.services.summarization import summarize_reviews


def build_insights(review_texts: list[str]) -> dict[str, object]:
    positive_reviews = [
        text for text in review_texts if analyze_sentiment(text).sentiment == "positive"
    ]
    negative_reviews = [
        text for text in review_texts if analyze_sentiment(text).sentiment == "negative"
    ]

    common_complaints = extract_common_complaints(negative_reviews or review_texts)

    return {
        "review_count": len(review_texts),
        "overall_sentiment": overall_sentiment(review_texts),
        "sentiment_breakdown": sentiment_breakdown(review_texts),
        "positive_themes": [theme for theme, _ in extract_themes(positive_reviews or review_texts)],
        "negative_themes": [theme for theme, _ in extract_themes(negative_reviews or review_texts)],
        "common_complaints": common_complaints,
        "summary": summarize_reviews(review_texts),
        "suggested_action_items": suggest_action_items(common_complaints),
    }


def suggest_action_items(common_complaints: list[str]) -> list[str]:
    action_map = {
        "delayed shipping": "Review carrier performance and set clearer delivery expectations.",
        "support response time": "Audit support response times and add coverage during peak hours.",
        "product quality issues": "Send recurring quality issues to the product or operations team.",
        "pricing concerns": "Compare pricing feedback against competitors and discount strategy.",
        "usability friction": "Prioritize onboarding and setup improvements in the next product pass.",
    }

    actions = [action_map[complaint] for complaint in common_complaints if complaint in action_map]
    if actions:
        return actions

    return ["Monitor new reviews and collect more examples before prioritizing changes."]
