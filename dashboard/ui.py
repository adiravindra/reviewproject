from html import escape
from typing import Any

import streamlit as st

from backend.app.services.sentiment import sentiment_evidence
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
            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(41, 92, 255, 0.08), transparent 32rem),
                    linear-gradient(180deg, #f8fafc 0%, #eef3f8 100%);
                color: #172033;
            }
            .block-container { padding-top: 1.25rem; padding-bottom: 3rem; max-width: 1180px; }
            section[data-testid="stSidebar"] { display: none; }
            h1, h2, h3 { color: #172033; letter-spacing: 0; }
            div[data-testid="stCaptionContainer"] { color: #5c6878; }
            div[data-testid="stMetric"] {
                background: #ffffff;
                border: 1px solid #e3e8ef;
                border-radius: 8px;
                padding: 14px 16px;
                box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
            }
            div[data-testid="stMetricLabel"] { color: #5c6878; font-weight: 700; }
            div[data-testid="stMetricValue"] { color: #172033; }
            div[data-testid="stButton"] button[data-testid="stBaseButton-primary"] {
                background: #1f5eff !important;
                background-color: #1f5eff !important;
                border: 1px solid #1f5eff !important;
                border-radius: 8px;
                color: #ffffff !important;
                min-height: 44px;
                font-weight: 800;
                box-shadow: 0 12px 24px rgba(37, 99, 235, 0.18);
            }
            div[data-testid="stButton"] button[data-testid="stBaseButton-primary"]:hover {
                background: #184bd6 !important;
                background-color: #184bd6 !important;
                border-color: #184bd6 !important;
                color: #ffffff !important;
            }
            .ri-nav {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 18px;
                border: 1px solid #dbe3ee;
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.94);
                padding: 13px 16px;
                margin-bottom: 22px;
                box-shadow: 0 14px 36px rgba(15, 23, 42, 0.08);
                backdrop-filter: blur(8px);
            }
            .ri-brand {
                align-items: center;
                color: #172033;
                display: flex;
                font-size: 1.02rem;
                font-weight: 900;
                gap: 10px;
                white-space: nowrap;
            }
            .ri-logo {
                align-items: center;
                background: #1f5eff;
                border-radius: 8px;
                color: #ffffff;
                display: inline-flex;
                font-size: 0.78rem;
                font-weight: 900;
                height: 32px;
                justify-content: center;
                width: 32px;
            }
            .ri-links { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
            .ri-links a {
                color: #5c6878;
                text-decoration: none;
                font-weight: 800;
                padding: 9px 12px;
                border-radius: 8px;
            }
            .ri-links a:hover, .ri-links a.ri-active { background: #eaf1ff; color: #1f5eff; }
            .ri-hero {
                border: 1px solid #dbe3ee;
                border-radius: 8px;
                background: #ffffff;
                padding: 28px 30px;
                margin-bottom: 18px;
                box-shadow: 0 16px 42px rgba(15, 23, 42, 0.08);
            }
            .ri-hero h1 { margin-bottom: 0.35rem; font-size: 2.15rem; }
            .ri-hero p { color: #5c6878; margin: 0; max-width: 760px; line-height: 1.65; }
            .ri-label {
                color: #5c6878; font-size: 0.78rem; font-weight: 900;
                letter-spacing: 0.05em; margin-bottom: 7px; text-transform: uppercase;
            }
            .ri-card {
                background: #ffffff;
                border: 1px solid #e3e8ef;
                border-radius: 8px;
                box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
                color: #172033;
                padding: 18px 20px;
            }
            .ri-summary { font-size: 1.02rem; line-height: 1.7; }
            .ri-results-grid {
                display: grid;
                gap: 16px;
                grid-template-columns: minmax(0, 1.15fr) minmax(280px, 0.85fr);
                margin-bottom: 16px;
            }
            .ri-sentiment-card {
                display: grid;
                gap: 12px;
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .ri-stat {
                background: #f8fafc;
                border: 1px solid #e6ebf2;
                border-radius: 8px;
                padding: 14px 15px;
            }
            .ri-stat-label {
                color: #5c6878;
                font-size: 0.78rem;
                font-weight: 900;
                letter-spacing: 0.04em;
                text-transform: uppercase;
            }
            .ri-stat-value { color: #172033; font-size: 1.45rem; font-weight: 900; margin-top: 4px; }
            .ri-pill {
                border-radius: 999px;
                display: inline-flex;
                font-size: 0.78rem;
                font-weight: 900;
                padding: 5px 10px;
                text-transform: uppercase;
            }
            .ri-pill-positive { background: #dcfce7; color: #166534; }
            .ri-pill-neutral { background: #fef9c3; color: #854d0e; }
            .ri-pill-negative { background: #fee2e2; color: #991b1b; }
            .ri-meta { color: #5c6878; font-size: 0.86rem; line-height: 1.55; margin-top: 12px; }
            .ri-highlighted-review {
                background: #ffffff;
                border: 1px solid #e3e8ef;
                border-radius: 8px;
                color: #172033;
                font-size: 1rem;
                line-height: 1.85;
                padding: 18px 20px;
            }
            .ri-keyword {
                border-radius: 5px;
                box-decoration-break: clone;
                font-weight: 850;
                padding: 1px 5px 2px;
            }
            .ri-keyword-positive { background: #bbf7d0; color: #14532d; }
            .ri-keyword-neutral { background: #fef08a; color: #713f12; }
            .ri-keyword-negative { background: #fecaca; color: #7f1d1d; }
            @media (max-width: 760px) {
                .ri-nav { align-items: flex-start; flex-direction: column; }
                .ri-links { justify-content: flex-start; }
                .ri-hero { padding: 22px 20px; }
                .ri-hero h1 { font-size: 1.65rem; }
                .ri-results-grid, .ri-sentiment-card { grid-template-columns: 1fr; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_nav(active_page: str) -> None:
    active_analysis = "ri-active" if active_page == "Analysis" else ""
    active_history = "ri-active" if active_page == "History" else ""
    st.markdown(
        f"""
        <nav class="ri-nav">
            <div class="ri-brand"><span class="ri-logo">RI</span><span>ReviewInsight</span></div>
            <div class="ri-links">
                <a class="{active_analysis}" href="/" target="_self">Analysis</a>
                <a class="{active_history}" href="/History" target="_self">History</a>
            </div>
        </nav>
        """,
        unsafe_allow_html=True,
    )


def backend_url_input() -> str:
    # Most users keep the default URL, so hide this setup detail by default.
    with st.expander("Backend connection", expanded=False):
        return st.text_input(
            "FastAPI backend URL",
            value=st.session_state.get("api_base_url", DEFAULT_API_BASE_URL),
        )


def render_result_tabs(result: dict[str, Any]) -> None:
    overview_tab, raw_tab = st.tabs(["Summary & Sentiment", "Raw Result"])

    with overview_tab:
        _render_summary_and_sentiment(result)

    with raw_tab:
        st.json(result)


def history_rows(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    # Flatten API history items into display-ready strings for Streamlit cards.
    return [
        {
            "Timestamp": str(item.get("created_at", "")),
            "Review": str(item.get("text", "")),
            "Sentiment": str(item.get("sentiment", "neutral")).title(),
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


def _render_summary_and_sentiment(result: dict[str, Any]) -> None:
    summary = escape(str(result.get("summary", "No summary returned.")))
    sentiment = str(result.get("sentiment", "neutral")).casefold()
    sentiment_label = sentiment.title()
    if sentiment not in {"positive", "neutral", "negative"}:
        sentiment = "neutral"
    score = result.get("sentiment_score", 0)
    confidence = result.get("sentiment_confidence")
    confidence_value = "N/A" if confidence is None else f"{float(confidence):.0%}"

    st.markdown(
        f"""
        <div class="ri-results-grid">
            <section class="ri-card">
                <div class="ri-label">Review summary</div>
                <div class="ri-summary">{summary}</div>
            </section>
            <section class="ri-card">
                <div class="ri-label">Sentiment analysis</div>
                <span class="ri-pill ri-pill-{sentiment}">{escape(sentiment_label)}</span>
                <div class="ri-sentiment-card" style="margin-top: 14px;">
                    <div class="ri-stat">
                        <div class="ri-stat-label">Score</div>
                        <div class="ri-stat-value">{escape(str(score))}</div>
                    </div>
                    <div class="ri-stat">
                        <div class="ri-stat-label">Confidence</div>
                        <div class="ri-stat-value">{escape(confidence_value)}</div>
                    </div>
                </div>
            </section>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if result.get("sentiment_explanation"):
        st.markdown(
            f"""
            <section class="ri-card" style="margin-bottom: 16px;">
                <div class="ri-label">Why this sentiment?</div>
                <div class="ri-summary">{escape(str(result["sentiment_explanation"]))}</div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="ri-label">Keyword highlights</div>
        <div class="ri-highlighted-review">{_highlight_keywords(str(result.get("text", "")), sentiment)}</div>
        """,
        unsafe_allow_html=True,
    )

    summary_source = str(result.get("summary_source", "rule_based_fallback")).replace("_", " ")
    sentiment_source = str(result.get("sentiment_source", "rule_based_fallback")).replace("_", " ")
    model_name = result.get("sentiment_model_name")
    model_line = f"<br>Sentiment model: {escape(str(model_name))}" if model_name else ""
    st.markdown(
        f"""
        <div class="ri-meta">
            Summary source: {escape(summary_source)}<br>
            Sentiment source: {escape(sentiment_source)}{model_line}
        </div>
        """,
        unsafe_allow_html=True,
    )
    if result.get("fallback_reason"):
        st.caption(f"Fallback reason: {result['fallback_reason']}")
    if result.get("sentiment_fallback_reason"):
        st.caption(f"Sentiment fallback reason: {result['sentiment_fallback_reason']}")


def _highlight_keywords(text: str, sentiment: str | None = None) -> str:
    if not text:
        return "No review text returned."

    evidence = sentiment_evidence(text, sentiment if sentiment in {"positive", "neutral", "negative"} else None)
    if not evidence:
        return escape(text)

    highlighted_parts: list[str] = []
    cursor = 0
    for item in evidence:
        if item.start < cursor:
            continue
        highlighted_parts.append(escape(text[cursor:item.start]))
        highlighted_parts.append(
            f'<mark class="ri-keyword ri-keyword-{item.tone}">{escape(text[item.start:item.end])}</mark>'
        )
        cursor = item.end

    highlighted_parts.append(escape(text[cursor:]))
    return "".join(highlighted_parts)
