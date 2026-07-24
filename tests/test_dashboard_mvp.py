"""Test dashboard client safety, staged flow, and pure formatting helpers."""

import inspect
import json
import unittest
from contextlib import nullcontext
from unittest.mock import patch

import requests
from streamlit.testing.v1 import AppTest

import dashboard.streamlit_app as streamlit_app
from dashboard.api_client import (
    ApiClientError,
    BackendUnavailable,
    check_health,
    request_analysis,
    request_collection,
    request_demo,
    request_history,
    request_history_report,
    request_import,
    request_import_options,
)
from dashboard.streamlit_app import (
    DASHBOARD_CSS,
    analysis_call,
    history_option,
    metric_values,
    rating_rows,
    review_rows,
    safe_badge_markup,
    safe_theme_card_markup,
    sentiment_rows,
    sentiment_visual,
    source_details,
)


class FakeResponse:
    """Simulate the JSON-capable subset of backend HTTP responses."""

    def __init__(self, payload, *, status_code=200, content_type="application/json"):
        """Configure response payload, status, and declared media type."""

        self.payload = payload
        self.status_code = status_code
        self.headers = {"content-type": content_type}

    def json(self):
        """Return the configured decoded backend payload."""

        return self.payload


class MalformedResponse(FakeResponse):
    """Simulate a response whose body cannot be decoded as JSON."""

    def json(self):
        """Raise the same safe-to-handle decode error as a malformed body."""

        raise ValueError("invalid JSON")


class FakeSession:
    """Simulate HTTP calls while recording their public client contract."""

    def __init__(self, *, get_responses=None, post_responses=None, error=None):
        """Configure route responses or one transport error for every request."""

        self.get_responses = get_responses or {}
        self.post_responses = post_responses or {}
        self.error = error
        self.calls = []

    def get(self, url, timeout):
        """Record and answer a GET request."""

        self.calls.append(("get", url, timeout))
        if self.error:
            raise self.error
        return self.get_responses[url]

    def post(self, url, json, timeout):
        """Record and answer a POST request."""

        self.calls.append(("post", url, json, timeout))
        if self.error:
            raise self.error
        return self.post_responses[url]


class FailingSession:
    """Simulate transport failures at either dashboard client endpoint."""

    def __init__(self, error):
        """Store the transport exception raised by all requests."""

        self.error = error

    def get(self, url, timeout):
        """Raise the configured health transport failure."""

        raise self.error

    def post(self, url, json, timeout):
        """Raise the configured analysis transport failure."""

        raise self.error


def sample_report():
    """Build a representative backend report for client and formatting tests."""

    return {
        "source": {
            "url": "https://example.com/product",
            "title": "Everyday Headphones",
            "extractor": "json_ld",
        },
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
        "reviews": [
            {"id": "r1", "text": "Clear sound and comfortable fit.", "rating": 5},
            {"id": "r2", "text": "Battery is adequate for a normal day.", "rating": 3},
            {"id": "r3", "text": "Microphone quality needs meaningful improvement.", "rating": None},
        ],
    }


def provider_collection(review_count: int) -> dict:
    """Build imported provider evidence with truthful source provenance."""

    return {
        "source": {
            "url": "https://www.amazon.com/dp/B000000000",
            "title": "Fixture product",
            "extractor": "provider_api",
            "is_demo": False,
            "platform": "amazon",
            "provider": "Apify (Axesso)",
            "requested_count": review_count,
            "retrieved_count": review_count,
            "retrieved_at": "2026-07-23T12:00:00Z",
            "cache_status": "miss",
        },
        "reviews": [
            {
                "id": f"r{index + 1}",
                "text": f"Imported review number {index + 1} has useful product evidence.",
                "rating": 5,
            }
            for index in range(review_count)
        ],
    }


def provider_report(imported_count: int, analyzed_count: int = 40) -> dict:
    """Build one rendered report for a bounded imported subset."""

    collection = provider_collection(imported_count)
    reviews = collection["reviews"][:analyzed_count]
    return {
        "source": collection["source"],
        "metrics": {
            "review_count": analyzed_count,
            "rated_count": analyzed_count,
            "average_rating": 5.0,
            "positive_percentage": 100.0,
            "sentiment_counts": {
                "positive": analyzed_count,
                "neutral": 0,
                "negative": 0,
            },
            "rating_distribution": {
                "1": 0,
                "2": 0,
                "3": 0,
                "4": 0,
                "5": analyzed_count,
            },
        },
        "insights": {
            "summary": "The analyzed subset consistently describes useful product evidence.",
            "overall_sentiment": "positive",
            "themes": [
                {
                    "name": "Consistency",
                    "description": "Customers consistently report useful product evidence.",
                    "mentions": analyzed_count,
                    "sentiment": "positive",
                }
            ],
            "strengths": ["Consistent results"],
            "weaknesses": [],
            "actions": [],
            "review_sentiments": [
                {"review_id": review["id"], "sentiment": "positive"}
                for review in reviews
            ],
        },
        "reviews": reviews,
    }


