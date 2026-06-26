from html import escape
from typing import Any

import streamlit as st

from api_client import DEFAULT_API_BASE_URL


# Shared Streamlit setup, including the small CSS layer used by both pages.
def configure_page(title: str) -> None:
    st.set_page_config(
        page_title=f"ReviewInsight | {title}",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(
        """
        <style>
            .stApp { background: #f5f7fb; color: #172033; }
            .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1180px; }
            h1, h2, h3 { color: #172033; letter-spacing: 0; }
            div[data-testid="stCaptionContainer"] { color: #687385; }
            .ri-nav {
                display: flex; justify-content: space-between; align-items: center;
                border: 1px solid #dfe4ec; border-radius: 8px; background: #fff;
                padding: 12px 14px; margin-bottom: 22px;
                box-shadow: 0 8px 24px rgba(23, 32, 51, 0.05);
            }
            .ri-brand { font-weight: 800; color: #172033; }
            .ri-links { display: flex; gap: 8px; flex-wrap: wrap; }
            .ri-links a {
                color: #687385; text-decoration: none; font-weight: 650;
                padding: 7px 9px; border-radius: 6px;
            }
            .ri-links a:hover { background: #eef4ff; color: #2563eb; }
            .ri-hero {
                border: 1px solid #dfe4ec; border-radius: 8px; background: #fff;
                padding: 22px 24px; margin-bottom: 18px;
                box-shadow: 0 10px 30px rgba(23, 32, 51, 0.06);
            }
            .ri-hero h1 { margin-bottom: 0.35rem; }
            .ri-hero p { color: #687385; margin: 0; max-width: 760px; }
            .ri-label {
                color: #687385; font-size: 0.78rem; font-weight: 800;
                letter-spacing: 0.05em; margin-bottom: 7px; text-transform: uppercase;
            }
            .ri-summary {
                background: #fff; border: 1px solid #e6ebf2; border-radius: 8px;
                padding: 14px 16px; color: #172033; line-height: 1.6;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_nav() -> None:
    # Keep navigation visible but understated so the review workflow stays primary.
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
    # Most users keep the default URL, so hide this setup detail by default.
    with st.expander("Backend connection", expanded=False):
        return st.text_input(
            "FastAPI backend URL",
            value=st.session_state.get("api_base_url", DEFAULT_API_BASE_URL),
        )


def render_result_tabs(result: dict[str, Any]) -> None:
    # The first two tabs answer the most common questions: summary first, sentiment second.
    summary_tab, sentiment_tab, topics_tab, urgency_tab, raw_tab = st.tabs(
        ["Summary", "Sentiment Analysis", "Topics / Categories", "Urgency", "Raw Result / Debug Info"]
    )

    with summary_tab:
        _render_summary(result)

    with sentiment_tab:
        col1, col2 = st.columns(2)
        col1.metric("Sentiment", str(result.get("sentiment", "neutral")).title())
        col2.metric("Sentiment Score", result.get("sentiment_score", 0))
        if result.get("sentiment_explanation"):
            st.markdown(
                f"""
                <div class="ri-label">Why this sentiment?</div>
                <div class="ri-summary">{escape(str(result["sentiment_explanation"]))}</div>
                """,
                unsafe_allow_html=True,
            )
        source = str(result.get("sentiment_source", "rule_based_fallback")).replace("_", " ")
        st.caption(f"Sentiment source: {source}")
        if result.get("sentiment_model_name"):
            st.caption(f"Sentiment model: {result['sentiment_model_name']}")
        if result.get("sentiment_confidence") is not None:
            st.caption(f"Sentiment confidence: {float(result['sentiment_confidence']):.2f}")
        if result.get("sentiment_fallback_reason"):
            st.caption(f"Sentiment fallback reason: {result['sentiment_fallback_reason']}")

    with topics_tab:
        topics = [str(topic) for topic in result.get("topics", []) if str(topic).strip()]
        st.write(", ".join(_format_topic(topic) for topic in topics) if topics else "General feedback")

    with urgency_tab:
        col1, col2 = st.columns(2)
        col1.metric("Urgency", str(result.get("urgency", "low")).title())
        col2.metric("Urgency Score", f"{float(result.get('urgency_score', 0.0)):.2f}")

    with raw_tab:
        st.json(result)


def history_rows(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    # Flatten API history items into display-ready strings for Streamlit cards.
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


def render_page_intro(title: str, description: str) -> None:
    st.markdown(
        f"""
        <section class="ri-hero">
            <h1>{escape(title)}</h1>
            <p>{escape(description)}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_summary(result: dict[str, Any]) -> None:
    # Keep the summary as one generated explanation without repeating quoted source text.
    summary = escape(str(result.get("summary", "No summary returned.")))
    st.markdown(
        f"""
        <div class="ri-label">Review summary</div>
        <div class="ri-summary">{summary}</div>
        """,
        unsafe_allow_html=True,
    )
    source = str(result.get("summary_source", "rule_based_fallback")).replace("_", " ")
    st.caption(f"Summary source: {source}")
    if result.get("fallback_reason"):
        st.caption(f"Fallback reason: {result['fallback_reason']}")


def _format_topic(topic: str) -> str:
    # Preserve common product abbreviations while title-casing regular labels.
    return "/".join(part.upper() if part.lower() in {"ui", "ux"} else part.title() for part in topic.split("/"))
