"""Test the bundled, explicit demo collection and staged model contracts."""

import unittest
from pathlib import Path

from pydantic import ValidationError

from backend.app.demo import load_demo_collection
from backend.app.models import AnalysisRequest, CollectionRequest, Review, SourceInfo


def live_source() -> SourceInfo:
    """Build a valid static-web source for request contract tests."""

    return SourceInfo(
        url="https://example.com/products/aurora-kettle",
        title="Aurora Pour-Over Kettle",
        extractor="json_ld",
        is_demo=False,
    )


def request_reviews() -> list[Review]:
    """Build the minimum accepted review evidence for analysis requests."""

    return [
        Review(id="r1", text="The temperature control is easy to use every morning.", rating=5),
        Review(id="r2", text="The handle stays cool, though the pour is a little slow.", rating=3),
    ]


class StagedContractTests(unittest.TestCase):
    """Cover strict inbound request and source-provenance validation."""

    def test_analysis_request_accepts_only_a_source_and_two_to_forty_reviews(self):
        """Require displayed evidence rather than a URL/provider analysis request."""

        request = AnalysisRequest.model_validate(
            {
                "source": live_source().model_dump(mode="json"),
                "reviews": [review.model_dump() for review in request_reviews()],
            }
        )
        self.assertEqual(len(request.reviews), 2)
        self.assertEqual(request.to_collection().source, live_source())

        with self.assertRaises(ValidationError):
            AnalysisRequest.model_validate(
                {
                    "source": live_source().model_dump(mode="json"),
                    "reviews": [review.model_dump() for review in request_reviews()],
                    "provider": "groq",
                }
            )
        with self.assertRaises(ValidationError):
            AnalysisRequest.model_validate(
                {"source": live_source().model_dump(mode="json"), "reviews": [request_reviews()[0].model_dump()]}
            )

    def test_collection_request_forbids_unknown_fields(self):
        """Keep collection inputs limited to exactly one public URL."""

        self.assertEqual(
            str(CollectionRequest.model_validate({"url": "https://example.com/reviews"}).url),
            "https://example.com/reviews",
        )
        with self.assertRaises(ValidationError):
            CollectionRequest.model_validate(
                {"url": "https://example.com/reviews", "provider": "groq"}
            )

    def test_source_provenance_requires_explicit_demo_metadata(self):
        """Allow URL-less provenance only for correctly marked bundled demo data."""

        demo_source = SourceInfo(
            url=None,
            title="Aurora Pour-Over Kettle",
            extractor="demo",
            is_demo=True,
        )
        self.assertTrue(demo_source.is_demo)
        for payload in (
            {"url": None, "title": "Missing URL", "extractor": "json_ld", "is_demo": False},
            {"url": "https://example.com/product", "title": "False Demo", "extractor": "demo", "is_demo": False},
            {"url": "https://example.com/product", "title": "Marked Demo", "extractor": "json_ld", "is_demo": True},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ValidationError):
                    SourceInfo.model_validate(payload)

    def test_review_text_has_a_bounded_safe_length(self):
        """Reject unbounded evidence payloads before agent processing."""

        with self.assertRaises(ValidationError):
            Review(id="oversized", text="x" * 5001)


class DemoDataTests(unittest.TestCase):
    """Cover deterministic bundled product-review loading without HTTP work."""

    def test_bundled_demo_collection_is_labeled_complete_and_mixed_rating(self):
        """Return the checked-in ten-review demo collection with its provenance."""

        collection = load_demo_collection()
        self.assertEqual(collection.source.extractor, "demo")
        self.assertTrue(collection.source.is_demo)
        self.assertIsNone(collection.source.url)
        self.assertEqual(len(collection.reviews), 10)
        self.assertEqual({review.rating for review in collection.reviews}, {1, 2, 3, 4, 5})
        self.assertTrue(all(review.date and len(review.text.split()) >= 8 for review in collection.reviews))

    def test_demo_loader_accepts_an_explicit_data_path(self):
        """Allow tests and local tooling to select a checked-in demo JSON file."""

        path = Path(__file__).resolve().parents[1] / "demo_data" / "product_reviews.json"
        self.assertEqual(load_demo_collection(path).source.title, "Aurora Pour-Over Kettle")


if __name__ == "__main__":
    unittest.main()
