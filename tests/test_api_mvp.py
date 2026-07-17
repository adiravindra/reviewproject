"""Test staged FastAPI routes and their safe public failure envelopes."""

import unittest
from inspect import signature
from unittest.mock import Mock

from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.collector import CollectionError
from backend.app.errors import AnalysisError
from backend.app.main import create_app
from backend.app.service import run_analysis
from backend.app.models import (
    AnalysisResponse,
    CollectionResult,
    HistoryItem,
    PublicError,
    Theme,
)


def sample_collection_payload() -> dict:
    """Build valid displayed evidence for the staged analysis endpoint."""

    return {
        "source": {
            "url": "https://example.com/product",
            "title": "Everyday Headphones",
            "extractor": "json_ld",
            "is_demo": False,
        },
        "reviews": [
            {"id": "r1", "text": "Clear sound and comfortable fit.", "rating": 5},
            {"id": "r2", "text": "Battery is adequate for a normal day.", "rating": 3},
            {"id": "r3", "text": "Microphone quality needs meaningful improvement."},
        ],
    }


def sample_collection() -> CollectionResult:
    """Build a valid collection returned by a collector or demo-loader fake."""

    return CollectionResult.model_validate(sample_collection_payload())


def sample_demo_collection() -> CollectionResult:
    """Build explicitly labeled demo data returned by the demo-loader fake."""

    payload = sample_collection_payload()
    payload["source"].update({"url": None, "extractor": "demo", "is_demo": True})
    return CollectionResult.model_validate(payload)


def sample_response() -> AnalysisResponse:
    """Build a fully validated response returned by API service fakes."""

    payload = sample_collection_payload()
    return AnalysisResponse.model_validate(
        {
            **payload,
            "metrics": {
                "review_count": 3,
                "rated_count": 2,
                "average_rating": 4.0,
                "positive_percentage": 66.7,
                "sentiment_counts": {"positive": 2, "neutral": 0, "negative": 1},
                "rating_distribution": {"1": 0, "2": 0, "3": 1, "4": 0, "5": 1},
            },
            "insights": {
                "summary": "Customers value sound and comfort while noting microphone limitations.",
                "overall_sentiment": "positive",
                "themes": [
                    {
                        "name": "Daily performance",
                        "description": "Sound, comfort, and microphone quality shape the feedback.",
                        "mentions": 3,
                        "sentiment": "positive",
                    }
                ],
                "strengths": ["Clear sound", "Comfortable fit"],
                "weaknesses": ["Microphone quality"],
                "actions": ["Improve microphone noise handling"],
                "review_sentiments": [
                    {"review_id": "r1", "sentiment": "positive"},
                    {"review_id": "r2", "sentiment": "positive"},
                    {"review_id": "r3", "sentiment": "negative"},
                ],
            },
        }
    )


class FakeHistoryStore:
    """Record history boundary calls without creating the lazy local database."""

    def __init__(self, *, saved_id=7, items=None, report=None):
        """Configure one deterministic history outcome for each endpoint."""

        self.saved_id = saved_id
        self.items = [] if items is None else items
        self.report = report
        self.saved_reports = []
        self.list_calls = 0
        self.get_calls = []

    def save(self, report):
        """Record the exact report submitted for persistence."""

        self.saved_reports.append(report)
        if isinstance(self.saved_id, Exception):
            raise self.saved_id
        return self.saved_id

    def list_runs(self):
        """Return the configured newest-first safe history summaries."""

        self.list_calls += 1
        if isinstance(self.items, Exception):
            raise self.items
        return self.items

    def get(self, run_id):
        """Return the configured report while retaining the looked-up ID."""

        self.get_calls.append(run_id)
        if isinstance(self.report, Exception):
            raise self.report
        return self.report


