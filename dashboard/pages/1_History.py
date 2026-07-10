import streamlit as st

from api_client import ApiClientError, fetch_history
from ui import backend_url_input, configure_page, history_rows, render_error, render_nav, render_page_intro


configure_page("History")
render_nav("History")
render_page_intro("Website History", "Review completed website-level analyses stored by the backend.")

api_base_url = backend_url_input()
st.session_state["api_base_url"] = api_base_url

try:
    history = fetch_history(api_base_url)
except ApiClientError as exc:
    render_error(exc)
else:
    items = history.get("items", [])
    rows = history_rows(items if isinstance(items, list) else [])
    if not rows:
        st.info("No website analyses have been saved yet.")
    for row in rows:
        with st.container(border=True):
            st.caption(row["Timestamp"])
            st.subheader(row["Source"])
            st.write(row["Summary"])
            reviews, sentiment = st.columns(2)
            reviews.metric("Reviews", row["Reviews"])
            sentiment.metric("Sentiment", row["Sentiment"])
