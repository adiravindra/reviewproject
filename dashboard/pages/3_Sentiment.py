import pandas as pd
import plotly.express as px
import streamlit as st

from ui import (
    configure_page,
    loaded_analysis_reviews,
    render_empty_state,
    render_hero,
    render_top_nav,
    sentiment_breakdown_rows,
    workspace_analysis,
)


configure_page("Sentiment")
render_top_nav()

render_hero(
    "Sentiment",
    "Understand the positive, neutral, and negative mix in the currently loaded reviews.",
)

analysis = workspace_analysis()
reviews = loaded_analysis_reviews(analysis)
if not reviews:
    render_empty_state()
else:
    metrics = dict(analysis.get("metrics", {}))
    breakdown = dict(metrics.get("sentiment_breakdown", {}))
    col1, col2, col3 = st.columns(3)
    col1.metric("Positive", breakdown.get("positive", 0))
    col2.metric("Neutral", breakdown.get("neutral", 0))
    col3.metric("Negative", breakdown.get("negative", 0))

    sentiment_data = pd.DataFrame(sentiment_breakdown_rows(breakdown))
    st.plotly_chart(
        px.bar(
            sentiment_data,
            x="Sentiment",
            y="Reviews",
            color="Sentiment",
            title="Sentiment Distribution",
        ),
        use_container_width=True,
    )

    st.subheader("Review Sentiment")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Sentiment": str(review.get("sentiment", "")).title(),
                    "Score": review.get("sentiment_score", 0),
                    "Review": review.get("text", ""),
                }
                for review in reviews
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
