# Review Intelligence Architecture

## Runtime topology

The MVP keeps the existing two-process local architecture. `run_app.py` is the only supported complete-application launcher: it loads the repository-root `.env` without replacing values already present in the parent environment, stages both services with the current Python interpreter, and opens the local dashboard once in the operating system's default browser only after both services are ready.

```text
run_app.py starts one shared 30-second deadline
  └── start Uvicorn / FastAPI       127.0.0.1:8000
        └── wait for GET /health: HTTP 200 + exactly {"status":"ok"}
              └── start Streamlit dashboard     127.0.0.1:8501
                    └── wait for GET /_stcore/health: HTTP 200
                          └── open browser once

Google Chrome or another local browser
  └── Streamlit HTTP client
        └── FastAPI JSON API
              ├── static collector
              ├── Groq analysis boundary
              └── SQLite history store
```

The supervisor launches FastAPI from the project root without a shell and immediately starts one shared 30-second startup deadline. It polls the backend process and exact FastAPI health contract before launching Streamlit, which avoids measured cold-start disk and CPU contention between the two heavyweight Python children. After backend readiness, it launches Streamlit from the same root and waits for the dashboard health endpoint without resetting the original deadline. The browser gate opens only after that second health check succeeds. Once both services are ready, the startup deadline no longer applies and normal process supervision continues.

If readiness is incomplete at the deadline, the supervisor prints `The application did not become ready within 30 seconds.`, returns a nonzero status, and stops whichever children were started. A backend timeout or exit before readiness never starts Streamlit. If either child exits after dashboard launch, the supervisor returns a nonzero status and stops its surviving peer. Cleanup first requests graceful termination, waits up to five seconds per running child, and then kills only a child that did not exit. `Ctrl+C` performs cleanup for all started children and returns a successful status. A browser-open failure is nonfatal and prints the manual dashboard URL.

## Staged data flow

The dashboard never imports backend services directly. Streamlit and FastAPI share validated JSON contracts over local HTTP.

```text
1. User submits a public URL
   Streamlit -> POST /api/collect -> static collector
   Streamlit <- CollectionResult (source + normalized reviews)

2. User inspects the evidence
   Streamlit renders a grouped source summary plus extractor, ratings, dates,
   and review text in the main flow

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

The opening workspace keeps live extraction and explicit demo collection side by side on desktop and explains the sequence with a three-step **How it works** strip. Loading demo data avoids a request to a live review page, but a later **Analyze with Groq** action follows the same credential-validation and provider-network path as live evidence.

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

Metrics are calculated in Python from validated review-level sentiments and ratings. The dashboard renders the extracted review evidence before analysis and then presents the report in this scan order:

1. A report hero with source context and an overall-sentiment badge.
2. Four metric cards for reviews analyzed, average rating, positive share, and overall sentiment.
3. A full-width executive summary.
4. Two customer-signal charts for sentiment mix and rating distribution.
5. A recurring-theme grid.
6. Parallel strengths, concerns, and recommended-actions panels.
7. A collapsed **Supporting review evidence** expander containing the post-analysis source and review table.

The source summary and review table remain visible in the main flow throughout the pre-analysis stage. Once a report exists, that primary evidence workspace is replaced by the report; the source and review evidence is then retained only inside the collapsed **Supporting review evidence** expander. Text-plus-icon treatments ensure color is not the only cue:

- `✅ Positive` is styled in green for strengths and favorable themes.
- `⚠️ Negative` is styled in red for complaints and unfavorable themes.
- `➖ Neutral` uses amber, and `↔ Mixed` uses a distinct indigo treatment.

Individual review classifications remain positive, neutral, or negative. Theme-level sentiment additionally permits `mixed` when the same recurring topic has meaningful positive and negative evidence; the backend schema and Groq prompt share that contract.

Untrusted source titles, themes, model insights, and review text are escaped before being included in styled markup. The dashboard uses Streamlit containers, metric cards, tables, charts, and sidebar controls without storing or displaying any credential.

Responsive CSS preserves the report hierarchy rather than removing information. Desktop uses side-by-side actions, four metric columns, two charts, up to three theme columns, and three insight columns. At the tablet breakpoint, Streamlit action columns and charts stack, metrics wrap to two columns, and themes use two columns. At the mobile breakpoint, the process strip, themes, and insight panels become single-column, while metrics remain a compact two-column grid and container padding is reduced. The sidebar uses Streamlit's automatic initial state for narrow screens.

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

This is a single-machine MVP. It has no browser automation, JavaScript rendering, anti-bot circumvention, login support, authentication, cloud deployment, Docker, workers, queues, background jobs, or universal website compatibility. It also does not treat the bundled demo set as a replacement for a failed live URL. Demo collection is local, but demo analysis still depends on valid Groq credentials, provider availability, and network access.
