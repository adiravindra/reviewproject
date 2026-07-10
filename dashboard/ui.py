from html import escape
from typing import Any

import streamlit as st

from dashboard.api_client import DEFAULT_API_BASE_URL


def configure_page(page_title: str) -> None:
    st.set_page_config(page_title=f"ReviewInsight | {page_title}", page_icon="RI", layout="wide")
    st.markdown(
        """
        <style>
        .ri-hero {background:#0f172a;border-radius:18px;color:white;padding:28px;margin-bottom:22px}
        .ri-hero h1 {margin:0 0 8px}.ri-hero p {color:#cbd5e1;margin:0}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_nav(active_page: str) -> None:
    st.caption(f"ReviewInsight / {active_page}")


def backend_url_input() -> str:
    with st.expander("Backend connection", expanded=False):
        return st.text_input(
            "FastAPI backend URL",
            value=st.session_state.get("api_base_url", DEFAULT_API_BASE_URL),
        )


def render_page_intro(title: str, description: str) -> None:
    st.markdown(
        f'<section class="ri-hero"><h1>{escape(title)}</h1><p>{escape(description)}</p></section>',
        unsafe_allow_html=True,
    )


def render_error(error: Exception) -> None:
    st.error(str(error))


def render_website_report(result: dict[str, Any]) -> None:
    st.subheader("Website review intelligence")
    st.json(result)


def history_rows(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "Timestamp": str(item.get("completed_at", "")),
            "Source": str(item.get("entity_name") or item.get("source_url", "")),
            "Reviews": str(item.get("review_count", 0)),
            "Sentiment": str(item.get("overall_sentiment", "mixed")).title(),
            "Summary": str(item.get("executive_summary", "")),
        }
        for item in items
    ]
