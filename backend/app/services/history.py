import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

from backend.app.schemas.reviews import (
    AnalysisRunResponse,
    DashboardMetricsResponse,
    HistoryItem,
    HistoryResponse,
    KeywordItem,
    ReviewDetailResponse,
)


DEFAULT_HISTORY_PATH = Path("data/review_history.json")


def save_analysis_run(run: AnalysisRunResponse) -> None:
    records = _read_records()
    records.append(_model_to_dict(run))
    _write_records(records)


def get_history(limit: int = 25) -> HistoryResponse:
    records = sorted(_read_records(), key=lambda item: item.get("created_at", ""), reverse=True)
    items = [
        HistoryItem(
            id=str(record["id"]),
            created_at=str(record["created_at"]),
            source=str(record["source"]),
            review_count=int(record["review_count"]),
            overall_sentiment=str(record["metrics"]["overall_sentiment"]),
            high_priority_reviews=int(record["metrics"]["high_priority_reviews"]),
            summary=str(record["summary"]),
        )
        for record in records[:limit]
    ]
    return HistoryResponse(items=items)


def get_analysis_run(run_id: str) -> AnalysisRunResponse | None:
    for record in _read_records():
        if str(record.get("id")) == run_id:
            return AnalysisRunResponse(**_normalize_analysis_record(record))
    return None


def get_latest_analysis_run() -> AnalysisRunResponse | None:
    records = sorted(_read_records(), key=lambda item: item.get("created_at", ""), reverse=True)
    if not records:
        return None
    return AnalysisRunResponse(**_normalize_analysis_record(records[0]))


def get_review_detail(run_id: str, review_index: int) -> ReviewDetailResponse | None:
    run = get_analysis_run(run_id)
    if run is None or review_index < 0 or review_index >= len(run.reviews):
        return None

    return ReviewDetailResponse(
        run_id=run.id,
        review_index=review_index,
        review=run.reviews[review_index],
    )


def get_dashboard_metrics() -> DashboardMetricsResponse:
    records = _read_records()
    sentiment_counts: Counter[str] = Counter({"positive": 0, "neutral": 0, "negative": 0})
    urgency_counts: Counter[str] = Counter({"low": 0, "medium": 0, "high": 0})
    topic_counts: Counter[str] = Counter()

    for record in records:
        metrics = record.get("metrics", {})
        sentiment_counts.update(metrics.get("sentiment_breakdown", {}))
        urgency_counts.update(metrics.get("urgency_breakdown", {}))
        topic_counts.update(
            {
                item.get("keyword", "general feedback"): int(item.get("count", 0))
                for item in metrics.get("top_topics", [])
            }
        )

    recent_records = sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)

    return DashboardMetricsResponse(
        total_runs=len(records),
        total_reviews=sum(int(record.get("review_count", 0)) for record in records),
        sentiment_breakdown={key: sentiment_counts[key] for key in ["positive", "neutral", "negative"]},
        urgency_breakdown={key: urgency_counts[key] for key in ["low", "medium", "high"]},
        top_topics=[
            KeywordItem(keyword=topic, count=count)
            for topic, count in topic_counts.most_common(5)
        ],
        recent_summaries=[str(record.get("summary", "")) for record in recent_records[:5]],
    )


def _history_path() -> Path:
    configured_path = os.getenv("REVIEWINSIGHT_HISTORY_PATH")
    return Path(configured_path) if configured_path else DEFAULT_HISTORY_PATH


def _read_records() -> list[dict[str, Any]]:
    path = _history_path()
    if not path.exists():
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _write_records(records: list[dict[str, Any]]) -> None:
    path = _history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")


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
