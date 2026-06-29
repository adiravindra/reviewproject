import streamlit as st

from api_client import ApiClientError, analyze_review
from ui import (
    backend_url_input,
    configure_page,
    render_page_intro,
    render_error,
    render_nav,
    render_result_tabs,
)


configure_page("Analysis")
render_nav("Analysis")

# This is the main Streamlit page for running a single review analysis.
render_page_intro(
    "Analysis",
    "Paste one customer review, then review a clear summary and sentiment insights in one focused workspace.",
)

api_base_url = backend_url_input()
st.session_state["api_base_url"] = api_base_url

# Streamlit reruns the script after each interaction, so session state keeps
# the latest result visible after the backend call finishes.
with st.container(border=True):
    st.subheader("Review input")
    review_text = st.text_area(
        "Customer review",
        value="The product quality is great, but shipping was late and support was slow.",
        height=180,
    )

    if st.button("Analyze Review", type="primary", use_container_width=True):
        try:
            # Give immediate feedback while the model/backend work is running.
            with st.spinner("Analyzing review and saving the result..."):
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
    # Show the result below the form after the user clicks Analyze.
    st.divider()
    render_result_tabs(result)
