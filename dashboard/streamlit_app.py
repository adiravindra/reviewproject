import streamlit as st

from api_client import ApiClientError, analyze_review, fetch_health
from ui import (
    backend_url_input,
    configure_page,
    render_error,
    render_nav,
    render_original_review,
    render_result_tabs,
)


configure_page("Analysis")
render_nav()

st.title("Analysis")
st.write("Paste one customer review, analyze it, and save it to SQLite history.")

api_base_url = backend_url_input()
st.session_state["api_base_url"] = api_base_url

try:
    health = fetch_health(api_base_url=api_base_url)
except ApiClientError:
    st.warning("Backend is offline. Start FastAPI before analyzing a review.")
else:
    st.caption(f"Backend status: {str(health.get('status', 'unknown')).upper()}")

review_text = st.text_area(
    "Customer review",
    value="The product quality is great, but shipping was late and support was slow.",
    height=180,
)

if st.button("Analyze Review", type="primary"):
    try:
        st.session_state["latest_review_result"] = analyze_review(
            review_text,
            api_base_url=api_base_url,
        )
    except ApiClientError as exc:
        render_error(exc)
    else:
        st.success("Review analyzed and saved to history.")

result = st.session_state.get("latest_review_result")
if isinstance(result, dict):
    st.divider()
    render_original_review(str(result.get("text", "")))
    render_result_tabs(result)
