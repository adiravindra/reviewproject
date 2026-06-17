import json
from contextlib import closing
from typing import Any

from backend.app.schemas.reviews import (
    AnalysisRunResponse,
    HistoryItem,
    HistoryResponse,
    ReviewDetailResponse,
)
from backend.app.services.db import connect


def save_analysis_run(run: AnalysisRunResponse) -> None:
    payload = _model_to_dict(run)
    metrics = payload.get("metrics", {})
    top_topics = {
        str(item.get("keyword", "general feedback")): int(item.get("count", 0))
        for item in metrics.get("top_topics", [])
        if isinstance(item, dict)
    }

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
                run.id,
                run.created_at,
                run.source,
                run.review_count,
                json.dumps(metrics.get("sentiment_breakdown", {}), sort_keys=True),
                json.dumps(top_topics, sort_keys=True),
                json.dumps(metrics.get("urgency_breakdown", {}), sort_keys=True),
                float(metrics.get("average_urgency", 0.0)),
                run.summary,
                json.dumps(payload, sort_keys=True),
            ),
        )
        connection.commit()


def get_history(limit: int = 25) -> HistoryResponse:
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

    items = [_history_item_from_payload(_payload(row)) for row in rows]
    return HistoryResponse(items=items)


def get_analysis_run(run_id: str) -> AnalysisRunResponse | None:
    with closing(connect()) as connection:
        row = connection.execute(
            "SELECT payload_json FROM analysis_runs WHERE id = ?",
            (run_id,),
        ).fetchone()

    if row is None:
        return None
    return AnalysisRunResponse(**_normalize_analysis_record(_payload(row)))


def get_latest_analysis_run() -> AnalysisRunResponse | None:
    with closing(connect()) as connection:
        row = connection.execute(
            """
            SELECT payload_json
            FROM analysis_runs
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()

    if row is None:
        return None
    return AnalysisRunResponse(**_normalize_analysis_record(_payload(row)))


def get_review_detail(run_id: str, review_index: int) -> ReviewDetailResponse | None:
    run = get_analysis_run(run_id)
    if run is None or review_index < 0 or review_index >= len(run.reviews):
        return None

    return ReviewDetailResponse(
        run_id=run.id,
        review_index=review_index,
        review=run.reviews[review_index],
    )


def _history_item_from_payload(record: dict[str, Any]) -> HistoryItem:
    metrics = dict(record.get("metrics", {}))
    return HistoryItem(
        id=str(record["id"]),
        created_at=str(record["created_at"]),
        input_type=str(record["source"]),
        review_count=int(record["review_count"]),
        overall_sentiment=str(metrics.get("overall_sentiment", "neutral")),
        high_priority_reviews=int(metrics.get("high_priority_reviews", 0)),
        summary=str(record["summary"]),
    )


def _payload(row: Any) -> dict[str, Any]:
    payload = json.loads(str(row["payload_json"]))
    return payload if isinstance(payload, dict) else {}


def _model_to_dict(model: AnalysisRunResponse) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _normalize_analysis_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    metrics = dict(normalized.get("metrics", {}))
    reviews = list(normalized.get("reviews", []))

    if "average_urgency" not in metrics:
        scores = [_urgency_score(str(review.get("urgency", "low"))) for review in reviews]
        metrics["average_urgency"] = round(sum(scores) / len(scores), 2) if scores else 0.0

    if "most_urgent_reviews" not in normalized:
        normalized["most_urgent_reviews"] = sorted(
            reviews,
            key=lambda review: (
                _urgency_score(str(review.get("urgency", "low"))),
                abs(int(review.get("sentiment_score", 0))),
            ),
            reverse=True,
        )[:5]

    normalized["metrics"] = metrics
    return normalized


def _urgency_score(urgency: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(urgency, 1)
