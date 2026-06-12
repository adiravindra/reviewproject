from typing import Any

import streamlit as st


DEFAULT_SAMPLE_REVIEWS = "\n".join(
    [
        "I love the product quality and fast delivery.",
        "Shipping was slow and support did not respond.",
        "The price is fair and setup is easy.",
    ]
)


def configure_page(title: str) -> None:
    st.set_page_config(page_title=f"ReviewInsight | {title}", layout="wide")


def backend_url_input() -> str:
    return st.sidebar.text_input(
        "FastAPI backend URL",
        value="http://127.0.0.1:8000",
    )


def split_review_lines(raw_reviews: str) -> list[str]:
    return [line.strip() for line in raw_reviews.splitlines() if line.strip()]


def sentiment_breakdown_rows(breakdown: dict[str, int]) -> list[dict[str, Any]]:
    return [
        {"Sentiment": sentiment.title(), "Reviews": count}
        for sentiment, count in breakdown.items()
    ]


def render_placeholder_panel(title: str, body: str) -> None:
    st.info(f"{title}: {body}")


def render_error(message: Exception) -> None:
    st.error(str(message))
