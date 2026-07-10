import unittest
from typing import Any

from backend.app.errors import AppError
from backend.app.schemas.website import (
    BatchAnalysisOutput,
    EvidenceItem,
    NormalizedReview,
    ReviewSentiment,
    SynthesisOutput,
)
from backend.app.settings import Settings


class FakeStructuredModel:
    def __init__(
        self,
        *,
        batch_outputs: list[Any],
        synthesis_outputs: list[Any],
    ) -> None:
        self.outputs = {
            BatchAnalysisOutput: list(batch_outputs),
            SynthesisOutput: list(synthesis_outputs),
        }
        self.prompts: list[tuple[type[Any], str]] = []

    def with_structured_output(self, schema: type[Any]) -> Any:
        parent = self

        class Runnable:
            def invoke(self, prompt: str) -> Any:
                parent.prompts.append((schema, prompt))
                outcome = parent.outputs[schema].pop(0)
                if isinstance(outcome, Exception):
                    raise outcome
                return outcome

        return Runnable()

    @property
    def call_count(self) -> int:
        return len(self.prompts)


def reviews(count: int, *, author: str | None = None) -> list[NormalizedReview]:
    return [
        NormalizedReview(
            id=f"r{index}",
            text=f"Original customer wording {index}.",
            rating=float((index % 5) + 1),
            author=author,
            publication_date=f"2026-06-{(index % 28) + 1:02d}",
            source_url=f"https://secret.example/{index}",
        )
        for index in range(count)
    ]


def valid_batch(review_ids: list[str]) -> BatchAnalysisOutput:
    first = review_ids[0]
    return BatchAnalysisOutput(
        sentiments=[
            ReviewSentiment(
                review_id=review_id,
                sentiment=("positive" if index % 3 == 0 else "neutral" if index % 3 == 1 else "negative"),
            )
            for index, review_id in enumerate(review_ids)
        ],
        positive_themes=[EvidenceItem(label="Quality", summary="Customers value quality.", review_ids=[first])],
        complaints=[EvidenceItem(label="Service", summary="Some service concerns recur.", review_ids=[first])],
        aspects=[EvidenceItem(label="Value", summary="Value is frequently discussed.", review_ids=[first])],
        opportunities=[EvidenceItem(label="Support", summary="Improve support consistency.", review_ids=[first])],
    )


def valid_synthesis(representative_ids: list[str]) -> SynthesisOutput:
    first = representative_ids[0]
    evidence = EvidenceItem(label="Quality", summary="Quality shapes the experience.", review_ids=[first])
    return SynthesisOutput(
        executive_summary="Customers report a mixed but actionable experience.",
        strengths=[evidence],
        complaints=[evidence],
        aspects=[evidence],
        opportunities=[evidence],
        representative_review_ids=representative_ids,
    )


class StructuredAnalysisTests(unittest.TestCase):
    def test_batches_are_bounded_authors_are_excluded_and_synthesis_has_no_raw_text(self) -> None:
        from backend.app.services.analysis import analyze_collection

        review_items = reviews(31, author="Secret Author")
        model = FakeStructuredModel(
            batch_outputs=[
                valid_batch([item.id for item in review_items[0:15]]),
                valid_batch([item.id for item in review_items[15:30]]),
                valid_batch([item.id for item in review_items[30:31]]),
            ],
            synthesis_outputs=[valid_synthesis(["r0", "r15", "r30"])],
        )

        result = analyze_collection(review_items, model=model, settings=Settings())

        self.assertEqual(result.batch_count, 3)
        self.assertEqual(result.call_count, 4)
        self.assertEqual(len(result.sentiments), 31)
        batch_prompts = [prompt for schema, prompt in model.prompts if schema is BatchAnalysisOutput]
        synthesis_prompt = [prompt for schema, prompt in model.prompts if schema is SynthesisOutput][0]
        self.assertTrue(all("Secret Author" not in prompt for prompt in batch_prompts))
        self.assertTrue(all("secret.example" not in prompt for prompt in batch_prompts))
        self.assertNotIn("Original customer wording", synthesis_prompt)

    def test_invalid_batch_output_retries_only_within_batch_and_total_call_budgets(self) -> None:
        from backend.app.services.analysis import analyze_collection

        review_items = reviews(15)
        incomplete = valid_batch([item.id for item in review_items[:-1]])
        model = FakeStructuredModel(
            batch_outputs=[incomplete, valid_batch([item.id for item in review_items])],
            synthesis_outputs=[valid_synthesis(["r0"])],
        )

        result = analyze_collection(review_items, model=model, settings=Settings())

        self.assertEqual(result.call_count, 3)

        sixty = reviews(60)
        no_retry_model = FakeStructuredModel(
            batch_outputs=[valid_batch([item.id for item in sixty[:14]])],
            synthesis_outputs=[valid_synthesis(["r0"])],
        )
        with self.assertRaises(AppError) as raised:
            analyze_collection(sixty, model=no_retry_model, settings=Settings())
        self.assertEqual(raised.exception.code, "llm_failed")
        self.assertEqual(no_retry_model.call_count, 1)

    def test_unknown_or_duplicate_review_ids_are_rejected(self) -> None:
        from backend.app.services.analysis import analyze_collection

        review_items = reviews(2)
        invalid = valid_batch(["r0", "r0"])
        model = FakeStructuredModel(
            batch_outputs=[invalid, invalid],
            synthesis_outputs=[valid_synthesis(["r0"])],
        )
        with self.assertRaises(AppError) as raised:
            analyze_collection(review_items, model=model, settings=Settings())
        self.assertEqual(raised.exception.code, "llm_failed")

        valid_model = FakeStructuredModel(
            batch_outputs=[valid_batch(["r0", "r1"])],
            synthesis_outputs=[valid_synthesis(["invented-review"])],
        )
        with self.assertRaises(AppError):
            analyze_collection(review_items, model=valid_model, settings=Settings())

    def test_representative_ids_resolve_to_stored_original_text(self) -> None:
        from backend.app.services.analysis import analyze_collection

        review_items = reviews(3, author="Private Name")
        model = FakeStructuredModel(
            batch_outputs=[valid_batch(["r0", "r1", "r2"])],
            synthesis_outputs=[valid_synthesis(["r2", "r0"])],
        )

        result = analyze_collection(review_items, model=model, settings=Settings())

        self.assertEqual(
            [item.text for item in result.insights.representative_reviews],
            ["Original customer wording 2.", "Original customer wording 0."],
        )
        self.assertFalse(hasattr(result.insights.representative_reviews[0], "author"))

    def test_provider_exception_is_sanitized_and_not_retried(self) -> None:
        from backend.app.services.analysis import analyze_collection

        model = FakeStructuredModel(
            batch_outputs=[RuntimeError("secret raw provider body")],
            synthesis_outputs=[],
        )
        with self.assertRaises(AppError) as raised:
            analyze_collection(reviews(2), model=model, settings=Settings())

        self.assertEqual(raised.exception.code, "llm_failed")
        self.assertTrue(raised.exception.retryable)
        self.assertNotIn("secret", raised.exception.message)
        self.assertEqual(model.call_count, 1)


if __name__ == "__main__":
    unittest.main()
