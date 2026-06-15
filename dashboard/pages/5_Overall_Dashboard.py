import pandas as pd
import plotly.express as px
import streamlit as st

from api_client import ApiClientError, fetch_dashboard_metrics
from ui import (
    backend_url_input,
    configure_page,
    render_error,
    render_hero,
    sentiment_breakdown_rows,
    topic_rows,
    urgency_breakdown_rows,
)


configure_page("Overall Dashboard")

api_base_url = backend_url_input()

render_hero(
    "Overall Dashboard",
    "A rollup of saved review analysis runs, sentiment health, priority mix, and recurring topics.",
)

try:
    metrics = fetch_dashboard_metrics(api_base_url=api_base_url)
except ApiClientError as exc:
    render_error(exc)
else:
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Analysis Runs", metrics["total_runs"])
    metric_col2.metric("Reviews Analyzed", metrics["total_reviews"])
    metric_col3.metric("High Priority", metrics["urgency_breakdown"]["high"])
    metric_col4.metric("Negative Reviews", metrics["sentiment_breakdown"]["negative"])

    sentiment_data = pd.DataFrame(sentiment_breakdown_rows(metrics["sentiment_breakdown"]))
    urgency_data = pd.DataFrame(urgency_breakdown_rows(metrics["urgency_breakdown"]))
    topic_data = pd.DataFrame(topic_rows(metrics["top_topics"]))

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.plotly_chart(
            px.pie(
                sentiment_data,
                names="Sentiment",
                values="Reviews",
                title="Sentiment Mix",
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
                title="Urgency Breakdown",
            ),
            use_container_width=True,
        )

    st.subheader("Top Topics")
    if topic_data.empty:
        st.caption("No saved topic data yet. Run an analysis from the homepage.")
    else:
        st.plotly_chart(
            px.bar(
                topic_data,
                x="Topic",
                y="Reviews",
                color="Topic",
                title="Recurring Topics",
            ),
            use_container_width=True,
        )

    st.subheader("Recent Summaries")
    if metrics["recent_summaries"]:
        for summary in metrics["recent_summaries"]:
            st.info(summary)
    else:
        st.caption("No summaries saved yet.")
