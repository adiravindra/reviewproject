import pandas as pd
import plotly.express as px
import streamlit as st

from ui import (
    configure_page,
    loaded_analysis_reviews,
    render_empty_state,
    render_hero,
    render_panel,
    render_top_nav,
    topic_rows,
    workspace_analysis,
)


configure_page("Topics")
render_top_nav()

render_hero(
    "Topics",
    "See which business themes appear in the currently loaded review data.",
)

analysis = workspace_analysis()
reviews = loaded_analysis_reviews(analysis)
if not reviews:
    render_empty_state()
else:
    metrics = dict(analysis.get("metrics", {}))
    topics = pd.DataFrame(topic_rows(list(metrics.get("top_topics", []))))

    if topics.empty:
        render_panel("No topics found", "Loaded reviews did not match the current rule-based topic vocabulary.")
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

    st.subheader("Review-Level Topics")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Topic": str(review.get("topic", "")).title(),
                    "Keywords": ", ".join(str(keyword) for keyword in review.get("keywords", [])),
                    "Review": review.get("text", ""),
                }
                for review in reviews
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
