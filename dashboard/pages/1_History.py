import streamlit as st

from api_client import ApiClientError, fetch_history
from ui import backend_url_input, configure_page, history_rows, render_error, render_nav, render_page_intro


configure_page("History")
render_nav("History")

# This page reads saved results from SQLite through the backend.
render_page_intro("History", "Review previous analyses saved by the backend in local SQLite history.")

api_base_url = backend_url_input()
st.session_state["api_base_url"] = api_base_url

try:
    # History is fetched once per page render and displayed as simple cards.
    history = fetch_history(api_base_url=api_base_url)
except ApiClientError as exc:
    render_error(exc)
else:
    items = history.get("items", [])
    rows = history_rows(items if isinstance(items, list) else [])
    if rows:
        # Plain cards are easier for beginners to understand than a data grid.
        for row in rows:
            with st.container(border=True):
                st.caption(row["Timestamp"])
                st.write(row["Review"])
                col1, col2 = st.columns([0.28, 0.72])
                col1.metric("Sentiment", row["Sentiment"])
                with col2:
                    st.markdown("**Summary**")
                    st.write(row["Summary"])
    else:
        st.info("No review history yet. Analyze a review on the Analysis page first.")
