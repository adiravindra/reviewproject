import pandas as pd
import streamlit as st

from api_client import ApiClientError, fetch_history
from ui import backend_url_input, configure_page, render_error, render_hero, render_panel


configure_page("History")

api_base_url = backend_url_input()

render_hero(
    "Analysis History",
    "Review previously saved analysis runs from manual input, CSV uploads, and API-style payloads.",
)

try:
    history = fetch_history(api_base_url=api_base_url)
except ApiClientError as exc:
    render_error(exc)
else:
    items = history.get("items", [])
    if not items:
        render_panel("No history yet", "Run an analysis from the homepage to create the first saved record.")
    else:
        st.metric("Saved Runs", len(items))
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Created": item["created_at"],
                        "Source": str(item["source"]).title(),
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
