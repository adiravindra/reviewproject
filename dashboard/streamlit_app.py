import json

import streamlit as st

from api_client import (
    ApiClientError,
    analyze_reviews_csv,
    analyze_reviews_from_api_payload,
    analyze_single_review,
    fetch_dashboard_metrics,
    fetch_health,
)
from ui import (
    backend_url_input,
    configure_page,
    parse_api_review_payload,
    render_analysis_result,
    render_error,
    render_hero,
    render_panel,
    render_status_chips,
)


configure_page("Home")

api_base_url = backend_url_input()

render_hero(
    "ReviewInsight",
    "A customer review intelligence workspace for sentiment, topics, urgency, summaries, and action-ready insights.",
)

status_col, metric_col1, metric_col2, metric_col3 = st.columns([1.2, 1, 1, 1])
with status_col:
    try:
        health = fetch_health(api_base_url=api_base_url)
    except ApiClientError:
        st.metric("Backend", "Offline")
    else:
        st.metric("Backend", str(health["status"]).upper())

try:
    metrics = fetch_dashboard_metrics(api_base_url=api_base_url)
except ApiClientError:
    metrics = {
        "total_reviews": 0,
        "total_runs": 0,
        "urgency_breakdown": {"high": 0},
    }

metric_col1.metric("Reviews Analyzed", metrics.get("total_reviews", 0))
metric_col2.metric("Analysis Runs", metrics.get("total_runs", 0))
metric_col3.metric("High Priority", metrics.get("urgency_breakdown", {}).get("high", 0))

render_status_chips(
    [
        "FastAPI-backed analysis",
        "Local JSON history",
        "CSV-ready workflow",
        "Rule-based MVP services",
    ]
)

st.subheader("Start A Review Analysis")
st.caption("Choose how review data enters the workflow. Results are saved to history by the backend.")

single_tab, csv_tab, api_tab, future_tab = st.tabs(
    ["Type or Paste", "Upload CSV", "API Payload", "More Sources"]
)

with single_tab:
    review_text = st.text_area(
        "Enter one customer review",
        value="The product quality is great, but shipping was late and support was slow.",
        height=170,
    )
    if st.button("Analyze Review", type="primary", key="home_single"):
        try:
            st.session_state["latest_analysis"] = analyze_single_review(
                review_text,
                api_base_url=api_base_url,
            )
        except ApiClientError as exc:
            render_error(exc)

with csv_tab:
    uploaded_file = st.file_uploader(
        "Upload a CSV file with a review, text, comment, or feedback column",
        type=["csv"],
    )
    if st.button("Analyze CSV", type="primary", key="home_csv"):
        if uploaded_file is None:
            st.warning("Upload a CSV file before analyzing.")
        else:
            try:
                st.session_state["latest_analysis"] = analyze_reviews_csv(
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    api_base_url=api_base_url,
                )
            except ApiClientError as exc:
                render_error(exc)

with api_tab:
    default_payload = json.dumps(
        {
            "reviews": [
                {"text": "Support was helpful and fast."},
                {"text": "Setup was confusing and shipping was slow."},
            ]
        },
        indent=2,
    )
    raw_payload = st.text_area(
        "Paste an API-style JSON payload",
        value=default_payload,
        height=220,
    )
    if st.button("Analyze API Payload", type="primary", key="home_api"):
        try:
            review_texts = parse_api_review_payload(raw_payload)
            st.session_state["latest_analysis"] = analyze_reviews_from_api_payload(
                review_texts,
                api_base_url=api_base_url,
            )
        except (ApiClientError, ValueError) as exc:
            render_error(exc)

with future_tab:
    render_panel(
        "Future input methods",
        "Connectors for app stores, support tickets, CRM exports, sample datasets, and scheduled API pulls can plug into the same backend analysis route later.",
    )

latest_analysis = st.session_state.get("latest_analysis")
if latest_analysis:
    st.divider()
    st.subheader("Latest Analysis")
    render_analysis_result(latest_analysis)
else:
    st.divider()
    render_panel(
        "No analysis selected yet",
        "Run one of the input flows above to populate this workspace with charts, metrics, and analyzed review records.",
    )
