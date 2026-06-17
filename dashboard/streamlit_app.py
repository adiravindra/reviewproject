import json

import streamlit as st

from api_client import (
    ApiClientError,
    analyze_single_review,
    analyze_reviews_csv,
    analyze_reviews_from_api_payload,
    fetch_analysis_runs,
    fetch_health,
)
from ui import (
    configure_page,
    render_backend_control,
    parse_api_review_payload,
    render_analysis_result,
    render_error,
    render_hero,
    render_panel,
    render_single_analysis_card,
    render_status_chips,
    render_top_nav,
    store_latest_analysis,
)


configure_page("Home")
render_top_nav()

api_base_url = render_backend_control()
st.session_state["api_base_url"] = api_base_url

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
    runs = fetch_analysis_runs(api_base_url=api_base_url).get("items", [])
except ApiClientError:
    runs = []

metric_col1.metric("Reviews Analyzed", sum(int(run.get("review_count", 0)) for run in runs))
metric_col2.metric("Analysis Runs", len(runs))
metric_col3.metric("High Priority", sum(int(run.get("high_priority_reviews", 0)) for run in runs))

render_status_chips(
    [
        "FastAPI-backed analysis",
        "SQLite history",
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
    save_single = st.checkbox("Save this analysis to history", value=False)
    if st.button("Analyze Review", type="primary", key="home_single"):
        try:
            result = analyze_single_review(
                review_text,
                save_to_history=save_single,
                api_base_url=api_base_url,
            )
        except ApiClientError as exc:
            render_error(exc)
        else:
            st.session_state["single_review_analysis"] = result
            saved_run = result.get("run")
            if isinstance(saved_run, dict):
                store_latest_analysis(saved_run)
                st.success("Review saved to history. Explore it from the dashboard pages.")

    single_review_analysis = st.session_state.get("single_review_analysis")
    if isinstance(single_review_analysis, dict):
        render_single_analysis_card(single_review_analysis)

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
                result = analyze_reviews_csv(
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    api_base_url=api_base_url,
                )
            except ApiClientError as exc:
                render_error(exc)
            else:
                store_latest_analysis(result)
                st.success("CSV reviews loaded. Explore the analysis pages from the top navigation.")

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
            result = analyze_reviews_from_api_payload(
                review_texts,
                api_base_url=api_base_url,
            )
        except (ApiClientError, ValueError) as exc:
            render_error(exc)
        else:
            store_latest_analysis(result)
            st.success("API payload reviews loaded. Explore the analysis pages from the top navigation.")

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
