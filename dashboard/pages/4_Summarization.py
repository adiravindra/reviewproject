import streamlit as st

from api_client import ApiClientError, fetch_summary
from ui import (
    DEFAULT_SAMPLE_REVIEWS,
    backend_url_input,
    configure_page,
    render_error,
    render_placeholder_panel,
    split_review_lines,
)


configure_page("Summarization")

st.title("Summarization")
st.write("Generate a short summary for one or more customer reviews.")

api_base_url = backend_url_input()

raw_reviews = st.text_area(
    "Customer reviews",
    value=DEFAULT_SAMPLE_REVIEWS,
    help="Enter one review per line.",
    height=240,
)

control_col1, control_col2 = st.columns(2)
control_col1.selectbox("Future summary length", ["Short", "Medium", "Detailed"], disabled=True)
control_col2.selectbox("Future summary tone", ["Business", "Support", "Executive"], disabled=True)

if st.button("Summarize Reviews", type="primary"):
    try:
        result = fetch_summary(split_review_lines(raw_reviews), api_base_url=api_base_url)
    except ApiClientError as exc:
        render_error(exc)
    else:
        st.metric("Reviews Summarized", result["review_count"])
        st.write("Summary")
        st.info(result["summary"])

        render_placeholder_panel(
            "Future GenAI controls",
            "Summary length, tone, and audience controls can be connected when a GenAI summarizer is added.",
        )
