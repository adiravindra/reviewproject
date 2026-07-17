"""Render Review Intelligence with Positive ✅, Negative ⚠️, Neutral ➖, and Mixed ↔ states."""

import html
import os
from dataclasses import dataclass
from typing import Any, Callable

import streamlit as st

from dashboard.api_client import (
    ApiClientError,
    BackendUnavailable,
    check_health,
    request_analysis,
    request_collection,
    request_demo,
    request_history,
    request_history_report,
)


APP_COMMAND = r".\.venv\Scripts\python.exe run_app.py"

DASHBOARD_CSS = """
:root {
    --ri-blue: #2563eb;
    --ri-navy: #0f1f4a;
    --ri-slate: #475569;
    --ri-border: #dbe3ef;
    --ri-positive: #15803d;
    --ri-positive-bg: #f0fdf4;
    --ri-negative: #b91c1c;
    --ri-negative-bg: #fef2f2;
    --ri-neutral: #a16207;
    --ri-neutral-bg: #fffbeb;
    --ri-mixed: #4f46e5;
    --ri-mixed-bg: #eef2ff;
}
[data-testid="stToolbar"] { display: none !important; }
.stApp { background: #ffffff; color: var(--ri-navy); }
[data-testid="stHeader"] { background: #ffffff; }
.block-container { max-width: 1200px; padding: 2rem 2.25rem 4rem; }
h1, h2, h3, p, label, [data-testid="stMetricLabel"] { color: var(--ri-navy); }
h1 { font-size: clamp(2rem, 4vw, 3rem); letter-spacing: -0.04em; font-weight: 750; }
h2 { letter-spacing: -0.025em; margin-top: 1.4rem; }
[data-testid="stCaptionContainer"] { color: var(--ri-slate); }
[data-testid="stSidebar"] { background: #f8fafc; border-right: 1px solid var(--ri-border); }
[data-testid="stSidebar"] .block-container { padding: 1.25rem .85rem; }
[data-testid="stForm"] { border: 1px solid var(--ri-border); border-radius: 16px; padding: 1.25rem; }
div[data-testid="stTextInput"] input { border-color: #cbd5e1; border-radius: 12px; }
.stButton > button, [data-testid="stFormSubmitButton"] > button {
    border-radius: 12px; border-color: var(--ri-blue); font-weight: 700;
}
[data-testid="stBaseButton-primaryFormSubmit"],
.stButton > button[kind="primary"] { background: #2563eb !important; color: #ffffff !important; }
[data-testid="stBaseButton-primaryFormSubmit"]:hover,
.stButton > button[kind="primary"]:hover { background: #1d4ed8 !important; }
button:focus-visible, input:focus-visible, [role="button"]:focus-visible {
    outline: 3px solid #93c5fd !important; outline-offset: 2px !important;
}
[data-testid="stMetric"] { border: 1px solid var(--ri-border); border-radius: 14px; padding: .9rem 1rem; background: #ffffff; }
[data-testid="stMetricValue"] { color: var(--ri-navy); letter-spacing: -0.025em; }
[data-testid="stDataFrame"] { border: 1px solid var(--ri-border); border-radius: 12px; overflow: hidden; }
.ri-badge { display: inline-block; padding: .28rem .55rem; border-radius: 999px; border: 1px solid; font-weight: 700; font-size: .88rem; }
.ri-card { border: 1px solid var(--ri-border); border-radius: 14px; padding: .9rem 1rem; margin: .45rem 0; background: #ffffff; }
.ri-positive { color: var(--ri-positive); background: var(--ri-positive-bg); border-color: #86efac; }
.ri-negative { color: var(--ri-negative); background: var(--ri-negative-bg); border-color: #fca5a5; }
.ri-neutral { color: var(--ri-neutral); background: var(--ri-neutral-bg); border-color: #fcd34d; }
.ri-mixed { color: var(--ri-mixed); background: var(--ri-mixed-bg); border-color: #a5b4fc; }
@media (max-width: 700px) {
    .block-container { padding: 1.35rem 1rem 3rem; }
    [data-testid="stForm"] { padding: 1rem; }
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: .7rem; }
    [data-testid="stSidebar"] { border-right: 0; }
}
"""


@dataclass(frozen=True)
class SentimentVisual:
    """Describe one accessible visual treatment for a sentiment category."""

    icon: str
    label: str
    semantic: str
    foreground: str
    background: str
    border: str


