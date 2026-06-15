import pandas as pd
import plotly.express as px
import streamlit as st

from ui import (
    average_urgency_label,
    configure_page,
    render_analysis_result,
    render_empty_state,
    render_hero,
    render_top_nav,
    sentiment_breakdown_rows,
    topic_rows,
    urgency_breakdown_rows,
    workspace_analysis,
)


configure_page("Overview")
render_top_nav()

render_hero(
    "Overview",
    "A shared workspace view of the review data loaded from Home/Add Reviews.",
)

analysis = workspace_analysis()
if not analysis:
    render_empty_state()
else:
    metrics = dict(analysis.get("metrics", {}))
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Reviews", analysis.get("review_count", 0))
    col2.metric("Overall Sentiment", str(metrics.get("overall_sentiment", "n/a")).title())
    col3.metric("Average Urgency", average_urgency_label(metrics.get("average_urgency")))
    col4.metric("High Priority", metrics.get("high_priority_reviews", 0))

    if int(analysis.get("review_count", 0)) == 1:
        render_analysis_result(analysis)
    else:
        sentiment_data = pd.DataFrame(sentiment_breakdown_rows(dict(metrics.get("sentiment_breakdown", {}))))
        urgency_data = pd.DataFrame(urgency_breakdown_rows(dict(metrics.get("urgency_breakdown", {}))))
        topic_data = pd.DataFrame(topic_rows(list(metrics.get("top_topics", []))))

        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.plotly_chart(
                px.pie(
                    sentiment_data,
                    names="Sentiment",
                    values="Reviews",
                    title="Sentiment Distribution",
                    hole=0.45,
                ),
                use_container_width=True,
            )
        with chart_col2:
            st.plotly_chart(
                px.bar(
                    urgency_data,
                    x="Urgency",
                    y="Reviews",
                    color="Urgency",
                    title="Urgency Mix",
                ),
                use_container_width=True,
            )

        if not topic_data.empty:
            st.subheader("Top Topics")
            st.dataframe(topic_data, use_container_width=True, hide_index=True)

        st.subheader("Executive Summary")
        st.info(str(analysis.get("summary", "No summary returned.")))
