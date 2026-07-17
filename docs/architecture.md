# Review Intelligence Architecture

## Runtime topology

The MVP keeps the existing two-process local architecture. `run_app.py` is the only supervisor: it loads the repository-root `.env` without replacing values already present in the parent environment, starts both services with the current Python interpreter, waits for Streamlit readiness, and opens the local dashboard once in the operating system's default browser.

```text
run_app.py
  ├── Uvicorn / FastAPI       127.0.0.1:8000
  └── Streamlit dashboard     127.0.0.1:8501

Google Chrome or another local browser
  └── Streamlit HTTP client
        └── FastAPI JSON API
              ├── static collector
              ├── Groq analysis boundary
              └── SQLite history store
```

The supervisor launches both children from the project root without a shell. It stops a surviving peer when either child exits, cleans up both on `Ctrl+C`, and forces shutdown only after the bounded graceful timeout. A browser-open failure is nonfatal and prints the manual dashboard URL.

## Staged data flow

The dashboard never imports backend services directly. Streamlit and FastAPI share validated JSON contracts over local HTTP.

```text
1. User submits a public URL
   Streamlit -> POST /api/collect -> static collector
   Streamlit <- CollectionResult (source + normalized reviews)

2. User inspects the evidence
   Streamlit renders extractor, ratings, dates, and review text

3. User explicitly starts analysis
   Streamlit -> POST /api/analyze (the exact displayed collection)
   FastAPI -> validate GROQ_API_KEY
   FastAPI -> one structured Groq analysis
   FastAPI -> deterministic metrics -> SQLite save
   Streamlit <- AnalysisResponse with history_id

4. User navigates saved reports
   Streamlit -> GET /api/history or GET /api/history/{run_id}
```

`GET /api/demo` is a separate, deliberate path that loads the bundled local collection. It does not run after a live collection error, and its `is_demo` metadata keeps `🧪 DEMO DATA` visible throughout the dashboard.

## Groq boundary

`GROQ_API_KEY` is the sole AI credential. The key comes from the inherited environment or repository-root `.env`; values already present in the shell or system environment take precedence because dotenv loading uses `override=False`. The Streamlit UI has no key entry field.

Before analysis, FastAPI calls Groq's non-generative model-list endpoint with a bearer authorization header. A blank key maps to `missing_api_key`; rejected credentials map to `invalid_api_key`; transport, rate-limit, or other validation failures map to `groq_unavailable`. No collection or model invocation starts after validation fails.

`backend.app.analyzer.build_model()` uses `langchain_groq.ChatGroq` only. The default model is `llama-3.3-70b-versatile`; `REVIEWINSIGHT_GROQ_MODEL` is an optional local override. The agent is invoked once with normalized review ID, text, rating, and date values and must return a schema-validated response with one sentiment for every review ID.

Only application-owned codes and messages cross FastAPI's public boundary. Credential values, authorization headers, raw model output, upstream response bodies, exception text, and stack traces are not returned to Streamlit.

## Collection boundary

The collector accepts public `http` and `https` URLs without embedded credentials. It validates the initial destination and every manually followed redirect, permits at most three redirects, uses bounded request timeouts, reads no more than 1 MiB of HTML, and caps normalized output at 40 reviews.

Extraction is intentionally static:

1. Schema.org-style JSON-LD is inspected first.
2. Conservative review-card and review-body markup is considered only when JSON-LD does not yield usable reviews.
3. Review text is normalized and deduplicated. At least two unique reviews are required.

The collector does not execute JavaScript, log in, paginate, automate a browser, or bypass access controls. Stable error codes distinguish invalid URLs, blocked sites, timeouts, malformed review-like JSON-LD, missing reviews, and generic safe collection failures.

## Report and presentation boundary

Metrics are calculated in Python from validated review-level sentiments and ratings. The dashboard renders the extracted review evidence before analysis and uses text-plus-icon treatments so color is not the only cue:

- `✅ Positive` is styled in green for strengths and favorable themes.
- `⚠️ Negative` is styled in red for complaints and unfavorable themes.
- `➖ Neutral` uses amber, and `↔ Mixed` uses a distinct indigo treatment.

Untrusted source titles, themes, and review text are escaped before being included in styled markup. The dashboard uses Streamlit containers, metric cards, tables, charts, and sidebar controls without storing or displaying any credential.

## Local history

FastAPI owns history through the standard-library `sqlite3` implementation in `backend.app.history.HistoryStore`. Its default path is `data/review_history.db`.

Each successful report is serialized as validated JSON and saved atomically with a compact summary row: timestamp, source metadata, demo flag, review count, and overall sentiment. The history list returns newest-first summaries; a single report can be retrieved by its integer ID. Database, filesystem, and malformed-record errors become the safe `history_failed` code. The `data/` directory is ignored by Git, so saved reports remain local.

## Endpoint contract

| Method and path | Input | Output | Side effects |
|---|---|---|---|
| `GET /health` | none | `{"status":"ok"}` | none |
| `POST /api/collect` | public URL | `CollectionResult` | static HTTP only |
| `GET /api/demo` | none | labeled demo `CollectionResult` | reads bundled JSON only |
| `POST /api/analyze` | validated source and 2–40 reviews | `AnalysisResponse` | Groq validation, one analysis, SQLite save |
| `GET /api/history` | none | history summary list | SQLite read |
| `GET /api/history/{run_id}` | integer ID | saved report or 404 | SQLite read |

## Ownership

- `run_app.py` — project environment loading, process supervision, readiness polling, and browser-open attempt.
- `backend/app/collector.py` — URL safety, bounded static retrieval, JSON-LD-first extraction, fallback markup, and normalization.
- `backend/app/credentials.py` — Groq key lookup and safe pre-analysis validation.
- `backend/app/analyzer.py` — one structured Groq invocation and result validation.
- `backend/app/service.py` — ordered validation, analysis, and deterministic metrics.
- `backend/app/history.py` — local SQLite persistence and retrieval.
- `backend/app/main.py` — endpoint composition and safe error mapping.
- `dashboard/api_client.py` — stage-specific HTTP timeouts and safe response decoding.
- `dashboard/streamlit_app.py` — staged user flow, accessible visual report, explicit demo control, and history navigation.

## Intentional limits

This is a single-machine MVP. It has no browser automation, JavaScript rendering, anti-bot circumvention, login support, authentication, cloud deployment, Docker, workers, queues, background jobs, or universal website compatibility. It also does not treat the bundled demo set as a replacement for a failed live URL.
