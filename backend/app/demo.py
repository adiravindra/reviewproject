"""Load the deterministic, explicitly labeled review collection bundled with the app."""

import json
from pathlib import Path

from backend.app.models import CollectionResult, Review, SourceInfo

DEMO_PATH = Path(__file__).resolve().parents[2] / "demo_data" / "product_reviews.json"


def load_demo_collection(path: Path | None = None) -> CollectionResult:
    """Read the bundled local JSON data without making any network request."""

    payload = json.loads((path or DEMO_PATH).read_text(encoding="utf-8"))
    reviews = [Review.model_validate(item) for item in payload["reviews"]]
    return CollectionResult(
        source=SourceInfo(
            url=None,
            title=payload["title"],
            extractor="demo",
            is_demo=True,
        ),
        reviews=reviews,
    )
