"""Audit operator setup and legal/usage caveats for provider imports."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ImportDocumentationTests(unittest.TestCase):
    """Keep import configuration and scope documentation explicit."""

    def test_environment_example_uses_only_blank_apify_provider_credential(self):
        """Keep one backend-only provider token without stale Outscraper setup."""

        content = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("APIFY_API_TOKEN=", content)
        self.assertNotIn("OUTSCRAPER_API_KEY", content)
        self.assertNotIn("APIFY_API_TOKEN=test", content)

    def test_readme_documents_actors_limits_analysis_cache_and_usage_controls(self):
        """Give operators every prerequisite before a manual live request."""

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for required in (
            "Apify account",
            "Apify API token",
            "automation-lab/amazon-reviews-scraper",
            "compass/google-maps-reviews-scraper",
            "$0.01",
            "$2.00 per 1,000",
            "$0.03",
            "$0.05",
            "$0.11",
            "$0.21",
            'sort: "helpful"',
            'reviewsSort: "mostRelevant"',
            "no star-rating filter",
            "10, 20, 50, or 100",
            "Source URL",
            "Paste an Amazon product or Google Maps place URL",
            "first 40",
            "40 of",
            "30 days",
            "Refresh from source",
            "unofficial scraping services",
            "cookies or session tokens",
            "fixtures and fakes",
            "pricing and availability can change",
            "provider-side retention",
            "Apify (Axesso)",
            "Outscraper",
            "Amazon Conditions of Use",
            "Google Maps Additional Terms",
        ):
            with self.subTest(required=required):
                self.assertIn(required, readme)
        self.assertNotIn("axesso_data/amazon-reviews-scraper", readme)
        self.assertNotIn("OUTSCRAPER_API_KEY", readme)
        self.assertNotIn("Outscraper account", readme)

    def test_architecture_and_status_preserve_staged_boundaries(self):
        """Document imports separately from Groq analysis and saved history."""

        combined = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in ("docs/architecture.md", "docs/project_status.md")
        )
        for required in (
            "/api/import/options",
            "/api/import",
            "review_import_cache.db",
            "APIFY_API_TOKEN",
            "automation-lab/amazon-reviews-scraper",
            "compass/google-maps-reviews-scraper",
            "apify_automation_lab_amazon",
            "10/20/50/100",
            "Source URL",
            'sort: "helpful"',
            'reviewsSort: "mostRelevant"',
            "provider order",
            "first 40",
            "personalData: false",
            "provider-side retention",
            "no automatic retries",
            "fixture",
            "no Amazon or Google account credentials",
            "No Actor copy",
        ):
            with self.subTest(required=required):
                self.assertIn(required, combined)
        self.assertNotIn("OUTSCRAPER_API_KEY", combined)


if __name__ == "__main__":
    unittest.main()
