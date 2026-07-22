"""Audit operator setup and legal/usage caveats for provider imports."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ImportDocumentationTests(unittest.TestCase):
    """Keep import configuration and scope documentation explicit."""

    def test_environment_example_lists_blank_backend_provider_credentials(self):
        """Declare provider variables without committing secret values."""

        content = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("OUTSCRAPER_API_KEY=", content)
        self.assertIn("APIFY_API_TOKEN=", content)
        self.assertNotIn("OUTSCRAPER_API_KEY=test", content)
        self.assertNotIn("APIFY_API_TOKEN=test", content)

    def test_readme_documents_accounts_actor_limits_cache_and_free_usage(self):
        """Give operators every prerequisite before a manual live request."""

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for required in (
            "Outscraper account",
            "Outscraper API key",
            "Apify account",
            "Apify API token",
            "compass/google-maps-reviews-scraper",
            "500 reviews",
            "$5",
            "5, 10, or 12",
            "5, 10, or 20",
            "30 days",
            "Refresh from source",
            "unofficial scraping services",
            "cookies or session tokens",
            "fixtures and fakes",
            "Amazon Conditions of Use",
            "Google Maps Additional Terms",
        ):
            with self.subTest(required=required):
                self.assertIn(required, readme)

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
            "OUTSCRAPER_API_KEY",
            "APIFY_API_TOKEN",
            "personalData",
            "provider-side retention",
            "no automatic retries",
            "fixture",
        ):
            with self.subTest(required=required):
                self.assertIn(required, combined)


if __name__ == "__main__":
    unittest.main()
