import re
from collections import Counter


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "but",
    "did",
    "for",
    "i",
    "in",
    "is",
    "it",
    "not",
    "of",
    "on",
    "or",
    "our",
    "the",
    "this",
    "to",
    "was",
    "we",
    "with",
}

THEME_TERMS = {
    "shipping": {"arrival", "delivery", "late", "package", "shipping"},
    "support": {"answered", "help", "helpful", "respond", "support"},
    "quality": {"broken", "durable", "quality", "reliable"},
    "price": {"affordable", "cost", "expensive", "fair", "price"},
    "usability": {"confusing", "easy", "setup", "simple", "use"},
}

COMPLAINT_TERMS = {
    "delayed shipping": {"delayed", "late", "shipping", "slow"},
    "support response time": {"answered", "respond", "slow", "support"},
    "product quality issues": {"bad", "broken", "poor", "quality"},
    "pricing concerns": {"cost", "expensive", "price"},
    "usability friction": {"confusing", "difficult", "setup", "use"},
}


def _tokens(review_texts: list[str]) -> list[str]:
    joined_text = " ".join(review_texts).casefold()
    return [
        token
        for token in re.findall(r"[a-z][a-z']+", joined_text)
        if token not in STOP_WORDS and len(token) > 2
    ]


def extract_keywords(review_texts: list[str], limit: int = 8) -> list[tuple[str, int]]:
    counts = Counter(_tokens(review_texts))
    return counts.most_common(limit)


def extract_themes(review_texts: list[str], limit: int = 5) -> list[tuple[str, int]]:
    tokens = set(_tokens(review_texts))
    theme_counts = {
        theme: len(tokens & terms)
        for theme, terms in THEME_TERMS.items()
        if tokens & terms
    }
    return Counter(theme_counts).most_common(limit)


def extract_common_complaints(review_texts: list[str], limit: int = 4) -> list[str]:
    tokens = set(_tokens(review_texts))
    complaints = [
        complaint
        for complaint, terms in COMPLAINT_TERMS.items()
        if tokens & terms
    ]
    return complaints[:limit]
