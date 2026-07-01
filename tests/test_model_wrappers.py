import os
import unittest
from unittest.mock import patch

from backend.app.services import analysis, model_runtime, model_sentiment, model_summarizer
from backend.app.services.model_sentiment import ModelSentimentResult
from backend.app.services.model_summarizer import ModelSummaryResult


class FakeCuda:
    def __init__(self, available: bool) -> None:
        self._available = available

    def is_available(self) -> bool:
        return self._available


class FakeTorch:
    float16 = "float16"

    def __init__(self, cuda_available: bool) -> None:
        self.cuda = FakeCuda(cuda_available)


class RuntimeDeviceTests(unittest.TestCase):
    def test_auto_device_uses_cuda_when_torch_can_see_gpu(self) -> None:
        settings = model_runtime.resolve_inference_device(
            torch_module=FakeTorch(cuda_available=True),
            requested_device="auto",
        )

        self.assertEqual(settings.model_device, "cuda:0")
        self.assertEqual(settings.pipeline_device, 0)
        self.assertEqual(settings.torch_dtype, "float16")

    def test_auto_device_falls_back_to_cpu_when_cuda_is_unavailable(self) -> None:
        settings = model_runtime.resolve_inference_device(
            torch_module=FakeTorch(cuda_available=False),
            requested_device="auto",
        )

        self.assertEqual(settings.model_device, "cpu")
        self.assertEqual(settings.pipeline_device, -1)
        self.assertIsNone(settings.torch_dtype)


class SentimentModelTests(unittest.TestCase):
    def test_cardiff_label_ids_map_to_three_sentiments(self) -> None:
        self.assertEqual(
            model_sentiment._parse_classifier_output([{"label": "LABEL_0", "score": 0.91}]),
            ("negative", 0.91),
        )
        self.assertEqual(
            model_sentiment._parse_classifier_output([{"label": "LABEL_1", "score": 0.72}]),
            ("neutral", 0.72),
        )
        self.assertEqual(
            model_sentiment._parse_classifier_output([{"label": "LABEL_2", "score": 0.88}]),
            ("positive", 0.88),
        )

    def test_batch_sentiment_uses_one_classifier_call_for_multiple_reviews(self) -> None:
        calls = []

        def fake_classifier(texts: list[str], **kwargs: object) -> list[dict[str, float | str]]:
            calls.append((texts, kwargs))
            return [
                {"label": "LABEL_2", "score": 0.9},
                {"label": "LABEL_0", "score": 0.8},
            ]

        with patch.object(model_sentiment, "_get_sentiment_classifier", return_value=fake_classifier):
            results = model_sentiment.analyze_sentiments_with_model(["Great quality.", "Late and broken."])

        self.assertEqual([result.sentiment for result in results], ["positive", "negative"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], ["Great quality.", "Late and broken."])


class SummaryModelTests(unittest.TestCase):
    def test_causal_summary_cleanup_removes_prompt_echoes(self) -> None:
        generated = (
            "Review: I loved the grinder.\n\n"
            "Analysis: The customer is very satisfied with the grinder's sturdy build and consistent performance. "
            "Overall, they recommend it confidently."
        )

        self.assertEqual(
            model_summarizer._clean_generated_summary(generated),
            (
                "The customer is very satisfied with the grinder's sturdy build and consistent performance. "
                "Overall, they recommend it confidently."
            ),
        )

    def test_qwen_models_use_causal_generation(self) -> None:
        self.assertTrue(model_summarizer._uses_causal_lm_model("Qwen/Qwen2.5-3B-Instruct"))
        self.assertFalse(model_summarizer._uses_causal_lm_model("google/flan-t5-large"))

    def test_explicit_quantization_uses_4bit_on_cuda(self) -> None:
        settings = model_runtime.InferenceDeviceSettings(
            model_device="cuda:0",
            pipeline_device=0,
            torch_dtype="float16",
        )

        with patch.dict(os.environ, {"REVIEWINSIGHT_SUMMARY_QUANTIZATION": "4bit"}):
            kwargs, quantized = model_summarizer._summary_model_load_kwargs(
                local_files_only=True,
                device_settings=settings,
                model_name="Qwen/Qwen2.5-1.5B-Instruct",
                bitsandbytes_config_cls=lambda **kwargs: ("bnb", kwargs),
            )

        self.assertTrue(quantized)
        self.assertEqual(kwargs["device_map"], "auto")
        self.assertEqual(kwargs["quantization_config"][0], "bnb")
        self.assertTrue(kwargs["quantization_config"][1]["load_in_4bit"])

    def test_auto_quantization_stays_plain_for_default_model_on_cuda(self) -> None:
        settings = model_runtime.InferenceDeviceSettings(
            model_device="cuda:0",
            pipeline_device=0,
            torch_dtype="float16",
        )

        kwargs, quantized = model_summarizer._summary_model_load_kwargs(
            local_files_only=True,
            device_settings=settings,
            model_name="Qwen/Qwen2.5-1.5B-Instruct",
            bitsandbytes_config_cls=lambda **kwargs: ("bnb", kwargs),
        )

        self.assertFalse(quantized)
        self.assertNotIn("quantization_config", kwargs)
        self.assertEqual(kwargs["dtype"], "float16")

    def test_auto_quantization_stays_plain_on_cpu(self) -> None:
        settings = model_runtime.InferenceDeviceSettings(model_device="cpu", pipeline_device=-1)

        kwargs, quantized = model_summarizer._summary_model_load_kwargs(
            local_files_only=True,
            device_settings=settings,
            model_name="Qwen/Qwen2.5-1.5B-Instruct",
            bitsandbytes_config_cls=lambda **kwargs: ("bnb", kwargs),
        )

        self.assertFalse(quantized)
        self.assertNotIn("quantization_config", kwargs)
        self.assertEqual(kwargs["local_files_only"], True)


class BatchAnalysisTests(unittest.TestCase):
    def test_many_reviews_batch_sentiment_and_generate_one_report_summary(self) -> None:
        sentiment_results = [
            ModelSentimentResult(
                text="Great battery and fast setup.",
                sentiment="positive",
                score=4,
                sentiment_source="transformer",
                model_name="sentiment-model",
                confidence=0.91,
            ),
            ModelSentimentResult(
                text="The case broke and support was slow.",
                sentiment="negative",
                score=-4,
                sentiment_source="transformer",
                model_name="sentiment-model",
                confidence=0.87,
            ),
        ]

        with (
            patch.object(analysis, "analyze_sentiments_with_model", return_value=sentiment_results) as sentiment_batch,
            patch.object(
                analysis,
                "summarize_with_model",
                return_value=ModelSummaryResult(
                    summary="Customers like setup and battery life, but complain about durability and support.",
                    summary_source="transformer",
                    model_name="summary-model",
                ),
            ) as summarize_batch,
        ):
            result = analysis.analyze_reviews(
                ["Great battery and fast setup.", "The case broke and support was slow."]
            )

        sentiment_batch.assert_called_once()
        summarize_batch.assert_called_once()
        self.assertEqual(result.review_count, 2)
        self.assertEqual(result.sentiment_counts, {"positive": 1, "neutral": 0, "negative": 1})
        self.assertEqual(result.overall_sentiment, "mixed")
        self.assertIn("battery", result.frequently_praised_features)
        self.assertIn("slow", result.recurring_complaints)


if __name__ == "__main__":
    unittest.main()
