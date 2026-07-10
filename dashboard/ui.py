from html import escape
from typing import Any

import altair as alt
import streamlit as st

from dashboard.api_client import ApiClientError, DEFAULT_API_BASE_URL


_SENTIMENT_COLORS = {
    "Positive": "#12a66a",
    "Neutral": "#d9900b",
    "Negative": "#e55353",
}


def configure_page(page_title: str) -> None:
    st.set_page_config(
        page_title=f"ReviewInsight | {page_title}",
        page_icon="RI",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(_STYLES, unsafe_allow_html=True)


def render_nav(active_page: str) -> None:
    analysis_class = "ri-nav-active" if active_page == "Analysis" else ""
    history_class = "ri-nav-active" if active_page == "History" else ""
    st.markdown(
        f"""
        <nav class="ri-nav">
          <a class="ri-brand" href="/" target="_self"><span class="ri-mark">RI</span>ReviewInsight</a>
          <div class="ri-nav-links">
            <a class="{analysis_class}" href="/" target="_self">Analysis</a>
            <a class="{history_class}" href="/History" target="_self">History</a>
          </div>
        </nav>
        """,
        unsafe_allow_html=True,
    )


def backend_url_input() -> str:
    with st.expander("Backend connection", expanded=False):
        return st.text_input(
            "FastAPI backend URL",
            value=st.session_state.get("api_base_url", DEFAULT_API_BASE_URL),
            help="The local runner uses http://127.0.0.1:8000.",
        )


def render_page_intro(title: str, description: str) -> None:
    st.markdown(
        f"""
        <section class="ri-intro">
          <h1>{escape(title)}</h1>
          <p>{escape(description)}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_error(error: Exception) -> None:
    if isinstance(error, ApiClientError):
        st.error(error.message)
        retry = " You can retry this request." if error.retryable else ""
        st.caption(f"Stage: {error.stage} · Error: {error.code}.{retry}")
        return
    st.error("The interface could not render this request safely.")


def dashboard_metrics(result: dict[str, Any]) -> dict[str, str]:
    collection = _mapping(result.get("collection"))
    metrics = _mapping(result.get("metrics"))
    average = metrics.get("average_rating")
    return {
        "Reviews": f"{int(collection.get('analyzed', 0))} analyzed / {int(collection.get('found', 0))} found",
        "Average rating": "Not rated" if average is None else f"{_number(average)} / 5",
        "Rated reviews": str(int(metrics.get("rated_reviews", 0))),
        "Overall sentiment": str(metrics.get("overall_sentiment", "mixed")).title(),
    }


def rating_chart_data(result: dict[str, Any]) -> list[dict[str, Any]]:
    distribution = _mapping(_mapping(result.get("metrics")).get("rating_distribution"))
    return [
        {
            "Rating": f"{star} star" if star == 1 else f"{star} stars",
            "Reviews": int(distribution.get(str(star), 0)),
        }
        for star in range(1, 6)
    ]


def sentiment_chart_data(result: dict[str, Any]) -> list[dict[str, Any]]:
    counts = _mapping(_mapping(result.get("metrics")).get("sentiment_counts"))
    return [
        {"Sentiment": sentiment.title(), "Reviews": int(counts.get(sentiment, 0))}
        for sentiment in ("positive", "neutral", "negative")
    ]


def history_rows(history: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, str]]:
    raw_items = history.get("items", []) if isinstance(history, dict) else history
    items = raw_items if isinstance(raw_items, list) else []
    rows: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        average = item.get("average_rating")
        rows.append(
            {
                "ID": str(item.get("id", "")),
                "Completed": str(item.get("completed_at", "")),
                "Source": str(item.get("entity_name") or item.get("source_url", "Unknown source")),
                "URL": str(item.get("source_url", "")),
                "Reviews": str(int(item.get("review_count", 0))),
                "Average rating": "Not rated" if average is None else _number(average),
                "Sentiment": str(item.get("overall_sentiment", "mixed")).title(),
                "Summary": str(item.get("executive_summary", "")),
                "Provider": str(item.get("provider", "")),
                "Model": str(item.get("model", "")),
            }
        )
    return rows


def render_website_report(result: dict[str, Any], *, show_heading: bool = True) -> None:
    source = _mapping(result.get("source"))
    collection = _mapping(result.get("collection"))
    analysis = _mapping(result.get("analysis"))
    if show_heading:
        st.markdown('<div class="ri-section-title">Completed intelligence report</div>', unsafe_allow_html=True)

    source_name = str(source.get("entity_name") or source.get("page_title") or "Review source")
    source_url = str(source.get("canonical_url") or source.get("requested_url") or "")
    st.markdown(
        f"""
        <section class="ri-source-strip">
          <div><strong>{escape(source_name)}</strong><a href="{escape(source_url)}" target="_blank">{escape(source_url)}</a></div>
          <dl>
            <div><dt>Entity</dt><dd>{escape(str(source.get('entity_type') or 'Website'))}</dd></div>
            <div><dt>Scraper</dt><dd>{escape(str(source.get('scraper_name') or 'static'))}</dd></div>
            <div><dt>Pages</dt><dd>{int(source.get('pages_succeeded', 0))} / {int(source.get('pages_attempted', 0))}</dd></div>
            <div><dt>Completed</dt><dd>{escape(str(analysis.get('completed_at') or ''))}</dd></div>
          </dl>
        </section>
        """,
        unsafe_allow_html=True,
    )

    for warning in collection.get("warnings", []):
        st.warning(str(warning))

    metric_values = dashboard_metrics(result)
    metric_columns = st.columns(4)
    for column, (label, value) in zip(metric_columns, metric_values.items()):
        column.metric(label, value)

    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.markdown("#### Rating distribution")
        rating_chart = (
            alt.Chart(alt.Data(values=rating_chart_data(result)))
            .mark_bar(cornerRadiusEnd=5, color="#1769e0")
            .encode(
                x=alt.X("Reviews:Q", title="Reviews", axis=alt.Axis(tickMinStep=1)),
                y=alt.Y(
                    "Rating:N",
                    sort=["5 stars", "4 stars", "3 stars", "2 stars", "1 star"],
                    title=None,
                ),
                tooltip=["Rating:N", "Reviews:Q"],
            )
            .properties(height=260)
        )
        st.altair_chart(rating_chart, width="stretch")
    with chart_right:
        st.markdown("#### Sentiment distribution")
        sentiment_data = sentiment_chart_data(result)
        sentiment_chart = (
            alt.Chart(alt.Data(values=sentiment_data))
            .mark_arc(innerRadius=60, outerRadius=105)
            .encode(
                theta=alt.Theta("Reviews:Q", stack=True),
                color=alt.Color(
                    "Sentiment:N",
                    scale=alt.Scale(
                        domain=list(_SENTIMENT_COLORS),
                        range=list(_SENTIMENT_COLORS.values()),
                    ),
                    legend=alt.Legend(orient="right", title=None),
                ),
                tooltip=["Sentiment:N", "Reviews:Q"],
            )
            .properties(height=260)
        )
        st.altair_chart(sentiment_chart, width="stretch")

    insights = _mapping(result.get("insights"))
    st.markdown(
        f"""
        <section class="ri-summary-band">
          <h3>Executive summary</h3>
          <p>{escape(str(insights.get('executive_summary') or 'No executive summary was returned.'))}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    strength_col, complaint_col, aspect_col = st.columns(3)
    with strength_col:
        _render_evidence("Positive themes", insights.get("strengths"), "positive")
    with complaint_col:
        _render_evidence("Recurring complaints", insights.get("complaints"), "negative")
    with aspect_col:
        _render_evidence("Important aspects", insights.get("aspects"), "accent")

    _render_opportunities(insights.get("opportunities"))
    _render_representatives(insights.get("representative_reviews"))
    _render_review_collection(result.get("reviews"))

    with st.expander("Raw JSON response", expanded=False):
        st.json(result)
    with st.expander("Analysis details", expanded=False):
        st.write(
            {
                "provider": analysis.get("provider"),
                "model": analysis.get("model"),
                "batch_count": analysis.get("batch_count"),
                "llm_call_count": analysis.get("llm_call_count"),
            }
        )


def _render_evidence(title: str, raw_items: Any, tone: str) -> None:
    items = raw_items if isinstance(raw_items, list) else []
    content = []
    for item in items:
        data = _mapping(item)
        support_count = len(data.get("review_ids", [])) if isinstance(data.get("review_ids"), list) else 0
        content.append(
            f"<li><strong>{escape(str(data.get('label', 'Insight')))}</strong>"
            f"<span>{escape(str(data.get('summary', '')))}</span>"
            f"<small>{support_count} supporting review{'s' if support_count != 1 else ''}</small></li>"
        )
    empty = "<li><span>No items returned.</span></li>" if not content else ""
    st.markdown(
        f'<section class="ri-insight ri-{tone}"><h3>{escape(title)}</h3><ul>{"".join(content)}{empty}</ul></section>',
        unsafe_allow_html=True,
    )


def _render_opportunities(raw_items: Any) -> None:
    items = raw_items if isinstance(raw_items, list) else []
    rows = []
    for index, item in enumerate(items, start=1):
        data = _mapping(item)
        rows.append(
            f"<li><span>{index}</span><div><strong>{escape(str(data.get('label', 'Opportunity')))}</strong>"
            f"<p>{escape(str(data.get('summary', '')))}</p></div></li>"
        )
    st.markdown(
        f'<section class="ri-opportunities"><h3>Prioritized improvement opportunities</h3><ol>{"".join(rows)}</ol></section>',
        unsafe_allow_html=True,
    )


def _render_representatives(raw_items: Any) -> None:
    items = raw_items if isinstance(raw_items, list) else []
    if not items:
        return
    st.markdown("#### Representative reviews")
    columns = st.columns(min(3, len(items)))
    for index, item in enumerate(items):
        data = _mapping(item)
        sentiment = str(data.get("sentiment", "neutral")).casefold()
        metadata = [
            f"Rating: {_number(data['rating'])}/5" if data.get("rating") is not None else None,
            str(data.get("publication_date")) if data.get("publication_date") else None,
        ]
        columns[index % len(columns)].markdown(
            f"""
            <article class="ri-quote ri-quote-{escape(sentiment)}">
              <div>{escape(sentiment.title())}</div>
              <blockquote>{escape(str(data.get('text', '')))}</blockquote>
              <small>{escape(' · '.join(value for value in metadata if value))}</small>
            </article>
            """,
            unsafe_allow_html=True,
        )


def _render_review_collection(raw_items: Any) -> None:
    reviews = raw_items if isinstance(raw_items, list) else []
    with st.expander(f"Normalized review collection ({len(reviews)} reviews)", expanded=False):
        for item in reviews:
            data = _mapping(item)
            metadata = [
                f"Rating {_number(data['rating'])}/5" if data.get("rating") is not None else "Unrated",
                f"Author {data['author']}" if data.get("author") else None,
                str(data.get("publication_date")) if data.get("publication_date") else None,
            ]
            st.markdown(f"> {escape(str(data.get('text', '')))}")
            st.caption(" · ".join(value for value in metadata if value))


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number(value: Any) -> str:
    number = float(value)
    return str(int(number)) if number.is_integer() else f"{number:.2f}".rstrip("0").rstrip(".")


_STYLES = """
<style>
:root {--navy:#071a45;--blue:#1769e0;--muted:#60708d;--border:#dce4ef;--positive:#12895b;--negative:#d93f4c;--amber:#a86100;}
[data-testid="stAppViewContainer"] {background:#fff;color:var(--navy);}
[data-testid="stHeader"] {background:rgba(255,255,255,.96);}
[data-testid="stMainBlockContainer"] {max-width:1240px;padding-top:1.5rem;padding-bottom:4rem;}
.ri-nav {align-items:center;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;margin-bottom:2.5rem;padding:0 0 .85rem;}
.ri-brand {align-items:center;color:var(--navy)!important;display:flex;font-size:1.15rem;font-weight:800;gap:.65rem;text-decoration:none!important;}
.ri-mark {align-items:center;background:var(--blue);border-radius:50%;color:#fff;display:inline-flex;font-size:.58rem;height:1.7rem;justify-content:center;letter-spacing:.04em;width:1.7rem;}
.ri-nav-links {display:flex;gap:2rem;}.ri-nav-links a {border-bottom:2px solid transparent;color:#52617c!important;font-size:.93rem;font-weight:650;padding:.55rem .1rem;text-decoration:none!important;}
.ri-nav-links a.ri-nav-active {border-color:var(--blue);color:var(--blue)!important;}
.ri-intro {margin-bottom:1.4rem}.ri-intro h1 {color:var(--navy);font-size:clamp(2rem,4vw,3.1rem);letter-spacing:-.045em;line-height:1.05;margin:0 0 .8rem;}.ri-intro p {color:#52617c;font-size:1.02rem;line-height:1.65;margin:0;max-width:860px;}
[data-testid="stForm"] {border:1px solid var(--border);border-radius:12px;box-shadow:0 14px 34px rgba(15,35,75,.08);padding:1.25rem 1.35rem 1.05rem;}
.stButton button,.stFormSubmitButton button {border-radius:8px;font-size:.94rem;font-weight:750;min-height:2.8rem;}
.ri-section-title {color:var(--navy);font-size:1.15rem;font-weight:800;margin:2.2rem 0 .8rem;}
.ri-source-strip {align-items:center;border:1px solid var(--border);border-radius:10px;display:flex;gap:2rem;justify-content:space-between;margin:1rem 0;padding:1rem 1.15rem;}
.ri-source-strip>div {min-width:240px}.ri-source-strip strong {display:block;font-size:1.03rem}.ri-source-strip a {color:var(--blue)!important;display:block;font-size:.78rem;margin-top:.2rem;max-width:330px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.ri-source-strip dl {display:flex;gap:2rem;margin:0}.ri-source-strip dl div {min-width:76px}.ri-source-strip dt {color:var(--muted);font-size:.68rem;font-weight:750;text-transform:uppercase}.ri-source-strip dd {font-size:.82rem;font-weight:650;margin:.25rem 0 0;}
[data-testid="stMetric"] {border:1px solid var(--border);border-radius:10px;min-height:130px;padding:1rem 1.1rem;}[data-testid="stMetricLabel"] {color:#52617c;font-weight:700;}[data-testid="stMetricValue"] {color:var(--navy);font-size:1.85rem;font-weight:800;}
.ri-summary-band {background:#f7faff;border:1px solid #bfd3fa;border-radius:10px;margin:1rem 0;padding:1.15rem 1.3rem}.ri-summary-band h3,.ri-insight h3,.ri-opportunities h3 {font-size:.98rem;margin:0 0 .7rem}.ri-summary-band p {line-height:1.7;margin:0;}
.ri-insight {border:1px solid var(--border);border-radius:10px;min-height:250px;padding:1.05rem}.ri-insight h3 {border-left:3px solid var(--blue);padding-left:.55rem}.ri-positive h3 {border-color:var(--positive)}.ri-negative h3 {border-color:var(--negative)}
.ri-insight ul {list-style:none;margin:0;padding:0}.ri-insight li {border-top:1px solid #edf1f6;padding:.7rem 0}.ri-insight li:first-child {border-top:0}.ri-insight strong,.ri-insight span,.ri-insight small {display:block}.ri-insight span {color:#52617c;font-size:.84rem;line-height:1.45;margin:.2rem 0}.ri-insight small {color:#8490a3;font-size:.7rem}
.ri-opportunities {border:1px solid var(--border);border-radius:10px;margin:1rem 0;padding:1.1rem}.ri-opportunities ol {list-style:none;margin:0;padding:0}.ri-opportunities li {align-items:flex-start;border-top:1px solid #edf1f6;display:flex;gap:.85rem;padding:.75rem 0}.ri-opportunities li>span {align-items:center;background:#eaf1ff;border-radius:50%;color:var(--blue);display:flex;font-size:.75rem;font-weight:800;height:1.6rem;justify-content:center;min-width:1.6rem}.ri-opportunities p {color:#52617c;font-size:.84rem;margin:.2rem 0 0}
.ri-quote {border:1px solid var(--border);border-radius:10px;min-height:190px;padding:1.1rem}.ri-quote>div {font-size:.72rem;font-weight:850;text-transform:uppercase}.ri-quote blockquote {font-size:.94rem;line-height:1.65;margin:.7rem 0}.ri-quote small {color:var(--muted)}.ri-quote-positive {background:#f5fcf8;border-color:#bce7d2}.ri-quote-positive>div {color:var(--positive)}.ri-quote-negative {background:#fff7f7;border-color:#f3c7cc}.ri-quote-negative>div {color:var(--negative)}.ri-quote-neutral {background:#fffbf2;border-color:#f0d9ab}.ri-quote-neutral>div {color:var(--amber)}
@media(max-width:800px){[data-testid="stMainBlockContainer"]{padding-left:1rem;padding-right:1rem}.ri-nav{align-items:flex-start;gap:1rem}.ri-nav-links{gap:1rem}.ri-source-strip{align-items:flex-start;flex-direction:column}.ri-source-strip dl{display:grid;grid-template-columns:1fr 1fr;gap:1rem}.ri-intro h1{font-size:2rem}}
</style>
"""
