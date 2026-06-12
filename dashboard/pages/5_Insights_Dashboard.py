import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.api_client import ApiClientError, fetch_review_insights
from dashboard.ui import (
    DEFAULT_SAMPLE_REVIEWS,
    backend_url_input,
    configure_page,
    render_error,
    sentiment_breakdown_rows,
    split_review_lines,
)


configure_page("Insights Dashboard")

st.title("Insights Dashboard")
st.write("Business-facing review analysis with sentiment, themes, complaints, summary, and action items.")

api_base_url = backend_url_input()

raw_reviews = st.text_area(
    "Customer reviews",
    value=DEFAULT_SAMPLE_REVIEWS,
    help="Enter one review per line.",
    height=240,
)

if st.button("Generate Insights", type="primary"):
    try:
        insights = fetch_review_insights(split_review_lines(raw_reviews), api_base_url=api_base_url)
    except ApiClientError as exc:
        render_error(exc)
    else:
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("Overall Sentiment", str(insights["overall_sentiment"]).title())
        metric_col2.metric("Reviews Analyzed", insights["review_count"])
        metric_col3.metric("Action Items", len(insights["suggested_action_items"]))

        chart_data = pd.DataFrame(sentiment_breakdown_rows(insights["sentiment_breakdown"]))
        fig = px.bar(
            chart_data,
            x="Sentiment",
            y="Reviews",
            title="Sentiment Distribution",
            color="Sentiment",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Summary")
        st.info(insights["summary"])

        theme_col1, theme_col2, complaint_col = st.columns(3)
        with theme_col1:
            st.subheader("Positive Themes")
            if insights["positive_themes"]:
                for theme in insights["positive_themes"]:
                    st.write(f"- {theme}")
            else:
                st.caption("No positive themes found yet.")

        with theme_col2:
            st.subheader("Negative Themes")
            if insights["negative_themes"]:
                for theme in insights["negative_themes"]:
                    st.write(f"- {theme}")
            else:
                st.caption("No negative themes found yet.")

        with complaint_col:
            st.subheader("Common Complaints")
            if insights["common_complaints"]:
                for complaint in insights["common_complaints"]:
                    st.write(f"- {complaint}")
            else:
                st.caption("No recurring complaints found yet.")

        st.subheader("Suggested Action Items")
        for action_item in insights["suggested_action_items"]:
            st.write(f"- {action_item}")
