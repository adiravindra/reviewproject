import json
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
    st.set_page_config(
        page_title=f"ReviewInsight | {title}",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_app_style()


def apply_app_style() -> None:
    st.markdown(
        """
        <style>
            :root {
                --ri-bg: #f7f8fb;
                --ri-surface: #ffffff;
                --ri-ink: #172033;
                --ri-muted: #687385;
                --ri-border: #dfe4ec;
                --ri-blue: #2563eb;
                --ri-green: #047857;
                --ri-red: #b42318;
                --ri-amber: #b45309;
            }

            .stApp {
                background: var(--ri-bg);
                color: var(--ri-ink);
            }

            h1, h2, h3 {
                color: var(--ri-ink);
                letter-spacing: 0;
            }

            div[data-testid="stMetric"] {
                background: var(--ri-surface);
                border: 1px solid var(--ri-border);
                border-radius: 8px;
                padding: 14px 16px;
                box-shadow: 0 1px 2px rgba(23, 32, 51, 0.04);
            }

            .ri-panel {
                background: var(--ri-surface);
                border: 1px solid var(--ri-border);
                border-radius: 8px;
                padding: 18px 20px;
                margin: 8px 0 18px;
                box-shadow: 0 1px 2px rgba(23, 32, 51, 0.04);
            }

            .ri-panel h3 {
                font-size: 1.05rem;
                margin: 0 0 8px;
            }

            .ri-panel p {
                color: var(--ri-muted);
                margin: 0;
            }

            .ri-hero {
                background: linear-gradient(135deg, #ffffff 0%, #eef4ff 100%);
                border: 1px solid var(--ri-border);
                border-radius: 8px;
                padding: 26px 28px;
                margin-bottom: 22px;
            }

            .ri-hero h1 {
                font-size: 2.2rem;
                line-height: 1.1;
                margin: 0 0 12px;
            }

            .ri-hero p {
                color: var(--ri-muted);
                font-size: 1.02rem;
                max-width: 760px;
                margin: 0;
            }

            .ri-chip {
                display: inline-block;
                border: 1px solid var(--ri-border);
                border-radius: 999px;
                color: var(--ri-muted);
                background: #ffffff;
                padding: 4px 10px;
                font-size: 0.78rem;
                margin: 0 6px 6px 0;
            }

            .ri-success {
                color: var(--ri-green);
                font-weight: 700;
            }

            .ri-warning {
                color: var(--ri-amber);
                font-weight: 700;
            }

            .ri-danger {
                color: var(--ri-red);
                font-weight: 700;
            }

            div[data-testid="stButton"] > button {
                border-radius: 8px;
                font-weight: 650;
            }

            div[data-testid="stButton"] > button[kind="primary"] {
                background: var(--ri-blue);
                border-color: var(--ri-blue);
                color: #ffffff;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def backend_url_input() -> str:
    return st.sidebar.text_input(
        "FastAPI backend URL",
        value="http://127.0.0.1:8000",
    )


def split_review_lines(raw_reviews: str) -> list[str]:
    return [line.strip() for line in raw_reviews.splitlines() if line.strip()]


def parse_api_review_payload(raw_payload: str) -> list[str]:
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise ValueError("Enter valid JSON for the API payload.") from exc

    if isinstance(payload, str):
        return split_review_lines(payload)

    if isinstance(payload, list):
        return _review_texts_from_list(payload)

    if isinstance(payload, dict):
        if "reviews" in payload and isinstance(payload["reviews"], list):
            return _review_texts_from_list(payload["reviews"])
        if isinstance(payload.get("text"), str):
            return split_review_lines(str(payload["text"]))

    raise ValueError('Use JSON like {"text": "..."} or {"reviews": [{"text": "..."}]}.')


def sentiment_breakdown_rows(breakdown: dict[str, int]) -> list[dict[str, Any]]:
    return [
        {"Sentiment": sentiment.title(), "Reviews": count}
        for sentiment, count in breakdown.items()
    ]


def urgency_breakdown_rows(breakdown: dict[str, int]) -> list[dict[str, Any]]:
    return [
        {"Urgency": urgency.title(), "Reviews": count}
        for urgency, count in breakdown.items()
    ]


def topic_rows(top_topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"Topic": str(item["keyword"]).title(), "Reviews": int(item["count"])}
        for item in top_topics
    ]


def render_hero(title: str, body: str) -> None:
    st.markdown(
        f"""
        <section class="ri-hero">
            <h1>{title}</h1>
            <p>{body}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_panel(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="ri-panel">
            <h3>{title}</h3>
            <p>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_chips(labels: list[str]) -> None:
    chips = "".join(f'<span class="ri-chip">{label}</span>' for label in labels)
    st.markdown(chips, unsafe_allow_html=True)


def result_reviews(result: dict[str, Any]) -> list[dict[str, Any]]:
    return list(result.get("reviews", []))


def render_analysis_result(result: dict[str, Any]) -> None:
    import pandas as pd
    import plotly.express as px

    metrics = dict(result.get("metrics", {}))
    reviews = result_reviews(result)

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Reviews", result.get("review_count", 0))
    metric_col2.metric("Overall Sentiment", str(metrics.get("overall_sentiment", "n/a")).title())
    metric_col3.metric("High Priority", metrics.get("high_priority_reviews", 0))
    metric_col4.metric("Source", str(result.get("source", "manual")).title())

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        sentiment_data = pd.DataFrame(
            sentiment_breakdown_rows(dict(metrics.get("sentiment_breakdown", {})))
        )
        if not sentiment_data.empty:
            st.plotly_chart(
                px.bar(
                    sentiment_data,
                    x="Sentiment",
                    y="Reviews",
                    color="Sentiment",
                    title="Sentiment Distribution",
                ),
                use_container_width=True,
            )

    with chart_col2:
        urgency_data = pd.DataFrame(
            urgency_breakdown_rows(dict(metrics.get("urgency_breakdown", {})))
        )
        if not urgency_data.empty:
            st.plotly_chart(
                px.bar(
                    urgency_data,
                    x="Urgency",
                    y="Reviews",
                    color="Urgency",
                    title="Urgency Breakdown",
                ),
                use_container_width=True,
            )

    st.subheader("Executive Summary")
    st.info(str(result.get("summary", "No summary returned.")))

    table_rows = [
        {
            "Review": review.get("text", ""),
            "Sentiment": str(review.get("sentiment", "")).title(),
            "Topic": str(review.get("topic", "")).title(),
            "Urgency": str(review.get("urgency", "")).title(),
            "Summary": review.get("summary", ""),
        }
        for review in reviews
    ]
    if table_rows:
        st.subheader("Analyzed Reviews")
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)


def render_placeholder_panel(title: str, body: str) -> None:
    render_panel(title, body)


def render_error(message: Exception) -> None:
    st.error(str(message))


def _review_texts_from_list(items: list[Any]) -> list[str]:
    review_texts: list[str] = []
    for item in items:
        if isinstance(item, str):
            review_texts.extend(split_review_lines(item))
        elif isinstance(item, dict) and isinstance(item.get("text"), str):
            review_texts.extend(split_review_lines(str(item["text"])))

    if not review_texts:
        raise ValueError("The API payload did not include any review text.")
    return review_texts
