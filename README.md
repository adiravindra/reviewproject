# Review Intelligence

Review Intelligence is a local, presentation-ready MVP for turning a public product or review-page URL into an evidence-backed review report. It keeps the user in control of the flow: extract reviews first, inspect the evidence, then request Groq analysis.

The application runs a FastAPI backend and a Streamlit dashboard under one local supervisor. It is Groq-only: there is no model-choice control in the interface and no credential field in the dashboard.

## What the MVP does

1. Accepts one public `http` or `https` review-page URL.
2. Collects review-like content from JSON-LD first, then conservative static HTML review cards.
3. Shows the normalized reviews and source metadata before any AI request.
4. Validates Groq access, analyzes the displayed evidence, and calculates metrics locally.
5. Presents labeled positive, negative, neutral, and mixed findings with accessible colors and icons.
6. Saves successful reports in local SQLite history for later loading.

Bundled demo data is available only through the explicit **Use bundled demo data** action. A failed live collection never substitutes demo reviews.

## Architecture

```text
run_app.py supervisor
  +-- FastAPI:   http://127.0.0.1:8000
  |     GET  /health        -> readiness only when body is exactly {"status":"ok"}
  |     POST /api/collect   -> static collection only
  |     GET  /api/demo      -> explicit bundled sample only
  |     POST /api/analyze   -> Groq validation + analysis + SQLite save
  |     GET  /api/history   -> local saved-run summaries
  |
  +-- Streamlit: http://127.0.0.1:8501
        GET /_stcore/health -> dashboard readiness
        -> staged evidence, analysis, results, and history UI
```

The detailed boundary and data-flow description is in [docs/architecture.md](docs/architecture.md).

## Install and configure on Windows

Python 3.12 or newer is recommended. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The only AI credential is `GROQ_API_KEY`. It is read from the existing process or system environment, or from a repository-root `.env` file. The dashboard never requests or displays it.

```dotenv
# .env — keep this file local and never commit a real value
GROQ_API_KEY=replace-with-your-local-secret
```

`run_app.py` loads `.env` with `override=False`, so values already present in the shell or system environment take precedence. `.env.example` lists the active non-secret settings:

```dotenv
REVIEWINSIGHT_API_URL=http://127.0.0.1:8000
GROQ_API_KEY=
REVIEWINSIGHT_GROQ_MODEL=llama-3.3-70b-versatile
```

`REVIEWINSIGHT_GROQ_MODEL` is optional; when it is unset, the application uses the existing Llama Versatile default, `llama-3.3-70b-versatile`. Do not put credentials in source code, screenshots, browser fields, or logs.

## Run the complete application

```powershell
.\.venv\Scripts\python.exe run_app.py
```

The supervisor starts FastAPI on `127.0.0.1:8000` and Streamlit on `127.0.0.1:8501`, then polls both readiness endpoints under one 30-second startup deadline. FastAPI is ready only when `GET /health` returns HTTP 200 with exactly `{"status":"ok"}`; Streamlit is ready when `GET /_stcore/health` returns HTTP 200. The supervisor automatically opens `http://127.0.0.1:8501` in the operating system's default browser only after both checks succeed.

If the complete application does not become ready within 30 seconds, startup returns a failure and both child processes are stopped. An unexpected child exit also fails the run and stops its peer. If only the browser-open attempt fails, the services continue and the supervisor prints the URL for manual use. Press `Ctrl+C` in the supervising terminal for a clean shutdown of both services.

## Dashboard flow

1. Use the bordered extraction workspace to paste a public product or review-page URL and select **Extract reviews**. The adjacent **Use bundled demo data** action is always explicit.
2. Follow the three-step **How it works** strip: extract, review evidence, then analyze.
3. Inspect the grouped source summary, extractor label, ratings, dates, and written evidence before analysis. Extraction does not call Groq, and the pre-analysis evidence remains visible.
4. Select **Analyze with Groq** only when the evidence is ready. The backend validates `GROQ_API_KEY` before model work.
5. Scan the report in order: source and overall sentiment, four metric cards, executive summary, sentiment and rating charts, recurring themes, strengths, concerns, and recommended actions. The duplicate post-analysis evidence is available in a collapsed **Supporting review evidence** section.
6. Use the sidebar to refresh local history and load a saved report.

