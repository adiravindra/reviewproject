import unittest
from unittest.mock import patch

from backend.app.services.analysis import analyze_review
from backend.app.services.model_summarizer import ModelSummaryResult


class AnalysisSummaryModelTests(unittest.TestCase):
    def test_analysis_uses_model_summary_result(self) -> None:
        with patch(
            "backend.app.services.analysis.analyze_sentiment_with_model",
        ) as sentiment, patch(
            "backend.app.services.analysis.summarize_with_model",
            return_value=ModelSummaryResult(
                summary="The review states that donuts are good. This is because the customer says they taste great.",
                summary_source="transformer",
                model_name="Falconsai/text_summarization",
            ),
        ):
            sentiment.return_value.sentiment = "positive"
            sentiment.return_value.score = 4
            sentiment.return_value.sentiment_source = "transformer"
            sentiment.return_value.model_name = "sentiment-model"
            sentiment.return_value.confidence = 0.98
            sentiment.return_value.fallback_reason = None

            result = analyze_review("Donuts are huge and taste great.")

        self.assertEqual(result.summary_source, "transformer")
        self.assertEqual(result.model_name, "Falconsai/text_summarization")
        self.assertIn("donuts are good", result.summary)


if __name__ == "__main__":
    unittest.main()