class ApiTests(unittest.TestCase):
    """Group regression contracts at the public HTTP boundary."""

    def test_exact_route_set_and_health_response(self):
        """Expose only readiness plus the staged collection, analysis, and history routes."""

        self.assertIs(signature(create_app).parameters["analysis_service"].default, run_analysis)
        client = TestClient(create_app(history_store=FakeHistoryStore()))
        self.assertEqual(client.get("/health").json(), {"status": "ok"})
        paths = set(client.get("/openapi.json").json()["paths"])
        self.assertEqual(
            paths,
            {
                "/health",
                "/api/collect",
                "/api/demo",
                "/api/analyze",
                "/api/history",
                "/api/history/{run_id}",
            },
        )

    def test_collect_passes_normalized_url_once_without_analysis_or_history(self):
        """Keep static collection independent from Groq analysis and local persistence."""

        collector = Mock(return_value=sample_collection())
        service = Mock(return_value=sample_response())
        history = FakeHistoryStore()
        response = TestClient(
            create_app(collector=collector, analysis_service=service, history_store=history)
        ).post("/api/collect", json={"url": "https://example.com/product"})
        self.assertEqual(response.status_code, 200)
        collector.assert_called_once_with("https://example.com/product")
        service.assert_not_called()
        self.assertEqual(history.saved_reports, [])
        self.assertEqual(response.json()["source"]["title"], "Everyday Headphones")

    def test_demo_calls_loader_once_and_preserves_explicit_provenance(self):
        """Serve bundled data only through its explicit, visibly labeled endpoint."""

        demo_loader = Mock(return_value=sample_demo_collection())
        response = TestClient(create_app(demo_loader=demo_loader, history_store=FakeHistoryStore())).get(
            "/api/demo"
        )
        self.assertEqual(response.status_code, 200)
        demo_loader.assert_called_once_with()
        self.assertEqual(
            response.json()["source"],
            {"url": None, "title": "Everyday Headphones", "extractor": "demo", "is_demo": True},
        )

    def test_analyze_rejects_provider_and_calls_no_service(self):
        """Forbid obsolete provider selection at the request-validation boundary."""

        service = Mock(return_value=sample_response())
        payload = sample_collection_payload() | {"provider": "groq"}
        response = TestClient(create_app(analysis_service=service, history_store=FakeHistoryStore())).post(
            "/api/analyze", json=payload
        )
        self.assertEqual(response.status_code, 422)
        service.assert_not_called()

    def test_analyze_passes_exact_collection_saves_once_and_returns_history_id(self):
        """Analyze only submitted evidence, persist it once, then expose its local ID."""

        service = Mock(return_value=sample_response())
        history = FakeHistoryStore(saved_id=13)
        response = TestClient(create_app(analysis_service=service, history_store=history)).post(
            "/api/analyze", json=sample_collection_payload()
        )
        self.assertEqual(response.status_code, 200)
        submitted = service.call_args.args[0]
        self.assertEqual(submitted, sample_collection())
        self.assertEqual(history.saved_reports, [sample_response()])
        self.assertEqual(response.json()["history_id"], 13)

    def test_analysis_failure_does_not_save_history(self):
        """Never persist a report when analysis itself did not succeed."""

        def fail(collection):
            """Simulate an expected Groq availability failure."""

            raise AnalysisError("groq_unavailable", "Groq is temporarily unavailable.")

        history = FakeHistoryStore()
        response = TestClient(create_app(analysis_service=fail, history_store=history)).post(
            "/api/analyze", json=sample_collection_payload()
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(history.saved_reports, [])

    def test_history_save_failure_does_not_return_successful_report(self):
        """Convert persistence failures into the documented safe history error."""

        history = FakeHistoryStore(
            saved_id=AnalysisError("history_failed", "Local history could not be updated.")
        )
        response = TestClient(
            create_app(analysis_service=Mock(return_value=sample_response()), history_store=history)
        ).post(
            "/api/analyze", json=sample_collection_payload()
        )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {
                "detail": {
                    "code": "history_failed",
                    "message": "Local analysis history could not be updated.",
                }
            },
        )

    def test_raw_history_save_failure_uses_the_safe_history_envelope(self):
        """Treat unexpected persistence exceptions as local history failures, never analysis errors."""

        marker = "database password raw storage traceback"
        history = FakeHistoryStore(saved_id=RuntimeError(marker))
        response = TestClient(
            create_app(analysis_service=Mock(return_value=sample_response()), history_store=history)
        ).post("/api/analyze", json=sample_collection_payload())
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {
                "detail": {
                    "code": "history_failed",
                    "message": "Local analysis history could not be updated.",
                }
            },
        )
        self.assertNotIn(marker, response.text)

    def test_history_list_returns_safe_newest_first_summaries(self):
        """Forward only the already-safe ordering and fields supplied by history storage."""

        items = [
            HistoryItem(
                id=9,
                created_at="2026-07-17T12:00:00Z",
                source_title="New report",
                source_url=None,
                extractor="demo",
                is_demo=True,
                review_count=10,
                overall_sentiment="mixed",
            )
        ]
        history = FakeHistoryStore(items=items)
        response = TestClient(create_app(history_store=history)).get("/api/history")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(history.list_calls, 1)
        self.assertEqual(response.json(), [item.model_dump() for item in items])

    def test_history_get_returns_report_with_looked_up_id_and_safe_absence(self):
        """Restore reports by ID and distinguish an absent row without storage details."""

        history = FakeHistoryStore(report=sample_response())
        client = TestClient(create_app(history_store=history))
        found = client.get("/api/history/42")
        self.assertEqual(found.status_code, 200)
        self.assertEqual(history.get_calls, [42])
        self.assertEqual(found.json()["history_id"], 42)

        absent_history = FakeHistoryStore(report=None)
        absent = TestClient(create_app(history_store=absent_history)).get("/api/history/404")
        self.assertEqual(absent.status_code, 404)
        self.assertEqual(
            absent.json(),
            {
                "detail": {
                    "code": "history_not_found",
                    "message": "That history entry was not found.",
                }
            },
        )

    def test_collection_errors_map_to_exact_safe_statuses(self):
        """Map every public collection error code without exposing chained details."""

        marker = "Authorization: Bearer fake-secret; raw page body"
        cases = [
            ("invalid_url", 422, "Use a public http or https review-page URL."),
            ("no_reviews", 422, "At least two public reviews are required."),
            ("malformed_json_ld", 422, "Review data on this page is malformed and could not be read."),
            ("site_blocked", 502, "The website blocked automated access. Try another public review page."),
            ("collection_timeout", 504, "The website took too long to respond. Try again or use another page."),
            ("collection_failed", 502, "The page could not be read. Try another public review page."),
        ]
        for code, expected_status, expected_message in cases:
            with self.subTest(code=code):
                error = CollectionError(code, marker)
                error.__cause__ = RuntimeError(marker)
                response = TestClient(
                    create_app(collector=Mock(side_effect=error), history_store=FakeHistoryStore())
                ).post("/api/collect", json={"url": "https://example.com/product"})
                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(
                    response.json(), {"detail": {"code": code, "message": expected_message}}
                )
                self.assertNotIn(marker, response.text)

    def test_analysis_and_history_errors_map_to_exact_safe_statuses(self):
        """Map every analysis/history code while withholding provider and storage markers."""

        marker = "Authorization: Bearer fake-secret; raw provider response"
        cases = [
            ("missing_api_key", 400, "Set GROQ_API_KEY before analyzing reviews."),
            ("invalid_api_key", 401, "Groq rejected the configured credential. Check the key and its permissions."),
            (
                "groq_unavailable",
                503,
                "Groq credentials could not be validated. Analysis did not start; try again when Groq is reachable.",
            ),
            ("analysis_failed", 502, "The analysis could not be completed."),
            ("model_output_invalid", 502, "The AI analysis returned an invalid result."),
            ("history_failed", 500, "Local analysis history could not be updated."),
        ]
        for code, expected_status, expected_message in cases:
            with self.subTest(code=code):
                error = AnalysisError(code, marker)
                error.__cause__ = RuntimeError(marker)
                if code == "history_failed":
                    history = FakeHistoryStore(saved_id=error)
                    app = create_app(analysis_service=Mock(return_value=sample_response()), history_store=history)
                else:
                    app = create_app(analysis_service=Mock(side_effect=error), history_store=FakeHistoryStore())
                response = TestClient(app).post("/api/analyze", json=sample_collection_payload())
                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(
                    response.json(), {"detail": {"code": code, "message": expected_message}}
                )
                self.assertNotIn(marker, response.text)

    def test_unknown_domain_error_codes_and_messages_are_generic(self):
        """Do not echo unallowlisted codes or messages from injected domain boundaries."""

        marker = "unreviewed-code configured secret"
        collection = TestClient(
            create_app(
                collector=Mock(side_effect=CollectionError("unreviewed_code", marker)),
                history_store=FakeHistoryStore(),
            )
        ).post("/api/collect", json={"url": "https://example.com/product"})
        analysis = TestClient(
            create_app(
                analysis_service=Mock(side_effect=AnalysisError("unreviewed_code", marker)),
                history_store=FakeHistoryStore(),
            )
        ).post("/api/analyze", json=sample_collection_payload())
        expected = {
            "detail": {
                "code": "analysis_failed",
                "message": "The analysis could not be completed.",
            }
        }
        for response in (collection, analysis):
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.json(), expected)
            self.assertNotIn(marker, response.text)

    def test_malformed_collection_url_is_rejected_before_collector_work(self):
        """Let request validation reject malformed URLs before any network collection begins."""

        collector = Mock(return_value=sample_collection())
        response = TestClient(create_app(collector=collector, history_store=FakeHistoryStore())).post(
            "/api/collect", json={"url": "not a url"}
        )
        self.assertEqual(response.status_code, 422)
        collector.assert_not_called()

    def test_unknown_and_demo_failures_use_generic_safe_messages(self):
        """Never leak raw bodies, configured credentials, or internal exception text."""

        marker = "fake-secret raw body traceback database password"
        collection = TestClient(
            create_app(collector=Mock(side_effect=RuntimeError(marker)), history_store=FakeHistoryStore())
        ).post("/api/collect", json={"url": "https://example.com/product"})
        self.assertEqual(collection.status_code, 500)
        self.assertEqual(
            collection.json(),
            {
                "detail": {
                    "code": "analysis_failed",
                    "message": "The analysis could not be completed.",
                }
            },
        )
        self.assertNotIn(marker, collection.text)

        unknown = TestClient(
            create_app(analysis_service=Mock(side_effect=RuntimeError(marker)), history_store=FakeHistoryStore())
        ).post("/api/analyze", json=sample_collection_payload())
        self.assertEqual(unknown.status_code, 500)
        self.assertEqual(
            unknown.json(),
            {
                "detail": {
                    "code": "analysis_failed",
                    "message": "The analysis could not be completed.",
                }
            },
        )
        self.assertNotIn(marker, unknown.text)

        demo = TestClient(
            create_app(demo_loader=Mock(side_effect=RuntimeError(marker)), history_store=FakeHistoryStore())
        ).get("/api/demo")
        self.assertEqual(demo.status_code, 500)
        self.assertEqual(
            demo.json(),
            {
                "detail": {
                    "code": "collection_failed",
                    "message": "Bundled demo data could not be loaded.",
                }
            },
        )
        self.assertNotIn(marker, demo.text)


