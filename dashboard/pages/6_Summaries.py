import pandas as pd
import streamlit as st

from ui import (
    configure_page,
    loaded_analysis_reviews,
    render_empty_state,
    render_hero,
    render_panel,
    render_top_nav,
    workspace_analysis,
)


configure_page("Summaries")
render_top_nav()

render_hero(
    "Summaries",
    "Review the generated summary and per-review summaries for the loaded data.",
)

analysis = workspace_analysis()
reviews = loaded_analysis_reviews(analysis)
if not reviews:
    render_empty_state()
else:
    st.subheader("Run Summary")
    st.info(str(analysis.get("summary", "No summary returned.")))

    col1, col2 = st.columns(2)
    with col1:
        render_panel(
            "Summary mode",
            "This MVP uses deterministic summaries from the backend service layer.",
        )
    with col2:
        render_panel(
            "Future GenAI controls",
            "Length, audience, citations, and model metadata can plug into the same loaded-review workflow.",
        )

    st.subheader("Review Summaries")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Summary": review.get("summary", ""),
                    "Sentiment": str(review.get("sentiment", "")).title(),
                    "Topic": str(review.get("topic", "")).title(),
                    "Review": review.get("text", ""),
                }
                for review in reviews
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
