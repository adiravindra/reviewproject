# Simple Review Insights MVP Design

**Date:** July 13, 2026  
**Status:** Proposed for implementation after user review

## Goal

Build a maintainable proof of concept that accepts one public review-page URL, collects reviews with ordinary HTTP requests, analyzes them with one LangChain agent backed by Gemini or Groq, and displays the result in a clean Streamlit dashboard.

The MVP preserves a lightweight FastAPI–Streamlit boundary so backend capabilities can grow later. It deliberately removes persistence, history, browser automation, background work, and the custom multi-call analysis machinery from the active implementation.

## Success Criteria

1. A user can submit a supported public URL in Streamlit and receive a complete report through FastAPI.
2. The collector extracts at least two reviews from a committed HTML fixture and the documented public sample page when that external page is reachable and unchanged.
3. One LangChain `create_agent` call returns validated structured insights using either Gemini or Groq.
4. The response includes a summary, overall sentiment, recurring themes, strengths, weaknesses, actions, review-level sentiment, deterministic metrics, and source metadata.
5. The dashboard presents four key metrics, sentiment and rating charts, the insight sections, and a review sample without requiring a second page.
6. Backend and frontend start independently with explicit commands; no project launcher spawns child processes.
7. Automated tests validate collection, analysis, orchestration, API behavior, and dashboard formatting without live websites or model calls.

## Architecture

```text
Browser
  -> Streamlit :8501
  -> POST FastAPI :8000/api/analyze
       -> collect_reviews(url)
            -> bounded static HTTP request
            -> JSON-LD extraction
            -> conservative HTML-card fallback
            -> normalize, deduplicate, cap
       -> analyze_reviews(reviews, provider)
            -> Gemini or Groq chat model
            -> one LangChain agent invocation
            -> validated structured response
       -> calculate_metrics(reviews, sentiments)
       -> AnalysisResponse
```

FastAPI owns input validation, collection, model calls, deterministic calculations, and public error mapping. Streamlit owns form state, progress, API calls, charts, and presentation. The frontend never imports backend application services.

## Active Files and Ownership

- `backend/app/main.py`: FastAPI construction, `GET /health`, and `POST /api/analyze`.
- `backend/app/models.py`: request, review, insight, metric, response, and error schemas.
- `backend/app/collector.py`: URL safety, bounded HTTP retrieval, JSON-LD and HTML extraction, normalization, and deduplication.
- `backend/app/analyzer.py`: provider factory, prompt construction, LangChain agent creation, invocation, and structured-output validation.
- `backend/app/service.py`: synchronous collection → analysis → metrics orchestration.
- `dashboard/streamlit_app.py`: the complete one-page dashboard.
- `dashboard/api_client.py`: health and analysis HTTP calls plus user-safe client errors.
- `tests/`: focused unit, API, pipeline, and dashboard-helper tests plus static HTML fixtures.

Obsolete routers, scraper registries, database/history code, multi-batch analysis code, history UI, and their tests will be removed only after replacement tests pass.

## HTTP API

### `GET /health`

Returns immediately without scraping or calling a model:

```json
{"status": "ok"}
```

Streamlit uses this endpoint to distinguish “backend is not running” from collection or model failures.

### `POST /api/analyze`

Request:

```json
{
  "url": "https://web-scraping.dev/product/1",
  "provider": "google"
}
```

`provider` is `google` or `groq`. Provider model names remain environment-configurable.

Successful response:

```json
{
  "source": {
    "url": "https://web-scraping.dev/product/1",
    "title": "Box of Chocolate Candy",
    "extractor": "json_ld"
  },
  "metrics": {
    "review_count": 5,
    "rated_count": 5,
    "average_rating": 4.2,
    "positive_percentage": 60.0,
    "sentiment_counts": {"positive": 3, "neutral": 1, "negative": 1},
    "rating_distribution": {"1": 0, "2": 1, "3": 0, "4": 1, "5": 3}
  },
  "insights": {
    "summary": "...",
    "overall_sentiment": "positive",
    "themes": [{"name": "Taste", "description": "...", "mentions": 4}],
    "strengths": ["..."],
    "weaknesses": ["..."],
    "actions": ["..."],
    "review_sentiments": [{"review_id": "r1", "sentiment": "positive"}]
  },
  "reviews": []
}
```

Errors use one small envelope:

```json
{
  "detail": {
    "code": "collection_failed",
    "message": "The page could not be read. Try another public review page."
  }
}
```

The public codes are `invalid_url`, `collection_failed`, `no_reviews`, `missing_api_key`, and `analysis_failed`. Raw provider responses, API keys, stack traces, and internal network details are never returned.

## Review Collection

The first version supports one public HTML page. It does not paginate and does not run JavaScript.

Collection rules:

- Accept only `http` and `https` URLs without embedded credentials.
- Resolve the hostname and reject loopback, private, link-local, reserved, multicast, and unspecified addresses.
- Follow at most three redirects, revalidating each target before requesting it.
- Use explicit connection/read timeouts, a descriptive user agent, an HTML content-type check, and a 1 MiB response ceiling.
- Attempt JSON-LD/Schema.org review extraction first.
- Fall back to conservative review-card selectors such as `[itemprop="review"]`, `.review`, `.review-card`, and `[data-review-id]`; require a review-body element rather than promoting arbitrary paragraphs.
- Normalize whitespace, keep original review wording, normalize valid ratings to 1–5, remove exact case-insensitive duplicates, and stop after 40 unique reviews.
- Require at least two valid reviews. Low sample sizes remain visible through the review-count metric rather than triggering extra workflow branches.

