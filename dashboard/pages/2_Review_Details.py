import streamlit as st

from ui import (
    configure_page,
    loaded_analysis_reviews,
    render_empty_state,
    render_hero,
    render_top_nav,
    workspace_analysis,
)


configure_page("Review Details")
render_top_nav()

render_hero(
    "Review Details",
    "Inspect the full analysis for one review from the currently loaded data.",
)

analysis = workspace_analysis()
reviews = loaded_analysis_reviews(analysis)
if not reviews:
    render_empty_state()
else:
    labels = [
        f"{index + 1}. {review.get('text', '')[:80]}"
        for index, review in enumerate(reviews)
    ]
    selected = st.selectbox(
        "Select review",
        options=list(range(len(reviews))),
        format_func=lambda index: labels[index],
        key="selected_review_index",
    )
    review = reviews[int(selected)]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Sentiment", str(review.get("sentiment", "n/a")).title())
    col2.metric("Topic", str(review.get("topic", "general feedback")).title())
    col3.metric("Urgency", str(review.get("urgency", "n/a")).title())
    col4.metric("Score", review.get("sentiment_score", 0))

    st.subheader("Review Text")
    st.write(review.get("text", ""))

    st.subheader("Short Summary")
    st.info(str(review.get("summary", "No summary returned.")))

    keywords = review.get("keywords", [])
    if keywords:
        st.subheader("Keywords")
        st.write(", ".join(str(keyword) for keyword in keywords))
