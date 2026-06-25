from dataclasses import dataclass
import os
from time import monotonic
from typing import Any


DEFAULT_SUMMARIZATION_MODEL = "Falconsai/text_summarization"
DEFAULT_MAX_INFERENCE_SECONDS = 20.0
MAX_INPUT_CHARACTERS = 4000
ENABLE_MODEL_SUMMARY_ENV = "REVIEWINSIGHT_ENABLE_MODEL_SUMMARY"
MODEL_LOCAL_ONLY_ENV = "REVIEWINSIGHT_MODEL_LOCAL_ONLY"
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}

_summary_components: tuple[Any, Any] | None = None


@dataclass(frozen=True)
class ModelSummaryResult:
    summary: str
    summary_source: str
    model_name: str | None = None
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

    try:
        tokenizer, model = _get_summary_components(model_name)
    except Exception as exc:
        return _fallback(fallback_summary, model_name, f"model_load_failed: {exc}")

    try:
        tokenized_input = tokenizer(
            _summarization_input(review_texts),
            max_length=512,
            truncation=True,
            return_tensors="pt",
        )
        if hasattr(tokenized_input, "to"):
            tokenized_input = tokenized_input.to(getattr(model, "device", "cpu"))

        output_ids = model.generate(
            **tokenized_input,
            max_new_tokens=80,
            min_new_tokens=20,
            num_beams=4,
            do_sample=False,
        )
        summary = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    except Exception as exc:
        return _fallback(fallback_summary, model_name, f"model_inference_failed: {exc}")

    elapsed = monotonic() - started_at
    if elapsed > max_inference_seconds:
        return _fallback(fallback_summary, model_name, f"model_inference_too_slow: {elapsed:.2f}s")

    summary = " ".join(str(summary).split()).strip()
    if not summary:
        return _fallback(fallback_summary, model_name, "model_returned_empty_summary")

    return ModelSummaryResult(
        summary=_format_review_summary(summary, review_texts),
        summary_source="transformer",
        model_name=model_name,
    )


def _get_summary_components(model_name: str) -> tuple[Any, Any]:
    global _summary_components

    if _summary_components is None:
        _summary_components = _load_summary_components(model_name)
    return _summary_components


def ensure_summary_model_ready(model_name: str = DEFAULT_SUMMARIZATION_MODEL) -> None:
    if _model_summary_enabled():
        _get_summary_components(model_name)


def _load_summary_components(model_name: str) -> tuple[Any, Any]:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    local_files_only = _model_local_files_only()
    tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=local_files_only)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name, local_files_only=local_files_only)
    return tokenizer, model


def _summarization_input(review_texts: list[str]) -> str:
    joined = " ".join(text.strip() for text in review_texts if text.strip())
    return joined[:MAX_INPUT_CHARACTERS]


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
