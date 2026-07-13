import os
from typing import Any

import streamlit as st

from dashboard.api_client import ApiClientError, BackendUnavailable, check_health, request_analysis


BACKEND_COMMAND = (
    r".\.venv\Scripts\python.exe -m uvicorn backend.app.main:app "
    r"--host 127.0.0.1 --port 8000"
)

DASHBOARD_CSS = """
[data-testid="stToolbar"] {
    display: none !important;
}
[data-testid="stBaseButton-primaryFormSubmit"] {
    background-color: #2563eb !important;
    border-color: #2563eb !important;
    color: #ffffff !important;
}
[data-testid="stBaseButton-primaryFormSubmit"]:hover,
[data-testid="stBaseButton-primaryFormSubmit"]:focus,
[data-testid="stBaseButton-primaryFormSubmit"]:active {
    background-color: #1d4ed8 !important;
    border-color: #1d4ed8 !important;
    color: #ffffff !important;
}
[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child {
    background-color: #2563eb !important;
    border-color: #2563eb !important;
}
"""


def metric_values(report: dict[str, Any]) -> tuple[str, str, str, str]:
    metrics = report["metrics"]
    insights = report["insights"]
    average = metrics.get("average_rating")
    average_label = "Not rated" if average is None else f"{float(average):.1f} / 5"
    return (
        str(metrics["review_count"]),
        average_label,
        f'{float(metrics["positive_percentage"]):.1f}%',
        str(insights["overall_sentiment"]).title(),
    )


def sentiment_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    counts = report["metrics"]["sentiment_counts"]
    return [
        {"Sentiment": sentiment.title(), "Reviews": int(counts.get(sentiment, 0))}
        for sentiment in ("positive", "neutral", "negative")
    ]


def rating_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    distribution = report["metrics"]["rating_distribution"]
    return [
        {"Rating": f"{star} star", "Reviews": int(distribution.get(str(star), 0))}
        for star in range(1, 6)
    ]


def _configure_page() -> None:
    st.set_page_config(page_title="ReviewInsight", page_icon="💬", layout="wide")
    st.markdown(
        """
        <style>
        :root {
            --ri-blue: #2563eb;
            --ri-slate-950: #0f172a;
            --ri-slate-600: #475569;
            --ri-slate-200: #e2e8f0;
        }
        .stApp { background: #ffffff; color: var(--ri-slate-950); }
        [data-testid="stHeader"] { background: rgba(255, 255, 255, 0.96); }
        .block-container { max-width: 1180px; padding-top: 3rem; padding-bottom: 5rem; }
        h1, h2, h3, p, label, [data-testid="stMetricLabel"] { color: var(--ri-slate-950); }
        h1 { letter-spacing: -0.035em; font-weight: 750; }
        h2 { letter-spacing: -0.02em; padding-top: 1.4rem; }
        [data-testid="stCaptionContainer"] { color: var(--ri-slate-600); }
        [data-testid="stForm"] { border: 1px solid var(--ri-slate-200); border-radius: 12px; padding: 1.25rem; }
        div[data-testid="stTextInput"] input, div[role="radiogroup"] { border-radius: 8px; }
        .stButton > button, [data-testid="stFormSubmitButton"] > button {
            border-radius: 8px;
            background: var(--ri-blue);
            border-color: var(--ri-blue);
            font-weight: 650;
        }
        [data-testid="stMetric"] { border-top: 1px solid var(--ri-slate-200); padding-top: 1rem; }
        [data-testid="stMetricValue"] { color: var(--ri-slate-950); letter-spacing: -0.025em; }
        hr { border-color: var(--ri-slate-200); }
        @media (max-width: 640px) {
            .block-container { padding: 1.5rem 1rem 3rem; }
            h1 { font-size: 2.15rem !important; }
            [data-testid="stForm"] { padding: 1rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f"<style>{DASHBOARD_CSS}</style>", unsafe_allow_html=True)


def _render_list(items: list[str]) -> None:
    if not items:
        st.write("—")
        return
    for item in items:
        st.markdown(f"- {item}")


def _render_report(report: dict[str, Any]) -> None:
    metrics = metric_values(report)
    metric_columns = st.columns(4)
    labels = ("Reviews analyzed", "Average rating", "Positive share", "Overall sentiment")
    for column, label, value in zip(metric_columns, labels, metrics):
        column.metric(label, value)

    st.header("What customers are saying")
    st.write(report["insights"]["summary"])

    chart_columns = st.columns(2)
    with chart_columns[0]:
        st.subheader("Sentiment mix")
        st.bar_chart(sentiment_rows(report), x="Sentiment", y="Reviews")
    with chart_columns[1]:
        st.subheader("Rating distribution")
        st.bar_chart(rating_rows(report), x="Rating", y="Reviews")

    st.header("Recurring themes")
    themes = [
        {
            "Theme": theme["name"],
            "What customers mention": theme["description"],
            "Mentions": theme["mentions"],
        }
        for theme in report["insights"]["themes"]
    ]
    st.dataframe(themes, hide_index=True, width="stretch")

    insight_columns = st.columns(2)
    with insight_columns[0]:
        st.subheader("Strengths")
        _render_list(report["insights"]["strengths"])
    with insight_columns[1]:
        st.subheader("Weaknesses")
        _render_list(report["insights"]["weaknesses"])

    st.header("Recommended actions")
    for index, action in enumerate(report["insights"]["actions"], start=1):
        st.markdown(f"{index}. {action}")

    with st.expander("Review sample"):
        source = report["source"]
        st.caption(f'{source["title"]} · {source["extractor"].replace("_", " ").title()}')
        for review in report["reviews"][:10]:
            metadata = []
            if review.get("rating") is not None:
                metadata.append(f'{review["rating"]} / 5')
            if review.get("date"):
                metadata.append(str(review["date"]))
            if metadata:
                st.caption(" · ".join(metadata))
            st.write(review["text"])
            st.divider()


def main() -> None:
    _configure_page()
    st.title("ReviewInsight")
    st.caption("Turn public customer reviews into a clear product readout.")

    base_url = os.getenv("REVIEWINSIGHT_API_URL", "http://127.0.0.1:8000")
    with st.form("review-analysis-form"):
        url = st.text_input(
            "Review page URL",
            placeholder="https://web-scraping.dev/product/1",
        )
        provider_label = st.radio("AI provider", ("Gemini", "Groq"), horizontal=True)
        submitted = st.form_submit_button("Analyze reviews", type="primary", width="stretch")

    if submitted:
        st.session_state.pop("latest_report", None)
        if not check_health(base_url):
            st.error("The FastAPI backend is not reachable. Start it with:")
            st.code(BACKEND_COMMAND, language="powershell")
        else:
            try:
                with st.spinner("Analyzing public reviews…"):
                    st.session_state["latest_report"] = request_analysis(
                        url.strip(),
                        "google" if provider_label == "Gemini" else "groq",
                        base_url,
                    )
            except BackendUnavailable:
                st.error("The FastAPI backend is not reachable. Start it with:")
                st.code(BACKEND_COMMAND, language="powershell")
            except ApiClientError as exc:
                st.error(exc.message)

    report = st.session_state.get("latest_report")
    if isinstance(report, dict):
        _render_report(report)


if __name__ == "__main__":
    main()
