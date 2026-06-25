import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.services.model_summarizer import (
    DEFAULT_SUMMARIZATION_MODEL,
    TRANSFORMER_SUMMARIZATION_TASK,
    _load_local_model,
    summarize_with_model,
)


class ModelSummarizerTests(unittest.TestCase):
    def test_default_model_is_a_distilled_summarizer(self) -> None:
        self.assertEqual(TRANSFORMER_SUMMARIZATION_TASK, "summarization")
        self.assertEqual(DEFAULT_SUMMARIZATION_MODEL, "sshleifer/distilbart-cnn-12-6")

    def test_model_summary_runs_by_default(self) -> None:
        summarizer = unittest.mock.Mock(return_value=[{"summary_text": "The donuts are large and consistently good."}])

        with patch.dict("os.environ", {}, clear=True), patch(
            "backend.app.services.model_summarizer._get_summarizer",
            return_value=summarizer,
        ):
            result = summarize_with_model(
                ["The product is great, but shipping was slow."],
                fallback_summary="fallback summary",
            )

        self.assertTrue(result.summary.startswith("The review states that "))
        self.assertIn("the donuts are large and consistently good", result.summary)
        self.assertIn("This is because", result.summary)
        self.assertEqual(result.summary_source, "transformer")
        self.assertIsNone(result.fallback_reason)
        _, kwargs = summarizer.call_args
        self.assertEqual(kwargs["max_length"], 80)
        self.assertEqual(kwargs["min_length"], 20)
        self.assertNotIn("max_new_tokens", kwargs)

    def test_model_summary_can_be_disabled(self) -> None:
        with patch.dict("os.environ", {"REVIEWINSIGHT_ENABLE_MODEL_SUMMARY": "0"}, clear=True), patch(
            "backend.app.services.model_summarizer._get_summarizer",
            side_effect=AssertionError("model should not load when disabled"),
        ):
            result = summarize_with_model(
                ["The product is great, but shipping was slow."],
                fallback_summary="fallback summary",
            )

        self.assertEqual(result.summary, "fallback summary")
        self.assertEqual(result.summary_source, "rule_based_fallback")
        self.assertEqual(result.fallback_reason, "model_summary_disabled")

    def test_model_loader_can_download_by_default(self) -> None:
        calls: list[tuple[str, bool]] = []

        class FakeLoader:
            @staticmethod
            def from_pretrained(model_name: str, local_files_only: bool) -> str:
                calls.append((model_name, local_files_only))
                return model_name

        fake_transformers = SimpleNamespace(
            AutoModelForSeq2SeqLM=FakeLoader,
            AutoTokenizer=FakeLoader,
            pipeline=lambda *args, **kwargs: "pipeline",
        )

        with patch.dict("os.environ", {}, clear=True), patch.dict(
            "sys.modules",
            {"transformers": fake_transformers},
        ), patch("backend.app.services.model_summarizer.pipeline", None):
            _load_local_model(DEFAULT_SUMMARIZATION_MODEL)

        self.assertEqual(
            calls,
            [
                (DEFAULT_SUMMARIZATION_MODEL, False),
                (DEFAULT_SUMMARIZATION_MODEL, False),
            ],
        )


if __name__ == "__main__":
    unittest.main()
