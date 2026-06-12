import unittest

from dashboard.ui import sentiment_breakdown_rows, split_review_lines


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


if __name__ == "__main__":
    unittest.main()
