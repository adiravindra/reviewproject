import json
from html import escape
from typing import Any

import streamlit as st

try:
    from api_client import DEFAULT_API_BASE_URL, ApiClientError, fetch_latest_analysis
except ModuleNotFoundError:
    from dashboard.api_client import DEFAULT_API_BASE_URL, ApiClientError, fetch_latest_analysis


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
        initial_sidebar_state="collapsed",
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

            section[data-testid="stSidebar"] {
                display: none;
            }

            div[data-testid="collapsedControl"] {
                display: none;
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

            .ri-top-nav {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 16px;
                background: #ffffff;
                border: 1px solid var(--ri-border);
                border-radius: 8px;
                padding: 10px 12px;
                margin: 4px 0 20px;
                box-shadow: 0 1px 2px rgba(23, 32, 51, 0.04);
            }

            .ri-brand {
                font-weight: 800;
                color: var(--ri-ink);
                white-space: nowrap;
            }

            .ri-nav-links {
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
            }

            .ri-top-nav a,
            div[data-testid="stPageLink"] a {
                color: var(--ri-muted);
                text-decoration: none;
                font-size: 0.9rem;
                font-weight: 650;
                padding: 7px 9px;
                border-radius: 6px;
            }

            .ri-top-nav a:hover,
            div[data-testid="stPageLink"] a:hover {
                background: #eef4ff;
                color: var(--ri-blue);
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
    return st.text_input(
        "FastAPI backend URL",
        value="http://127.0.0.1:8000",
        label_visibility="collapsed",
    )


def render_top_nav() -> None:
    st.markdown(
        """
        <nav class="ri-top-nav">
            <div class="ri-brand">ReviewInsight</div>
        </nav>
        """,
        unsafe_allow_html=True,
    )
    nav_items = [
        ("streamlit_app.py", "Home/Add Reviews"),
        ("pages/1_Overview.py", "Overview"),
        ("pages/2_Review_Details.py", "Review Details"),
        ("pages/3_Sentiment.py", "Sentiment"),
        ("pages/4_Topics.py", "Topics"),
        ("pages/5_Urgency.py", "Urgency"),
        ("pages/6_Summaries.py", "Summaries"),
        ("pages/7_History.py", "History"),
    ]
    nav_columns = st.columns([1.25, 0.9, 1.25, 0.9, 0.8, 0.85, 1.0, 0.85])
    for column, (page, label) in zip(nav_columns, nav_items):
        with column:
            st.page_link(page, label=label)


def render_backend_control() -> str:
    with st.expander("Backend connection", expanded=False):
        return backend_url_input()


def latest_analysis() -> dict[str, Any] | None:
    value = st.session_state.get("latest_analysis")
    return value if isinstance(value, dict) else None


def workspace_analysis() -> dict[str, Any] | None:
    analysis = latest_analysis()
    if analysis:
        return analysis

    api_base_url = str(st.session_state.get("api_base_url", DEFAULT_API_BASE_URL))
    try:
        analysis = fetch_latest_analysis(api_base_url=api_base_url)
    except ApiClientError:
        return None

    store_latest_analysis(analysis)
    return analysis


def store_latest_analysis(result: dict[str, Any]) -> None:
    st.session_state["latest_analysis"] = result
    st.session_state["selected_review_index"] = 0


def loaded_analysis_reviews(result: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not result:
        return []
    reviews = result.get("reviews", [])
    return [review for review in reviews if isinstance(review, dict)]


def render_empty_state() -> None:
    render_panel(
        "No reviews loaded",
        "Go to Home/Add Reviews to paste a review, upload a CSV, or try the API payload placeholder.",
    )


def average_urgency_label(score: float | int | None) -> str:
    if score is None:
        return "N/A"
    if float(score) >= 2.5:
        return "High"
    if float(score) >= 1.5:
        return "Medium"
    return "Low"


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


def single_analysis_card_fields(result: dict[str, Any]) -> dict[str, str]:
    topics = result.get("topics", [])
    topic_labels = [
        _format_topic_label(str(topic))
        for topic in topics
        if str(topic).strip()
    ]

    return {
        "text": str(result.get("text", "")),
        "sentiment": str(result.get("sentiment", "n/a")).title(),
        "topics": ", ".join(topic_labels) if topic_labels else "No specific topic detected",
        "urgency_score": f"{float(result.get('urgency_score', 0.0)):.2f}",
        "urgency_label": str(result.get("urgency_label", "n/a")).title(),
        "summary": str(result.get("summary", "No summary returned.")),
    }


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
    return loaded_analysis_reviews(result)


def render_analysis_result(result: dict[str, Any]) -> None:
    import pandas as pd
    import plotly.express as px

    metrics = dict(result.get("metrics", {}))
    reviews = result_reviews(result)
    is_single_review = len(reviews) == 1

    if is_single_review:
        review = reviews[0]
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        metric_col1.metric("Sentiment", str(review.get("sentiment", "n/a")).title())
        metric_col2.metric("Topic", str(review.get("topic", "general feedback")).title())
        metric_col3.metric("Urgency", str(review.get("urgency", "n/a")).title())
        metric_col4.metric("Source", str(result.get("source", "manual")).title())
        st.subheader("Short Summary")
        st.info(str(review.get("summary", result.get("summary", "No summary returned."))))
        return

    sentiment_breakdown = dict(metrics.get("sentiment_breakdown", {}))
    urgency_breakdown = dict(metrics.get("urgency_breakdown", {}))

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Total Reviews", result.get("review_count", 0))
    metric_col2.metric("Positive", sentiment_breakdown.get("positive", 0))
    metric_col3.metric("Neutral", sentiment_breakdown.get("neutral", 0))
    metric_col4.metric("Negative", sentiment_breakdown.get("negative", 0))

    metric_col5, metric_col6, metric_col7, metric_col8 = st.columns(4)
    metric_col5.metric("Overall Sentiment", str(metrics.get("overall_sentiment", "n/a")).title())
    metric_col6.metric("Average Urgency", average_urgency_label(metrics.get("average_urgency")))
    metric_col7.metric("High Priority", metrics.get("high_priority_reviews", 0))
    metric_col8.metric("Source", str(result.get("source", "manual")).title())

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        sentiment_data = pd.DataFrame(
            sentiment_breakdown_rows(sentiment_breakdown)
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
            urgency_breakdown_rows(urgency_breakdown)
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

    topic_data = pd.DataFrame(topic_rows(list(metrics.get("top_topics", []))))
    if not topic_data.empty:
        st.subheader("Top Topics")
        st.dataframe(topic_data, use_container_width=True, hide_index=True)

    urgent_reviews = loaded_analysis_reviews({"reviews": result.get("most_urgent_reviews", [])})
    if urgent_reviews:
        st.subheader("Most Urgent Reviews")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Urgency": str(review.get("urgency", "")).title(),
                        "Sentiment": str(review.get("sentiment", "")).title(),
                        "Topic": str(review.get("topic", "")).title(),
                        "Review": review.get("text", ""),
                    }
                    for review in urgent_reviews
                ]
            ),
            use_container_width=True,
            hide_index=True,
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


def render_single_analysis_card(result: dict[str, Any]) -> None:
    fields = single_analysis_card_fields(result)
    st.markdown(
        """
        <div class="ri-panel">
            <h3>Single Review Result</h3>
            <p>Immediate structured analysis from the backend.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Sentiment", fields["sentiment"])
    metric_col2.metric("Urgency", fields["urgency_label"])
    metric_col3.metric("Urgency Score", fields["urgency_score"])
    metric_col4.metric("Topics", fields["topics"])

    st.markdown(
        f"""
        <div class="ri-panel">
            <h3>Summary</h3>
            <p>{escape(fields["summary"])}</p>
        </div>
        <div class="ri-panel">
            <h3>Original Review</h3>
            <p>{escape(fields["text"])}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


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


def _format_topic_label(topic: str) -> str:
    return "/".join(
        part.upper() if part.lower() in {"ui", "ux"} else part.title()
        for part in topic.split("/")
    )
