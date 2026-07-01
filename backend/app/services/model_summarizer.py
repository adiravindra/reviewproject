from dataclasses import dataclass
import os
import re
from typing import Any

from backend.app.services.model_runtime import inference_context, resolve_inference_device


SUMMARY_MODEL_ENV = "REVIEWINSIGHT_SUMMARY_MODEL"
DEFAULT_SUMMARIZATION_MODEL = os.getenv(SUMMARY_MODEL_ENV, "Qwen/Qwen2.5-1.5B-Instruct")
MAX_INPUT_CHARACTERS = 4000
MODEL_LOCAL_ONLY_ENV = "REVIEWINSIGHT_MODEL_LOCAL_ONLY"
SUMMARY_QUANTIZATION_ENV = "REVIEWINSIGHT_SUMMARY_QUANTIZATION"
SUMMARY_MAX_NEW_TOKENS_ENV = "REVIEWINSIGHT_SUMMARY_MAX_NEW_TOKENS"
SUMMARY_NUM_BEAMS_ENV = "REVIEWINSIGHT_SUMMARY_NUM_BEAMS"
TRUE_VALUES = {"1", "true", "yes", "on"}
DEFAULT_SUMMARY_MAX_NEW_TOKENS = 120
DEFAULT_SUMMARY_NUM_BEAMS = 2

_summary_components: tuple[str, str, Any, Any] | None = None


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
        model_type, tokenizer, model = _get_summary_components(model_name)
    except Exception as exc:
        return _fallback(fallback_summary, model_name, f"model_load_failed: {exc}")

    try:
        if model_type == "causal":
            summary = _generate_causal_summary(review_texts, tokenizer, model)
        else:
            summary = _generate_seq2seq_summary(review_texts, model_name, tokenizer, model)
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


def _get_summary_components(model_name: str) -> tuple[str, Any, Any]:
    global _summary_components

    if _summary_components is None or _summary_components[0] != model_name:
        model_type, tokenizer, model = _load_summary_components(model_name)
        _summary_components = (model_name, model_type, tokenizer, model)
    return _summary_components[1], _summary_components[2], _summary_components[3]


def ensure_summary_model_ready(model_name: str = DEFAULT_SUMMARIZATION_MODEL) -> None:
    # The runner calls this before launching the UI to avoid a slow first click.
    _get_summary_components(model_name)


def _load_summary_components(model_name: str) -> tuple[str, Any, Any]:
    from transformers import AutoModelForCausalLM, AutoModelForSeq2SeqLM, AutoTokenizer

    local_files_only = _model_local_files_only()
    device_settings = resolve_inference_device()
    model_kwargs, quantized = _summary_model_load_kwargs(local_files_only, device_settings, model_name)

    tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=local_files_only)
    if _uses_causal_lm_model(model_name):
        model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
        return "causal", tokenizer, _prepare_model_for_inference(model, device_settings.model_device, quantized)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name, **model_kwargs)
    return "seq2seq", tokenizer, _prepare_model_for_inference(model, device_settings.model_device, quantized)


def _generate_seq2seq_summary(review_texts: list[str], model_name: str, tokenizer: Any, model: Any) -> str:
    input_text = _summarization_input(review_texts, model_name)
    tokenized_input = tokenizer(
        input_text,
        max_length=512,
        truncation=True,
        return_tensors="pt",
    )
    if hasattr(tokenized_input, "to"):
        tokenized_input = tokenized_input.to(getattr(model, "device", "cpu"))

    with inference_context():
        output_ids = model.generate(
            **tokenized_input,
            max_new_tokens=_summary_max_new_tokens(),
            min_new_tokens=40,
            num_beams=_summary_num_beams(),
            length_penalty=0.9,
            repetition_penalty=1.15,
            no_repeat_ngram_size=3,
            do_sample=False,
        )
    return tokenizer.decode(output_ids[0], skip_special_tokens=True)


def _generate_causal_summary(review_texts: list[str], tokenizer: Any, model: Any) -> str:
    prompt = _causal_prompt(review_texts, tokenizer)
    tokenized_input = tokenizer(
        prompt,
        max_length=2048,
        truncation=True,
        return_tensors="pt",
    )
    if hasattr(tokenized_input, "to"):
        tokenized_input = tokenized_input.to(getattr(model, "device", "cpu"))

    input_length = tokenized_input["input_ids"].shape[-1]
    with inference_context():
        output_ids = model.generate(
            **tokenized_input,
            max_new_tokens=_summary_max_new_tokens(),
            do_sample=False,
            repetition_penalty=1.08,
            pad_token_id=getattr(tokenizer, "eos_token_id", None),
        )
    generated_ids = output_ids[0][input_length:]
    return tokenizer.decode(generated_ids, skip_special_tokens=True)


def _causal_prompt(review_texts: list[str], tokenizer: Any) -> str:
    review_text = _joined_review_text(review_texts)
    messages = [
        {
            "role": "system",
            "content": (
                "You write polished customer-review summaries for business owners. "
                "Be specific, natural, and concise."
            ),
        },
        {
            "role": "user",
            "content": (
                "Summarize this customer review in 2 to 4 natural sentences. "
                "Capture the main sentiment, the concrete product or service details, important supporting points, "
                "and the customer's overall takeaway. Do not sound generic or robotic. "
                "Return only the summary.\n\n"
                f"Review: {review_text}"
            ),
        },
    ]
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return f"{messages[0]['content']}\n\n{messages[1]['content']}\n\nSummary:"


