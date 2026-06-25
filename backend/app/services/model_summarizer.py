from dataclasses import dataclass
import os
from time import monotonic
from typing import Any


TRANSFORMER_SUMMARIZATION_TASK = "summarization"
DEFAULT_SUMMARIZATION_MODEL = "sshleifer/distilbart-cnn-12-6"
DEFAULT_MAX_INFERENCE_SECONDS = 12.0
MAX_INPUT_CHARACTERS = 4000
ENABLE_MODEL_SUMMARY_ENV = "REVIEWINSIGHT_ENABLE_MODEL_SUMMARY"
MODEL_LOCAL_ONLY_ENV = "REVIEWINSIGHT_MODEL_LOCAL_ONLY"
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}

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
    if not _model_summary_enabled():
        return _fallback(fallback_summary, model_name, "model_summary_disabled")

    started_at = monotonic()

    # If anything goes wrong, return the simple summary instead of crashing.
    try:
        summarizer = _get_summarizer(model_name)
    except Exception as exc:
        return _fallback(fallback_summary, model_name, f"model_load_failed: {exc}")

    try:
        output = summarizer(
            _summarization_input(review_texts),
            max_length=80,
            min_length=20,
            do_sample=False,
            clean_up_tokenization_spaces=False,
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
        summary=_format_review_summary(summary, review_texts),
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

    if pipeline is None:
        from transformers import (
            AutoModelForSeq2SeqLM,
            AutoTokenizer,
            pipeline as transformers_pipeline,
        )

        pipeline = transformers_pipeline
    else:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    local_files_only = _model_local_files_only()
    tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=local_files_only)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name, local_files_only=local_files_only)
    return pipeline, tokenizer, model


def _summarization_input(review_texts: list[str]) -> str:
    joined = " ".join(text.strip() for text in review_texts if text.strip())
    return joined[:MAX_INPUT_CHARACTERS]


def _extract_summary_text(output: Any) -> str:
    generated_text = ""
    if isinstance(output, list) and output and isinstance(output[0], dict):
        generated_text = str(output[0].get("summary_text") or output[0].get("generated_text") or "")
    elif isinstance(output, dict):
        generated_text = str(output.get("summary_text") or output.get("generated_text") or "")

    if "Summary:" in generated_text:
        generated_text = generated_text.rsplit("Summary:", 1)[-1]

    return " ".join(generated_text.split()).strip()


def _format_review_summary(summary: str, review_texts: list[str]) -> str:
    cleaned_summary = _sentence_fragment(summary)
    reason = _supporting_reason(review_texts)
    return f"The review states that {cleaned_summary}. This is because {reason}."


def _sentence_fragment(text: str) -> str:
    cleaned = " ".join(text.split()).strip(" .")
    if not cleaned:
        return "the customer shared feedback"
    return f"{cleaned[:1].casefold()}{cleaned[1:]}"


def _supporting_reason(review_texts: list[str]) -> str:
    joined = " ".join(text.strip() for text in review_texts if text.strip())
    first_sentence = joined.replace("\n", " ").split(".", 1)[0].strip(" ,;:")
    if not first_sentence:
        return "the customer mentions specific details from the review"
    return f'the customer mentions "{first_sentence}"'


def _model_summary_enabled() -> bool:
    configured_value = os.getenv(ENABLE_MODEL_SUMMARY_ENV, "").strip().casefold()
    if configured_value in FALSE_VALUES:
        return False
    return True


def _model_local_files_only() -> bool:
    return os.getenv(MODEL_LOCAL_ONLY_ENV, "").strip().casefold() in TRUE_VALUES


def _fallback(summary: str, model_name: str, reason: str) -> ModelSummaryResult:
    return ModelSummaryResult(
        summary=summary,
        summary_source="rule_based_fallback",
        model_name=model_name,
        fallback_reason=reason,
    )
