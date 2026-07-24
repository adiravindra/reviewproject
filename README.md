# Review Intelligence

Review Intelligence is a local, presentation-ready MVP for turning public reviews into an evidence-backed report. It keeps the user in control of the flow: import or extract reviews first, inspect the evidence, then request Groq analysis.

The application runs a FastAPI backend and a Streamlit dashboard under one local supervisor. It is Groq-only: there is no model-choice control in the interface and no credential field in the dashboard.

## What the MVP does

1. Imports a small review set from one Amazon product URL or Google Maps place URL.
2. Preserves the existing generic static collector, which reads JSON-LD first and conservative HTML review cards second.
3. Shows the normalized reviews and source metadata before any AI request.
4. Validates Groq access, analyzes the displayed evidence, and calculates metrics locally.
5. Presents labeled positive, negative, neutral, and mixed findings with accessible colors and icons.
6. Saves successful reports in local SQLite history for later loading.

Bundled demo data is available only through the explicit **Use bundled demo data** action. A failed live collection never substitutes demo reviews.

## Architecture

```text
run_app.py supervisor
  1. Start FastAPI:   http://127.0.0.1:8000
       GET  /health        -> ready only with HTTP 200 + exactly {"status":"ok"}
       POST /api/collect   -> static collection only
       GET  /api/demo      -> explicit bundled sample only
       POST /api/analyze   -> Groq validation + analysis + SQLite save
       GET  /api/history   -> local saved-run summaries
  2. After FastAPI is ready, start Streamlit: http://127.0.0.1:8501
       GET /_stcore/health -> ready with HTTP 200
       -> staged evidence, analysis, results, and history UI
  3. After Streamlit is ready, open the browser
```

The detailed boundary and data-flow description is in [docs/architecture.md](docs/architecture.md).

## Install and configure on Windows

Python 3.12 or newer is recommended. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The only AI credential is `GROQ_API_KEY`. Both review-source adapters use one separate backend-only `APIFY_API_TOKEN`. Values are read from the existing process or system environment, or from a repository-root `.env` file. The dashboard never requests or displays either credential.

```dotenv
# .env — keep this file local and never commit a real value
GROQ_API_KEY=replace-with-your-local-secret
```

`run_app.py` loads `.env` with `override=False`, so values already present in the shell or system environment take precedence. `.env.example` lists the active non-secret settings:

```dotenv
REVIEWINSIGHT_API_URL=http://127.0.0.1:8000
GROQ_API_KEY=
REVIEWINSIGHT_GROQ_MODEL=llama-3.3-70b-versatile
APIFY_API_TOKEN=
```

`REVIEWINSIGHT_GROQ_MODEL` is optional; when it is unset, the application uses the existing Llama Versatile default, `llama-3.3-70b-versatile`. Do not put credentials in source code, screenshots, browser fields, or logs.

## Run the complete application

```powershell
.\.venv\Scripts\python.exe run_app.py
```

The supervisor stages startup under one shared 30-second deadline to avoid cold-start contention. It starts FastAPI on `127.0.0.1:8000` first and waits until `GET /health` returns HTTP 200 with exactly `{"status":"ok"}`. Only then does it start Streamlit on `127.0.0.1:8501` and wait until `GET /_stcore/health` returns HTTP 200. The deadline starts with the backend and is not reset for the dashboard. The supervisor automatically opens `http://127.0.0.1:8501` in the operating system's default browser only after both stages succeed.

If the complete application does not become ready within 30 seconds, startup returns a failure and stops whichever child processes were started. A backend exit before readiness never starts Streamlit; a later child exit fails the run and stops its running peer. If only the browser-open attempt fails, the services continue and the supervisor prints the URL for manual use. Press `Ctrl+C` in the supervising terminal for a clean shutdown of all started services.

## Dashboard flow

1. Select Amazon or Google Maps. The generic **Source URL** field uses the prompt **Paste an Amazon product or Google Maps place URL**. Choose a shared limit of 10, 20, 50, or 100, then select **Import reviews**. The adjacent **Use bundled demo data** action remains explicit.
2. Follow the three-step **How it works** strip: import, review evidence, then analyze.
3. Inspect the original source, provider, requested count, actual usable count, retrieval time, cache state, ratings, dates, and written evidence before analysis. Import does not call Groq.
4. Select **Analyze with Groq** only when the evidence is ready. The dashboard displays every imported review, up to 100, but sends only the first 40 to the single Groq analysis. Larger reports disclose `40 of N reviews analyzed` while retaining the actual imported count in source provenance. The backend validates `GROQ_API_KEY` before model work.
5. Once a report exists, scan it in order: source and overall sentiment, four metric cards, executive summary, sentiment and rating charts, recurring themes, strengths, concerns, and recommended actions. At this stage, the source and review evidence is retained only in the collapsed **Supporting review evidence** section.
6. Use the sidebar to refresh local history and load a saved report.

For a repeatable collection without requesting a live source page, select **Use bundled demo data** and inspect the ten clearly labeled fictional reviews. The `🧪 DEMO DATA` label remains visible in the source and report views. Selecting **Analyze with Groq** for that demo still requires a valid `GROQ_API_KEY`, network access, and an available Groq service; only demo collection itself is local.

On desktop, the extraction and demo actions share a row, the metric cards use four columns, charts use two columns, and themes and insight panels use multi-column grids. At narrower widths, actions and charts stack, metrics wrap to two columns, themes reduce from three to two and then one column, insight panels stack, and the main content uses tighter padding.

