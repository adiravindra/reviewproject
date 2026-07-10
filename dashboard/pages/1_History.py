import streamlit as st

from dashboard.api_client import ApiClientError, fetch_history, fetch_history_item
from dashboard.ui import (
    backend_url_input,
    configure_page,
    history_rows,
    render_error,
    render_nav,
    render_page_intro,
    render_website_report,
)


configure_page("History")
render_nav("History")
render_page_intro(
    "Website Analysis History",
    "Open a completed report without collecting reviews or calling the language model again.",
)

api_base_url = backend_url_input()
st.session_state["api_base_url"] = api_base_url

try:
    history = fetch_history(api_base_url)
except ApiClientError as exc:
    render_error(exc)
else:
    rows = history_rows(history)
    if not rows:
        st.info("No website analyses have been saved yet. Completed analyses will appear here.")
    for row in rows:
        label = (
            f"{row['Source']}  ·  {row['Completed']}  ·  {row['Reviews']} reviews  ·  "
            f"{row['Average rating']} / 5  ·  {row['Sentiment']}"
        )
        with st.expander(label, expanded=False):
            st.markdown(f"**Source:** [{row['URL']}]({row['URL']})")
            st.write(row["Summary"])
            st.caption(f"Provider: {row['Provider']} · Model: {row['Model']}")
            if st.button("Open stored report", key=f"open-history-{row['ID']}"):
                try:
                    with st.spinner("Loading the completed report from history..."):
                        st.session_state["history_report"] = fetch_history_item(
                            row["ID"],
                            api_base_url,
                        )
                except ApiClientError as exc:
                    render_error(exc)

            report = st.session_state.get("history_report")
            if isinstance(report, dict) and report.get("id") == row["ID"]:
                render_website_report(report, show_heading=False)
