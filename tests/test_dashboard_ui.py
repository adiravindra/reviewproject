import unittest

from dashboard.ui import (
    average_urgency_label,
    loaded_analysis_reviews,
    parse_api_review_payload,
    sentiment_breakdown_rows,
    single_analysis_card_fields,
    split_review_lines,
)


class DashboardUiTests(unittest.TestCase):
    def test_split_review_lines_trims_and_removes_blank_lines(self) -> None:
        self.assertEqual(
            split_review_lines(" Great product \n\n Slow shipping \n   "),
            ["Great product", "Slow shipping"],
        )

    def test_sentiment_breakdown_rows_title_cases_labels(self) -> None:
        self.assertEqual(
            sentiment_breakdown_rows({"positive": 2, "neutral": 1, "negative": 0}),
            [
                {"Sentiment": "Positive", "Reviews": 2},
                {"Sentiment": "Neutral", "Reviews": 1},
                {"Sentiment": "Negative", "Reviews": 0},
            ],
        )

    def test_parse_api_review_payload_accepts_reviews_list(self) -> None:
        self.assertEqual(
            parse_api_review_payload('{"reviews":[{"text":" Great "},{"text":"Slow shipping"}]}'),
            ["Great", "Slow shipping"],
        )

    def test_parse_api_review_payload_accepts_single_text(self) -> None:
        self.assertEqual(
            parse_api_review_payload('{"text":"Helpful support"}'),
            ["Helpful support"],
        )

    def test_parse_api_review_payload_rejects_invalid_json(self) -> None:
        with self.assertRaises(ValueError):
            parse_api_review_payload("{invalid")

    def test_loaded_analysis_reviews_returns_review_list(self) -> None:
        self.assertEqual(
            loaded_analysis_reviews({"reviews": [{"text": "Great"}, {"text": "Slow"}]}),
            [{"text": "Great"}, {"text": "Slow"}],
        )

    def test_average_urgency_label_formats_numeric_score(self) -> None:
        self.assertEqual(average_urgency_label(2.0), "Medium")
        self.assertEqual(average_urgency_label(3.0), "High")

    def test_single_analysis_card_fields_formats_result(self) -> None:
        self.assertEqual(
            single_analysis_card_fields(
                {
                    "text": "The app crashes when I log in.",
                    "sentiment": "negative",
                    "topics": ["bugs/crashes", "login/auth"],
                    "urgency_score": 0.85,
                    "urgency_label": "high",
                    "summary": "This review reports crashes during login.",
                }
            ),
            {
                "text": "The app crashes when I log in.",
                "sentiment": "Negative",
                "topics": "Bugs/Crashes, Login/Auth",
                "urgency_score": "0.85",
                "urgency_label": "High",
                "summary": "This review reports crashes during login.",
            },
        )

    def test_single_analysis_card_fields_uses_topic_fallback(self) -> None:
        self.assertEqual(
            single_analysis_card_fields(
                {
                    "text": "Thanks",
                    "sentiment": "neutral",
                    "topics": [],
                    "urgency_score": 0,
                    "urgency_label": "low",
                    "summary": "This review says: Thanks.",
                }
            )["topics"],
            "No specific topic detected",
        )


if __name__ == "__main__":
    unittest.main()
