from dataclasses import dataclass
from time import monotonic
from typing import Any


TRANSFORMER_SUMMARIZATION_TASK = "text-generation"
DEFAULT_SUMMARIZATION_MODEL = "distilgpt2"
DEFAULT_MAX_INFERENCE_SECONDS = 12.0
MAX_INPUT_CHARACTERS = 4000

pipeline: Any | None = None
_summarizer_pipeline: Any | None = None


# Small return object for either a model summary or a fallback summary.
@dataclass(frozen=True)
class ModelSummaryResult:
    summary: str
    summary_source: str
    model_name: str
    fallback_reason: str | None = None


def summarize_with_model(
    review_texts: list[str],
    fallback_summary: str,
    model_name: str = DEFAULT_SUMMARIZATION_MODEL,
    max_inference_seconds: float = DEFAULT_MAX_INFERENCE_SECONDS,
) -> ModelSummaryResult:
    started_at = monotonic()

    # If anything goes wrong, return the simple summary instead of crashing.
    try:
        summarizer = _get_summarizer(model_name)
    except Exception as exc:
        return _fallback(fallback_summary, model_name, f"model_load_failed: {exc}")

    try:
        output = summarizer(
            _summarization_input(review_texts),
            max_new_tokens=60,
            do_sample=False,
            no_repeat_ngram_size=3,
            repetition_penalty=1.2,
            clean_up_tokenization_spaces=False,
            return_full_text=False,
        )
    except Exception as exc:
        return _fallback(fallback_summary, model_name, f"model_inference_failed: {exc}")

    elapsed = monotonic() - started_at
    if elapsed > max_inference_seconds:
        return _fallback(
            fallback_summary,
            model_name,
            f"model_inference_too_slow: {elapsed:.2f}s",
        )

    summary = _extract_summary_text(output)
    if not summary:
        return _fallback(fallback_summary, model_name, "model_returned_empty_summary")

    return ModelSummaryResult(
        summary=summary,
        summary_source="transformer",
        model_name=model_name,
    )


def _get_summarizer(model_name: str) -> Any:
    global _summarizer_pipeline

    if _summarizer_pipeline is None:
        pipeline_factory, tokenizer, model = _load_local_model(model_name)
        _summarizer_pipeline = pipeline_factory(
            TRANSFORMER_SUMMARIZATION_TASK,
            model=model,
            tokenizer=tokenizer,
        )
    return _summarizer_pipeline


def _load_local_model(model_name: str) -> tuple[Any, Any, Any]:
    global pipeline

    # local_files_only keeps this MVP from downloading files during a request.
    if pipeline is None:
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            pipeline as transformers_pipeline,
        )

        pipeline = transformers_pipeline
    else:
        from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(model_name, local_files_only=True)
    return pipeline, tokenizer, model


def _summarization_input(review_texts: list[str]) -> str:
    joined = " ".join(text.strip() for text in review_texts if text.strip())
    return (
        "Summarize this customer review feedback in one concise sentence:\n"
        f"{joined[:MAX_INPUT_CHARACTERS]}\n\nSummary:"
    )


def _extract_summary_text(output: Any) -> str:
    generated_text = ""
    if isinstance(output, list) and output and isinstance(output[0], dict):
        generated_text = str(output[0].get("summary_text") or output[0].get("generated_text") or "")
    elif isinstance(output, dict):
        generated_text = str(output.get("summary_text") or output.get("generated_text") or "")

    if "Summary:" in generated_text:
        generated_text = generated_text.rsplit("Summary:", 1)[-1]

    return " ".join(generated_text.split()).strip()


def _fallback(summary: str, model_name: str, reason: str) -> ModelSummaryResult:
    return ModelSummaryResult(
        summary=summary,
        summary_source="rule_based_fallback",
        model_name=model_name,
        fallback_reason=reason,
    )
