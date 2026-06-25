import json
from contextlib import closing
from typing import Any

from backend.app.schemas.reviews import (
    HistoryItem,
    HistoryResponse,
    ReviewAnalysisResponse,
    model_to_dict,
)
from backend.app.services.db import connect


def save_review_analysis(result: ReviewAnalysisResponse) -> None:
    payload = model_to_dict(result)
    topic_counts = {topic: 1 for topic in result.topics}
    urgency_counts = {"low": 0, "medium": 0, "high": 0}
    urgency_counts[result.urgency] = 1

    with closing(connect()) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO analysis_runs (
                id,
                created_at,
                input_type,
                review_count,
                sentiment_counts_json,
                topic_counts_json,
                urgency_counts_json,
                average_urgency,
                overall_summary,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.id,
                result.created_at,
                "single",
                1,
                json.dumps({result.sentiment: 1}, sort_keys=True),
                json.dumps(topic_counts, sort_keys=True),
                json.dumps(urgency_counts, sort_keys=True),
                result.urgency_score,
                result.summary,
                json.dumps(payload, sort_keys=True),
            ),
        )
        connection.commit()


def get_history(limit: int = 50) -> HistoryResponse:
    with closing(connect()) as connection:
        rows = connection.execute(
            """
            SELECT payload_json
            FROM analysis_runs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return HistoryResponse(items=[_history_item_from_payload(_payload(row)) for row in rows])


def _payload(row: Any) -> dict[str, Any]:
    payload = json.loads(str(row["payload_json"]))
    return payload if isinstance(payload, dict) else {}


def _history_item_from_payload(payload: dict[str, Any]) -> HistoryItem:
    if "text" in payload:
        return HistoryItem(
            id=str(payload.get("id", "")),
            created_at=str(payload.get("created_at", "")),
            text=str(payload.get("text", "")),
            sentiment=str(payload.get("sentiment", "neutral")),
            topics=[str(topic) for topic in payload.get("topics", [])],
            urgency=str(payload.get("urgency", "low")),
            summary=str(payload.get("summary", "")),
        )

    reviews = payload.get("reviews", [])
    first_review = reviews[0] if isinstance(reviews, list) and reviews else {}
    return HistoryItem(
        id=str(payload.get("id", "")),
        created_at=str(payload.get("created_at", "")),
        text=str(first_review.get("text", "")) if isinstance(first_review, dict) else "",
        sentiment=str(first_review.get("sentiment", "neutral")) if isinstance(first_review, dict) else "neutral",
        topics=[str(first_review.get("topic", "general feedback"))] if isinstance(first_review, dict) else [],
        urgency=str(first_review.get("urgency", "low")) if isinstance(first_review, dict) else "low",
        summary=str(first_review.get("summary", payload.get("summary", ""))) if isinstance(first_review, dict) else "",
    )
