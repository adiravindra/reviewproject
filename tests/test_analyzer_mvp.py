import json
import os
import unittest
from unittest.mock import Mock, patch

from backend.app.analyzer import AnalysisError, analyze_reviews, build_model
from backend.app.models import AgentInsights, Review


def sample_reviews():
    return [
        Review(id="r1", text="Clear sound and comfortable fit.", rating=5, date="2026-06-01"),
        Review(id="r2", text="Battery lasts well but the microphone is average.", rating=3, date=None),
    ]


def valid_insights(review_ids=None):
    review_ids = review_ids or ["r1", "r2"]
    return AgentInsights(
        summary="Customers value sound and comfort while noting microphone limitations.",
        overall_sentiment="positive",
        themes=[
            {
                "name": "Everyday audio",
                "description": "Sound and practical daily use shape the feedback.",
                "mentions": 2,
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
    def __init__(self, insights):
        self.insights = insights
        self.invocations = 0
        self.state = None

    def invoke(self, state):
        self.invocations += 1
        self.state = state
        return {"structured_response": self.insights}


class AnalyzerTests(unittest.TestCase):
    def test_missing_provider_key_is_explicit(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(AnalysisError) as raised:
                build_model("google")
        self.assertEqual(raised.exception.code, "missing_api_key")
        self.assertNotIn("GOOGLE_API_KEY=", str(raised.exception))

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(AnalysisError) as raised:
                build_model("groq")
        self.assertEqual(raised.exception.code, "missing_api_key")

    def test_one_agent_invocation_returns_validated_insights(self):
        fake_agent = FakeAgent(valid_insights())
        factory = Mock(return_value=fake_agent)
        result = analyze_reviews(
            sample_reviews(),
            "google",
            agent_factory=factory,
            model_factory=lambda provider: object(),
        )
        factory.assert_called_once()
        self.assertEqual(factory.call_args.kwargs["tools"], [])
        self.assertIs(factory.call_args.kwargs["response_format"], AgentInsights)
        self.assertIn("exactly one sentiment", factory.call_args.kwargs["system_prompt"].lower())
        self.assertEqual(fake_agent.invocations, 1)
        self.assertEqual(result.overall_sentiment, "positive")

        message = fake_agent.state["messages"][0]
        payload = json.loads(message["content"])
        self.assertEqual(message["role"], "user")
        self.assertEqual(set(payload[0]), {"id", "text", "rating", "date"})
        self.assertEqual(payload[0]["id"], "r1")
        self.assertNotIn("author", message["content"].lower())

    def test_missing_unknown_or_duplicate_review_sentiment_ids_fail(self):
        for review_ids in (["r1"], ["r1", "unknown"], ["r1", "r1"]):
            with self.subTest(review_ids=review_ids):
                invalid = valid_insights(review_ids=list(review_ids))
                with self.assertRaises(AnalysisError) as raised:
                    analyze_reviews(
                        sample_reviews(),
                        "groq",
                        agent_factory=lambda **kwargs: FakeAgent(invalid),
                        model_factory=lambda provider: object(),
                    )
                self.assertEqual(raised.exception.code, "analysis_failed")

    def test_provider_exception_is_sanitized(self):
        agent = Mock()
        agent.invoke.side_effect = RuntimeError("provider response contained sensitive internals")
        with self.assertRaises(AnalysisError) as raised:
            analyze_reviews(
                sample_reviews(),
                "google",
                agent_factory=lambda **kwargs: agent,
                model_factory=lambda provider: object(),
            )
        self.assertEqual(raised.exception.code, "analysis_failed")
        self.assertNotIn("sensitive", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
