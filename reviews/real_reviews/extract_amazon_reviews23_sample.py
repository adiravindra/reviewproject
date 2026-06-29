"""Sample real reviews from the Amazon Reviews'23 public dataset.

This script is for manual evaluation data, not automated tests. It streams a
category file, selects balanced positive/negative/neutral examples, and writes a
local JSONL file under reviews/real_reviews/generated/.
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import sys
from typing import Any
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.sentiment import sentiment_evidence
from backend.app.services.summarization import summarize_review


DEFAULT_CATEGORY = "All_Beauty"
DEFAULT_PER_SENTIMENT = 10
BASE_URL = "https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/review_categories"
OUTPUT_PATH = Path(__file__).resolve().parent / "generated" / "real_review_samples.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract balanced real review samples for manual evaluation.")
    parser.add_argument("--category", default=DEFAULT_CATEGORY, help="Amazon Reviews'23 category name.")
    parser.add_argument("--per-sentiment", type=int, default=DEFAULT_PER_SENTIMENT)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    samples = sample_reviews(args.category, args.per_sentiment)
    write_jsonl(samples, args.output)
    print(f"Wrote {len(samples)} real review samples to {args.output}")


def sample_reviews(category: str, per_sentiment: int) -> list[dict[str, Any]]:
    wanted = {"positive": per_sentiment, "negative": per_sentiment, "neutral": per_sentiment}
    collected: dict[str, list[dict[str, Any]]] = {"positive": [], "negative": [], "neutral": []}
    url = f"{BASE_URL}/{category}.jsonl.gz"

    with urlopen(url) as response:
        with gzip.GzipFile(fileobj=response) as gzip_file:
            for raw_line in gzip_file:
                if all(len(items) >= wanted[sentiment] for sentiment, items in collected.items()):
                    break
                record = json.loads(raw_line.decode("utf-8"))
                sentiment = sentiment_from_rating(record.get("rating"))
                if sentiment is None or len(collected[sentiment]) >= wanted[sentiment]:
                    continue
                text = clean_review_text(str(record.get("text", "")))
                if not useful_for_evaluation(text):
                    continue
                collected[sentiment].append(build_sample(record, text, sentiment, category))

    missing = {sentiment: wanted[sentiment] - len(items) for sentiment, items in collected.items()}
    missing = {sentiment: count for sentiment, count in missing.items() if count > 0}
    if missing:
        raise RuntimeError(f"Could not collect enough samples from {category}: {missing}")

    samples: list[dict[str, Any]] = []
    for sentiment in ("positive", "negative", "neutral"):
        samples.extend(collected[sentiment])
    return samples


def build_sample(record: dict[str, Any], text: str, sentiment: str, category: str) -> dict[str, Any]:
    evidence = sentiment_evidence(text, sentiment)
    return {
        "review_text": text,
        "source_type": "Amazon Reviews'23 dataset",
        "source_dataset": "https://amazon-reviews-2023.github.io/",
        "source_category": category,
        "rating": record.get("rating"),
        "expected_sentiment": sentiment,
        "expected_sentiment_keywords_phrases": [item.phrase for item in evidence],
        "expected_summary_seed": summarize_review(text),
        "notes": "Real review sampled from an authorized dataset source; verify model output manually.",
    }


def sentiment_from_rating(rating: Any) -> str | None:
    try:
        numeric_rating = float(rating)
    except (TypeError, ValueError):
        return None
    if numeric_rating >= 4:
        return "positive"
    if numeric_rating <= 2:
        return "negative"
    if numeric_rating == 3:
        return "neutral"
    return None


def clean_review_text(text: str) -> str:
    return " ".join(text.split())


def useful_for_evaluation(text: str) -> bool:
    words = text.split()
    return 20 <= len(words) <= 140


def write_jsonl(samples: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output_file:
        for sample in samples:
            output_file.write(json.dumps(sample, ensure_ascii=True) + "\n")


if __name__ == "__main__":
    main()