_VISUALS = {
    "positive": SentimentVisual("✅", "Positive", "positive", "#15803d", "#f0fdf4", "#86efac"),
    "negative": SentimentVisual("⚠️", "Negative", "negative", "#b91c1c", "#fef2f2", "#fca5a5"),
    "neutral": SentimentVisual("➖", "Neutral", "neutral", "#a16207", "#fffbeb", "#fcd34d"),
    "mixed": SentimentVisual("↔", "Mixed", "mixed", "#4f46e5", "#eef2ff", "#a5b4fc"),
}


def metric_values(report: dict[str, Any]) -> tuple[str, str, str, str]:
    """Format live report headline metrics without Streamlit state."""

    metrics = report["metrics"]
    average = metrics.get("average_rating")
    average_label = "Not rated" if average is None else f"{float(average):.1f} / 5"
    return (
        str(metrics.get("review_count", 0)),
        average_label,
        f'{float(metrics.get("positive_percentage", 0)):.1f}%',
        sentiment_visual(str(report.get("insights", {}).get("overall_sentiment", "neutral"))).label,
    )


def sentiment_visual(sentiment: str) -> SentimentVisual:
    """Return a safe, labeled visual for a known sentiment or neutral fallback."""

    return _VISUALS.get(str(sentiment).strip().lower(), _VISUALS["neutral"])


def _extractor_label(extractor: Any) -> str:
    """Turn known extractor identifiers into reader-friendly provenance text."""

    labels = {"json_ld": "JSON-LD", "html_cards": "HTML fallback", "demo": "Demo data"}
    return labels.get(str(extractor), "Unknown extractor")