def _summarization_input(review_texts: list[str], model_name: str = DEFAULT_SUMMARIZATION_MODEL) -> str:
    # Bound model input so unusually long reviews do not dominate inference time.
    review_text = _joined_review_text(review_texts)
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


def _joined_review_text(review_texts: list[str]) -> str:
    joined = " ".join(text.strip() for text in review_texts if text.strip())
    return joined[:MAX_INPUT_CHARACTERS]


def _clean_generated_summary(text: str) -> str:
    # Let the model speak naturally, but remove prompt echoes and normalize punctuation.
    cleaned = " ".join(text.split()).strip()
    cleaned = _strip_prompt_echo(cleaned)
    if cleaned.casefold().startswith(("summary:", "analysis:")):
        cleaned = cleaned.split(":", 1)[1].strip()
    if not cleaned:
        return "The customer shared feedback about their experience."
    cleaned = f"{cleaned[:1].upper()}{cleaned[1:]}"
    return cleaned if cleaned.endswith((".", "!", "?")) else f"{cleaned}."


def _strip_prompt_echo(text: str) -> str:
    for marker in ("Analysis:", "Summary:"):
        matches = list(re.finditer(re.escape(marker), text, flags=re.IGNORECASE))
        if matches:
            return text[matches[-1].end() :].strip()
    return text


def _uses_instruction_prompt(model_name: str) -> bool:
    # FLAN/T5 checkpoints respond better when the task is phrased as an instruction.
    normalized_name = model_name.casefold()
    return "flan" in normalized_name or "t5" in normalized_name


def _uses_causal_lm_model(model_name: str) -> bool:
    normalized_name = model_name.casefold()
    causal_markers = ("qwen", "gemma", "phi-", "llama", "mistral")
    return any(marker in normalized_name for marker in causal_markers)


def _model_local_files_only() -> bool:
    return os.getenv(MODEL_LOCAL_ONLY_ENV, "").strip().casefold() in TRUE_VALUES


def _summary_model_load_kwargs(
    local_files_only: bool,
    device_settings: Any,
    model_name: str = DEFAULT_SUMMARIZATION_MODEL,
    bitsandbytes_config_cls: Any | None = None,
) -> tuple[dict[str, Any], bool]:
    kwargs: dict[str, Any] = {"local_files_only": local_files_only}
    quantization_mode = _summary_quantization_mode(device_settings, model_name)
    if quantization_mode in {"4bit", "8bit"}:
        if bitsandbytes_config_cls is None:
            from transformers import BitsAndBytesConfig

            bitsandbytes_config_cls = BitsAndBytesConfig

        quantization_kwargs: dict[str, Any]
        if quantization_mode == "4bit":
            quantization_kwargs = {
                "load_in_4bit": True,
                "bnb_4bit_compute_dtype": device_settings.torch_dtype,
                "bnb_4bit_quant_type": "nf4",
                "bnb_4bit_use_double_quant": True,
            }
        else:
            quantization_kwargs = {"load_in_8bit": True}
        kwargs["quantization_config"] = bitsandbytes_config_cls(**quantization_kwargs)
        kwargs["device_map"] = "auto"
        return kwargs, True

    if device_settings.torch_dtype is not None:
        kwargs["dtype"] = device_settings.torch_dtype
    return kwargs, False


def _summary_quantization_mode(device_settings: Any, model_name: str) -> str:
    requested = os.getenv(SUMMARY_QUANTIZATION_ENV, "auto").strip().casefold()
    if requested in {"none", "off", "false", "0"}:
        return "none"
    if requested in {"4bit", "8bit"} and str(device_settings.model_device).startswith("cuda"):
        return requested
    if (
        requested == "auto"
        and str(device_settings.model_device).startswith("cuda")
        and _prefers_quantization(model_name)
    ):
        return "4bit"
    return "none"


def _prefers_quantization(model_name: str) -> bool:
    normalized_name = model_name.casefold()
    large_markers = ("3b", "4b", "7b", "8b", "14b", "32b", "70b")
    return any(marker in normalized_name for marker in large_markers)


def _prepare_model_for_inference(model: Any, model_device: str, quantized: bool = False) -> Any:
    if not quantized and hasattr(model, "to"):
        model = model.to(model_device)
    if hasattr(model, "eval"):
        model.eval()
    return model


def _summary_max_new_tokens() -> int:
    try:
        return max(32, int(os.getenv(SUMMARY_MAX_NEW_TOKENS_ENV, str(DEFAULT_SUMMARY_MAX_NEW_TOKENS))))
    except ValueError:
        return DEFAULT_SUMMARY_MAX_NEW_TOKENS


def _summary_num_beams() -> int:
    try:
        return max(1, int(os.getenv(SUMMARY_NUM_BEAMS_ENV, str(DEFAULT_SUMMARY_NUM_BEAMS))))
    except ValueError:
        return DEFAULT_SUMMARY_NUM_BEAMS


def _fallback(summary: str, model_name: str, reason: str) -> ModelSummaryResult:
    return ModelSummaryResult(
        summary=summary,
        summary_source="rule_based_fallback",
        model_name=model_name,
        fallback_reason=reason,
    )
