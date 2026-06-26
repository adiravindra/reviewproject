import re


POSITIVE_CUES = {"amazing", "easy", "excellent", "fast", "good", "great", "helpful", "love", "wonderful"}
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


# Simple fallback summary used when the model is disabled or unavailable.
def summarize_review(text: str, max_length: int = 260) -> str:
    cleaned = " ".join(text.split())

    # Keep fallback output as generated prose only; the UI displays the quoted
    # source review in the input area rather than repeating it in the summary.
    if not cleaned:
        return "No review text was available to summarize."

    sentences = _sentences(cleaned)
    tone = _tone(cleaned)
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


def _clean_fragment(text: str) -> str:
    fragment = text.strip(" .!?")
    if not fragment:
        return "the review details"
    normalized = f"{fragment[:1].casefold()}{fragment[1:]}"
    if normalized.startswith("tried to "):
        return f"they {normalized}"
    return normalized
