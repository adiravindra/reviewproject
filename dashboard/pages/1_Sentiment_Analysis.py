import streamlit as st

from api_client import ApiClientError, analyze_single_review
from ui import backend_url_input, configure_page, render_analysis_result, render_error, render_hero


configure_page("Sentiment Analysis")

api_base_url = backend_url_input()

render_hero(
    "Sentiment Analysis",
    "Classify a customer review as positive, neutral, or negative and keep the result in the backend analysis history.",
)

review_text = st.text_area(
    "Customer review",
    value="I love the fast delivery and excellent quality.",
    height=180,
)

if st.button("Analyze Sentiment", type="primary"):
    try:
        result = analyze_single_review(review_text, api_base_url=api_base_url)
    except ApiClientError as exc:
        render_error(exc)
    else:
        render_analysis_result(result)

st.caption("Current sentiment logic is rule-based and can be replaced by an ML model later.")