## API boundaries

| Endpoint | Purpose | Calls Groq? |
|---|---|---:|
| `GET /health` | Process-readiness check. | No |
| `GET /api/import/options` | Returns registered source labels and small limits without provider work. | No |
| `POST /api/import` | Imports or returns cached Amazon/Google Maps evidence. | No |
| `POST /api/collect` | Accepts `{"url": "https://..."}` and returns normalized live evidence. | No |
| `GET /api/demo` | Returns the bundled, explicitly labeled demo collection. | No |
| `POST /api/analyze` | Accepts a previously collected source and at most the first 40 reviews; validates Groq, analyzes once, and saves the report. | Yes |
| `GET /api/history` | Returns newest-first local history summaries. | No |
| `GET /api/history/{run_id}` | Returns one saved local report. | No |

Successful reports are stored by FastAPI in `data/review_history.db`. Transient normalized imports are stored separately in `data/review_import_cache.db` for 30 days. The generated `data/` directory is local and ignored by Git.

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

## External setup for live imports

Automated tests and bundled demo use require no provider account. Before the first live request, create one Apify account, obtain an Apify API token from **Settings / API & Integrations**, and set backend-only `APIFY_API_TOKEN`. Apify's current free plan is $0, needs no payment card, includes $5 of non-rollover monthly usage, and hard-stops when exhausted. Check current [Apify pricing](https://apify.com/pricing), and if intentionally using a paid plan, configure the lowest practical platform spending limit first.

- **Amazon:** ReviewInsight calls public Actor [`axesso_data/amazon-reviews-scraper`](https://apify.com/axesso_data/amazon-reviews-scraper) for one validated `amazon.com` ASIN.
- **Google Maps:** ReviewInsight calls public Actor [`compass/google-maps-reviews-scraper`](https://apify.com/compass/google-maps-reviews-scraper) for one place URL with most-relevant ordering, Google-only origin, English output, and `personalData: false`.
- **Actor setup:** no Actor copy, task, schedule, build, webhook, custom configuration, or Actor ID environment variable is required.
- **Analysis:** GROQ_API_KEY remains necessary only after import when **Analyze with Groq** is selected.

Do not perform a manual live smoke request until the account, token, Actor availability, free-plan/billing/spending-limit configuration, and environment value have been confirmed. The application never asks users for Amazon or Google account credentials, browser cookies or session tokens.

## Import cache and usage controls

Provider results are cached locally for 30 days. Repeating the same import uses normalized cached evidence without contacting the provider. **Refresh from source** is the only way to bypass a live entry and warns that it may consume free-tier usage. Page loads, Streamlit reruns, history operations, and analysis never refresh provider data. A failed refresh preserves the displayed evidence and prior cache entry.

- Both separate, replaceable adapters support 10, 20, 50, or 100 reviews and make one synchronous Actor request per cache miss or explicit refresh. A selected limit is a ceiling: Amazon can return fewer usable written reviews, and source provenance displays the actual count.
- Axesso currently advertises $0.90 per 1,000 Amazon reviews. Approximate maximum review-event costs are $0.009, $0.018, $0.045, and $0.09 for limits 10, 20, 50, and 100. Compass uses separate Actor pricing.
- There is no application-side follow-up pagination, background import, schedule, webhook, automatic retry, or monthly quota ledger.

These are planning estimates, not billing guarantees. Provider pricing and availability can change.

## Unofficial providers, terms, privacy, and retention

Both Apify Actors are unofficial scraping services. Their availability does not grant ReviewInsight or its users rights to copy, analyze, retain, redistribute, or commercialize source content. Users are responsible for confirming their use and retention are permitted. Review the [Amazon Conditions of Use](https://www.amazon.com/gp/help/customer/display.html?nodeId=GLSBYFE9MGKKQXXM) and [Google Maps Additional Terms](https://maps.google.com/help/terms_maps/?refresh=1). This documentation does not claim blanket legal permission or endorsement by Amazon or Google.

ReviewInsight retains the original public URL, provider label, requested count, actual count, and normalized evidence. It discards provider reviewer names, profiles, avatars, media, variations, helpful-vote data, owner responses, provider IDs, and raw response bodies. Axesso may include public personal fields transiently and does not expose the Google Actor's `personalData: false` control; ReviewInsight discards those fields but cannot prevent provider-side processing or storage. Review text can still contain personal information and is sent to Groq only after explicit analysis. The normalized cache expires after 30 days, while successful report history retains evidence until the operator deletes the local history database. Historical saved reports labeled `Outscraper` remain readable with their original provenance.

Apify may retain Actor run and dataset data under its provider-side retention policy. Version one does not programmatically delete those runs or datasets; operators may remove them manually in Apify Console. This proof of concept is for small local evaluation, not bulk redistribution.

## Test and validate

Automated tests use saved provider fixtures and fakes, so they do not spend Apify, Axesso, Compass, Amazon, Google Maps, or Groq quota and do not depend on external review pages:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q backend dashboard tests run_app.py
```

The bundled workflow was verified in installed Google Chrome on July 21, 2026: ordered dual-service startup, explicit demo loading, provider-backed Groq analysis, SQLite history restoration, desktop and 430-pixel responsive layouts, and a clean warning/error console all passed. Live third-party source extraction remains a separate environment-dependent smoke check; see [docs/project_status.md](docs/project_status.md) for the detailed record.
