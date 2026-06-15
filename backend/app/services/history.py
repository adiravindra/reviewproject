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
