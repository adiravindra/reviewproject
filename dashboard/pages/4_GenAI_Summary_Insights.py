import streamlit as st

from api_client import ApiClientError, analyze_reviews_from_api_payload
from ui import (
    DEFAULT_SAMPLE_REVIEWS,
    backend_url_input,
    configure_page,
    render_error,
    render_hero,
    render_panel,
    split_review_lines,
)


configure_page("GenAI Summary")

api_base_url = backend_url_input()

render_hero(
    "GenAI Summary / Insights",
    "Turn a batch of reviews into a concise customer narrative and reusable insight cards.",
)

raw_reviews = st.text_area(
    "Customer reviews",
    value=DEFAULT_SAMPLE_REVIEWS,
    help="Enter one review per line.",
    height=240,
)

control_col1, control_col2 = st.columns(2)
control_col1.selectbox("Summary length", ["Short", "Medium", "Detailed"], disabled=True)
control_col2.selectbox("Audience", ["Executive", "Support", "Product"], disabled=True)

if st.button("Generate Summary", type="primary"):
    try:
        result = analyze_reviews_from_api_payload(
            split_review_lines(raw_reviews),
            api_base_url=api_base_url,
        )
    except ApiClientError as exc:
        render_error(exc)
    else:
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("Reviews", result["review_count"])
        metric_col2.metric("Overall Sentiment", str(result["metrics"]["overall_sentiment"]).title())
        metric_col3.metric("High Priority", result["metrics"]["high_priority_reviews"])

        st.subheader("Generated Summary")
        st.info(result["summary"])

        insight_col1, insight_col2 = st.columns(2)
        with insight_col1:
            render_panel(
                "What customers are saying",
                "The current MVP summary is deterministic. A future GenAI service can add richer phrasing, citations, and model metadata.",
            )
        with insight_col2:
            render_panel(
                "Next best action",
                "Use the topic and urgency pages to decide which operational team should review the highest-impact feedback first.",
            )
