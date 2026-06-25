import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.services.model_summarizer import (
    DEFAULT_SUMMARIZATION_MODEL,
    _load_summary_components,
    summarize_with_model,
)


class FakeTensor:
    def to(self, device: str) -> "FakeTensor":
        return self


class FakeTokenizedInput(dict):
    def __init__(self) -> None:
        super().__init__({"input_ids": FakeTensor(), "attention_mask": FakeTensor()})

    def to(self, device: str) -> "FakeTokenizedInput":
        return self


class FakeTokenizer:
    def __call__(
        self,
        text: str,
        max_length: int,
        truncation: bool,
        return_tensors: str,
    ) -> FakeTokenizedInput:
        self.text = text
        self.max_length = max_length
        self.truncation = truncation
        self.return_tensors = return_tensors
        return FakeTokenizedInput()

    def decode(self, output: str, skip_special_tokens: bool) -> str:
        self.skip_special_tokens = skip_special_tokens
        return "Donuts are large, high quality, and pair well with matcha drinks."


class FakeModel:
    device = "cpu"

    def generate(self, **kwargs: object) -> list[str]:
        self.kwargs = kwargs
        return ["summary-token"]


class ModelSummarizerTests(unittest.TestCase):
    def test_default_model_is_falconsai_text_summarization(self) -> None:
        self.assertEqual(DEFAULT_SUMMARIZATION_MODEL, "Falconsai/text_summarization")

    def test_summary_model_runs_by_default_with_direct_generation(self) -> None:
        tokenizer = FakeTokenizer()
        model = FakeModel()

        with patch.dict("os.environ", {}, clear=True), patch(
            "backend.app.services.model_summarizer._get_summary_components",
            return_value=(tokenizer, model),
        ):
            result = summarize_with_model(
                ["Donuts are huge, consistent quality and taste great."],
                fallback_summary="fallback summary",
            )

        self.assertTrue(result.summary.startswith("The review states that "))
        self.assertIn("donuts are large", result.summary.casefold())
        self.assertEqual(result.summary_source, "transformer")
        self.assertEqual(result.model_name, DEFAULT_SUMMARIZATION_MODEL)
        self.assertIsNone(result.fallback_reason)
        self.assertEqual(model.kwargs["max_new_tokens"], 80)
        self.assertEqual(model.kwargs["min_new_tokens"], 20)

    def test_summary_model_can_be_disabled(self) -> None:
        with patch.dict("os.environ", {"REVIEWINSIGHT_ENABLE_MODEL_SUMMARY": "0"}, clear=True), patch(
            "backend.app.services.model_summarizer._get_summary_components",
            side_effect=AssertionError("summary model should not load when disabled"),
        ):
            result = summarize_with_model(
                ["Donuts are huge, consistent quality and taste great."],
                fallback_summary="fallback summary",
            )

        self.assertEqual(result.summary, "fallback summary")
        self.assertEqual(result.summary_source, "rule_based_fallback")
        self.assertEqual(result.fallback_reason, "model_summary_disabled")

    def test_loader_uses_seq2seq_classes_without_pipeline(self) -> None:
        calls: list[tuple[str, bool]] = []

        class FakeLoader:
            @staticmethod
            def from_pretrained(model_name: str, local_files_only: bool) -> str:
                calls.append((model_name, local_files_only))
                return model_name

        fake_transformers = SimpleNamespace(
            AutoModelForSeq2SeqLM=FakeLoader,
            AutoTokenizer=FakeLoader,
        )

        with patch.dict("os.environ", {}, clear=True), patch.dict(
            "sys.modules",
            {"transformers": fake_transformers},
        ), patch("backend.app.services.model_summarizer._summary_components", None):
            _load_summary_components(DEFAULT_SUMMARIZATION_MODEL)

        self.assertEqual(
            calls,
            [
                (DEFAULT_SUMMARIZATION_MODEL, False),
                (DEFAULT_SUMMARIZATION_MODEL, False),
            ],
        )


if __name__ == "__main__":
    unittest.main()
