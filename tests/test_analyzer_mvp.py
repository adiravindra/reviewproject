"""Test evidence-only Groq invocation and structured-result safeguards."""

import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import backend.app.analyzer as analyzer_module
from backend.app.analyzer import analyze_reviews, build_model
from backend.app.errors import AnalysisError
from backend.app.models import AgentInsights, Review


def sample_reviews():
    """Build representative normalized evidence for analyzer tests."""

    return [
        Review(id="r1", text="Clear sound and comfortable fit.", rating=5, date="2026-06-01"),
        Review(id="r2", text="Battery lasts well but the microphone is average.", rating=3, date=None),
    ]


def valid_insights(review_ids=None):
    """Build schema-valid insights with configurable returned review IDs."""

    review_ids = review_ids or ["r1", "r2"]
    return AgentInsights(
        summary="Customers value sound and comfort while noting microphone limitations.",
        overall_sentiment="positive",
        themes=[
            {
                "name": "Everyday audio",
                "description": "Sound is strong while microphone quality is inconsistent.",
                "mentions": 2,
                "sentiment": "mixed",
            }
        ],
        strengths=["Clear sound", "Comfortable fit"],
        weaknesses=["Average microphone"],
        actions=["Improve microphone noise handling"],
        review_sentiments=[
            {"review_id": review_id, "sentiment": "positive" if review_id == "r1" else "neutral"}
            for review_id in review_ids
        ],
    )


class FakeAgent:
    """Simulate one structured agent invocation while recording its payload."""

    def __init__(self, result):
        """Store the result returned by the fake invocation."""

        self.result = result
        self.invocations = 0
        self.state = None

    def invoke(self, state):
        """Record agent state and return the configured agent result."""

        self.invocations += 1
        self.state = state
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class AnalyzerTests(unittest.TestCase):
    """Group model setup and structured analysis boundary contracts."""

    def test_build_model_uses_groq_default_and_bounded_options(self):
        """Construct Groq with the normalized key, default model, and fixed bounds."""

        constructor_calls = []

        class FakeGroqModel:
            """Record explicit parameters supplied by the model factory."""

            def __init__(self, **kwargs):
                """Capture construction parameters without network activity."""

                constructor_calls.append(kwargs)

        fake_module = SimpleNamespace(ChatGroq=FakeGroqModel)
        with (
            patch.dict(os.environ, {"GROQ_API_KEY": "  groq-secret  "}, clear=True),
            patch.dict(sys.modules, {"langchain_groq": fake_module}),
        ):
            build_model()

        self.assertEqual(
            constructor_calls,
            [
                {
                    "model": "llama-3.3-70b-versatile",
                    "api_key": "groq-secret",
                    "temperature": 0,
                    "timeout": 30,
                    "max_retries": 0,
                }
            ],
        )

    def test_build_model_allows_the_groq_model_override(self):
        """Use the configured Groq model while preserving the fixed options."""

        constructor_calls = []

        class FakeGroqModel:
            """Record explicit parameters supplied by the model factory."""

            def __init__(self, **kwargs):
                """Capture construction parameters without network activity."""

                constructor_calls.append(kwargs)

        with (
            patch.dict(
                os.environ,
                {"GROQ_API_KEY": "groq-secret", "REVIEWINSIGHT_GROQ_MODEL": "custom-model"},
                clear=True,
            ),
            patch.dict(sys.modules, {"langchain_groq": SimpleNamespace(ChatGroq=FakeGroqModel)}),
        ):
            build_model()

        self.assertEqual(constructor_calls[0]["model"], "custom-model")
        self.assertEqual(constructor_calls[0]["api_key"], "groq-secret")

    def test_build_model_maps_construction_failures_safely(self):
        """Hide import and constructor failure details behind the public boundary."""

        class FailingGroqModel:
            """Raise a representative dependency error during construction."""

            def __init__(self, **kwargs):
                """Raise sensitive implementation details that must not escape."""

                raise RuntimeError("constructor internals")

        with (
            patch.dict(os.environ, {"GROQ_API_KEY": "groq-secret"}, clear=True),
            patch.dict(sys.modules, {"langchain_groq": SimpleNamespace(ChatGroq=FailingGroqModel)}),
            self.assertRaises(AnalysisError) as raised,
        ):
            build_model()
        self.assertEqual(raised.exception.code, "analysis_failed")
        self.assertNotIn("constructor internals", str(raised.exception))

    def test_module_documents_only_the_required_lazy_groq_integration(self):
        """Describe the one required integration as a lazy dependency."""

        documentation = analyzer_module.__doc__.lower()
        self.assertIn("required", documentation)
        self.assertIn("lazily", documentation)
        self.assertIn("groq", documentation)
        self.assertNotIn("optional dependency", documentation)

    def test_one_agent_invocation_returns_validated_evidence_only_insights(self):
        """Require one tool-free structured call carrying exactly review evidence."""

        fake_agent = FakeAgent({"structured_response": valid_insights()})
        factory = Mock(return_value=fake_agent)
        reviews = sample_reviews()
        result = analyze_reviews(reviews, agent_factory=factory, model_factory=lambda: object())

        factory.assert_called_once()
        self.assertEqual(factory.call_args.kwargs["tools"], [])
        self.assertIs(factory.call_args.kwargs["response_format"], AgentInsights)
        self.assertIn("sentiment for every theme", factory.call_args.kwargs["system_prompt"].lower())
        self.assertEqual(fake_agent.invocations, 1)
        self.assertEqual(result.overall_sentiment, "positive")
        self.assertEqual(result.themes[0].sentiment, "mixed")

        message = fake_agent.state["messages"][0]
        self.assertEqual(message["role"], "user")
        self.assertEqual(json.loads(message["content"]), [review.model_dump() for review in reviews])
        self.assertNotIn("author", message["content"].lower())

    def test_invocation_failure_is_sanitized(self):
        """Map invocation failures without exposing raw agent state or details."""

        agent = FakeAgent(RuntimeError("sensitive invocation internals"))
        with self.assertRaises(AnalysisError) as raised:
            analyze_reviews(
                sample_reviews(), agent_factory=lambda **kwargs: agent, model_factory=lambda: object()
            )
        self.assertEqual(raised.exception.code, "analysis_failed")
        self.assertNotIn("sensitive", str(raised.exception))

    def test_malformed_or_missing_structured_output_is_invalid(self):
        """Treat absent and schema-invalid structured output as model output errors."""

        cases = [
            {},
            {"structured_response": {"summary": "not a complete result"}},
            {"structured_response": valid_insights().model_dump() | {"themes": []}},
        ]
        for state in cases:
            with self.subTest(state=state):
                with self.assertRaises(AnalysisError) as raised:
                    analyze_reviews(
                        sample_reviews(),
                        agent_factory=lambda **kwargs: FakeAgent(state),
                        model_factory=lambda: object(),
                    )
                self.assertEqual(raised.exception.code, "model_output_invalid")

    def test_missing_unknown_or_duplicate_review_ids_are_invalid(self):
        """Reject review sentiments that do not exactly map to submitted reviews."""

        for review_ids in (["r1"], ["r1", "unknown"], ["r1", "r1"]):
            with self.subTest(review_ids=review_ids):
                with self.assertRaises(AnalysisError) as raised:
                    analyze_reviews(
                        sample_reviews(),
                        agent_factory=lambda **kwargs: FakeAgent(
                            {"structured_response": valid_insights(list(review_ids))}
                        ),
                        model_factory=lambda: object(),
                    )
                self.assertEqual(raised.exception.code, "model_output_invalid")


if __name__ == "__main__":
    unittest.main()
