import unittest

from backend.app.services.summarization import summarize_review


class RuleBasedSummaryTests(unittest.TestCase):
    def test_summary_is_written_about_the_review(self) -> None:
        summary = summarize_review(
            "Donuts are huge, consistent quality and taste great. My kids love coming here."
        )

        self.assertTrue(summary.startswith("The review states that "))
        self.assertIn("This is because", summary)
        self.assertIn("donuts", summary.casefold())


if __name__ == "__main__":
    unittest.main()
