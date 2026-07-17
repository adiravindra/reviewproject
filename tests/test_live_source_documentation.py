"""Guard the evidence fields required in the curated demo-source guide."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_SOURCES = PROJECT_ROOT / "docs" / "demo_sources.md"
LIVE_REQUIRED_FIELDS = (
    "**URL:** <https://",
    "**Access date:** 2026-07-17",
    "**Extractor:** `",
    "**Observed review count:**",
    "**Extraction notes:**",
    "**Runtime requirements:** No login, browser automation, JavaScript rendering, or anti-bot circumvention required.",
)
DATASET_REQUIRED_FIELDS = (
    "**Access method:**",
    "**Authentication:**",
    "**License/source:**",
    "**Product identifiers:**",
    "**Suitability:**",
)
DATASET_HEADINGS = (
    "Kaggle: Women's E-Commerce Clothing Reviews",
    "McAuley Amazon Reviews 2023",
    "Stanford SNAP Amazon Fine Foods",
    "Hugging Face Amazon Reviews Multi",
)


def _subsections(markdown: str, heading: str) -> list[str]:
    """Return level-three subsections within one level-two Markdown section."""

    section_match = re.search(rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)", markdown, re.MULTILINE)
    if section_match is None:
        return []
    return re.split(r"(?=^### )", section_match.group(1), flags=re.MULTILINE)[1:]


class LiveSourceDocumentationTests(unittest.TestCase):
    """Keep published live-source and dataset claims auditable and complete."""

    def test_verified_live_entries_include_collection_evidence(self) -> None:
        """Require exact URLs and static-collection evidence for every listed source."""

        markdown = DEMO_SOURCES.read_text(encoding="utf-8")
        entries = _subsections(markdown, "Verified live sources")

        self.assertGreaterEqual(len(entries), 2)
        for entry in entries:
            with self.subTest(entry=entry.splitlines()[0]):
                for field in LIVE_REQUIRED_FIELDS:
                    self.assertIn(field, entry)
                self.assertRegex(entry, r"\*\*Extractor:\*\* `(json_ld|html_cards)`")
                count = re.search(r"\*\*Observed review count:\*\* (\d+)", entry)
                self.assertIsNotNone(count)
                self.assertGreaterEqual(int(count.group(1)), 2)

    def test_dataset_entries_cover_access_and_product_retrieval_limits(self) -> None:
        """Require source-linked access facts before presenting a dataset option."""

        markdown = DEMO_SOURCES.read_text(encoding="utf-8")
        entries = _subsections(markdown, "Open dataset assessment")

        self.assertEqual(len(entries), len(DATASET_HEADINGS))
        for heading in DATASET_HEADINGS:
            matching = [entry for entry in entries if entry.startswith(f"### {heading}")]
            self.assertEqual(len(matching), 1, heading)
            for field in DATASET_REQUIRED_FIELDS:
                self.assertIn(field, matching[0])
            self.assertRegex(matching[0], r"https://")


if __name__ == "__main__":
    unittest.main()
