import streamlit as st

from api_client import ApiClientError, fetch_history
from ui import backend_url_input, configure_page, history_rows, render_error, render_nav


configure_page("History")
render_nav()

st.title("History")
st.write("Previously analyzed reviews saved in SQLite.")

api_base_url = backend_url_input()
st.session_state["api_base_url"] = api_base_url

try:
    history = fetch_history(api_base_url=api_base_url)
except ApiClientError as exc:
    render_error(exc)
else:
    items = history.get("items", [])
    rows = history_rows(items if isinstance(items, list) else [])
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No review history yet. Analyze a review on the Analysis page first.")