class DashboardClientTests(unittest.TestCase):
    """Group HTTP-client timeout, decoding, and safe-error contracts."""

    def test_health_uses_a_short_timeout(self):
        """Keep readiness probing on its dedicated short timeout."""

        session = FakeSession(
            get_responses={
                "http://127.0.0.1:8000/health": FakeResponse({"status": "ok"})
            }
        )
        self.assertTrue(check_health("http://127.0.0.1:8000", session=session))
        self.assertEqual(session.calls, [("get", "http://127.0.0.1:8000/health", 2)])

    def test_health_failure_returns_false_without_os_details(self):
        """Reduce health transport failures to false without leaking OS details."""

        session = FailingSession(requests.ConnectionError("OS detail"))
        self.assertFalse(check_health("http://127.0.0.1:8000", session=session))

    def test_connection_failure_is_backend_unavailable(self):
        """Reduce every stage's connection failure to the safe unavailable error."""

        for request in (
            lambda session: request_collection("https://example.com", "http://127.0.0.1:8000", session=session),
            lambda session: request_demo("http://127.0.0.1:8000", session=session),
            lambda session: request_analysis({"source": {}, "reviews": []}, "http://127.0.0.1:8000", session=session),
            lambda session: request_history("http://127.0.0.1:8000", session=session),
            lambda session: request_history_report(1, "http://127.0.0.1:8000", session=session),
        ):
            with self.subTest(request=request):
                with self.assertRaises(BackendUnavailable) as raised:
                    request(FailingSession(requests.ConnectionError("OS detail")))
                self.assertEqual(str(raised.exception), "The FastAPI backend is not reachable.")

    def test_timeout_failure_is_backend_unavailable_for_every_stage(self):
        """Reduce every stage's timeout failure to the safe unavailable error."""

        for request in (
            lambda session: request_collection("https://example.com", "http://127.0.0.1:8000", session=session),
            lambda session: request_demo("http://127.0.0.1:8000", session=session),
            lambda session: request_analysis({"source": {}, "reviews": []}, "http://127.0.0.1:8000", session=session),
            lambda session: request_history("http://127.0.0.1:8000", session=session),
            lambda session: request_history_report(1, "http://127.0.0.1:8000", session=session),
        ):
            with self.subTest(request=request):
                with self.assertRaises(BackendUnavailable):
                    request(FailingSession(requests.Timeout("network detail")))

    def test_structured_api_error_is_preserved(self):
        """Preserve documented error code and message from JSON detail."""

        session = FakeSession(post_responses={
            "http://127.0.0.1:8000/api/collect": FakeResponse(
                {"detail": {"code": "no_reviews", "message": "At least two public reviews are required."}},
                status_code=422,
            )
        })
        with self.assertRaises(ApiClientError) as raised:
            request_collection("https://example.com", "http://127.0.0.1:8000", session=session)
        self.assertEqual(raised.exception.code, "no_reviews")
        self.assertEqual(str(raised.exception), "At least two public reviews are required.")

    def test_structured_api_error_discards_sensitive_extra_fields(self):
        """Preserve exactly safe nested fields and discard untrusted extras."""

        session = FakeSession(post_responses={
            "http://127.0.0.1:8000/api/collect": FakeResponse(
                {"detail": {"code": "no_reviews", "message": "At least two reviews are required.", "token": "secret-value", "raw_body": "private details"}},
                status_code=422,
            )
        })
        with self.assertRaises(ApiClientError) as raised:
            request_collection("https://example.com", "http://127.0.0.1:8000", session=session)
        self.assertEqual(raised.exception.code, "no_reviews")
        self.assertEqual(str(raised.exception), "At least two reviews are required.")
        self.assertNotIn("secret-value", str(raised.exception))
        self.assertNotIn("private details", str(raised.exception))

    def test_collection_uses_staged_endpoint_payload_and_timeout(self):
        """Collect a URL before analysis with its dedicated timeout budget."""

        collection = {"source": {"url": "https://example.com"}, "reviews": []}
        session = FakeSession(post_responses={"http://127.0.0.1:8000/api/collect": FakeResponse(collection)})
        self.assertEqual(request_collection("https://example.com", "http://127.0.0.1:8000/", session=session), collection)
        self.assertEqual(session.calls, [("post", "http://127.0.0.1:8000/api/collect", {"url": "https://example.com"}, 15)])

    def test_import_options_and_import_use_provider_neutral_contracts(self):
        """Load choices cheaply and give imports a bounded Actor-sized timeout."""

        options = {
            "platforms": [
                {
                    "key": "amazon",
                    "label": "Amazon product",
                    "limits": [10, 20, 50, 100],
                }
            ]
        }
        collection = {"source": {"provider": "Apify (Axesso)"}, "reviews": [{}, {}]}
        session = FakeSession(
            get_responses={
                "http://127.0.0.1:8000/api/import/options": FakeResponse(options)
            },
            post_responses={
                "http://127.0.0.1:8000/api/import": FakeResponse(collection)
            },
        )

        self.assertEqual(
            request_import_options("http://127.0.0.1:8000/", session=session),
            options,
        )
        self.assertEqual(
            request_import(
                "amazon",
                "https://www.amazon.com/dp/B000000000",
                20,
                False,
                "http://127.0.0.1:8000/",
                session=session,
            ),
            collection,
        )
        self.assertEqual(
            session.calls,
            [
                ("get", "http://127.0.0.1:8000/api/import/options", 5),
                (
                    "post",
                    "http://127.0.0.1:8000/api/import",
                    {
                        "platform": "amazon",
                        "url": "https://www.amazon.com/dp/B000000000",
                        "limit": 20,
                        "refresh": False,
                    },
                    130,
                ),
            ],
        )

    def test_demo_uses_staged_endpoint_and_timeout(self):
        """Load deterministic demo collection data with its short work budget."""

        collection = {"source": {"url": "demo"}, "reviews": []}
        session = FakeSession(get_responses={"http://127.0.0.1:8000/api/demo": FakeResponse(collection)})
        self.assertEqual(request_demo("http://127.0.0.1:8000/", session=session), collection)
        self.assertEqual(session.calls, [("get", "http://127.0.0.1:8000/api/demo", 15)])

    def test_analysis_sends_only_collection_source_and_reviews(self):
        """Analyze an already collected payload using only its required fields."""

        collection = {"source": {"url": "https://example.com"}, "reviews": [{"text": "Good"}], "unused": "discarded"}
        session = FakeSession(post_responses={"http://127.0.0.1:8000/api/analyze": FakeResponse(sample_report())})
        self.assertEqual(request_analysis(collection, "http://127.0.0.1:8000/", session=session), sample_report())
        self.assertEqual(session.calls, [("post", "http://127.0.0.1:8000/api/analyze", {"source": collection["source"], "reviews": collection["reviews"]}, 45)])

    def test_history_uses_list_endpoint_and_timeout(self):
        """Request run history with its own response shape and timeout."""

        history = [{"id": 1, "source": "Demo"}]
        session = FakeSession(get_responses={"http://127.0.0.1:8000/api/history": FakeResponse(history)})
        self.assertEqual(request_history("http://127.0.0.1:8000/", session=session), history)
        self.assertEqual(session.calls, [("get", "http://127.0.0.1:8000/api/history", 5)])

    def test_history_report_uses_object_endpoint_and_timeout(self):
        """Request one stored report with its own response shape and timeout."""

        report = sample_report()
        session = FakeSession(get_responses={"http://127.0.0.1:8000/api/history/7": FakeResponse(report)})
        self.assertEqual(request_history_report(7, "http://127.0.0.1:8000/", session=session), report)
        self.assertEqual(session.calls, [("get", "http://127.0.0.1:8000/api/history/7", 5)])

    def test_invalid_history_id_is_rejected_without_a_request(self):
        """Reject locally invalid history IDs without reaching the backend."""

        for run_id in (0, -1, True, "1"):
            with self.subTest(run_id=run_id):
                session = FakeSession()
                with self.assertRaises(ApiClientError) as raised:
                    request_history_report(run_id, "http://127.0.0.1:8000", session=session)
                self.assertEqual(raised.exception.code, "history_not_found")
                self.assertEqual(str(raised.exception), "That history entry was not found.")
                self.assertEqual(session.calls, [])

    def test_malformed_error_response_uses_the_generic_safe_error(self):
        """Never surface an untrusted error response payload to the dashboard."""

        session = FakeSession(post_responses={
            "http://127.0.0.1:8000/api/collect": MalformedResponse(None, status_code=500, content_type="text/html")
        })
        with self.assertRaises(ApiClientError) as raised:
            request_collection("https://example.com", "http://127.0.0.1:8000", session=session)
        self.assertEqual(raised.exception.code, "analysis_failed")
        self.assertEqual(str(raised.exception), "The request could not be completed.")

    def test_success_shape_mismatch_uses_the_generic_invalid_response_error(self):
        """Reject successful payloads that do not match each endpoint contract."""

        cases = (
            (lambda session: request_collection("https://example.com", "http://127.0.0.1:8000", session=session), FakeSession(post_responses={"http://127.0.0.1:8000/api/collect": FakeResponse([])})),
            (lambda session: request_demo("http://127.0.0.1:8000", session=session), FakeSession(get_responses={"http://127.0.0.1:8000/api/demo": FakeResponse([])})),
            (lambda session: request_analysis({"source": {}, "reviews": []}, "http://127.0.0.1:8000", session=session), FakeSession(post_responses={"http://127.0.0.1:8000/api/analyze": FakeResponse([])})),
            (lambda session: request_history("http://127.0.0.1:8000", session=session), FakeSession(get_responses={"http://127.0.0.1:8000/api/history": FakeResponse(["not-an-object"])})),
            (lambda session: request_history_report(1, "http://127.0.0.1:8000", session=session), FakeSession(get_responses={"http://127.0.0.1:8000/api/history/1": FakeResponse([])})),
        )
        for request, session in cases:
            with self.subTest(request=request):
                with self.assertRaises(ApiClientError) as raised:
                    request(session)
                self.assertEqual(raised.exception.code, "analysis_failed")
                self.assertEqual(str(raised.exception), "The backend returned an invalid response.")


