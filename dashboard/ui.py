from html import escape
from typing import Any

import streamlit as st

from api_client import DEFAULT_API_BASE_URL


def configure_page(title: str) -> None:
    st.set_page_config(
        page_title=f"ReviewInsight | {title}",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(
        """
        <style>
            .stApp { background: #f7f8fb; color: #172033; }
            section[data-testid="stSidebar"], div[data-testid="collapsedControl"] { display: none; }
            h1, h2, h3 { color: #172033; letter-spacing: 0; }
            .ri-nav {
                display: flex; justify-content: space-between; align-items: center;
                border: 1px solid #dfe4ec; border-radius: 8px; background: #fff;
                padding: 10px 12px; margin-bottom: 18px;
            }
            .ri-brand { font-weight: 800; }
            .ri-links { display: flex; gap: 8px; flex-wrap: wrap; }
            .ri-links a {
                color: #687385; text-decoration: none; font-weight: 650;
                padding: 7px 9px; border-radius: 6px;
            }
            .ri-links a:hover { background: #eef4ff; color: #2563eb; }
            .ri-panel {
                border: 1px solid #dfe4ec; border-radius: 8px; background: #fff;
                padding: 16px 18px; margin: 8px 0 16px;
            }
            .ri-panel h3 { font-size: 1.05rem; margin: 0 0 8px; }
            .ri-panel p { color: #687385; margin: 0; }
            div[data-testid="stMetric"] {
                border: 1px solid #dfe4ec; border-radius: 8px; background: #fff;
                padding: 12px 14px;
            }
            div[data-testid="stButton"] > button { border-radius: 8px; font-weight: 650; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_nav() -> None:
    st.markdown(
        """
        <nav class="ri-nav">
            <div class="ri-brand">ReviewInsight</div>
        </nav>
        """,
        unsafe_allow_html=True,
    )
    analysis_col, history_col, spacer = st.columns([0.16, 0.16, 0.68])
    with analysis_col:
        st.page_link("streamlit_app.py", label="Analysis")
    with history_col:
        st.page_link("pages/1_History.py", label="History")


def backend_url_input() -> str:
    with st.expander("Backend connection", expanded=False):
        return st.text_input(
            "FastAPI backend URL",
            value=st.session_state.get("api_base_url", DEFAULT_API_BASE_URL),
        )


def render_result_tabs(result: dict[str, Any]) -> None:
    sentiment_tab, topics_tab, urgency_tab, summary_tab, raw_tab = st.tabs(
        ["Sentiment", "Topics / Categories", "Urgency", "Summary", "Raw Result / Debug Info"]
    )

    with sentiment_tab:
        st.metric("Sentiment", str(result.get("sentiment", "neutral")).title())
        st.metric("Sentiment Score", result.get("sentiment_score", 0))

    with topics_tab:
        topics = [str(topic) for topic in result.get("topics", []) if str(topic).strip()]
        st.write(", ".join(_format_topic(topic) for topic in topics) if topics else "General feedback")

    with urgency_tab:
        st.metric("Urgency", str(result.get("urgency", "low")).title())
        st.metric("Urgency Score", f"{float(result.get('urgency_score', 0.0)):.2f}")

    with summary_tab:
        st.write(str(result.get("summary", "No summary returned.")))
        source = str(result.get("summary_source", "rule_based_fallback")).replace("_", " ")
        st.caption(f"Summary source: {source}")
        if result.get("fallback_reason"):
            st.caption(f"Fallback reason: {result['fallback_reason']}")

    with raw_tab:
        st.json(result)


def history_rows(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "Timestamp": str(item.get("created_at", "")),
            "Review": str(item.get("text", "")),
            "Sentiment": str(item.get("sentiment", "neutral")).title(),
            "Topics": ", ".join(_format_topic(str(topic)) for topic in item.get("topics", [])),
            "Urgency": str(item.get("urgency", "low")).title(),
            "Summary": str(item.get("summary", "")),
        }
        for item in items
    ]


def render_error(error: Exception) -> None:
    st.error(str(error))


def render_original_review(text: str) -> None:
    st.markdown(
        f"""
        <div class="ri-panel">
            <h3>Original Review</h3>
            <p>{escape(text)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _format_topic(topic: str) -> str:
    return "/".join(part.upper() if part.lower() in {"ui", "ux"} else part.title() for part in topic.split("/"))
