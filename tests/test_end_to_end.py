import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.schemas.website import BatchAnalysisOutput, SynthesisOutput
from backend.app.scrapers.registry import default_registry
from backend.app.services.analysis import analyze_collection
from backend.app.services.history import save_website_analysis
from backend.app.services.orchestration import AnalysisDependencies
from backend.app.services.scraping import collect_reviews
from backend.app.settings import Settings
from tests.test_scraping import MappingFetcher, fixture_page


class ResponsiveStructuredModel:
    def with_structured_output(self, schema: type[Any]) -> Any:
        class Runnable:
            def invoke(self, prompt: str) -> dict[str, Any]:
                if schema is BatchAnalysisOutput:
                    records = json.loads(prompt.split("Review records (JSON):\n", 1)[1])
                    sentiments = ["positive", "negative", "positive", "neutral", "negative", "positive"]
                    first_id = records[0]["review_id"]
                    return {
                        "sentiments": [
                            {
                                "review_id": record["review_id"],
                                "sentiment": sentiments[index],
                            }
                            for index, record in enumerate(records)
                        ],
                        "positive_themes": [
                            {
                                "label": "Portability",
                                "summary": "Customers value portability and ease of use.",
                                "review_ids": [first_id],
                            }
                        ],
                        "complaints": [
                            {
                                "label": "Durability",
                                "summary": "Some components feel less durable.",
                                "review_ids": [first_id],
                            }
                        ],
                        "aspects": [
                            {
                                "label": "Value",
                                "summary": "Value and utility shape the experience.",
                                "review_ids": [first_id],
                            }
                        ],
                        "opportunities": [
                            {
                                "label": "Improve components",
                                "summary": "Strengthen the handle and lid.",
                                "review_ids": [first_id],
                            }
                        ],
                    }
                batches = json.loads(prompt.split("Batch structures (JSON):\n", 1)[1])
                review_ids = [
                    item["review_id"]
                    for batch in batches
                    for item in batch["sentiments"]
                ]
                evidence = {
                    "label": "Product experience",
                    "summary": "The collection contains clear strengths and actionable concerns.",
                    "review_ids": [review_ids[0]],
                }
                return {
                    "executive_summary": "Customers value portability while identifying component improvements.",
                    "strengths": [evidence],
                    "complaints": [evidence],
                    "aspects": [evidence],
                    "opportunities": [evidence],
                    "representative_review_ids": review_ids[:3],
                }

        return Runnable()


class EndToEndTests(unittest.TestCase):
    def test_public_url_to_saved_dashboard_payload_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "reviewinsight.db"
            settings = Settings(max_pages=2, db_path=database)
            first_url = "https://public.example/kettle/reviews"
            second_url = "https://public.example/kettle/reviews?page=2"
            fetcher = MappingFetcher(
                {
                    first_url: fixture_page("static_cards_page_1.html", first_url),
                    second_url: fixture_page("static_cards_page_2.html", second_url),
                }
            )
            registry = default_registry()
            model = ResponsiveStructuredModel()

            def scrape(url: str, deadline: float):
                return collect_reviews(
                    url,
                    fetcher=fetcher,
                    registry=registry,
                    settings=settings,
                    clock=lambda: 0.0,
                    overall_deadline=deadline,
                )

            dependencies = AnalysisDependencies(
                settings=settings,
                scrape=scrape,
                analyze=lambda reviews: analyze_collection(reviews, model=model, settings=settings),
                save=lambda response: save_website_analysis(response, database),
                clock=lambda: 0.0,
                id_factory=lambda: "run_end_to_end",
                now=lambda: datetime(2026, 7, 10, 17, 0, tzinfo=timezone.utc),
            )
            client = TestClient(create_app(dependencies))

            response = client.post("/analysis/website", json={"url": first_url})
            stored = client.get("/analysis/history/run_end_to_end")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["collection"]["found"], 6)
        self.assertEqual(payload["collection"]["analyzed"], 6)
        self.assertEqual(
            payload["metrics"]["sentiment_counts"],
            {"positive": 3, "neutral": 1, "negative": 2},
        )
        normalized_text = {item["text"] for item in payload["reviews"]}
        self.assertTrue(
            all(
                item["text"] in normalized_text
                for item in payload["insights"]["representative_reviews"]
            )
        )
        self.assertEqual(stored.json(), payload)


if __name__ == "__main__":
    unittest.main()
