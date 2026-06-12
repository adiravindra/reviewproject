import streamlit as st

from api_client import ApiClientError, fetch_sentiment
from ui import backend_url_input, configure_page, render_error, render_placeholder_panel


configure_page("Sentiment Analysis")

st.title("Sentiment Analysis")
st.write("Analyze one review with the current rule-based sentiment service.")

api_base_url = backend_url_input()

review_text = st.text_area(
    "Customer review",
    value="I love the fast delivery and excellent quality.",
    height=180,
)

if st.button("Analyze Sentiment", type="primary"):
    try:
        result = fetch_sentiment(review_text, api_base_url=api_base_url)
    except ApiClientError as exc:
        render_error(exc)
    else:
        col1, col2 = st.columns(2)
        col1.metric("Sentiment", str(result["sentiment"]).title())
        col2.metric("Rule-Based Score", result["score"])

        st.write("Analyzed Text")
        st.info(result["text"])

        render_placeholder_panel(
            "Future model confidence",
            "A production ML model can add confidence, probability scores, and model version metadata here.",
        )

st.caption("Current sentiment logic is intentionally simple and can be replaced by a trained model later.")
