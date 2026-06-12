import pandas as pd
import plotly.express as px
import streamlit as st

from api_client import ApiClientError, fetch_keywords
from ui import (
    DEFAULT_SAMPLE_REVIEWS,
    backend_url_input,
    configure_page,
    render_error,
    render_placeholder_panel,
    split_review_lines,
)


configure_page("Keyword Themes")

st.title("Keyword / Theme Extraction")
st.write("Find recurring keywords and simple business themes across multiple reviews.")

api_base_url = backend_url_input()

raw_reviews = st.text_area(
    "Customer reviews",
    value=DEFAULT_SAMPLE_REVIEWS,
    help="Enter one review per line.",
    height=240,
)

if st.button("Extract Keywords and Themes", type="primary"):
    try:
        result = fetch_keywords(split_review_lines(raw_reviews), api_base_url=api_base_url)
    except ApiClientError as exc:
        render_error(exc)
    else:
        keyword_col, theme_col = st.columns(2)

        with keyword_col:
            st.subheader("Keywords")
            st.dataframe(pd.DataFrame(result["keywords"]), use_container_width=True)

        with theme_col:
            st.subheader("Themes")
            theme_data = pd.DataFrame(result["themes"])
            st.dataframe(theme_data, use_container_width=True)
            if not theme_data.empty:
                fig = px.bar(theme_data, x="keyword", y="count", title="Theme Counts")
                st.plotly_chart(fig, use_container_width=True)

        render_placeholder_panel(
            "Future topic modeling",
            "This section can later compare rule-based themes with clustering or transformer-based topic labels.",
        )