class DashboardFormattingTests(unittest.TestCase):
    """Group visual-token and report-formatting regression contracts."""

    def test_accessible_semantic_css_and_controls_keep_the_design_tokens(self):
        """Keep primary, focus, and named semantic tokens in the responsive CSS."""

        self.assertIn('[data-testid="stBaseButton-primaryFormSubmit"]', DASHBOARD_CSS)
        self.assertIn('[data-testid="stToolbar"]', DASHBOARD_CSS)
        self.assertIn("#2563eb", DASHBOARD_CSS)
        self.assertIn(":focus-visible", DASHBOARD_CSS)
        for label, icon, token in (
            ("Positive", "✅", "--ri-positive"),
            ("Negative", "⚠️", "--ri-negative"),
            ("Neutral", "➖", "--ri-neutral"),
            ("Mixed", "↔", "--ri-mixed"),
        ):
            self.assertIn(label, streamlit_app.__doc__ or "")
            self.assertIn(icon, inspect.getsource(streamlit_app))
            self.assertIn(token, DASHBOARD_CSS)
        self.assertNotIn("stRadio", DASHBOARD_CSS)

    def test_recovery_guidance_uses_supported_full_application_command(self):
        """Direct recovery through the supported supervisor entry point."""

        self.assertTrue(hasattr(streamlit_app, "APP_COMMAND"))
        self.assertEqual(
            streamlit_app.APP_COMMAND,
            r".\.venv\Scripts\python.exe run_app.py",
        )
        self.assertNotIn("uvicorn", streamlit_app.APP_COMMAND.lower())

    def test_metrics_and_charts_use_response_values(self):
        """Transform report values into deterministic metric and chart displays."""

        report = sample_report()
        self.assertEqual(metric_values(report), ("3", "4.0 / 5", "66.7%", "Positive"))
        self.assertEqual(sentiment_rows(report)[0], {"Sentiment": "Positive", "Reviews": 2})
        self.assertEqual(
            [row["Sentiment"] for row in sentiment_rows(report)],
            ["Positive", "Neutral", "Negative"],
        )
        self.assertEqual(rating_rows(report)[4], {"Rating": "5 star", "Reviews": 1})

    def test_missing_average_rating_has_a_clear_display(self):
        """Render unrated reports with an explicit nonnumeric label."""

        report = sample_report()
        report["metrics"]["average_rating"] = None
        self.assertEqual(metric_values(report)[1], "Not rated")

    def test_sentiment_visual_has_distinct_labeled_safe_fallbacks(self):
        """Map every approved sentiment to its text, icon, and distinct semantic token."""

        expected = {
            "positive": ("✅", "Positive", "positive"),
            "negative": ("⚠️", "Negative", "negative"),
            "neutral": ("➖", "Neutral", "neutral"),
            "mixed": ("↔", "Mixed", "mixed"),
        }
        visuals = {}
        for input_value, expectation in expected.items():
            visual = sentiment_visual(input_value)
            self.assertEqual((visual.icon, visual.label, visual.semantic), expectation)
            visuals[input_value] = (visual.foreground, visual.background, visual.border)
        self.assertEqual(sentiment_visual("unrecognized").semantic, "neutral")
        self.assertEqual(len(set(visuals.values())), 4)

    def test_review_rows_preserve_evidence_before_and_join_sentiment_after_analysis(self):
        """Show extracted facts first and exact review sentiment joins only after analysis."""

        collection = {
            "source": {"extractor": "json_ld"},
            "reviews": [
                {"id": "b", "rating": 2, "date": "2025-01-02", "text": "Second"},
                {"id": "a", "rating": 5, "date": "2025-01-01", "text": "First"},
            ],
        }
        before = review_rows(collection)
        self.assertEqual([row["Review"] for row in before], ["Second", "First"])
        self.assertEqual(before[0]["Rating"], 2)
        self.assertEqual(before[0]["Date"], "2025-01-02")
        self.assertEqual(before[0]["Extractor"], "JSON-LD")
        self.assertNotIn("Sentiment", before[0])

        report = sample_report()
        report["insights"]["review_sentiments"] = [
            {"review_id": "a", "sentiment": "positive"},
            {"review_id": "b", "sentiment": "negative"},
        ]
        after = review_rows(collection, report)
        self.assertEqual(after[0]["Sentiment"], "⚠️ Negative")
        self.assertEqual(after[0]["Sentiment semantic"], "negative")
        self.assertEqual(after[1]["Sentiment"], "✅ Positive")

    def test_review_rows_label_html_card_fallback_provenance(self):
        """Name the collector's HTML-card extractor clearly in visible evidence."""

        collection = {
            "source": {"extractor": "html_cards"},
            "reviews": [{"id": "review-1", "text": "A complete written review."}],
        }

        self.assertEqual(review_rows(collection)[0]["Extractor"], "HTML fallback")

    def test_safe_badge_markup_escapes_untrusted_labels(self):
        """Escape customer/model text before it is interpolated into styled HTML."""

        markup = safe_badge_markup(sentiment_visual("positive"), "<script>alert('x')</script>")
        self.assertNotIn("<script>", markup)
        self.assertIn("&lt;script&gt;", markup)
        self.assertIn("✅", markup)

    def test_theme_card_markup_uses_a_semantic_card_and_escapes_all_live_content(self):
        """Render every live theme field inside the semantic card rather than a bare badge."""

        markup = safe_theme_card_markup(
            sentiment_visual("negative"),
            "<script>theme</script>",
            "<b>description</b>",
            "<em>7</em>",
        )
        self.assertIn('class="ri-card ri-negative"', markup)
        self.assertIn("⚠️ Negative", markup)
        self.assertIn("&lt;script&gt;theme&lt;/script&gt;", markup)
        self.assertIn("&lt;b&gt;description&lt;/b&gt;", markup)
        self.assertIn("&lt;em&gt;7&lt;/em&gt; mentions", markup)
        self.assertNotIn("<script>", markup)
        self.assertIn("safe_theme_card_markup(visual, title, description, mentions)", inspect.getsource(streamlit_app))

    def test_theme_cards_share_one_anatomy_across_every_sentiment_state(self):
        """Keep positive, neutral, negative, and mixed themes structurally consistent."""

        for semantic in ("positive", "neutral", "negative", "mixed"):
            with self.subTest(semantic=semantic):
                visual = sentiment_visual(semantic)
                markup = safe_theme_card_markup(visual, "Theme", "Description", 3)
                self.assertIn(f'class="ri-card ri-{semantic}"', markup)
                self.assertIn(f'class="ri-badge ri-{semantic}"', markup)
                self.assertIn(f"{visual.icon} {visual.label}", markup)
                self.assertEqual(markup.count("<strong>"), 1)
                self.assertEqual(markup.count("<p>"), 1)
                self.assertEqual(markup.count("<small>"), 1)

    def test_section_heading_markup_establishes_hierarchy_and_escapes_copy(self):
        """Build one reusable escaped heading for every major report section."""

        markup = streamlit_app.safe_section_heading_markup(
            "Analysis",
            "Customer signals",
            "Compare sentiment and rating patterns across the review set.",
        )
        self.assertIn('class="ri-section-heading"', markup)
        self.assertIn('class="ri-section-heading__eyebrow"', markup)
        self.assertIn("<h2>Customer signals</h2>", markup)
        escaped = streamlit_app.safe_section_heading_markup(
            "<script>alert('x')</script>",
            "<Signals>",
            "<b>Unsafe</b>",
        )
        self.assertNotIn("<script>", escaped)
        self.assertNotIn("<b>", escaped)
        self.assertIn("&lt;Signals&gt;", escaped)

    def test_metric_card_markup_escapes_all_values_and_uses_semantic_classes(self):
        """Keep live metric content escaped inside one semantic metric surface."""

        markup = streamlit_app.safe_metric_card_markup(
            label="<Reviews>",
            value="<strong>5</strong>",
            detail="<em>Analyzed</em>",
            semantic="positive",
        )

        self.assertNotIn("<Reviews>", markup)
        self.assertNotIn("<strong>", markup)
        self.assertNotIn("<em>", markup)
        self.assertIn("&lt;Reviews&gt;", markup)
        self.assertIn("&lt;strong&gt;5&lt;/strong&gt;", markup)
        self.assertIn("&lt;em&gt;Analyzed&lt;/em&gt;", markup)
        self.assertIn("ri-metric-card", markup)
        self.assertIn("ri-positive", markup)

    def test_panel_markup_escapes_heading_and_every_list_item(self):
        """Escape every model-supplied panel value while retaining semantic context."""

        markup = streamlit_app.safe_panel_markup(
            sentiment_visual("negative"),
            "<Concerns>",
            ["<script>alert('x')</script>", "<b>Price</b>"],
        )

        self.assertIn('class="ri-insight-panel ri-negative"', markup)
        self.assertIn("⚠️", markup)
        self.assertIn("&lt;Concerns&gt;", markup)
        self.assertIn("&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;", markup)
        self.assertIn("&lt;b&gt;Price&lt;/b&gt;", markup)
        self.assertNotIn("<Concerns>", markup)
        self.assertNotIn("<script>", markup)
        self.assertNotIn("<b>", markup)
        self.assertEqual(markup.count("<li>"), 2)

    def test_recommended_actions_use_a_distinct_informational_panel(self):
        """Keep actions visually parallel to insights without mislabeling sentiment."""

        markup = streamlit_app.safe_panel_markup(
            streamlit_app._INFO_VISUAL,
            "Recommended actions",
            ["Improve temperature consistency"],
        )
        self.assertIn('class="ri-insight-panel ri-info"', markup)
        self.assertIn(f"{streamlit_app._INFO_VISUAL.icon} Recommended actions", markup)
        self.assertIn("--ri-info", DASHBOARD_CSS)
        self.assertIn(".ri-info", DASHBOARD_CSS)

    def test_history_timestamp_drops_microseconds_and_timezone_suffixes(self):
        """Keep history labels concise and stable across stored ISO timestamp variants."""

        self.assertEqual(
            streamlit_app.format_history_timestamp("2025-05-12T10:42:00.123456Z"),
            "2025-05-12 10:42:00",
        )
        self.assertEqual(
            streamlit_app.format_history_timestamp("2025-05-12T10:42:00.987654+05:30"),
            "2025-05-12 10:42:00",
        )
        self.assertEqual(streamlit_app.format_history_timestamp("Unknown time"), "Unknown time")

    def test_report_css_defines_responsive_semantic_layout_primitives(self):
        """Expose the reusable report surfaces and both approved responsive breakpoints."""

        for selector in (
            ".ri-report-hero",
            ".ri-section-heading",
            ".ri-metric-grid",
            ".ri-insight-grid",
            ".ri-theme-grid",
            ".ri-chart-card",
        ):
            self.assertIn(selector, DASHBOARD_CSS)
        self.assertIn("--ri-section-gap", DASHBOARD_CSS)
        self.assertIn("--ri-card-gap", DASHBOARD_CSS)
        self.assertIn("@media (max-width: 1100px)", DASHBOARD_CSS)
        self.assertIn("@media (max-width: 900px)", DASHBOARD_CSS)
        self.assertIn("@media (max-width: 640px)", DASHBOARD_CSS)

    def test_medium_width_reflows_dense_report_grids_before_the_sidebar_squeezes_them(self):
        """Keep report cards readable when the open sidebar reduces content width."""

        medium_css = DASHBOARD_CSS.split("@media (max-width: 1100px)", 1)[1].split(
            "@media (max-width: 900px)", 1
        )[0]
        self.assertIn(".ri-metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }", medium_css)
        self.assertIn(".ri-theme-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }", medium_css)
        self.assertIn(".ri-insight-grid { grid-template-columns: 1fr; }", medium_css)

    def test_page_configuration_uses_streamlits_mobile_safe_sidebar_state(self):
        """Let Streamlit collapse the sidebar automatically on narrow screens."""

        with (
            patch.object(streamlit_app.st, "set_page_config") as set_page_config,
            patch.object(streamlit_app.st, "markdown"),
        ):
            streamlit_app._configure_page()

        set_page_config.assert_called_once_with(
            page_title="Review Intelligence",
            page_icon="💬",
            layout="wide",
            initial_sidebar_state="auto",
        )

    def test_sidebar_buttons_have_explicit_readable_contrast(self):
        """Keep secondary sidebar button text dark against its white surface."""

        selector = '[data-testid="stSidebar"] .stButton > button {'
        self.assertIn(selector, DASHBOARD_CSS)
        rule = DASHBOARD_CSS.split(selector, 1)[1].split("}", 1)[0]
        self.assertIn("color: var(--ri-navy) !important", rule)
        self.assertIn("background: #ffffff !important", rule)
        label_selector = '[data-testid="stSidebar"] .stButton > button p {'
        self.assertIn(label_selector, DASHBOARD_CSS)
        label_rule = DASHBOARD_CSS.split(label_selector, 1)[1].split("}", 1)[0]
        self.assertIn("color: inherit !important", label_rule)

    def test_theme_grid_caps_desktop_rows_at_three_and_prevents_badge_collisions(self):
        """Keep theme cards scan-friendly with separate badge and title rows."""

        self.assertIn(
            ".ri-theme-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }",
            DASHBOARD_CSS,
        )
        self.assertIn(
            ".ri-theme-grid .ri-card { height: 100%; margin: 0; display: grid;",
            DASHBOARD_CSS,
        )
        self.assertIn(".ri-theme-grid .ri-badge { width: max-content; max-width: 100%; }", DASHBOARD_CSS)
        tablet_css = DASHBOARD_CSS.split("@media (max-width: 900px)", 1)[1].split("@media (max-width: 640px)", 1)[0]
        self.assertIn(".ri-theme-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }", tablet_css)
        self.assertIn(".ri-insight-grid { grid-template-columns: 1fr; }", tablet_css)

    def test_chart_specs_use_semantic_colors_without_warning_prone_bindings(self):
        """Build deterministic responsive bars without scale-bound interactions or stacking fields."""

        self.assertTrue(hasattr(streamlit_app, "sentiment_chart_spec"))
        self.assertTrue(hasattr(streamlit_app, "rating_chart_spec"))
        sentiment_spec = streamlit_app.sentiment_chart_spec(sample_report())
        rating_spec = streamlit_app.rating_chart_spec(sample_report())

        self.assertEqual(sentiment_spec["mark"]["type"], "bar")
        self.assertEqual(sentiment_spec["height"], 260)
        self.assertEqual(
            sentiment_spec["encoding"]["color"]["scale"],
            {
                "domain": ["Positive", "Neutral", "Negative"],
                "range": ["#15803d", "#a16207", "#b91c1c"],
            },
        )
        self.assertEqual(rating_spec["encoding"]["color"]["value"], "#2563eb")
        for spec in (sentiment_spec, rating_spec):
            serialized = json.dumps(spec)
            self.assertEqual(spec["width"], "container")
            self.assertIsNone(spec["encoding"]["y"]["stack"])
            self.assertEqual(spec["encoding"]["y"]["scale"]["domain"][0], 0)
            self.assertGreaterEqual(spec["encoding"]["y"]["scale"]["domain"][1], 1)
            self.assertNotIn('"params"', serialized)
            self.assertNotIn('"bind"', serialized)
            self.assertNotIn("Reviews_start", serialized)
            self.assertNotIn("Reviews_end", serialized)

    def test_compact_evidence_keeps_rows_without_repeating_the_section_heading(self):
        """Keep pre-analysis evidence prominent and make only the report duplicate compact."""

        class EvidenceRecorder:
            """Record the evidence widgets emitted by one render mode."""

            def __init__(self):
                """Initialize captured section headings and dataframes."""

                self.subheaders = []
                self.dataframes = []

            def subheader(self, label):
                """Capture a rendered evidence section heading."""

                self.subheaders.append(label)

            def header(self, label):
                """Capture a legacy top-level heading if one is rendered."""

                self.subheaders.append(label)

            def caption(self, _label):
                """Accept supporting copy without affecting the assertion state."""

                return None

            def dataframe(self, rows, **options):
                """Capture normalized rows and display options."""

                self.dataframes.append((rows, options))

            def info(self, _message):
                """Accept the empty-evidence message for recorder completeness."""

                return None

        collection = {
            "source": {"extractor": "json_ld"},
            "reviews": [{"id": "r1", "text": "Visible evidence", "rating": 5}],
        }
        full = EvidenceRecorder()
        compact = EvidenceRecorder()

        self.assertIn("compact", inspect.signature(streamlit_app._render_evidence).parameters)
        with patch.object(streamlit_app, "st", full):
            streamlit_app._render_evidence(collection)
        with patch.object(streamlit_app, "st", compact):
            streamlit_app._render_evidence(collection, compact=True)

        self.assertEqual(full.subheaders, ["Review evidence"])
        self.assertEqual(compact.subheaders, [])
        self.assertEqual(full.dataframes[0][0][0]["Review"], "Visible evidence")
        self.assertEqual(compact.dataframes[0][0][0]["Review"], "Visible evidence")
        self.assertGreater(full.dataframes[0][1]["height"], compact.dataframes[0][1]["height"])

    def test_report_layout_consumes_escaped_semantic_markup_primitives(self):
        """Compose the report grids only through helpers that escape live values."""

        report_source = inspect.getsource(streamlit_app._render_report)
        themes_source = inspect.getsource(streamlit_app._render_themes)
        for call in ("safe_metric_card_markup", "safe_badge_markup", "safe_panel_markup", "html.escape"):
            self.assertIn(call, report_source)
        self.assertIn("safe_theme_card_markup", themes_source)
        self.assertIn("ri-metric-grid", report_source)
        self.assertIn("ri-theme-grid", themes_source)
        self.assertIn("ri-insight-grid", report_source)

    def test_history_option_exposes_source_time_sentiment_and_demo_status(self):
        """Make stored history provenance recognizable without loading its report."""

        option = history_option(
            {
                "id": 7,
                "created_at": "2025-05-12T10:42:00",
                "source_title": "Example product",
                "overall_sentiment": "positive",
                "is_demo": True,
            }
        )
        self.assertIn("2025-05-12", option)
        self.assertIn("Example product", option)
        self.assertIn("Positive", option)
        self.assertIn("DEMO DATA", option)

    def test_provider_source_details_show_origin_counts_time_and_cache(self):
        """Make imported evidence provenance visible before and after analysis."""

        details = source_details(
            {
                "url": "https://www.amazon.com/dp/B000000000",
                "extractor": "provider_api",
                "platform": "amazon",
                "provider": "Apify (Axesso)",
                "requested_count": 10,
                "retrieved_count": 7,
                "retrieved_at": "2026-07-22T12:00:00+00:00",
                "cache_status": "hit",
            },
            review_count=7,
        )

        joined = " ".join(details)
        for value in (
            "https://www.amazon.com/dp/B000000000",
            "Amazon via Apify (Axesso)",
            "Retrieved 7 usable written reviews - Requested 10",
            "2026-07-22 12:00:00",
            "Cached result",
        ):
            self.assertIn(value, joined)

    def test_source_details_discloses_only_analyzed_report_subsets(self):
        """Distinguish imported evidence from a report containing only the first 40."""

        source = provider_collection(100)["source"]

        pre_analysis = source_details(source, review_count=100)
        report = source_details(source, review_count=40)

        self.assertNotIn("reviews analyzed", " ".join(pre_analysis))
        self.assertIn("40 of 100 reviews analyzed", " ".join(report))

    def test_analysis_call_sends_at_most_first_forty_without_mutating_import(self):
        """Copy the bounded analysis payload while preserving order and provenance."""

        for review_count in (40, 50, 100):
            with self.subTest(review_count=review_count):
                collection = provider_collection(review_count)
                original = json.loads(json.dumps(collection))
                calls = []

                def fake_request(received_collection, received_base_url):
                    """Record the exact staged UI client call without a network request."""

                    calls.append((received_collection, received_base_url))
                    return {"ok": True}

                self.assertEqual(
                    analysis_call(collection, "http://api", request=fake_request),
                    {"ok": True},
                )
                submitted, base_url = calls[0]
                self.assertEqual(base_url, "http://api")
                self.assertEqual(
                    submitted["reviews"],
                    collection["reviews"][:40],
                )
                self.assertEqual(submitted["source"], collection["source"])
                self.assertEqual(
                    submitted["source"]["retrieved_count"],
                    review_count,
                )
                self.assertEqual(collection, original)
                self.assertIsNot(submitted, collection)
        self.assertEqual(list(inspect.signature(analysis_call).parameters), ["collection", "base_url", "request"])

    def test_failed_refresh_preserves_displayed_collection(self):
        """Keep the last good evidence when an explicit provider refresh fails."""

        previous = {"source": {"provider": "Outscraper"}, "reviews": [{"id": "r1"}]}

        class StateRecorder:
            """Provide the Streamlit state and messages used by the helper."""

            def __init__(self):
                """Initialize previous state and captured errors."""

                self.session_state = {"collection": previous}
                self.errors = []

            def spinner(self, _label):
                """Return a no-op spinner context."""

                return nullcontext()

            def error(self, message):
                """Capture the safe provider error."""

                self.errors.append(message)

        recorder = StateRecorder()
        with (
            patch.object(streamlit_app, "st", recorder),
            patch.object(streamlit_app, "check_health", return_value=True),
            patch.object(
                streamlit_app,
                "request_import",
                side_effect=ApiClientError("provider_unavailable", "Provider unavailable."),
            ),
        ):
            streamlit_app._import_collection(
                "http://api",
                "amazon",
                "https://www.amazon.com/dp/B000000000",
                20,
                refresh=True,
            )

        self.assertIs(recorder.session_state["collection"], previous)
        self.assertEqual(recorder.errors, ["Provider unavailable."])

    def test_staged_ui_source_removes_retired_controls_and_keeps_explicit_demo(self):
        """Guard the staged flow against obsolete controls and implicit demo recovery."""

        source = inspect.getsource(streamlit_app)
        for retired in ("st.radio", "Gemini", "GOOGLE_API_KEY", "provider_label"):
            self.assertNotIn(retired, source)
        self.assertIn("request_demo", source)
        self.assertIn("request_import_options", source)
        self.assertIn("request_import", source)
        self.assertIn('"Review source"', source)
        self.assertIn('"Review limit"', source)
        self.assertIn('"Import reviews"', source)
        self.assertIn('"Refresh from source"', source)
        self.assertIn("may consume provider free-tier usage", source)
        self.assertIn("unofficial scraping services", source)
        self.assertIn("responsible for permitted use and retention", source)
        self.assertIn("DEMO DATA", source)
        self.assertIn('st.expander("Supporting review evidence"', source)
        self.assertIn("Executive summary", source)
        self.assertIn("Customer signals", source)
        self.assertIn("Recommended actions", source)
        self.assertIn("How it works", source)
        self.assertNotIn('st.header("Extracted reviews (evidence)")', source)
        self.assertNotIn("except BackendUnavailable:\n                st.session_state[\"collection\"] = request_demo", source)


