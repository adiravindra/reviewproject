"""Render Review Intelligence with Positive ✅, Negative ⚠️, Neutral ➖, and Mixed ↔ states."""

import html
import os
from dataclasses import dataclass
from datetime import datetime
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
    --ri-blue-hover: #1d4ed8;
    --ri-navy: #0f2450;
    --ri-sidebar: #102437;
    --ri-slate: #64748b;
    --ri-border: #dbe4f0;
    --ri-surface: #ffffff;
    --ri-surface-subtle: #f8fafc;
    --ri-shadow-surface: 0 12px 32px rgba(15, 36, 80, .08);
    --ri-radius-control: 10px;
    --ri-radius-card: 14px;
    --ri-radius-surface: 18px;
    --ri-space-1: 4px;
    --ri-space-2: 8px;
    --ri-space-3: 12px;
    --ri-space-4: 16px;
    --ri-space-6: 24px;
    --ri-space-8: 32px;
    --ri-space-12: 48px;
    --ri-font-body: 1rem;
    --ri-font-label: .875rem;
    --ri-font-section: clamp(1.375rem, 2.4vw, 1.75rem);
    --ri-font-value: clamp(1.75rem, 3vw, 2.125rem);
    --ri-positive: #15803d;
    --ri-positive-bg: #f0fdf4;
    --ri-positive-border: #86efac;
    --ri-negative: #b91c1c;
    --ri-negative-bg: #fef2f2;
    --ri-negative-border: #fca5a5;
    --ri-neutral: #a16207;
    --ri-neutral-bg: #fffbeb;
    --ri-neutral-border: #fcd34d;
    --ri-mixed: #4f46e5;
    --ri-mixed-bg: #eef2ff;
    --ri-mixed-border: #a5b4fc;
}
[data-testid="stToolbar"] { display: none !important; }
.stApp { background: #ffffff; color: var(--ri-navy); }
[data-testid="stHeader"] { background: #ffffff; }
.block-container { max-width: 1200px; padding: 2rem 2.25rem 4rem; }
h1, h2, h3, p, label, [data-testid="stMetricLabel"] { color: var(--ri-navy); }
h1 { font-size: clamp(2rem, 4vw, 3rem); letter-spacing: -0.04em; font-weight: 750; }
h2 { letter-spacing: -0.025em; margin-top: 1.4rem; }
[data-testid="stCaptionContainer"] { color: var(--ri-slate); }
[data-testid="stSidebar"] { background: var(--ri-sidebar); border-right: 1px solid var(--ri-border); }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #ffffff; }
[data-testid="stSidebar"] .block-container { padding: 1.25rem .85rem; }
[data-testid="stForm"] { border: 1px solid var(--ri-border); border-radius: 16px; padding: 1.25rem; }
div[data-testid="stTextInput"] input { border-color: #cbd5e1; border-radius: 12px; }
.stButton > button, [data-testid="stFormSubmitButton"] > button {
    border-radius: 12px; border-color: var(--ri-blue); font-weight: 700;
}
[data-testid="stBaseButton-primaryFormSubmit"],
.stButton > button[kind="primary"] { background: #2563eb !important; color: #ffffff !important; }
[data-testid="stBaseButton-primaryFormSubmit"]:hover,
.stButton > button[kind="primary"]:hover { background: var(--ri-blue-hover) !important; }
button:focus-visible, input:focus-visible, [role="button"]:focus-visible {
    outline: 3px solid #93c5fd !important; outline-offset: 2px !important;
}
[data-testid="stMetric"] { border: 1px solid var(--ri-border); border-radius: 14px; padding: .9rem 1rem; background: #ffffff; }
[data-testid="stMetricValue"] { color: var(--ri-navy); letter-spacing: -0.025em; }
[data-testid="stDataFrame"] { border: 1px solid var(--ri-border); border-radius: 12px; overflow: hidden; }
.ri-badge { display: inline-block; padding: .28rem .55rem; border-radius: 999px; border: 1px solid; font-weight: 700; font-size: .88rem; }
.ri-card { border: 1px solid var(--ri-border); border-radius: 14px; padding: .9rem 1rem; margin: .45rem 0; background: #ffffff; }
.ri-process-strip {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--ri-space-4);
    border: 1px solid var(--ri-border);
    border-radius: var(--ri-radius-card);
    padding: var(--ri-space-4);
    margin: var(--ri-space-4) 0 var(--ri-space-6);
}
.ri-process-step { display: flex; align-items: flex-start; gap: var(--ri-space-3); min-width: 0; }
.ri-process-step__number {
    display: grid;
    place-items: center;
    flex: 0 0 2rem;
    width: 2rem;
    height: 2rem;
    border-radius: 999px;
    color: var(--ri-blue);
    background: #eff6ff;
    font-weight: 750;
}
.ri-process-step strong { display: block; color: var(--ri-navy); margin-bottom: var(--ri-space-1); }
.ri-process-step p { color: var(--ri-slate); font-size: var(--ri-font-label); line-height: 1.55; margin: 0; }
.ri-report-hero,
.ri-summary-card,
.ri-chart-card {
    border: 1px solid var(--ri-border);
    border-radius: var(--ri-radius-surface);
    background: var(--ri-surface);
    box-shadow: var(--ri-shadow-surface);
}
.ri-report-hero { padding: var(--ri-space-6); margin: var(--ri-space-4) 0; }
.ri-report-hero__content { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--ri-space-4); }
.ri-report-hero h2 { font-size: var(--ri-font-section); margin: 0 0 var(--ri-space-2); }
.ri-report-hero p { color: var(--ri-slate); line-height: 1.55; margin: 0; overflow-wrap: anywhere; }
.ri-summary-card { padding: var(--ri-space-4); margin: var(--ri-space-4) 0; }
.ri-summary-card h3 { font-size: 1rem; margin: 0 0 var(--ri-space-2); }
.ri-summary-card p { color: var(--ri-navy); line-height: 1.65; margin: 0; }
.ri-chart-card { padding: var(--ri-space-4); min-width: 0; }
.st-key-ri_sentiment_chart_card,
.st-key-ri_rating_chart_card { min-width: 0; }
.ri-metric-grid,
.ri-insight-grid,
.ri-theme-grid,
.ri-chart-grid {
    display: grid;
    gap: var(--ri-space-4);
    width: 100%;
}
.ri-metric-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.ri-insight-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.ri-theme-grid { grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }
.ri-theme-grid .ri-card { height: 100%; margin: 0; }
.ri-chart-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.ri-metric-card,
.ri-insight-panel {
    border: 1px solid var(--ri-border);
    border-radius: var(--ri-radius-card);
    background: var(--ri-surface);
    padding: var(--ri-space-4);
    min-width: 0;
}
.ri-metric-card__label {
    color: var(--ri-navy);
    font-size: var(--ri-font-label);
    font-weight: 700;
}
.ri-metric-card__value {
    color: currentColor;
    font-size: var(--ri-font-value);
    font-weight: 750;
    letter-spacing: -.025em;
    line-height: 1.2;
    margin: var(--ri-space-2) 0 var(--ri-space-1);
}
.ri-metric-card__detail {
    color: var(--ri-slate);
    font-size: var(--ri-font-label);
    line-height: 1.55;
}
.ri-insight-panel h3 {
    color: currentColor;
    font-size: 1rem;
    margin: 0 0 var(--ri-space-2);
}
.ri-insight-panel ul { margin: 0; padding-left: 1.25rem; }
.ri-insight-panel li { line-height: 1.6; }
.ri-positive { color: var(--ri-positive); background: var(--ri-positive-bg); border-color: var(--ri-positive-border); }
.ri-negative { color: var(--ri-negative); background: var(--ri-negative-bg); border-color: var(--ri-negative-border); }
.ri-neutral { color: var(--ri-neutral); background: var(--ri-neutral-bg); border-color: var(--ri-neutral-border); }
.ri-mixed { color: var(--ri-mixed); background: var(--ri-mixed-bg); border-color: var(--ri-mixed-border); }
@media (max-width: 900px) {
    .ri-metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .ri-chart-grid { grid-template-columns: 1fr; }
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: .7rem; }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }
}
@media (max-width: 640px) {
    .block-container { padding: 1.35rem 1rem 3rem; }
    [data-testid="stForm"] { padding: 1rem; }
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: .7rem; }
    [data-testid="stSidebar"] { border-right: 0; }
    .ri-report-hero,
    .ri-summary-card,
    .ri-chart-card,
    .ri-metric-card,
    .ri-insight-panel { border-radius: var(--ri-radius-card); }
    .ri-report-hero { padding: var(--ri-space-4); }
    .ri-report-hero__content { flex-direction: column; }
    .ri-process-strip { grid-template-columns: 1fr; }
    .ri-insight-grid,
    .ri-theme-grid { grid-template-columns: 1fr; }
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


def format_history_timestamp(value: Any) -> str:
    """Format stored ISO timestamps to seconds without timezone suffixes."""

    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    return parsed.replace(microsecond=0, tzinfo=None).isoformat(sep=" ", timespec="seconds")


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

    created = format_history_timestamp(item.get("created_at", "Unknown time"))
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


def safe_metric_card_markup(label: Any, value: Any, detail: Any, semantic: str) -> str:
    """Build one escaped metric card with a known semantic color treatment."""

    visual = sentiment_visual(semantic)
    return (
        f'<section class="ri-metric-card ri-{visual.semantic}">'
        f'<div class="ri-metric-card__label">{html.escape(str(label))}</div>'
        f'<div class="ri-metric-card__value">{html.escape(str(value))}</div>'
        f'<div class="ri-metric-card__detail">{html.escape(str(detail))}</div>'
        "</section>"
    )


def safe_panel_markup(visual: SentimentVisual, heading: Any, items: list[Any]) -> str:
    """Build one escaped semantic insight panel and its unordered list."""

    safe_visual = sentiment_visual(visual.semantic)
    safe_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in items)
    return (
        f'<section class="ri-insight-panel ri-{safe_visual.semantic}">'
        f"<h3>{html.escape(str(safe_visual.icon))} {html.escape(str(heading))}</h3>"
        f"<ul>{safe_items}</ul>"
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
    """Render the collected source and its provenance as one concise summary."""

    source = collection.get("source", {})
    st.subheader(str(source.get("title", "Extracted reviews")))
    details = [f"Extractor: {_extractor_label(source.get('extractor'))}", f"Reviews: {len(collection.get('reviews', []))}"]
    if source.get("url"):
        details.insert(0, f"Source: {source['url']}")
    st.caption(" · ".join(details))


def _render_evidence(
    collection: dict[str, Any], report: dict[str, Any] | None = None, *, compact: bool = False
) -> None:
    """Render normalized evidence prominently or in a compact report duplicate."""

    if not compact:
        st.subheader("Review evidence")
        st.caption("Inspect the normalized public reviews before starting analysis.")
    rows = review_rows(collection, report)
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch", height=320 if compact else 520)
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
    """Render escaped semantic theme cards in the responsive report grid."""

    st.subheader("Recurring themes")
    if not themes:
        st.info("No recurring themes were returned.")
        return
    cards = []
    for theme in themes:
        visual = sentiment_visual(str(theme.get("sentiment", "neutral")))
        title = str(theme.get("name", "Unnamed theme"))
        description = str(theme.get("description", ""))
        mentions = theme.get("mentions", 0)
        cards.append(safe_theme_card_markup(visual, title, description, mentions))
    st.markdown(f'<section class="ri-theme-grid">{"".join(cards)}</section>', unsafe_allow_html=True)


def _render_report(report: dict[str, Any], collection: dict[str, Any]) -> None:
    """Render the analysis report in the approved evidence-first scan order."""

    source = report.get("source", collection.get("source", {}))
    if source.get("is_demo") is True:
        _demo_notice()

    insights = report.get("insights", {})
    overall = sentiment_visual(str(insights.get("overall_sentiment", "neutral")))
    report_reviews = report.get("reviews", collection.get("reviews", []))
    evidence_collection = {"source": source, "reviews": report_reviews}
    source_details = [
        f"Extractor: {_extractor_label(source.get('extractor'))}",
        f"Reviews: {len(report_reviews)}",
    ]
    if source.get("url"):
        source_details.insert(0, f"Source: {source['url']}")
    safe_source_title = html.escape(str(source.get("title", "Review analysis")))
    safe_source_details = " · ".join(html.escape(str(detail)) for detail in source_details)
    st.markdown(
        '<section class="ri-report-hero"><div class="ri-report-hero__content">'
        f"<div><h2>{safe_source_title}</h2><p>{safe_source_details}</p></div>"
        f'{safe_badge_markup(overall, overall.label)}</div></section>',
        unsafe_allow_html=True,
    )

    values = metric_values(report)
    metric_specs = (
        ("Reviews analyzed", values[0], "Normalized evidence", "mixed"),
        ("Average rating", values[1], "Rated on a five-point scale", "neutral"),
        ("Positive share", values[2], "Share of analyzed reviews", "positive"),
        ("Overall sentiment", values[3], "Customer signal", overall.semantic),
    )
    metric_cards = "".join(safe_metric_card_markup(*spec) for spec in metric_specs)
    st.markdown(f'<section class="ri-metric-grid">{metric_cards}</section>', unsafe_allow_html=True)

    summary = html.escape(str(insights.get("summary", "No summary was returned.")))
    st.markdown(
        '<section class="ri-summary-card"><h3>Executive summary</h3>'
        f"<p>{summary}</p></section>",
        unsafe_allow_html=True,
    )

    st.subheader("Customer signals")
    chart_columns = st.columns(2)
    with chart_columns[0]:
        with st.container(border=True, key="ri_sentiment_chart_card"):
            st.subheader("Sentiment mix")
            st.bar_chart(sentiment_rows(report), x="Sentiment", y="Reviews")
    with chart_columns[1]:
        with st.container(border=True, key="ri_rating_chart_card"):
            st.subheader("Rating distribution")
            st.bar_chart(rating_rows(report), x="Rating", y="Reviews")

    _render_themes(list(insights.get("themes", [])))
    strengths = list(insights.get("strengths", [])) or ["No strengths were returned."]
    concerns = list(insights.get("weaknesses", [])) or ["No concerns were returned."]
    actions = list(insights.get("actions", [])) or ["No recommended actions were returned."]
    insight_panels = "".join(
        (
            safe_panel_markup(_VISUALS["positive"], "Strengths", strengths),
            safe_panel_markup(_VISUALS["negative"], "Concerns", concerns),
            safe_panel_markup(_VISUALS["mixed"], "Recommended actions", actions),
        )
    )
    st.markdown(f'<section class="ri-insight-grid">{insight_panels}</section>', unsafe_allow_html=True)

    with st.expander("Supporting review evidence", expanded=False):
        _render_source(evidence_collection)
        _render_evidence(evidence_collection, report, compact=True)


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
        st.caption("Refresh and reopen a saved analysis report.")
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
        action_columns = st.columns(2)
        with action_columns[0]:
            extracted = st.form_submit_button("Extract reviews", type="primary", width="stretch")
        with action_columns[1]:
            demo_selected = st.form_submit_button("Use bundled demo data", width="stretch")
    if extracted:
        _new_collection(base_url, url.strip())
    if demo_selected:
        _new_collection(base_url)

    st.subheader("How it works")
    st.markdown(
        """
        <section class="ri-process-strip">
            <div class="ri-process-step"><span class="ri-process-step__number">1</span>
                <div><strong>Extract</strong><p>Collect normalized public reviews from the product page.</p></div>
            </div>
            <div class="ri-process-step"><span class="ri-process-step__number">2</span>
                <div><strong>Review evidence</strong><p>Inspect the source and normalized review text.</p></div>
            </div>
            <div class="ri-process-step"><span class="ri-process-step__number">3</span>
                <div><strong>Analyze</strong><p>Generate sentiment, themes, and recommended actions.</p></div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    collection = st.session_state.get("collection")
    report = st.session_state.get("latest_report")
    if isinstance(collection, dict) and not isinstance(report, dict):
        with st.container(border=True, key="ri_evidence_workspace"):
            source = collection.get("source", {})
            if source.get("is_demo") is True:
                _demo_notice()
            _render_source(collection)
            _render_evidence(collection)
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
