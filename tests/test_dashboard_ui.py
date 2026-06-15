import unittest

from dashboard.ui import parse_api_review_payload, sentiment_breakdown_rows, split_review_lines


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


if __name__ == "__main__":
    unittest.main()
