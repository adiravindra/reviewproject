import unittest
from unittest.mock import patch

import requests

from dashboard.api_client import ANALYZE_TIMEOUT_SECONDS, ApiClientError, analyze_review


class AnalyzeReviewClientTests(unittest.TestCase):
    def test_read_timeout_is_wrapped_for_streamlit(self) -> None:
        with patch(
            "dashboard.api_client.requests.post",
            side_effect=requests.ReadTimeout("timed out"),
        ):
            with self.assertRaises(ApiClientError) as raised:
                analyze_review("The product is good, but shipping was slow.")

        self.assertIn("timed out", str(raised.exception).casefold())

    def test_analysis_timeout_allows_first_model_load(self) -> None:
        self.assertGreaterEqual(ANALYZE_TIMEOUT_SECONDS, 120)


if __name__ == "__main__":
    unittest.main()