The supported demonstration URL is `https://web-scraping.dev/product/1`. Live compatibility is checked manually and is not part of the deterministic test suite.

## LangChain Analysis

The analysis layer uses `langchain.agents.create_agent` with an empty tool list and a Pydantic structured-response schema. LangChain documents that an empty tool list produces a single model node, while `response_format` returns the validated value in `structured_response`. This satisfies the agent requirement without introducing unnecessary tool loops.

One request sends at most 40 compact review records containing only ID, text, rating, and date. Authors and source metadata are not included in the model prompt.

The agent returns:

- A concise overall summary.
- `positive`, `neutral`, `negative`, or `mixed` overall sentiment.
- Three to six recurring themes with descriptions and approximate mention counts.
- Up to five strengths, weaknesses, and actionable recommendations.
- Exactly one sentiment label for every submitted review ID.

The service rejects a structured response with missing, duplicate, or unknown review IDs. There is no custom retry loop, batching layer, persistence, memory, tracing service, or local heuristic fallback.

Providers:

- Google: `ChatGoogleGenerativeAI`, `GOOGLE_API_KEY`, model controlled by `REVIEWINSIGHT_GOOGLE_MODEL`.
- Groq: `ChatGroq`, `GROQ_API_KEY`, model controlled by `REVIEWINSIGHT_GROQ_MODEL`.

Both official LangChain integrations advertise tool calling and structured output. Free-tier availability and quotas are controlled by the provider account and are not guaranteed by the application.

References:

- [LangChain agents](https://docs.langchain.com/oss/python/langchain/agents)
- [LangChain structured output](https://docs.langchain.com/oss/python/langchain/structured-output)
- [Gemini integration](https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai)
- [Groq integration](https://docs.langchain.com/oss/python/integrations/chat/groq)

## Deterministic Metrics

Python calculates all counts and chart values from collected reviews and the validated review-level sentiment labels:

- Review and rated-review counts.
- Average rating rounded to one decimal, or `null` when no ratings exist.
- Positive percentage over all analyzed reviews.
- Positive, neutral, and negative counts.
- One-through-five rating distribution.

The model does not calculate these values.

## Dashboard

The Streamlit page contains:

1. A restrained header and one-sentence explanation.
2. A URL field, provider selector, and primary “Analyze reviews” button.
3. A backend-unavailable message that includes the exact backend start command.
4. Four metrics: reviews analyzed, average rating, positive share, and overall sentiment.
5. Side-by-side sentiment and rating bar charts.
6. A full-width summary.
7. Recurring themes in a simple table/list.
8. Strengths and weaknesses in two columns.
9. Actionable recommendations.
10. An expandable sample of collected reviews.

The UI uses Streamlit primitives and a small CSS token block. It does not add navigation, history, authentication, fake loading stages, decorative illustrations, or a custom frontend build system.

## Reliability and Previous Connection Failure

The preserved July 10 browser-QA logs show that FastAPI and Streamlit both started successfully and returned OpenAPI responses; they do not contain an application exception. During the July 13 investigation, Codex repeatedly reproduced Windows `CreateProcessAsUserW` error 1312 through the WindowsApps `pwsh.exe` execution path, while the system PowerShell executable succeeded. The old `scripts/run_app.py` also starts two child processes and blocks on them, adding process-lifecycle and localhost timing failure modes.

The MVP addresses the controllable causes:

- Delete the subprocess launcher from the active workflow.
- Document two explicit terminal commands using the existing virtual environment.
- Start Streamlit headlessly on `127.0.0.1:8501` and FastAPI on `127.0.0.1:8000`.
- Add `/health` and make the frontend check it with a short timeout before analysis.
- Give the analysis request a longer timeout than the backend’s model timeout so backend errors reach the dashboard.
- Use the system PowerShell executable for Codex-driven Windows verification when shell spawning is needed.
- Use Codex’s in-app browser against the already-running Streamlit URL; do not make the application launch or control a browser.

This does not claim to fix Codex’s external Windows logon-session state. It removes application-owned subprocess and browser lifecycle dependencies and turns remaining backend availability problems into explicit UI errors.

## Testing and Incremental Delivery

Implementation proceeds in independently verifiable stages:

1. Replace contracts and collection behind fixture tests.
2. Add deterministic metrics and orchestration tests.
3. Add the fake-agent contract, then the real Gemini/Groq agent factory.
4. Expose `/health` and `/api/analyze` with FastAPI dependency overrides in API tests.
5. Replace the Streamlit/API-client surface and verify formatting helpers.
6. Remove inactive implementation files and update setup documentation.
7. Run the full automated suite, compile checks, backend health check, Streamlit health check, in-app browser desktop/mobile verification, and an optional real-provider test when credentials exist.

No stage depends on a live site or paid model call to pass automated verification.

## Explicit Non-Goals

- Universal website support or anti-bot bypasses.
- Browser rendering, Selenium, Playwright, or browser extension control.
- Pagination, authenticated review pages, or JavaScript-only reviews.
- Public marketplace API discovery in the first version. A documented provider API can later be added behind `collect_reviews` without changing API or dashboard contracts.
- Database persistence, history, user accounts, background workers, queues, containers, or cloud infrastructure.
- Production-grade rate limiting, observability, or distributed deployment.