class DashboardRuntimeTests(unittest.TestCase):
    """Verify staged dashboard behavior through Streamlit's retained runtime harness."""

    def test_import_controls_load_options_without_passive_provider_work(self):
        """Render backend-driven choices without running an import on page load."""

        options = {
            "platforms": [
                {
                    "key": "amazon",
                    "label": "Amazon product",
                    "limits": [10, 20, 50, 100],
                },
                {
                    "key": "google_maps",
                    "label": "Google Maps place",
                    "limits": [10, 20, 50, 100],
                },
            ]
        }
        app = AppTest.from_file(streamlit_app.__file__)
        with (
            patch("dashboard.api_client.check_health", return_value=True),
            patch("dashboard.api_client.request_import_options", return_value=options) as option_call,
            patch("dashboard.api_client.request_import") as import_call,
        ):
            app.run(timeout=30)

        self.assertEqual(list(app.exception), [])
        self.assertIn("Review source", [element.label for element in app.selectbox])
        self.assertIn("Review limit", [element.label for element in app.selectbox])
        self.assertEqual([element.label for element in app.text_input], ["Source URL"])
        self.assertEqual(
            app.text_input[0].proto.placeholder,
            "Paste an Amazon product or Google Maps place URL",
        )
        self.assertNotIn(
            "Amazon product URL",
            [element.label for element in app.text_input],
        )
        self.assertNotIn(
            "Google Maps place URL",
            [element.label for element in app.text_input],
        )
        limit_selector = next(
            element for element in app.selectbox if element.label == "Review limit"
        )
        self.assertEqual(limit_selector.options, ["10", "20", "50", "100"])
        self.assertEqual(limit_selector.value, 20)
        self.assertIn("Import reviews", [element.label for element in app.button])
        option_call.assert_called_once()
        import_call.assert_not_called()

    def test_fifty_imported_reviews_render_and_analyze_only_first_forty(self):
        """Display all evidence, disclose the cap, and submit one first-40 copy."""

        collection = provider_collection(50)
        report = provider_report(50)
        app = AppTest.from_file(streamlit_app.__file__)
        app.session_state["collection"] = collection
        with (
            patch("dashboard.api_client.check_health", return_value=True),
            patch("dashboard.api_client.request_analysis", return_value=report) as request_call,
            patch("dashboard.api_client.request_history", return_value=[]),
        ):
            app.run(timeout=30)
            self.assertEqual(len(app.dataframe[0].value), 50)
            self.assertIn(
                "Groq will analyze the first 40 of 50 imported reviews.",
                [element.value for element in app.caption],
            )
            next(
                button for button in app.button if button.label == "Analyze with Groq"
            ).click()
            app.run(timeout=30)

        submitted = request_call.call_args.args[0]
        self.assertEqual(submitted["reviews"], collection["reviews"][:40])
        self.assertEqual(submitted["source"]["retrieved_count"], 50)
        self.assertEqual(len(collection["reviews"]), 50)
        self.assertIn(
            "40 of 50 reviews analyzed",
            " ".join(element.value for element in app.caption),
        )

    def test_pre_analysis_runtime_keeps_evidence_visible_without_an_expander(self):
        """Render collected evidence directly before any report exists."""

        report = sample_report()
        app = AppTest.from_file(streamlit_app.__file__)
        app.session_state["collection"] = {"source": report["source"], "reviews": report["reviews"]}

        app.run(timeout=30)

        self.assertEqual(list(app.exception), [])
        self.assertEqual(len(app.expander), 0)
        self.assertEqual(len(app.dataframe), 1)
        self.assertIn("Review evidence", [element.value for element in app.subheader])
        self.assertIn("Analyze with Groq", [element.label for element in app.button])

    def test_successful_analysis_transition_renders_only_the_report(self):
        """Rerun immediately after analysis so the evidence workspace is not duplicated."""

        report = sample_report()
        app = AppTest.from_file(streamlit_app.__file__)
        app.session_state["collection"] = {"source": report["source"], "reviews": report["reviews"]}
        with (
            patch("dashboard.api_client.check_health", return_value=True),
            patch("dashboard.api_client.request_analysis", return_value=report),
            patch("dashboard.api_client.request_history", return_value=[]),
        ):
            app.run(timeout=30)
            next(button for button in app.button if button.label == "Analyze with Groq").click()
            app.run(timeout=30)

        self.assertEqual(list(app.exception), [])
        self.assertNotIn("Analyze with Groq", [element.label for element in app.button])
        self.assertNotIn("Review evidence", [element.value for element in app.subheader])
        self.assertEqual(len(app.expander), 1)
        self.assertEqual(app.expander[0].label, "Supporting review evidence")
        self.assertEqual(len(app.dataframe), 1)

    def test_post_analysis_runtime_orders_sections_and_collapses_only_duplicate_evidence(self):
        """Render one ordered report with warning-free charts and one collapsed evidence duplicate."""

        report = sample_report()
        app = AppTest.from_file(streamlit_app.__file__)
        app.session_state["latest_report"] = report
        app.session_state["collection"] = {"source": report["source"], "reviews": report["reviews"]}

        app.run(timeout=30)

        self.assertEqual(list(app.exception), [])
        self.assertEqual(len(app.expander), 1)
        self.assertEqual(app.expander[0].label, "Supporting review evidence")
        self.assertFalse(app.expander[0].proto.expanded)
        self.assertEqual(len(app.expander[0].dataframe), 1)

        children = list(app.main.children.values())
        report_index = next(
            index
            for index, child in enumerate(children)
            if str(getattr(child, "value", "")).startswith('<section class="ri-report-hero"')
        )
        metric_index = next(
            index
            for index, child in enumerate(children)
            if str(getattr(child, "value", "")).startswith('<section class="ri-metric-grid"')
        )
        summary_index = next(
            index
            for index, child in enumerate(children)
            if str(getattr(child, "value", "")).startswith('<section class="ri-summary-card"')
        )
        customer_signals_index = next(
            index
            for index, child in enumerate(children)
            if '<h2>Customer signals</h2>' in str(getattr(child, "value", ""))
        )
        chart_index = next(
            index
            for index, child in enumerate(children)
            if getattr(child, "type", "") == "flex_container" and len(child.get("vega_lite_chart")) == 2
        )
        themes_index = next(
            index
            for index, child in enumerate(children)
            if '<h2>Recurring themes</h2>' in str(getattr(child, "value", ""))
        )
        theme_grid_index = next(
            index
            for index, child in enumerate(children)
            if str(getattr(child, "value", "")).startswith('<section class="ri-theme-grid"')
        )
        insights_index = next(
            index
            for index, child in enumerate(children)
            if str(getattr(child, "value", "")).startswith('<section class="ri-insight-grid"')
        )
        priorities_index = next(
            index
            for index, child in enumerate(children)
            if '<h2>Customer priorities</h2>' in str(getattr(child, "value", ""))
        )
        evidence_index = next(
            index
            for index, child in enumerate(children)
            if getattr(child, "label", "") == "Supporting review evidence"
        )
        ordered_sections = [
            report_index,
            metric_index,
            summary_index,
            customer_signals_index,
            chart_index,
            themes_index,
            theme_grid_index,
            priorities_index,
            insights_index,
            evidence_index,
        ]
        self.assertEqual(ordered_sections, sorted(ordered_sections))

        charts = app.get("vega_lite_chart")
        self.assertEqual(len(charts), 2)
        rendered_specs = [json.loads(chart.proto.spec) for chart in charts]
        self.assertEqual(rendered_specs[0]["height"], 260)
        self.assertEqual(
            rendered_specs[0]["encoding"]["color"]["scale"]["range"],
            ["#15803d", "#a16207", "#b91c1c"],
        )
        for spec in rendered_specs:
            serialized = json.dumps(spec)
            self.assertNotIn('"params"', serialized)
            self.assertNotIn('"bind"', serialized)
            self.assertNotIn("Reviews_start", serialized)
            self.assertNotIn("Reviews_end", serialized)


if __name__ == "__main__":
    unittest.main()
