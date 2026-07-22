"""Exercise strict platform URL allowlists before provider quota is spent."""

import unittest

from backend.app.imports.contracts import ReviewImportError
from backend.app.imports.policies import validate_import_source


class ImportPolicyTests(unittest.TestCase):
    """Cover the exact source URL allowlists for both platforms."""

    def test_amazon_accepts_product_paths_and_returns_asin_identity(self):
        """Use recognized Amazon product paths and ASIN cache identity."""

        for url in (
            "https://www.amazon.com/dp/B000000000",
            "https://amazon.com/gp/product/1612680194?tag=example",
            "https://amazon.com/gp/aw/d/B000000000",
        ):
            with self.subTest(url=url):
                source = validate_import_source("amazon", url)
                self.assertIn(source.source_key, ("B000000000", "1612680194"))
                self.assertEqual(source.original_url, url)

    def test_google_accepts_one_place_url_or_share_url(self):
        """Accept direct place, CID, and non-root Google Maps share URLs."""

        for url in (
            "https://www.google.com/maps/place/Test+Cafe/@41.0,-87.0,15z",
            "https://google.com/maps?cid=123456789",
            "https://maps.google.com/?cid=123456789",
            "https://maps.app.goo.gl/AbCdEf123",
        ):
            with self.subTest(url=url):
                source = validate_import_source("google_maps", url)
                self.assertEqual(source.original_url, url)
                self.assertEqual(len(source.source_key), 64)

    def test_rejects_unsafe_or_wrong_platform_urls(self):
        """Stop unsafe, ambiguous, or mismatched URLs before adapter work."""

        cases = (
            ("amazon", "http://www.amazon.com/dp/B000000000"),
            ("amazon", "https://user:pass@amazon.com/dp/B000000000"),
            ("amazon", "https://amazon.com/s?k=kettle"),
            ("amazon", "https://amazon.com/product-reviews/B000000000"),
            ("amazon", "https://www.google.com/maps/place/Test"),
            ("google_maps", "https://www.google.com/search?q=cafe"),
            ("google_maps", "https://www.google.com/maps/search/cafe"),
            ("google_maps", "https://maps.app.goo.gl/"),
            ("unknown", "https://example.com/place"),
        )
        for platform, url in cases:
            with self.subTest(platform=platform, url=url):
                with self.assertRaises(ReviewImportError) as raised:
                    validate_import_source(platform, url)
                self.assertIn(raised.exception.code, ("invalid_import_url", "unsupported_import_platform"))


if __name__ == "__main__":
    unittest.main()
