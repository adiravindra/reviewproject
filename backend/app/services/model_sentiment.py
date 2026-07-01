from dataclasses import dataclass
import os
from typing import Any

from backend.app.services.model_runtime import resolve_inference_device
from backend.app.services.sentiment import SentimentResult, analyze_sentiment


TRANSFORMER_SENTIMENT_TASK = "sentiment-analysis"
SENTIMENT_MODEL_ENV = "REVIEWINSIGHT_SENTIMENT_MODEL"
DEFAULT_SENTIMENT_MODEL = os.getenv(
    SENTIMENT_MODEL_ENV,
    "cardiffnlp/twitter-roberta-base-sentiment-latest",
)
MODEL_LOCAL_ONLY_ENV = "REVIEWINSIGHT_MODEL_LOCAL_ONLY"
SENTIMENT_BATCH_SIZE_ENV = "REVIEWINSIGHT_SENTIMENT_BATCH_SIZE"
TRUE_VALUES = {"1", "true", "yes", "on"}
DEFAULT_SENTIMENT_BATCH_SIZE = 16

pipeline: Any | None = None
_sentiment_classifier: tuple[str, Any] | None = None


@dataclass(frozen=True)
class ModelSentimentResult(SentimentResult):
    sentiment_source: str = "rule_based_fallback"
    model_name: str | None = None
    confidence: float | None = None
    fallback_reason: str | None = None


def analyze_sentiment_with_model(
    text: str,
    model_name: str = DEFAULT_SENTIMENT_MODEL,
) -> ModelSentimentResult:
    return analyze_sentiments_with_model([text], model_name=model_name)[0]


def analyze_sentiments_with_model(
    texts: list[str],
    model_name: str = DEFAULT_SENTIMENT_MODEL,
) -> list[ModelSentimentResult]:
    if not texts:
        return []

    fallbacks = [analyze_sentiment(text) for text in texts]

    try:
        classifier = _get_sentiment_classifier(model_name)
    except Exception as exc:
        return [_fallback(fallback, model_name, f"model_load_failed: {exc}") for fallback in fallbacks]

    try:
        output = classifier(
            [text[:4000] for text in texts],
            batch_size=_sentiment_batch_size(),
            truncation=True,
        )
    except Exception as exc:
        return [_fallback(fallback, model_name, f"model_inference_failed: {exc}") for fallback in fallbacks]

    outputs = output if isinstance(output, list) else [output]
    results: list[ModelSentimentResult] = []
    for text, fallback, item in zip(texts, fallbacks, outputs, strict=False):
        parsed = _parse_classifier_output(item)
        if parsed is None:
            results.append(_fallback(fallback, model_name, "model_returned_invalid_sentiment"))
            continue

        sentiment, confidence = parsed
        results.append(
            ModelSentimentResult(
                text=text,
                sentiment=sentiment,
                score=_confidence_to_score(sentiment, confidence),
                sentiment_source="transformer",
                model_name=model_name,
                confidence=confidence,
            )
        )

    if len(results) < len(texts):
        for fallback in fallbacks[len(results) :]:
            results.append(_fallback(fallback, model_name, "model_returned_incomplete_sentiment_batch"))
    return results


def _get_sentiment_classifier(model_name: str) -> Any:
    global _sentiment_classifier

    if _sentiment_classifier is None or _sentiment_classifier[0] != model_name:
        _sentiment_classifier = (model_name, _load_sentiment_pipeline(model_name))
    return _sentiment_classifier[1]


def ensure_sentiment_model_ready(model_name: str = DEFAULT_SENTIMENT_MODEL) -> None:
    # Used by the runner to fail early if the configured model cannot load.
    _get_sentiment_classifier(model_name)


def _load_sentiment_pipeline(model_name: str) -> Any:
    global pipeline

    if pipeline is None:
        from transformers import pipeline as transformers_pipeline

        pipeline = transformers_pipeline

    device_settings = resolve_inference_device()
    return pipeline(
        TRANSFORMER_SENTIMENT_TASK,
        model=model_name,
        device=device_settings.pipeline_device,
        local_files_only=_model_local_files_only(),
    )


def _parse_classifier_output(output: Any) -> tuple[str, float] | None:
    # Transformers pipelines usually return a list with one label/score dict,
    # but this accepts a bare dict to keep the boundary tolerant.
    if isinstance(output, list) and output and isinstance(output[0], dict):
        item = output[0]
    elif isinstance(output, dict):
        item = output
    else:
        return None

    label = str(item.get("label", "")).casefold()
    try:
        confidence = float(item.get("score", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    if label in {"label_2", "pos"} or "positive" in label:
        return "positive", confidence
    if label in {"label_0", "neg"} or "negative" in label:
        return "negative", confidence
    if label == "label_1" or "neutral" in label:
        return "neutral", confidence
    return None


def _confidence_to_score(sentiment: str, confidence: float) -> int:
    score = max(1, int(confidence * 5))
    if sentiment == "negative":
        return -score
    if sentiment == "neutral":
        return 0
    return score


def _model_local_files_only() -> bool:
    return os.getenv(MODEL_LOCAL_ONLY_ENV, "").strip().casefold() in TRUE_VALUES


def _sentiment_batch_size() -> int:
    try:
        return max(1, int(os.getenv(SENTIMENT_BATCH_SIZE_ENV, str(DEFAULT_SENTIMENT_BATCH_SIZE))))
    except ValueError:
        return DEFAULT_SENTIMENT_BATCH_SIZE


def _fallback(fallback: SentimentResult, model_name: str, reason: str) -> ModelSentimentResult:
    return ModelSentimentResult(
        text=fallback.text,
        sentiment=fallback.sentiment,
        score=fallback.score,
        sentiment_source="rule_based_fallback",
        model_name=model_name,
        fallback_reason=reason,
    )