class ApiContractTests(unittest.TestCase):
    """Cover response additions consumed by later API and history endpoints."""

    def test_theme_requires_a_constrained_sentiment(self):
        """Expose the sentiment needed to render each recurring theme."""

        theme = Theme(
            name="Pour control",
            description="Reviewers discuss the precision and speed of the gooseneck pour.",
            mentions=3,
            sentiment="positive",
        )
        self.assertEqual(theme.sentiment, "positive")
        with self.assertRaises(ValidationError):
            Theme(
                name="Pour control",
                description="Reviewers discuss the precision and speed of the gooseneck pour.",
                mentions=3,
                sentiment="mixed",
            )

    def test_public_error_accepts_history_not_found(self):
        """Keep the explicit absent-history code inside the declared public schema."""

        error = PublicError(code="history_not_found", message="That history entry was not found.")
        self.assertEqual(error.code, "history_not_found")

    def test_history_item_preserves_safe_source_summary_metadata(self):
        """Represent history navigation without retaining arbitrary provider content."""

        item = HistoryItem(
            id=7,
            created_at="2026-07-17T12:00:00Z",
            source_title="Aurora Pour-Over Kettle",
            source_url=None,
            extractor="demo",
            is_demo=True,
            review_count=10,
            overall_sentiment="mixed",
        )
        self.assertEqual(item.id, 7)
        self.assertTrue(item.is_demo)

    def test_analysis_response_history_id_is_optional(self):
        """Permit unsaved reports while exposing a saved local-history identifier."""

        self.assertIn("history_id", AnalysisResponse.model_fields)
        self.assertIsNone(AnalysisResponse.model_fields["history_id"].default)


if __name__ == "__main__":
    unittest.main()
