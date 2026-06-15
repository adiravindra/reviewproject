import pandas as pd
import plotly.express as px
import streamlit as st

from ui import (
    average_urgency_label,
    configure_page,
    loaded_analysis_reviews,
    render_empty_state,
    render_hero,
    render_top_nav,
    urgency_breakdown_rows,
    workspace_analysis,
)


configure_page("Urgency")
render_top_nav()

render_hero(
    "Urgency",
    "Prioritize the loaded reviews by follow-up risk and operational importance.",
)

analysis = workspace_analysis()
reviews = loaded_analysis_reviews(analysis)
if not reviews:
    render_empty_state()
else:
    metrics = dict(analysis.get("metrics", {}))
    urgency_breakdown = dict(metrics.get("urgency_breakdown", {}))
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("High", urgency_breakdown.get("high", 0))
    col2.metric("Medium", urgency_breakdown.get("medium", 0))
    col3.metric("Low", urgency_breakdown.get("low", 0))
    col4.metric("Average", average_urgency_label(metrics.get("average_urgency")))

    urgency_data = pd.DataFrame(urgency_breakdown_rows(urgency_breakdown))
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

    urgent_reviews = loaded_analysis_reviews({"reviews": analysis.get("most_urgent_reviews", [])})
    st.subheader("Most Urgent Reviews")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Urgency": str(review.get("urgency", "")).title(),
                    "Sentiment": str(review.get("sentiment", "")).title(),
                    "Topic": str(review.get("topic", "")).title(),
                    "Review": review.get("text", ""),
                }
                for review in urgent_reviews
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
