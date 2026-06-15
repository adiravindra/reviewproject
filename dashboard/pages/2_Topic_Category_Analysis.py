import pandas as pd
import plotly.express as px
import streamlit as st

from api_client import ApiClientError, analyze_reviews_from_api_payload
from ui import (
    DEFAULT_SAMPLE_REVIEWS,
    backend_url_input,
    configure_page,
    render_error,
    render_hero,
    render_panel,
    split_review_lines,
    topic_rows,
)


configure_page("Topic Analysis")

api_base_url = backend_url_input()

render_hero(
    "Topic / Category Analysis",
    "Group review language into business themes such as shipping, support, quality, price, and usability.",
)

raw_reviews = st.text_area(
    "Customer reviews",
    value=DEFAULT_SAMPLE_REVIEWS,
    help="Enter one review per line.",
    height=230,
)

if st.button("Analyze Topics", type="primary"):
    try:
        result = analyze_reviews_from_api_payload(
            split_review_lines(raw_reviews),
            api_base_url=api_base_url,
        )
    except ApiClientError as exc:
        render_error(exc)
    else:
        topics = pd.DataFrame(topic_rows(result["metrics"]["top_topics"]))
        if topics.empty:
            render_panel("No topics found", "Try reviews that mention shipping, support, price, quality, or setup.")
        else:
            chart_col, table_col = st.columns([1.4, 1])
            with chart_col:
                st.plotly_chart(
                    px.bar(
                        topics,
                        x="Topic",
                        y="Reviews",
                        color="Topic",
                        title="Top Review Topics",
                    ),
                    use_container_width=True,
                )
            with table_col:
                st.dataframe(topics, use_container_width=True, hide_index=True)

        st.subheader("Review-Level Categories")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Review": review["text"],
                        "Topic": str(review["topic"]).title(),
                        "Keywords": ", ".join(review["keywords"]),
                    }
                    for review in result["reviews"]
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
