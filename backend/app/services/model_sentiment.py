from dataclasses import dataclass
import os
from typing import Any

from backend.app.services.sentiment import SentimentResult, analyze_sentiment


TRANSFORMER_SENTIMENT_TASK = "sentiment-analysis"
DEFAULT_SENTIMENT_MODEL = "distilbert-base-uncased-finetuned-sst-2-english"
ENABLE_MODEL_SENTIMENT_ENV = "REVIEWINSIGHT_ENABLE_MODEL_SENTIMENT"
MODEL_LOCAL_ONLY_ENV = "REVIEWINSIGHT_MODEL_LOCAL_ONLY"
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}

pipeline: Any | None = None
_sentiment_classifier: Any | None = None


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
    fallback = analyze_sentiment(text)

    if not _model_sentiment_enabled():
        return _fallback(fallback, model_name, "model_sentiment_disabled")

    try:
        classifier = _get_sentiment_classifier(model_name)
    except Exception as exc:
        return _fallback(fallback, model_name, f"model_load_failed: {exc}")

    try:
        output = classifier(text[:4000])
    except Exception as exc:
        return _fallback(fallback, model_name, f"model_inference_failed: {exc}")

    parsed = _parse_classifier_output(output)
    if parsed is None:
        return _fallback(fallback, model_name, "model_returned_invalid_sentiment")

    sentiment, confidence = parsed
    return ModelSentimentResult(
        text=text,
        sentiment=sentiment,
        score=_confidence_to_score(sentiment, confidence),
        sentiment_source="transformer",
        model_name=model_name,
        confidence=confidence,
    )


def _get_sentiment_classifier(model_name: str) -> Any:
    global _sentiment_classifier

    if _sentiment_classifier is None:
        _sentiment_classifier = _load_sentiment_pipeline(model_name)
    return _sentiment_classifier


def ensure_sentiment_model_ready(model_name: str = DEFAULT_SENTIMENT_MODEL) -> None:
    if _model_sentiment_enabled():
        _get_sentiment_classifier(model_name)


def _load_sentiment_pipeline(model_name: str) -> Any:
    global pipeline

    if pipeline is None:
        from transformers import pipeline as transformers_pipeline

        pipeline = transformers_pipeline

    return pipeline(
        TRANSFORMER_SENTIMENT_TASK,
        model=model_name,
        local_files_only=_model_local_files_only(),
    )


def _parse_classifier_output(output: Any) -> tuple[str, float] | None:
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

    if "positive" in label or label in {"label_1", "pos"}:
        return "positive", confidence
    if "negative" in label or label in {"label_0", "neg"}:
        return "negative", confidence
    if "neutral" in label:
        return "neutral", confidence
    return None


def _confidence_to_score(sentiment: str, confidence: float) -> int:
    score = max(1, int(confidence * 5))
    if sentiment == "negative":
        return -score
    if sentiment == "neutral":
        return 0
    return score


def _model_sentiment_enabled() -> bool:
    configured_value = os.getenv(ENABLE_MODEL_SENTIMENT_ENV, "").strip().casefold()
    if configured_value in FALSE_VALUES:
        return False
    return True


def _model_local_files_only() -> bool:
    return os.getenv(MODEL_LOCAL_ONLY_ENV, "").strip().casefold() in TRUE_VALUES


def _fallback(fallback: SentimentResult, model_name: str, reason: str) -> ModelSentimentResult:
    return ModelSentimentResult(
        text=fallback.text,
        sentiment=fallback.sentiment,
        score=fallback.score,
        sentiment_source="rule_based_fallback",
        model_name=model_name,
        fallback_reason=reason,
    )
