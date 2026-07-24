"""Exercise strict platform URL allowlists before provider quota is spent."""

import unittest

from backend.app.imports.apify import ApifyGoogleMapsAdapter
from backend.app.imports.apify_amazon import ApifyAmazonReviewsAdapter
from backend.app.imports.contracts import IMPORT_LIMITS, ReviewImportError
from backend.app.imports.policies import extract_amazon_asin, validate_import_source
from backend.app.imports.registry import build_default_registry


class ImportPolicyTests(unittest.TestCase):
    """Cover the exact source URL allowlists for both platforms."""

    def test_shared_import_limits_are_used_by_google_adapter(self):
        """Keep platform limits on one provider-neutral policy tuple."""

        self.assertEqual(IMPORT_LIMITS, (10, 20, 50, 100))
        self.assertIs(ApifyGoogleMapsAdapter.allowed_limits, IMPORT_LIMITS)

    def test_default_amazon_adapter_uses_automation_lab_identity(self):
        """Expose a new cache/provenance identity for the replacement Actor."""

        adapter = build_default_registry()["amazon"]

        self.assertIsInstance(adapter, ApifyAmazonReviewsAdapter)
        self.assertEqual(adapter.provider_key, "apify_automation_lab_amazon")
        self.assertEqual(adapter.provider_label, "Apify (Automation Lab)")
        self.assertIs(adapter.allowed_limits, IMPORT_LIMITS)

    def test_extract_amazon_asin_supports_common_product_paths_and_tracking(self):
        """Find an uppercase ASIN by path shape and ignore later URL components."""

        cases = {
            "https://www.amazon.com/dp/b08c1w5n87": "B08C1W5N87",
            "https://amazon.com/gp/product/B08C1W5N87?tag=example": "B08C1W5N87",
            "https://amazon.com/gp/aw/d/B08C1W5N87": "B08C1W5N87",
            "https://www.amazon.com/product-name/dp/B08C1W5N87": "B08C1W5N87",
            "https://www.amazon.com/product-reviews/B08C1W5N87": "B08C1W5N87",
            (
                "https://www.amazon.com/product-name/dp/B08C1W5N87/ref=sr_1_1"
                "?keywords=example&qid=1234567890&sr=8-1"
            ): "B08C1W5N87",
            "https://amazon.com/s?k=kettle": None,
            "https://amazon.com/dp/not-an-asin": None,
        }

        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(extract_amazon_asin(url), expected)

    def test_amazon_accepts_product_paths_and_returns_asin_identity(self):
        """Use recognized Amazon product paths and ASIN cache identity."""

        for url in (
            "https://www.amazon.com/dp/B08C1W5N87",
            "https://amazon.com/gp/product/B08C1W5N87?tag=example",
            "https://amazon.com/gp/aw/d/B08C1W5N87",
            "https://www.amazon.com/product-name/dp/B08C1W5N87",
            "https://www.amazon.com/product-reviews/B08C1W5N87",
        ):
            with self.subTest(url=url):
                source = validate_import_source("amazon", url)
                self.assertEqual(source.source_key, "B08C1W5N87")
                self.assertEqual(source.original_url, url)

    def test_amazon_rejects_shortened_and_unsupported_urls(self):
        """Require an inspectable Amazon host and recognized product path."""

        for url in (
            "https://amzn.to/3example",
            "https://a.co/d/example",
            "https://www.amazon.com/s?k=kettle",
            "https://www.amazon.com/gp/help/customer/display.html",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ReviewImportError) as raised:
                    validate_import_source("amazon", url)
                self.assertEqual(raised.exception.code, "invalid_import_url")

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
