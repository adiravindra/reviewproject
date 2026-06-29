from dataclasses import dataclass
import os
from typing import Any


SUMMARY_MODEL_ENV = "REVIEWINSIGHT_SUMMARY_MODEL"
DEFAULT_SUMMARIZATION_MODEL = os.getenv(SUMMARY_MODEL_ENV, "google/flan-t5-small")
MAX_INPUT_CHARACTERS = 4000
MODEL_LOCAL_ONLY_ENV = "REVIEWINSIGHT_MODEL_LOCAL_ONLY"
TRUE_VALUES = {"1", "true", "yes", "on"}

_summary_components: tuple[str, Any, Any] | None = None


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
) -> ModelSummaryResult:
    try:
        tokenizer, model = _get_summary_components(model_name)
    except Exception as exc:
        return _fallback(fallback_summary, model_name, f"model_load_failed: {exc}")

    try:
        input_text = _summarization_input(review_texts, model_name)
        tokenized_input = tokenizer(
            input_text,
            max_length=512,
            truncation=True,
            return_tensors="pt",
        )
        if hasattr(tokenized_input, "to"):
            tokenized_input = tokenized_input.to(getattr(model, "device", "cpu"))

        output_ids = model.generate(
            **tokenized_input,
            max_new_tokens=180,
            min_new_tokens=50,
            num_beams=4,
            length_penalty=0.9,
            repetition_penalty=1.15,
            no_repeat_ngram_size=3,
            do_sample=False,
        )
        summary = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    except Exception as exc:
        return _fallback(fallback_summary, model_name, f"model_inference_failed: {exc}")

    summary = " ".join(str(summary).split()).strip()
    if not summary:
        return _fallback(fallback_summary, model_name, "model_returned_empty_summary")

    cleaned_summary = _clean_generated_summary(summary)
    return ModelSummaryResult(
        summary=cleaned_summary,
        summary_source="transformer",
        model_name=model_name,
    )


def _get_summary_components(model_name: str) -> tuple[Any, Any]:
    global _summary_components

    if _summary_components is None or _summary_components[0] != model_name:
        tokenizer, model = _load_summary_components(model_name)
        _summary_components = (model_name, tokenizer, model)
    return _summary_components[1], _summary_components[2]


def ensure_summary_model_ready(model_name: str = DEFAULT_SUMMARIZATION_MODEL) -> None:
    # The runner calls this before launching the UI to avoid a slow first click.
    _get_summary_components(model_name)


def _load_summary_components(model_name: str) -> tuple[Any, Any]:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    local_files_only = _model_local_files_only()
    tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=local_files_only)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name, local_files_only=local_files_only)
    return tokenizer, model


def _summarization_input(review_texts: list[str], model_name: str = DEFAULT_SUMMARIZATION_MODEL) -> str:
    # Bound model input so unusually long reviews do not dominate inference time.
    joined = " ".join(text.strip() for text in review_texts if text.strip())
    review_text = joined[:MAX_INPUT_CHARACTERS]
    if _uses_instruction_prompt(model_name):
        return (
            "Write a detailed customer review analysis for a business owner in 3 to 4 natural sentences. "
            "Capture the full meaning of the review instead of copying one sentence from it. "
            "Mention the main praise or complaint points with concrete details, including pricing, communication, "
            "punctuality, flexibility, professionalism, quality, and the overall customer experience when those "
            "details appear. "
            "Explain why the customer likely felt that way and the overall takeaway for the business. "
            "Do not give advice directly to the customer.\n\n"
            f"Review: {review_text}\n\nAnalysis:"
        )
    return review_text


def _clean_generated_summary(text: str) -> str:
    # Let the model speak naturally, but remove prompt echoes and normalize punctuation.
    cleaned = " ".join(text.split()).strip()
    if cleaned.casefold().startswith("summary:"):
        cleaned = cleaned.split(":", 1)[1].strip()
    if not cleaned:
        return "The customer shared feedback about their experience."
    cleaned = f"{cleaned[:1].upper()}{cleaned[1:]}"
    return cleaned if cleaned.endswith((".", "!", "?")) else f"{cleaned}."


def _uses_instruction_prompt(model_name: str) -> bool:
    # FLAN/T5 checkpoints respond better when the task is phrased as an instruction.
    normalized_name = model_name.casefold()
    return "flan" in normalized_name or "t5" in normalized_name


def _model_local_files_only() -> bool:
    return os.getenv(MODEL_LOCAL_ONLY_ENV, "").strip().casefold() in TRUE_VALUES


def _fallback(summary: str, model_name: str, reason: str) -> ModelSummaryResult:
    return ModelSummaryResult(
        summary=summary,
        summary_source="rule_based_fallback",
        model_name=model_name,
        fallback_reason=reason,
    )
