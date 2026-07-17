"""Test strict models shared by the staged FastAPI boundary."""

import unittest

from pydantic import ValidationError

from backend.app.models import AnalysisResponse, HistoryItem, PublicError, Theme


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

    def test_public_error_uses_the_safe_error_shape(self):
        """Retain the only public error schema while staged endpoints are added later."""

        error = PublicError(code="analysis_failed", message="The analysis could not be completed.")
        self.assertEqual(error.code, "analysis_failed")


if __name__ == "__main__":
    unittest.main()
