import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.services.model_sentiment import (
    DEFAULT_SENTIMENT_MODEL,
    TRANSFORMER_SENTIMENT_TASK,
    _load_sentiment_pipeline,
    analyze_sentiment_with_model,
)


class ModelSentimentTests(unittest.TestCase):
    def test_default_model_uses_supported_sentiment_task(self) -> None:
        self.assertEqual(TRANSFORMER_SENTIMENT_TASK, "sentiment-analysis")
        self.assertEqual(DEFAULT_SENTIMENT_MODEL, "distilbert-base-uncased-finetuned-sst-2-english")

    def test_model_sentiment_runs_by_default(self) -> None:
        classifier = unittest.mock.Mock(return_value=[{"label": "POSITIVE", "score": 0.98}])

        with patch.dict("os.environ", {}, clear=True), patch(
            "backend.app.services.model_sentiment._get_sentiment_classifier",
            return_value=classifier,
        ):
            result = analyze_sentiment_with_model("Donuts are huge and taste great.")

        self.assertEqual(result.sentiment, "positive")
        self.assertEqual(result.score, 4)
        self.assertEqual(result.sentiment_source, "transformer")
        self.assertEqual(result.model_name, DEFAULT_SENTIMENT_MODEL)
        self.assertEqual(result.confidence, 0.98)
        self.assertIsNone(result.fallback_reason)

    def test_model_sentiment_can_be_disabled(self) -> None:
        with patch.dict("os.environ", {"REVIEWINSIGHT_ENABLE_MODEL_SENTIMENT": "0"}, clear=True), patch(
            "backend.app.services.model_sentiment._get_sentiment_classifier",
            side_effect=AssertionError("model should not load when disabled"),
        ):
            result = analyze_sentiment_with_model("Donuts are huge and taste great.")

        self.assertEqual(result.sentiment, "positive")
        self.assertEqual(result.sentiment_source, "rule_based_fallback")
        self.assertEqual(result.fallback_reason, "model_sentiment_disabled")

    def test_model_loader_uses_sentiment_pipeline(self) -> None:
        calls: list[tuple[str, str, bool]] = []

        def fake_pipeline(task: str, model: str, local_files_only: bool) -> str:
            calls.append((task, model, local_files_only))
            return "classifier"

        fake_transformers = SimpleNamespace(pipeline=fake_pipeline)

        with patch.dict("os.environ", {}, clear=True), patch.dict(
            "sys.modules",
            {"transformers": fake_transformers},
        ), patch("backend.app.services.model_sentiment.pipeline", None):
            _load_sentiment_pipeline(DEFAULT_SENTIMENT_MODEL)

        self.assertEqual(
            calls,
            [(TRANSFORMER_SENTIMENT_TASK, DEFAULT_SENTIMENT_MODEL, False)],
        )


if __name__ == "__main__":
    unittest.main()
