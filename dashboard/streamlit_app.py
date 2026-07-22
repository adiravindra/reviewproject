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
    request_import,
    request_import_options,
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
    --ri-card-gap: 16px;
    --ri-section-gap: 36px;
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
    --ri-info: #1d4ed8;
    --ri-info-bg: #eff6ff;
    --ri-info-border: #93c5fd;
}
[data-testid="stToolbar"] { display: none !important; }
.stApp { background: #ffffff; color: var(--ri-navy); }
[data-testid="stHeader"] { background: #ffffff; }
.block-container { max-width: 1240px; padding: 2rem 2.25rem 4rem; }
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
[data-testid="stSidebar"] .stButton > button {
    color: var(--ri-navy) !important;
    background: #ffffff !important;
    border-color: #cbd5e1 !important;
}
[data-testid="stSidebar"] .stButton > button p { color: inherit !important; }
[data-testid="stSidebar"] .stButton > button:hover {
    color: var(--ri-navy) !important;
    background: var(--ri-surface-subtle) !important;
    border-color: #93c5fd !important;
}
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
.ri-report-hero { padding: var(--ri-space-6); margin: var(--ri-space-6) 0 var(--ri-card-gap); }
.ri-report-hero__content { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--ri-space-4); }
.ri-report-hero h2 { font-size: var(--ri-font-section); margin: 0 0 var(--ri-space-2); }
.ri-report-hero p { color: #52637a; line-height: 1.55; margin: 0; overflow-wrap: anywhere; }
.ri-summary-card { padding: var(--ri-space-6); margin: var(--ri-card-gap) 0 0; }
.ri-summary-card h3 { font-size: 1rem; margin: 0 0 var(--ri-space-2); }
.ri-summary-card p { color: #243b5a; line-height: 1.7; margin: 0; max-width: 76ch; }
.ri-chart-card { padding: var(--ri-space-4); min-width: 0; }
.st-key-ri_sentiment_chart_card,
.st-key-ri_rating_chart_card {
    min-width: 0;
    height: 100%;
    border-color: var(--ri-border) !important;
    border-radius: var(--ri-radius-card) !important;
    box-shadow: 0 6px 20px rgba(15, 36, 80, .05);
}
.ri-section-heading {
    display: grid;
    gap: var(--ri-space-1);
    margin: var(--ri-section-gap) 0 var(--ri-space-3);
}
.ri-section-heading__eyebrow {
    color: var(--ri-blue);
    font-size: .75rem;
    font-weight: 800;
    letter-spacing: .09em;
    line-height: 1.2;
    text-transform: uppercase;
}
.ri-section-heading h2 {
    color: var(--ri-navy);
    font-size: var(--ri-font-section);
    letter-spacing: -.025em;
    line-height: 1.25;
    margin: 0;
}
.ri-section-heading p {
    color: #52637a;
    font-size: var(--ri-font-label);
    line-height: 1.55;
    margin: 0;
    max-width: 72ch;
}
.ri-metric-grid,
.ri-insight-grid,
.ri-theme-grid,
.ri-chart-grid {
    display: grid;
    gap: var(--ri-card-gap);
    width: 100%;
}
.ri-metric-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.ri-insight-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.ri-theme-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.ri-theme-grid .ri-card { height: 100%; margin: 0; display: grid; gap: var(--ri-space-2); align-content: start; }
.ri-theme-grid .ri-badge { width: max-content; max-width: 100%; }
.ri-theme-grid .ri-card strong { display: block; line-height: 1.4; }
.ri-theme-grid .ri-card p { margin: 0; }
.ri-chart-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.ri-metric-card,
.ri-insight-panel {
    border: 1px solid var(--ri-border);
    border-radius: var(--ri-radius-card);
    background: var(--ri-surface);
    padding: var(--ri-space-4);
    min-width: 0;
}
.ri-metric-card { min-height: 142px; }
.ri-metric-card.ri-positive,
.ri-metric-card.ri-negative,
.ri-metric-card.ri-neutral,
.ri-metric-card.ri-mixed {
    background: var(--ri-surface);
    border-color: var(--ri-border);
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
.ri-insight-panel li { line-height: 1.6; margin-bottom: var(--ri-space-1); }
.ri-positive { color: var(--ri-positive); background: var(--ri-positive-bg); border-color: var(--ri-positive-border); }
.ri-negative { color: var(--ri-negative); background: var(--ri-negative-bg); border-color: var(--ri-negative-border); }
.ri-neutral { color: var(--ri-neutral); background: var(--ri-neutral-bg); border-color: var(--ri-neutral-border); }
.ri-mixed { color: var(--ri-mixed); background: var(--ri-mixed-bg); border-color: var(--ri-mixed-border); }
.ri-info { color: var(--ri-info); background: var(--ri-info-bg); border-color: var(--ri-info-border); }
@media (max-width: 1100px) {
    .ri-metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .ri-theme-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .ri-insight-grid { grid-template-columns: 1fr; }
}
@media (max-width: 900px) {
    .ri-metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .ri-theme-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .ri-insight-grid { grid-template-columns: 1fr; }
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
    .ri-section-heading { margin-top: var(--ri-space-8); }
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

_REVIEW_SENTIMENT_ORDER = ("positive", "neutral", "negative")
_INFO_VISUAL = SentimentVisual("🎯", "Action", "info", "#1d4ed8", "#eff6ff", "#93c5fd")


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

    labels = {
        "json_ld": "JSON-LD",
        "html_cards": "HTML fallback",
        "provider_api": "Provider API",
        "demo": "Demo data",
    }
    return labels.get(str(extractor), "Unknown extractor")


def source_details(source: dict[str, Any], *, review_count: int) -> list[str]:
    """Build readable provenance for generic, demo, or provider evidence."""

    details: list[str] = []
    if source.get("url"):
        details.append(f"Source: {source['url']}")
    if source.get("extractor") == "provider_api":
        platform = {
            "amazon": "Amazon",
            "google_maps": "Google Maps",
        }.get(str(source.get("platform")), "Imported reviews")
        provider = str(source.get("provider") or "Unknown provider")
        details.append(f"{platform} via {provider}")
        actual = source.get("retrieved_count", review_count)
        requested = source.get("requested_count")
        details.append(
            f"Retrieved {actual} usable written reviews - Requested {requested}"
        )
        if source.get("retrieved_at"):
            details.append(f"Fetched: {format_history_timestamp(source['retrieved_at'])}")
        cache_label = {
            "miss": "Fresh import",
            "hit": "Cached result",
            "refresh": "Explicit refresh",
        }.get(str(source.get("cache_status")))
        if cache_label:
            details.append(cache_label)
    else:
        details.append(f"Extractor: {_extractor_label(source.get('extractor'))}")
        details.append(f"Reviews: {review_count}")
    return details


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
    provider = f" · {item['provider']}" if item.get("provider") else ""
    return f"{created} · {title}{provider} · {sentiment}{demo}"


def analysis_call(
    collection: dict[str, Any], base_url: str, *, request: Callable[[dict[str, Any], str], dict[str, Any]] = request_analysis
) -> dict[str, Any]:
    """Call the staged analysis client with precisely its collection contract."""

    return request(collection, base_url)


def sentiment_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert live sentiment counts into deterministic chart rows."""

    counts = report["metrics"].get("sentiment_counts", {})
    return [
        {"Sentiment": sentiment_visual(name).label, "Reviews": int(counts.get(name, 0))}
        for name in _REVIEW_SENTIMENT_ORDER
    ]


def rating_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert the complete one-to-five distribution into chart rows."""

    distribution = report["metrics"].get("rating_distribution", {})
    return [{"Rating": f"{star} star", "Reviews": int(distribution.get(str(star), 0))} for star in range(1, 6)]


def sentiment_chart_spec(report: dict[str, Any]) -> dict[str, Any]:
    """Build a warning-free sentiment bar spec with explicit semantic colors."""

    domain = [sentiment_visual(name).label for name in _REVIEW_SENTIMENT_ORDER]
    rows = sentiment_rows(report)
    review_domain = [0, max(1, *(row["Reviews"] for row in rows))]
    colors = [_VISUALS[name].foreground for name in _REVIEW_SENTIMENT_ORDER]
    return {
        "data": {"values": rows},
        "mark": {"type": "bar", "cornerRadiusTopLeft": 4, "cornerRadiusTopRight": 4},
        "encoding": {
            "x": {
                "field": "Sentiment",
                "type": "nominal",
                "sort": domain,
                "axis": {"title": None, "labelAngle": 0},
            },
            "y": {
                "field": "Reviews",
                "type": "quantitative",
                "stack": None,
                "scale": {"domain": review_domain, "nice": True},
                "axis": {"title": "Reviews", "tickMinStep": 1},
            },
            "color": {
                "field": "Sentiment",
                "type": "nominal",
                "scale": {"domain": domain, "range": colors},
                "legend": None,
            },
            "tooltip": [
                {"field": "Sentiment", "type": "nominal"},
                {"field": "Reviews", "type": "quantitative"},
            ],
        },
        "width": "container",
        "height": 260,
        "config": {"view": {"stroke": None}},
    }


def rating_chart_spec(report: dict[str, Any]) -> dict[str, Any]:
    """Build a warning-free royal-blue rating-distribution bar spec."""

    rating_order = [f"{star} star" for star in range(1, 6)]
    rows = rating_rows(report)
    review_domain = [0, max(1, *(row["Reviews"] for row in rows))]
    return {
        "data": {"values": rows},
        "mark": {"type": "bar", "cornerRadiusTopLeft": 4, "cornerRadiusTopRight": 4},
        "encoding": {
            "x": {
                "field": "Rating",
                "type": "ordinal",
                "sort": rating_order,
                "axis": {"title": None, "labelAngle": 0},
            },
            "y": {
                "field": "Reviews",
                "type": "quantitative",
                "stack": None,
                "scale": {"domain": review_domain, "nice": True},
                "axis": {"title": "Reviews", "tickMinStep": 1},
            },
            "color": {"value": "#2563eb"},
            "tooltip": [
                {"field": "Rating", "type": "ordinal"},
                {"field": "Reviews", "type": "quantitative"},
            ],
        },
        "width": "container",
        "height": 260,
        "config": {"view": {"stroke": None}},
    }


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


def safe_section_heading_markup(eyebrow: Any, heading: Any, description: Any) -> str:
    """Build one escaped heading block for a major report section."""

    return (
        '<header class="ri-section-heading">'
        f'<span class="ri-section-heading__eyebrow">{html.escape(str(eyebrow))}</span>'
        f"<h2>{html.escape(str(heading))}</h2>"
        f"<p>{html.escape(str(description))}</p>"
        "</header>"
    )


def safe_panel_markup(visual: SentimentVisual, heading: Any, items: list[Any]) -> str:
    """Build one escaped semantic insight panel and its unordered list."""

    safe_visual = _INFO_VISUAL if visual.semantic == "info" else sentiment_visual(visual.semantic)
    safe_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in items)
    return (
        f'<section class="ri-insight-panel ri-{safe_visual.semantic}">'
        f"<h3>{html.escape(str(safe_visual.icon))} {html.escape(str(heading))}</h3>"
        f"<ul>{safe_items}</ul>"
        "</section>"
    )


def _configure_page() -> None:
    """Apply page metadata and the concise responsive token system."""

    st.set_page_config(
        page_title="Review Intelligence",
        page_icon="💬",
        layout="wide",
        initial_sidebar_state="auto",
    )
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
    details = source_details(source, review_count=len(collection.get("reviews", [])))
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

    st.markdown(
        safe_section_heading_markup(
            "Theme analysis",
            "Recurring themes",
            "See which product experiences appear repeatedly and how customers feel about them.",
        ),
        unsafe_allow_html=True,
    )
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
    report_source_details = source_details(source, review_count=len(report_reviews))
    safe_source_title = html.escape(str(source.get("title", "Review analysis")))
    safe_source_details = " · ".join(
        html.escape(str(detail)) for detail in report_source_details
    )
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

    st.markdown(
        safe_section_heading_markup(
            "Review patterns",
            "Customer signals",
            "Compare sentiment and rating patterns across the analyzed review set.",
        ),
        unsafe_allow_html=True,
    )
    chart_columns = st.columns(2)
    with chart_columns[0]:
        with st.container(border=True, key="ri_sentiment_chart_card"):
            st.subheader("Sentiment mix")
            st.vega_lite_chart(spec=sentiment_chart_spec(report), width="stretch", theme=None)
    with chart_columns[1]:
        with st.container(border=True, key="ri_rating_chart_card"):
            st.subheader("Rating distribution")
            st.vega_lite_chart(spec=rating_chart_spec(report), width="stretch", theme=None)

    _render_themes(list(insights.get("themes", [])))
    strengths = list(insights.get("strengths", [])) or ["No strengths were returned."]
    concerns = list(insights.get("weaknesses", [])) or ["No concerns were returned."]
    actions = list(insights.get("actions", [])) or ["No recommended actions were returned."]
    st.markdown(
        safe_section_heading_markup(
            "Actionable insights",
            "Customer priorities",
            "Turn the strongest customer signals into focused product decisions.",
        ),
        unsafe_allow_html=True,
    )
    insight_panels = "".join(
        (
            safe_panel_markup(_VISUALS["positive"], "Strengths", strengths),
            safe_panel_markup(_VISUALS["negative"], "Concerns", concerns),
            safe_panel_markup(_INFO_VISUAL, "Recommended actions", actions),
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


def _new_collection(base_url: str) -> None:
    """Load explicit demo data and replace prior state only after success."""

    if not check_health(base_url):
        _unavailable()
        return
    try:
        with st.spinner("Loading bundled demo reviews…"):
            collection = request_demo(base_url)
        st.session_state["collection"] = collection
        st.session_state.pop("latest_report", None)
    except BackendUnavailable:
        _unavailable()
    except ApiClientError as exc:
        st.error(exc.message)


def _import_collection(
    base_url: str,
    platform: str,
    url: str,
    limit: int,
    *,
    refresh: bool,
) -> None:
    """Import or refresh once while preserving the last good state on failure."""

    if not check_health(base_url):
        _unavailable()
        return
    try:
        label = "Refreshing reviews from source…" if refresh else "Importing normalized reviews…"
        with st.spinner(label):
            collection = request_import(platform, url, limit, refresh, base_url)
        st.session_state["collection"] = collection
        st.session_state.pop("latest_report", None)
    except BackendUnavailable:
        _unavailable()
    except ApiClientError as exc:
        st.error(exc.message)


def _load_import_options(base_url: str) -> None:
    """Load provider-neutral source choices without triggering a scrape."""

    if not check_health(base_url):
        _unavailable()
        return
    try:
        st.session_state["import_options"] = request_import_options(base_url)
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
    """Coordinate staged import, deliberate demo use, analysis, and history loading."""

    _configure_page()
    base_url = os.getenv("REVIEWINSIGHT_API_URL", "http://127.0.0.1:8000")
    _render_history(base_url)

    st.title("Review Intelligence")
    st.caption("Import normalized public reviews, inspect the evidence, then analyze customer signals with Groq.")
    if (
        "import_options" not in st.session_state
        and "collection" not in st.session_state
        and "latest_report" not in st.session_state
    ):
        _load_import_options(base_url)
    platforms = st.session_state.get("import_options", {}).get("platforms", [])
    imported = False
    demo_selected = False
    selected_platform: dict[str, Any] | None = None
    url = ""
    limit = 5
    with st.form("review-import-form"):
        if platforms:
            selected_index = st.selectbox(
                "Review source",
                range(len(platforms)),
                format_func=lambda index: str(platforms[index].get("label", "Review source")),
            )
            selected_platform = platforms[int(selected_index)]
            platform_key = str(selected_platform.get("key", "amazon"))
            url_label = "Amazon product URL" if platform_key == "amazon" else "Google Maps place URL"
            placeholder = (
                "https://www.amazon.com/dp/B000000000"
                if platform_key == "amazon"
                else "https://www.google.com/maps/place/..."
            )
            url = st.text_input(url_label, placeholder=placeholder)
            limits = [int(value) for value in selected_platform.get("limits", [5])]
            limit = int(st.selectbox("Review limit", limits, index=min(1, len(limits) - 1)))
        else:
            st.info("Import choices are unavailable until the backend is reachable.")
        action_columns = st.columns(2)
        with action_columns[0]:
            imported = st.form_submit_button(
                "Import reviews",
                type="primary",
                width="stretch",
                disabled=not bool(platforms),
            )
        with action_columns[1]:
            demo_selected = st.form_submit_button("Use bundled demo data", width="stretch")
    if imported and selected_platform is not None:
        _import_collection(
            base_url,
            str(selected_platform["key"]),
            url.strip(),
            limit,
            refresh=False,
        )
    if demo_selected:
        _new_collection(base_url)

    st.subheader("How it works")
    st.markdown(
        """
        <section class="ri-process-strip">
            <div class="ri-process-step"><span class="ri-process-step__number">1</span>
                <div><strong>Import</strong><p>Retrieve a small cached review set from the selected source.</p></div>
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
            if source.get("extractor") == "provider_api":
                st.caption(
                    "Refresh from source contacts the provider and may consume provider free-tier usage."
                )
                if st.button("Refresh from source", width="stretch"):
                    _import_collection(
                        base_url,
                        str(source.get("platform", "")),
                        str(source.get("url", "")),
                        int(source.get("requested_count", len(collection.get("reviews", [])))),
                        refresh=True,
                    )
            if report is None and st.button("Analyze with Groq", type="primary", width="stretch"):
                if not check_health(base_url):
                    _unavailable()
                else:
                    try:
                        with st.spinner("Analyzing normalized review evidence…"):
                            st.session_state["latest_report"] = analysis_call(collection, base_url)
                        _load_history(base_url)
                        st.rerun()
                    except BackendUnavailable:
                        _unavailable()
                    except ApiClientError as exc:
                        st.error(exc.message)
    if isinstance(st.session_state.get("latest_report"), dict) and isinstance(st.session_state.get("collection"), dict):
        _render_report(st.session_state["latest_report"], st.session_state["collection"])


if __name__ == "__main__":
    main()