For a repeatable collection without requesting a live source page, select **Use bundled demo data** and inspect the ten clearly labeled fictional reviews. The `🧪 DEMO DATA` label remains visible in the source and report views. Selecting **Analyze with Groq** for that demo still requires a valid `GROQ_API_KEY`, network access, and an available Groq service; only demo collection itself is local.

On desktop, the extraction and demo actions share a row, the metric cards use four columns, charts use two columns, and themes and insight panels use multi-column grids. At narrower widths, actions and charts stack, metrics wrap to two columns, themes reduce from three to two and then one column, insight panels stack, and the main content uses tighter padding.

## API boundaries

| Endpoint | Purpose | Calls Groq? |
|---|---|---:|
| `GET /health` | Process-readiness check. | No |
| `POST /api/collect` | Accepts `{"url": "https://..."}` and returns normalized live evidence. | No |
| `GET /api/demo` | Returns the bundled, explicitly labeled demo collection. | No |
| `POST /api/analyze` | Accepts a previously collected `source` and `reviews`; validates Groq, analyzes, and saves the report. | Yes |
| `GET /api/history` | Returns newest-first local history summaries. | No |
| `GET /api/history/{run_id}` | Returns one saved local report. | No |

Successful reports are stored by FastAPI in `data/review_history.db`. The generated `data/` directory is local and ignored by Git; deleting that database clears saved history without changing bundled demo data.

## Safe errors

The backend returns short application-owned error envelopes such as:

```json
{"detail":{"code":"no_reviews","message":"At least two public reviews are required."}}
```

| Code | HTTP status | Meaning |
|---|---:|---|
| `invalid_url` | 422 | Use a public `http` or `https` URL without embedded credentials. |
| `no_reviews` | 422 | Fewer than two usable reviews were found. |
| `malformed_json_ld` | 422 | Review-like structured data was malformed and no safe fallback succeeded. |
| `site_blocked` | 502 | The target rejected automated static access. |
| `collection_timeout` | 504 | The target did not respond within the collection limit. |
| `collection_failed` | 502 | The page could not be safely read as HTML. |
| `missing_api_key` | 400 | `GROQ_API_KEY` is absent or blank. |
| `invalid_api_key` | 401 | Groq rejected the configured credential. |
| `groq_unavailable` | 503 | Groq credential validation could not complete. |
| `analysis_failed` | 502 | The analysis request could not complete. |
| `model_output_invalid` | 502 | The returned structured analysis did not satisfy the expected schema. |
| `history_failed` | 500 | Local SQLite history could not be updated or read. |
| `history_not_found` | 404 | The requested saved run is not present. |

Credentials, authorization headers, raw AI responses, upstream response bodies, exception internals, and tracebacks never cross the API boundary.

## Collection limits

- Static HTTP only; no JavaScript execution, browser automation, login, or anti-bot bypass.
- JSON-LD review extraction has priority; static HTML cards are a conservative fallback.
- One page, up to three manually validated redirects, a 1 MiB response cap, and up to 40 normalized reviews.
- Public destinations are checked before every request and redirect; at least two unique reviews are required.
- Pagination, authenticated pages, universal website support, queues, cloud deployment, and accounts are intentionally outside this MVP.

## Test and validate

Automated tests use fixtures and fakes, so they do not spend Groq quota or depend on external review pages:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q backend dashboard tests run_app.py
```

The controller-owned final local smoke test must use installed Google Chrome and cover startup readiness, live extraction and Groq analysis, history restoration, safe error paths, explicit demo analysis, responsive layouts, and the application console. That final Chrome pass is still pending for this redesigned build; see [docs/project_status.md](docs/project_status.md) for the current automated record and remaining verification work.
