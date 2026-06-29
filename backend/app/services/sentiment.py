from dataclasses import dataclass
import re


POSITIVE_WORDS = {
    "amazing",
    "best",
    "easy",
    "excellent",
    "fast",
    "good",
    "great",
    "helpful",
    "love",
    "perfect",
    "quality",
    "recommend",
}

NEGATIVE_WORDS = {
    "bad",
    "broken",
    "confusing",
    "delayed",
    "difficult",
    "hate",
    "late",
    "not",
    "poor",
    "problem",
    "refund",
    "slow",
    "terrible",
    "unfortunately",
    "waste",
    "worth",
    "worst",
}


SENTIMENT_EVIDENCE_LIMIT = 3
PHRASE_EVIDENCE_LIMIT = 8

POSITIVE_PHRASES = (
    "communication was excellent",
    "exactly at the scheduled time",
    "adjusted the day",
    "better price",
    "5 stars",
    "five stars",
    "the best",
    "best",
    "excellent communication",
    "great communication",
    "on time",
    "professional",
    "would recommend",
    "highly recommend",
)
NEUTRAL_PHRASES = (
    "as expected",
    "average",
    "decent",
    "fair",
    "fine",
    "mixed",
    "ok",
    "okay",
)
NEGATIVE_PHRASES = (
    "poor communication",
    "bad communication",
    "not on time",
    "late",
    "delayed",
    "too expensive",
    "doubled in price",
    "waste of money",
    "worst",
    "terrible",
    "refund",
)
WORD_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9'-]*")


# A tiny sentiment result object keeps the return value easy to read.
@dataclass(frozen=True)
class SentimentResult:
    text: str
    sentiment: str
    score: int


@dataclass(frozen=True)
class SentimentEvidence:
    phrase: str
    tone: str
    start: int
    end: int


def analyze_sentiment(text: str) -> SentimentResult:
    # Count simple positive and negative words.
    words = {word.strip(".,!?;:()[]{}\"'").casefold() for word in text.split()}
    score = len(words & POSITIVE_WORDS) - len(words & NEGATIVE_WORDS)

    if score > 0:
        sentiment = "positive"
    elif score < 0:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return SentimentResult(text=text, sentiment=sentiment, score=score)


def explain_sentiment(text: str, sentiment: str, score: int, confidence: float | None = None) -> str:
    """Create a short human-readable reason for the sentiment classification."""
    words = {word.strip(".,!?;:()[]{}\"'").casefold() for word in text.split()}
    positive_hits = sorted(words & POSITIVE_WORDS)
    negative_hits = sorted(words & NEGATIVE_WORDS)
    confidence_text = _confidence_text(confidence)

    if sentiment == "positive":
        evidence = _evidence_phrase(
            sentiment_evidence(text, "positive"),
            positive_hits,
            "positive wording",
            "positive phrases",
        )
        return f"This review was classified as positive{confidence_text} because it includes {evidence}."
    if sentiment == "negative":
        evidence = _evidence_phrase(
            sentiment_evidence(text, "negative"),
            negative_hits,
            "negative wording or unresolved problems",
            "negative phrases",
        )
        return f"This review was classified as negative{confidence_text} because it includes {evidence}."

    if positive_hits and negative_hits:
        return (
            f"This review was classified as neutral{confidence_text} because it contains both positive and negative signals, "
            "so the overall tone is mixed."
        )
    return (
        f"This review was classified as neutral{confidence_text} because it does not contain enough clearly positive "
        "or negative language to move the result in either direction."
    )


def sentiment_breakdown(review_texts: list[str]) -> dict[str, int]:
    breakdown = {"positive": 0, "neutral": 0, "negative": 0}

    for text in review_texts:
        result = analyze_sentiment(text)
        breakdown[result.sentiment] += 1

    return breakdown


def overall_sentiment(review_texts: list[str]) -> str:
    breakdown = sentiment_breakdown(review_texts)
    positive_count = breakdown["positive"]
    negative_count = breakdown["negative"]

    if positive_count and negative_count:
        return "mixed"
    if positive_count > negative_count:
        return "positive"
    if negative_count > positive_count:
        return "negative"
    return "neutral"


def sentiment_evidence(text: str, tone: str | None = None) -> list[SentimentEvidence]:
    """Return ordered sentiment words and phrases found in the review text."""
    normalized_tone = tone.casefold() if tone else None
    evidence: list[SentimentEvidence] = []
    occupied: list[tuple[int, int]] = []

    tone_phrases = {
        "positive": POSITIVE_PHRASES,
        "neutral": NEUTRAL_PHRASES,
        "negative": NEGATIVE_PHRASES,
    }
    phrase_items = [
        (item_tone, phrase)
        for item_tone, phrases in tone_phrases.items()
        for phrase in phrases
        if normalized_tone in {None, item_tone}
    ]
    phrase_items.sort(key=lambda item: len(item[1]), reverse=True)

    for item_tone, phrase in phrase_items:
        for match in _phrase_matches(text, phrase):
            span = (match.start(), match.end())
            if _overlaps(span, occupied):
                continue
            evidence.append(
                SentimentEvidence(
                    phrase=_normalize_evidence_phrase(match.group(0)),
                    tone=item_tone,
                    start=match.start(),
                    end=match.end(),
                )
            )
            occupied.append(span)

    word_tones = {
        "positive": POSITIVE_WORDS,
        "neutral": set(NEUTRAL_PHRASES),
        "negative": NEGATIVE_WORDS,
    }
    for match in WORD_PATTERN.finditer(text):
        span = (match.start(), match.end())
        if _overlaps(span, occupied):
            continue
        word = match.group(0).casefold().strip("'")
        for item_tone, tone_words in word_tones.items():
            if normalized_tone not in {None, item_tone}:
                continue
            if word in tone_words:
                evidence.append(
                    SentimentEvidence(
                        phrase=_normalize_evidence_phrase(match.group(0)),
                        tone=item_tone,
                        start=match.start(),
                        end=match.end(),
                    )
                )
                occupied.append(span)
                break

    return sorted(evidence, key=lambda item: item.start)


def _confidence_text(confidence: float | None) -> str:
    if confidence is None:
        return ""
    return f" with {confidence:.0%} model confidence"


def _evidence_phrase(
    phrase_matches: list[SentimentEvidence],
    word_matches: list[str],
    fallback: str,
    label: str,
) -> str:
    examples = [item.phrase for item in phrase_matches[:PHRASE_EVIDENCE_LIMIT]]
    if not examples:
        examples = word_matches[:SENTIMENT_EVIDENCE_LIMIT]
    if not examples:
        return fallback
    return f"{label} such as {', '.join(examples)}"


def _phrase_matches(text: str, phrase: str) -> list[re.Match[str]]:
    pattern = r"\b" + r"\s+".join(re.escape(part) for part in phrase.split()) + r"\b"
    return list(re.finditer(pattern, text, flags=re.IGNORECASE))


def _overlaps(span: tuple[int, int], occupied: list[tuple[int, int]]) -> bool:
    start, end = span
    return any(start < occupied_end and end > occupied_start for occupied_start, occupied_end in occupied)


def _normalize_evidence_phrase(text: str) -> str:
    normalized = " ".join(text.casefold().split()).strip(" .,!?:;\"'")
    if normalized.startswith("the "):
        return normalized[4:]
    return normalized
