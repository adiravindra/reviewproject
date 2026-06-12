import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.api_client import ApiClientError, fetch_review_insights


st.set_page_config(page_title="ReviewInsight Dashboard", layout="wide")

st.title("ReviewInsight Dashboard")

api_base_url = st.sidebar.text_input(
    "FastAPI backend URL",
    value="http://127.0.0.1:8000",
)

review_text = st.text_area(
    "Customer reviews",
    placeholder="Paste one customer review per line...",
    height=220,
)

if st.button("Analyze Reviews", type="primary"):
    reviews = review_text.splitlines()

    try:
        insights = fetch_review_insights(reviews, api_base_url=api_base_url)
    except ApiClientError as exc:
        st.error(str(exc))
    else:
        st.subheader("Analysis Results")

        col1, col2, col3 = st.columns(3)
        col1.metric("Overall Sentiment", str(insights["overall_sentiment"]).title())
        col2.metric("Reviews Analyzed", insights["review_count"])
        col3.metric("Action Items", len(insights["suggested_action_items"]))

        st.write("Summary")
        st.info(insights["summary"])

        breakdown = insights["sentiment_breakdown"]
        chart_data = pd.DataFrame(
            {
                "Sentiment": [sentiment.title() for sentiment in breakdown.keys()],
                "Reviews": list(breakdown.values()),
            }
        )
        fig = px.bar(
            chart_data,
            x="Sentiment",
            y="Reviews",
            title="Sentiment Counts",
            color="Sentiment",
        )
        st.plotly_chart(fig, use_container_width=True)

        left_col, right_col = st.columns(2)
        with left_col:
            st.write("Positive Themes")
            if insights["positive_themes"]:
                st.write(", ".join(insights["positive_themes"]))
            else:
                st.caption("No positive themes found yet.")

            st.write("Common Complaints")
            if insights["common_complaints"]:
                for complaint in insights["common_complaints"]:
                    st.write(f"- {complaint}")
            else:
                st.caption("No recurring complaints found yet.")

        with right_col:
            st.write("Negative Themes")
            if insights["negative_themes"]:
                st.write(", ".join(insights["negative_themes"]))
            else:
                st.caption("No negative themes found yet.")

            st.write("Suggested Action Items")
            for action_item in insights["suggested_action_items"]:
                st.write(f"- {action_item}")