def review_rows(collection: dict[str, Any], report: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Preserve review evidence order and add exact analysis labels only when supplied."""

    source = collection.get("source", {})
    extractor = _extractor_label(source.get("extractor"))
    joined: dict[Any, str] = {}
    if report is not None:
        for item in report.get("insights", {}).get("review_sentiments", []):
            if isinstance(item, dict) and "review_id" in item:
                joined[item["review_id"]] = str(item.get("sentiment", "neutral"))

    rows = []
    for review in collection.get("reviews", []):
        if not isinstance(review, dict):
            continue
        row = {
            "Review": str(review.get("text", "")),
            "Rating": review.get("rating"),
            "Date": review.get("date") or "—",
            "Extractor": extractor,
        }
        if report is not None and review.get("id") in joined:
            visual = sentiment_visual(joined[review["id"]])
            row["Sentiment"] = f"{visual.icon} {visual.label}"
            row["Sentiment semantic"] = visual.semantic
        rows.append(row)
    return rows


def history_option(item: dict[str, Any]) -> str:
    """Create a readable provenance label for one history entry."""

    created = str(item.get("created_at", "Unknown time")).replace("T", " ").replace("Z", "")
    title = str(item.get("source_title", item.get("source", "Untitled source")))
    sentiment = sentiment_visual(str(item.get("overall_sentiment", "neutral"))).label
    demo = " · 🧪 DEMO DATA" if item.get("is_demo") is True else ""
    return f"{created} · {title} · {sentiment}{demo}"


def analysis_call(
    collection: dict[str, Any], base_url: str, *, request: Callable[[dict[str, Any], str], dict[str, Any]] = request_analysis
) -> dict[str, Any]:
    """Call the staged analysis client with precisely its collection contract."""

    return request(collection, base_url)


def sentiment_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert live sentiment counts into deterministic chart rows."""

    counts = report["metrics"].get("sentiment_counts", {})
    return [{"Sentiment": sentiment_visual(name).label, "Reviews": int(counts.get(name, 0))} for name in _VISUALS]


def rating_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert the complete one-to-five distribution into chart rows."""

    distribution = report["metrics"].get("rating_distribution", {})
    return [{"Rating": f"{star} star", "Reviews": int(distribution.get(str(star), 0))} for star in range(1, 6)]


def safe_badge_markup(visual: SentimentVisual, label: str) -> str:
    """Build a compact semantic badge while escaping all supplied text."""

    return (
        f'<span class="ri-badge ri-{visual.semantic}" style="color:{visual.foreground};'
        f'background:{visual.background};border-color:{visual.border}">{visual.icon} {html.escape(label)}</span>'
    )


def safe_theme_card_markup(visual: SentimentVisual, name: str, description: str, mentions: Any) -> str:
    """Build one escaped semantic theme card from live analysis content."""

    safe_visual = sentiment_visual(visual.semantic)
    return (
        f'<section class="ri-card ri-{safe_visual.semantic}" style="color:{safe_visual.foreground};'
        f'background:{safe_visual.background};border-color:{safe_visual.border}">'
        f'<span class="ri-badge ri-{safe_visual.semantic}">{safe_visual.icon} '
        f'{html.escape(safe_visual.label)}</span>'
        f'<strong>{html.escape(name)}</strong>'
        f'<p>{html.escape(description)}</p>'
        f'<small>{html.escape(str(mentions))} mentions</small>'
        "</section>"
    )


def _configure_page() -> None:
    """Apply page metadata and the concise responsive token system."""

    st.set_page_config(page_title="Review Intelligence", page_icon="💬", layout="wide")
    st.markdown(f"<style>{DASHBOARD_CSS}</style>", unsafe_allow_html=True)


def _unavailable() -> None:
    """Show recovery guidance without exposing transport diagnostics."""

    st.error("The complete application is not reachable. Start or restart it with:")
    st.code(APP_COMMAND, language="powershell")


def _demo_notice() -> None:
    """Keep bundled demo provenance prominent at each relevant stage."""

    st.warning("🧪 DEMO DATA — You are viewing bundled demo data, not a live collection.")


def _render_source(collection: dict[str, Any]) -> None:
    """Render source provenance using normal Streamlit text widgets."""

    source = collection.get("source", {})
    st.subheader(str(source.get("title", "Extracted reviews")))
    details = [f"Extractor: {_extractor_label(source.get('extractor'))}", f"Reviews: {len(collection.get('reviews', []))}"]
    if source.get("url"):
        details.insert(0, f"Source: {source['url']}")
    st.caption(" · ".join(details))


def _render_evidence(collection: dict[str, Any], report: dict[str, Any] | None = None) -> None:
    """Render readable normalized review evidence before and after analysis."""

    st.header("Extracted reviews (evidence)")
    rows = review_rows(collection, report)
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.info("No normalized reviews are available yet.")


def _render_list(items: list[Any]) -> None:
    """Render an insight list without interpolating untrusted HTML."""

    if not items:
        st.write("—")
        return
    for item in items:
        st.write(f"• {item}")


def _render_themes(themes: list[dict[str, Any]]) -> None:
    """Render theme cards with each live theme's semantic treatment."""

    st.header("Recurring themes")
    if not themes:
        st.info("No recurring themes were returned.")
        return
    for theme in themes:
        visual = sentiment_visual(str(theme.get("sentiment", "neutral")))
        title = str(theme.get("name", "Unnamed theme"))
        description = str(theme.get("description", ""))
        mentions = theme.get("mentions", 0)
        st.markdown(safe_theme_card_markup(visual, title, description, mentions), unsafe_allow_html=True)


def _render_report(report: dict[str, Any], collection: dict[str, Any]) -> None:
    """Render live report metrics, findings, charts, provenance, and review labels."""

    source = report.get("source", collection.get("source", {}))
    if source.get("is_demo") is True:
        _demo_notice()

    st.header("Analysis results")
    values = metric_values(report)
    for column, label, value in zip(st.columns(4), ("Reviews analyzed", "Average rating", "Positive share", "Overall sentiment"), values):
        column.metric(label, value)

    overall = sentiment_visual(str(report.get("insights", {}).get("overall_sentiment", "neutral")))
    st.markdown(safe_badge_markup(overall, f"Overall sentiment: {overall.label}"), unsafe_allow_html=True)
    st.write(str(report.get("insights", {}).get("summary", "No summary was returned.")))

    chart_columns = st.columns(2)
    with chart_columns[0]:
        st.subheader("Sentiment mix")
        st.bar_chart(sentiment_rows(report), x="Sentiment", y="Reviews")
    with chart_columns[1]:
        st.subheader("Rating distribution")
        st.bar_chart(rating_rows(report), x="Rating", y="Reviews")

    insights = report.get("insights", {})
    _render_themes(list(insights.get("themes", [])))
    finding_columns = st.columns(2)
    with finding_columns[0]:
        st.markdown(safe_badge_markup(_VISUALS["positive"], "Strengths"), unsafe_allow_html=True)
        _render_list(list(insights.get("strengths", [])))
    with finding_columns[1]:
        st.markdown(safe_badge_markup(_VISUALS["negative"], "Complaints"), unsafe_allow_html=True)
        _render_list(list(insights.get("weaknesses", [])))
    st.info("Recommended actions")
    _render_list(list(insights.get("actions", [])))

    _render_source({"source": source, "reviews": report.get("reviews", collection.get("reviews", []))})
    _render_evidence({"source": source, "reviews": report.get("reviews", collection.get("reviews", []))}, report)


def _load_history(base_url: str) -> None:
    """Refresh sidebar entries after checking that the backend is reachable."""

    if not check_health(base_url):
        _unavailable()
        return
    try:
        st.session_state["history_items"] = request_history(base_url)
    except BackendUnavailable:
        _unavailable()
    except ApiClientError as exc:
        st.error(exc.message)


def _new_collection(base_url: str, url: str | None = None) -> None:
    """Run an explicit extraction or demo request and retain state only on success."""

    st.session_state.pop("collection", None)
    st.session_state.pop("latest_report", None)
    if not check_health(base_url):
        _unavailable()
        return
    try:
        with st.spinner("Extracting normalized public reviews…"):
            collection = request_collection(url, base_url) if url is not None else request_demo(base_url)
        st.session_state["collection"] = collection
    except BackendUnavailable:
        _unavailable()
    except ApiClientError as exc:
        st.error(exc.message)


def _render_history(base_url: str) -> None:
    """Render explicit history refresh and selected-report loading controls."""

    with st.sidebar:
        st.header("History")
        if st.button("Refresh history", width="stretch"):
            _load_history(base_url)
        items = st.session_state.get("history_items", [])
        if not items:
            st.caption("No saved analyses yet. Refresh history after analyzing reviews.")
            return
        labels = [history_option(item) for item in items]
        selected = st.selectbox("Saved analyses", range(len(items)), format_func=lambda index: labels[index])
        if st.button("Load selected report", width="stretch"):
            if not check_health(base_url):
                _unavailable()
                return
            try:
                report = request_history_report(int(items[selected]["id"]), base_url)
                st.session_state["latest_report"] = report
                st.session_state["collection"] = {"source": report.get("source", {}), "reviews": report.get("reviews", [])}
            except BackendUnavailable:
                _unavailable()
            except ApiClientError as exc:
                st.error(exc.message)


def main() -> None:
    """Coordinate staged extraction, deliberate demo use, analysis, and history loading."""

    _configure_page()
    base_url = os.getenv("REVIEWINSIGHT_API_URL", "http://127.0.0.1:8000")
    _render_history(base_url)

    st.title("Review Intelligence")
    st.caption("Extract normalized public reviews, inspect the evidence, then analyze customer signals with Groq.")
    with st.form("review-extraction-form"):
        url = st.text_input("Review page URL", placeholder="https://example.com/product")
        extracted = st.form_submit_button("Extract reviews", type="primary", width="stretch")
    if extracted:
        _new_collection(base_url, url.strip())
    if st.button("Use bundled demo data", width="stretch"):
        _new_collection(base_url)

    collection = st.session_state.get("collection")
    report = st.session_state.get("latest_report")
    if isinstance(collection, dict) and not isinstance(report, dict):
        source = collection.get("source", {})
        if source.get("is_demo") is True:
            _demo_notice()
        _render_source(collection)
        _render_evidence(collection, report if isinstance(report, dict) else None)
        if report is None and st.button("Analyze with Groq", type="primary", width="stretch"):
            if not check_health(base_url):
                _unavailable()
            else:
                try:
                    with st.spinner("Analyzing normalized review evidence…"):
                        st.session_state["latest_report"] = analysis_call(collection, base_url)
                    _load_history(base_url)
                except BackendUnavailable:
                    _unavailable()
                except ApiClientError as exc:
                    st.error(exc.message)
    if isinstance(st.session_state.get("latest_report"), dict) and isinstance(st.session_state.get("collection"), dict):
        _render_report(st.session_state["latest_report"], st.session_state["collection"])


if __name__ == "__main__":
    main()
