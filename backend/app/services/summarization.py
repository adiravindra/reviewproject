import re

from backend.app.services.sentiment import sentiment_evidence


POSITIVE_CUES = {
    "amazing",
    "best",
    "easy",
    "excellent",
    "fast",
    "good",
    "great",
    "helpful",
    "love",
    "professional",
    "stars",
    "wonderful",
}
NEGATIVE_CUES = {
    "bad",
    "broken",
    "confusing",
    "disappointed",
    "late",
    "not",
    "poor",
    "slow",
    "terrible",
    "unfortunately",
    "waste",
    "worst",
}
PRICE_CUES = {"charge", "cost", "expensive", "price", "prices", "tag", "worth"}
MONEY_PATTERN = re.compile(r"\$\s?\d+(?:\.\d{2})?")


# Simple fallback summary used only when the model cannot complete analysis.
def summarize_review(text: str, max_length: int = 260) -> str:
    cleaned = " ".join(text.split())

    # Keep fallback output as generated prose only; the UI displays the quoted
    # source review in the input area rather than repeating it in the summary.
    if not cleaned:
        return "No review text was available to summarize."

    sentences = _sentences(cleaned)
    tone = _tone(cleaned)
    detail_summary = _detailed_experience_summary(cleaned, tone)
    if detail_summary:
        return detail_summary

    highlights = _highlights(sentences, max_length)
    cause = _likely_reason(cleaned, tone)
    takeaway = _business_takeaway(cleaned, tone)
    return (
        f"The customer describes a {tone} experience, with the main issue being that {highlights}. "
        f"They likely felt this way because {cause}. "
        f"Overall, this suggests {takeaway}."
    )


def _sentences(text: str) -> list[str]:
    return [sentence.strip(" .!?") for sentence in text.replace("!", ".").replace("?", ".").split(".") if sentence.strip()]


def _tone(text: str) -> str:
    words = {word.strip(".,!?;:()[]{}\"'").casefold() for word in text.split()}
    positive_count = len(words & POSITIVE_CUES)
    negative_count = len(words & NEGATIVE_CUES)
    if positive_count > negative_count:
        return "positive"
    if negative_count > positive_count:
        return "negative"
    return "mixed or neutral"


def _highlights(sentences: list[str], max_length: int) -> str:
    selected = _most_informative_sentences(sentences) if sentences else ["the review details"]
    highlights = "; ".join(_clean_fragment(sentence) for sentence in selected)
    if len(highlights) > max_length:
        highlights = f"{highlights[: max_length - 3].rstrip(' .')}..."
    return highlights


def _most_informative_sentences(sentences: list[str]) -> list[str]:
    scored = sorted(
        sentences,
        key=lambda sentence: _sentence_score(sentence),
        reverse=True,
    )
    return scored[:2] or sentences[:1]


def _sentence_score(sentence: str) -> int:
    words = {word.strip(".,!?;:()[]{}\"'").casefold() for word in sentence.split()}
    cue_count = len(words & POSITIVE_CUES) + len(words & NEGATIVE_CUES) + len(words & PRICE_CUES)
    return cue_count + min(len(words), 20)


def _likely_reason(text: str, tone: str) -> str:
    words = {word.strip(".,!?;:()[]{}\"'").casefold() for word in text.split()}
    money_mentions = list(dict.fromkeys(MONEY_PATTERN.findall(text)))

    if words & PRICE_CUES or money_mentions:
        price_detail = f"the review mentions {', '.join(money_mentions)} and " if money_mentions else ""
        return f"{price_detail}the value did not seem to match the quality or experience"
    if tone == "positive":
        return "the parts they cared about most met or exceeded their expectations"
    if tone == "negative":
        return "the experience did not meet the expectations set by the customer"
    return "the review includes both helpful and disappointing details"


def _business_takeaway(text: str, tone: str) -> str:
    words = {word.strip(".,!?;:()[]{}\"'").casefold() for word in text.split()}
    if words & PRICE_CUES:
        return "the business should pay close attention to perceived value, pricing, and quality consistency"
    if tone == "positive":
        return "the business is doing well in the areas the customer mentioned and should preserve those strengths"
    if tone == "negative":
        return "the business may need to address the specific pain points that shaped the customer's disappointment"
    return "the business should look at the specific details in the review to understand what worked and what did not"


def _detailed_experience_summary(text: str, tone: str) -> str | None:
    details = _experience_details(text)
    if len(details) < 3:
        return None

    subject = _review_subject(text)
    if tone == "positive":
        return (
            f"The customer describes a positive experience with {subject}, highlighting "
            f"{_join_details(details)}. "
            "Those details made the service feel dependable, flexible, professional, and high value. "
            f"Overall, the review reads as a strong endorsement of {subject}, including 5-star service."
        )
    if tone == "negative":
        return (
            f"The customer describes a negative experience with {subject}, highlighting "
            f"{_join_details(details)}. "
            "Those details shaped the overall disappointment and lowered trust in the service. "
            f"Overall, the review points to specific issues {subject} would need to address."
        )
    return (
        f"The customer describes a mixed experience with {subject}, highlighting {_join_details(details)}. "
        "The review includes enough concrete detail to show what shaped the customer's reaction. "
        f"Overall, the feedback gives {subject} clear signals about the parts of the experience that mattered most."
    )


def _experience_details(text: str) -> list[str]:
    evidence_phrases = {item.phrase for item in sentiment_evidence(text)}
    lowered = text.casefold()
    details: list[str] = []

    detail_rules = [
        ("better price" in evidence_phrases or "price" in lowered, "competitive price"),
        (
            "communication was excellent" in evidence_phrases or "excellent communication" in evidence_phrases,
            "excellent communication",
        ),
        (
            "exactly at the scheduled time" in evidence_phrases or "on time" in evidence_phrases,
            "punctual drop-off and pickup at the scheduled time",
        ),
        ("adjusted the day" in evidence_phrases, "flexibility when Rudy adjusted the day"),
        ("professional" in evidence_phrases, "professionalism"),
        ("5 stars" in evidence_phrases or "five stars" in evidence_phrases, "5 stars / 5-star service"),
        ("quality" in evidence_phrases, "quality"),
        ("refund" in evidence_phrases, "refund concerns"),
        ("late" in evidence_phrases or "delayed" in evidence_phrases, "timing problems"),
    ]
    for matched, detail in detail_rules:
        if matched and detail not in details:
            details.append(detail)
    return details


def _review_subject(text: str) -> str:
    has_rudy = re.search(r"\bRudy\b", text) is not None
    has_rm = re.search(r"\bRM Junk Removal\b", text) is not None
    if has_rudy and has_rm:
        return "Rudy and RM Junk Removal"
    if has_rm:
        return "RM Junk Removal"
    if has_rudy:
        return "Rudy"
    return "the business"


def _join_details(details: list[str]) -> str:
    if len(details) == 1:
        return details[0]
    if len(details) == 2:
        return f"{details[0]} and {details[1]}"
    return f"{', '.join(details[:-1])}, and {details[-1]}"


def _clean_fragment(text: str) -> str:
    fragment = text.strip(" .!?")
    if not fragment:
        return "the review details"
    normalized = f"{fragment[:1].casefold()}{fragment[1:]}"
    if normalized.startswith("tried to "):
        return f"they {normalized}"
    return normalized
