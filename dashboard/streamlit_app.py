import streamlit as st

from dashboard.api_client import ApiClientError, analyze_website
from dashboard.ui import (
    backend_url_input,
    configure_page,
    render_error,
    render_nav,
    render_page_intro,
    render_website_report,
)


configure_page("Analysis")
render_nav("Analysis")
render_page_intro(
    "Website Review Intelligence",
    "Analyze reviews available in the static HTML of a public product, business, restaurant, hotel, or place page.",
)

api_base_url = backend_url_input()
st.session_state["api_base_url"] = api_base_url

with st.form("website-analysis-form"):
    website_url = st.text_input(
        "Public review page URL",
        placeholder="https://example.com/product/reviews",
        help="The address must resolve publicly and return static HTML review data.",
    )
    st.caption("Pages must be public and expose reviews in static HTML. Analysis covers up to 60 unique reviews across 3 pages.")
    submitted = st.form_submit_button("Analyze Reviews", type="primary", width="stretch")

if submitted:
    st.session_state.pop("latest_website_result", None)
    try:
        with st.spinner(
            "Accessing the page, collecting available reviews, and generating intelligence. This can take up to two minutes..."
        ):
            st.session_state["latest_website_result"] = analyze_website(
                website_url,
                api_base_url,
            )
    except ApiClientError as exc:
        render_error(exc)
    else:
        st.success("Website analysis completed, validated, and saved to history.")

result = st.session_state.get("latest_website_result")
if isinstance(result, dict):
    render_website_report(result)
