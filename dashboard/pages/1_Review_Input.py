import pandas as pd
import streamlit as st

from dashboard.api_client import ApiClientError, submit_review_batch, submit_single_review
from dashboard.ui import (
    DEFAULT_SAMPLE_REVIEWS,
    backend_url_input,
    configure_page,
    render_error,
    render_placeholder_panel,
    split_review_lines,
)


configure_page("Review Input")

st.title("Review Input")
st.write("Clean and validate review text before running analysis.")

api_base_url = backend_url_input()

single_tab, batch_tab, upload_tab = st.tabs(["Single Review", "Batch Reviews", "CSV Upload"])

with single_tab:
    single_review = st.text_area(
        "Single customer review",
        placeholder="Paste one review here...",
        height=160,
    )

    if st.button("Validate Single Review", type="primary"):
        try:
            result = submit_single_review(single_review, api_base_url=api_base_url)
        except ApiClientError as exc:
            render_error(exc)
        else:
            st.metric("Cleaned Reviews", result["count"])
            st.dataframe(pd.DataFrame(result["reviews"]), use_container_width=True)

with batch_tab:
    batch_reviews = st.text_area(
        "Batch customer reviews",
        value=DEFAULT_SAMPLE_REVIEWS,
        help="Enter one review per line.",
        height=220,
    )

    if st.button("Validate Batch Reviews", type="primary"):
        try:
            result = submit_review_batch(split_review_lines(batch_reviews), api_base_url=api_base_url)
        except ApiClientError as exc:
            render_error(exc)
        else:
            st.metric("Cleaned Reviews", result["count"])
            st.dataframe(pd.DataFrame(result["reviews"]), use_container_width=True)

with upload_tab:
    render_placeholder_panel(
        "Future CSV upload",
        "This area will accept CSV files once file ingestion is added to the backend architecture.",
    )
    st.file_uploader("CSV file", type=["csv"], disabled=True)
