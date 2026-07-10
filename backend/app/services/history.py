import json
from contextlib import closing
from pathlib import Path

from pydantic import ValidationError

from backend.app.schemas.website import (
    WebsiteAnalysisResponse,
    WebsiteHistoryItem,
    WebsiteHistoryResponse,
    model_to_dict,
)
from backend.app.services.db import connect


def save_website_analysis(
    result: WebsiteAnalysisResponse,
    path: Path | None = None,
) -> None:
    validated = WebsiteAnalysisResponse.model_validate(model_to_dict(result))
    payload = json.dumps(model_to_dict(validated), sort_keys=True, separators=(",", ":"))
    with closing(connect(path)) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO website_analysis_runs (
                    id,
                    completed_at,
                    source_url,
                    entity_name,
                    review_count,
                    average_rating,
                    overall_sentiment,
                    executive_summary,
                    provider,
                    model,
                    payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    validated.id,
                    validated.analysis.completed_at,
                    validated.source.requested_url,
                    validated.source.entity_name,
                    validated.metrics.reviews_analyzed,
                    validated.metrics.average_rating,
                    validated.metrics.overall_sentiment,
                    validated.insights.executive_summary,
                    validated.analysis.provider,
                    validated.analysis.model,
                    payload,
                ),
            )


def list_website_analyses(
    limit: int = 50,
    path: Path | None = None,
) -> WebsiteHistoryResponse:
    bounded_limit = min(200, max(1, int(limit)))
    with closing(connect(path)) as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                completed_at,
                source_url,
                entity_name,
                review_count,
                average_rating,
                overall_sentiment,
                executive_summary,
                provider,
                model
            FROM website_analysis_runs
            ORDER BY completed_at DESC
            LIMIT ?
            """,
            (bounded_limit,),
        ).fetchall()
    return WebsiteHistoryResponse(
        items=[
            WebsiteHistoryItem(
                id=str(row["id"]),
                completed_at=str(row["completed_at"]),
                source_url=str(row["source_url"]),
                entity_name=str(row["entity_name"]) if row["entity_name"] is not None else None,
                review_count=int(row["review_count"]),
                average_rating=float(row["average_rating"]) if row["average_rating"] is not None else None,
                overall_sentiment=str(row["overall_sentiment"]),
                executive_summary=str(row["executive_summary"]),
                provider=str(row["provider"]),
                model=str(row["model"]),
            )
            for row in rows
        ]
    )


def get_website_analysis(
    run_id: str,
    path: Path | None = None,
) -> WebsiteAnalysisResponse | None:
    with closing(connect(path)) as connection:
        row = connection.execute(
            "SELECT payload_json FROM website_analysis_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    if row is None:
        return None
    try:
        payload = json.loads(str(row["payload_json"]))
        return WebsiteAnalysisResponse.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, TypeError):
        return None
