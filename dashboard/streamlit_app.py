import streamlit as st

from api_client import ApiClientError, analyze_website
from ui import backend_url_input, configure_page, render_error, render_nav, render_page_intro, render_website_report


configure_page("Analysis")
render_nav("Analysis")
render_page_intro(
    "Website Review Intelligence",
    "Analyze reviews available in the static HTML of a public product, business, restaurant, hotel, or place page.",
)

api_base_url = backend_url_input()
st.session_state["api_base_url"] = api_base_url

with st.container(border=True):
    website_url = st.text_input("Public review page URL", placeholder="https://example.com/product")
    if st.button("Analyze Reviews", type="primary", use_container_width=True):
        try:
            with st.spinner("Accessing the page, collecting reviews, and generating intelligence..."):
                st.session_state["latest_website_result"] = analyze_website(website_url, api_base_url)
        except ApiClientError as exc:
            render_error(exc)

result = st.session_state.get("latest_website_result")
if isinstance(result, dict):
    render_website_report(result)
