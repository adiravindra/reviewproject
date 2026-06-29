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


# Save the full analysis JSON in SQLite.
def save_review_analysis(result: ReviewAnalysisResponse) -> None:
    payload = model_to_dict(result)
    # Legacy aggregate columns stay populated for database compatibility, while
    # payload_json keeps the exact single-review result used by the History page.
    topic_counts: dict[str, int] = {}
    urgency_counts = {"low": 0, "medium": 0, "high": 0}

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
                0.0,
                result.summary,
                json.dumps(payload, sort_keys=True),
            ),
        )
        connection.commit()


def get_history(limit: int = 50) -> HistoryResponse:
    # Newest reviews appear first.
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
    # Guard against malformed stored JSON so one bad row does not break history.
    try:
        payload = json.loads(str(row["payload_json"]))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _history_item_from_payload(payload: dict[str, Any]) -> HistoryItem:
    return HistoryItem(
        id=str(payload.get("id", "")),
        created_at=str(payload.get("created_at", "")),
        text=str(payload.get("text", "")),
        sentiment=str(payload.get("sentiment", "neutral")),
        summary=str(payload.get("summary", "")),
    )
