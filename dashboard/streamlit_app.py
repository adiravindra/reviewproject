import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="ReviewInsight Dashboard", layout="wide")

st.title("ReviewInsight Dashboard")

review_text = st.text_area(
    "Customer review",
    placeholder="Paste a customer review here...",
    height=160,
)

if st.button("Analyze Review", type="primary"):
    cleaned_text = review_text.strip()

    if cleaned_text:
        summary = f"Placeholder summary for: {cleaned_text[:120]}"
    else:
        summary = "Enter a customer review to see placeholder analysis."

    st.subheader("Analysis Results")
    col1, col2, col3 = st.columns(3)
    col1.metric("Sentiment", "Neutral")
    col2.metric("Topic", "General Feedback")
    col3.metric("Urgency", "Low")
    st.write("Summary")
    st.info(summary)

st.subheader("Sample Review Trends")

sample_data = pd.DataFrame(
    {
        "Sentiment": ["Positive", "Neutral", "Negative"],
        "Reviews": [18, 9, 6],
    }
)

fig = px.bar(
    sample_data,
    x="Sentiment",
    y="Reviews",
    title="Sample Sentiment Counts",
    color="Sentiment",
)
st.plotly_chart(fig, use_container_width=True)
