import pandas as pd
import streamlit as st

from api_client import ApiClientError, fetch_analysis_run, fetch_analysis_runs
from ui import (
    configure_page,
    render_backend_control,
    render_error,
    render_hero,
    render_panel,
    render_top_nav,
    store_latest_analysis,
)


configure_page("History")
render_top_nav()
api_base_url = render_backend_control()
st.session_state["api_base_url"] = api_base_url

render_hero(
    "History",
    "Review previously saved analysis runs from manual input, CSV uploads, and API-style payloads.",
)

try:
    history = fetch_analysis_runs(api_base_url=api_base_url)
except ApiClientError as exc:
    render_error(exc)
else:
    items = history.get("items", [])
    if not items:
        render_panel("No history yet", "Run an analysis from Home/Add Reviews to create the first saved record.")
    else:
        st.metric("Saved Runs", len(items))

        labels = [
            f"{item['created_at']} | {str(item['input_type']).title()} | {item['review_count']} reviews"
            for item in items
        ]
        selected_index = st.selectbox(
            "Select a saved run",
            options=list(range(len(items))),
            format_func=lambda index: labels[index],
        )
        if st.button("Load Selected Run", type="primary"):
            try:
                selected_run = fetch_analysis_run(
                    str(items[int(selected_index)]["id"]),
                    api_base_url=api_base_url,
                )
            except ApiClientError as exc:
                render_error(exc)
            else:
                store_latest_analysis(selected_run)
                st.success("Saved run loaded. Use the top navigation to explore it.")

        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Created": item["created_at"],
                        "Input Type": str(item["input_type"]).title(),
                        "Reviews": item["review_count"],
                        "Overall Sentiment": str(item["overall_sentiment"]).title(),
                        "High Priority": item["high_priority_reviews"],
                        "Summary": item["summary"],
                    }
                    for item in items
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
