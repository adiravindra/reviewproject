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
    split_review_lines,
    urgency_breakdown_rows,
)


configure_page("Urgency Priority")

api_base_url = backend_url_input()

render_hero(
    "Urgency / Priority Analysis",
    "Separate routine feedback from reviews that need faster operational follow-up.",
)

raw_reviews = st.text_area(
    "Customer reviews",
    value="\n".join(
        [
            DEFAULT_SAMPLE_REVIEWS,
            "The item arrived broken and I need an urgent refund.",
        ]
    ),
    help="Enter one review per line.",
    height=240,
)

if st.button("Analyze Priority", type="primary"):
    try:
        result = analyze_reviews_from_api_payload(
            split_review_lines(raw_reviews),
            api_base_url=api_base_url,
        )
    except ApiClientError as exc:
        render_error(exc)
    else:
        urgency_data = pd.DataFrame(
            urgency_breakdown_rows(result["metrics"]["urgency_breakdown"])
        )
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("High Priority", result["metrics"]["urgency_breakdown"]["high"])
        metric_col2.metric("Medium Priority", result["metrics"]["urgency_breakdown"]["medium"])
        metric_col3.metric("Low Priority", result["metrics"]["urgency_breakdown"]["low"])

        st.plotly_chart(
            px.bar(
                urgency_data,
                x="Urgency",
                y="Reviews",
                color="Urgency",
                title="Priority Queue",
            ),
            use_container_width=True,
        )

        st.subheader("Priority Worklist")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Urgency": str(review["urgency"]).title(),
                        "Sentiment": str(review["sentiment"]).title(),
                        "Topic": str(review["topic"]).title(),
                        "Review": review["text"],
                    }
                    for review in result["reviews"]
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
