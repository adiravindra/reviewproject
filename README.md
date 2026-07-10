# ReviewInsight

ReviewInsight turns one public review-page URL into a website-level intelligence report. The synchronous FastAPI workflow safely collects available static reviews, normalizes and deduplicates them, calculates review and rating metrics in code, uses a configured LangChain chat provider for structured themes and sentiment labels, saves the completed report to SQLite, and renders it in Streamlit.

The URL workflow is the only analysis workflow. There is no pasted-review route, local model, browser renderer, or rule-based analysis fallback.

## What the report contains

- Requested and canonical source URLs, entity identity, scraper, and page counts.
- Reviews found, valid, analyzed, duplicated, invalid, and omitted by the cap.
- Deterministic average rating, 1–5 star distribution, rated-review count, sentiment counts, and overall sentiment.
- Structured executive summary, strengths, complaints, aspects, and improvement opportunities.
- Representative review IDs resolved back to stored original customer wording.
- Normalized reviews with rating, date, source URL, and author metadata when available.
- Explicit partial-collection, truncation, and low-sample warnings.
- Website-level history that loads stored reports without scraping or model calls.

## Architecture

```text
POST /analysis/website
  -> public URL and DNS validation
  -> redirect-safe bounded HTTP streaming
  -> scraper registry
       1. JSON-LD / Schema.org
       2. conservative static review cards
  -> clean, normalize, deduplicate, and cap
  -> LangChain structured batches and synthesis
  -> deterministic metrics and quotation resolution
  -> validate complete response
  -> one atomic SQLite save
```

See [docs/architecture.md](docs/architecture.md) for diagrams and component ownership.

## Safety and request limits

| Limit | Default and hard ceiling |
| --- | ---: |
| Response body per page | 2 MiB |
| Same-origin pages | 3 |
| Scraping deadline | 25 seconds |
| Unique reviews analyzed | 60 |
| Reviews per model batch | 15 |
| Batch calls | 4 |
| Synthesis calls | 1 |
| Total model calls | 5 |
| Provider timeout per call | 20 seconds |
| Overall request deadline | 120 seconds |
| Minimum valid reviews | 2 |
| Low-sample warning | fewer than 5 |

Environment overrides can make demo limits stricter. Values above safe ceilings are clamped.

Only `http` and `https` URLs without embedded credentials are accepted. Every DNS answer and redirect target is checked; loopback, private, link-local, reserved, multicast, unspecified, and otherwise non-public addresses are rejected. Fetching uses explicit timeouts, a descriptive user agent, streamed size enforcement, content-type checks, redirect limits, and common challenge-page detection.

## Verified public scraping demonstration

On July 10, 2026, the production URL validator, HTTP fetcher, registry, JSON-LD extractor, and normalization pipeline reproduced this public learning-site page:

- [web-scraping.dev — Box of Chocolate Candy](https://web-scraping.dev/product/1)
- Scraper: `json_ld`
- Entity: `Box of Chocolate Candy`
- Result: 5 found, 5 valid, 5 analyzed, 1 page, no collection warnings

This verifies that exact page state, not compatibility with every page on the domain. External markup can change at any time. The automated suite uses committed HTML fixtures and never depends on this live page.

## Install

From the project folder:

```powershell
cd C:\Users\adith\Desktop\Work\reviewproject
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

`.env.example` is a reference template; the app does not load it automatically. Set secrets in the process environment only.

### Google Gemini (default)

```powershell
$env:GOOGLE_API_KEY = "your-key"
$env:REVIEWINSIGHT_LLM_PROVIDER = "google"
$env:REVIEWINSIGHT_LLM_MODEL = "gemini-2.5-flash-lite"
```

### Groq

```powershell
$env:GROQ_API_KEY = "your-key"
$env:REVIEWINSIGHT_LLM_PROVIDER = "groq"
$env:REVIEWINSIGHT_LLM_MODEL = "llama-3.3-70b-versatile"
```

Provider keys are never hardcoded, returned to clients, or included in prompts. Authors are retained in stored review metadata but excluded from every model prompt.

## Run

Start FastAPI and Streamlit together:

```powershell
python scripts\run_app.py
```

Open `http://127.0.0.1:8501`. The backend listens on `http://127.0.0.1:8000`.

Or run them in separate terminals:

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

```powershell
python -m streamlit run dashboard\streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

## API

### Analyze a website

`POST /analysis/website`

```powershell
$body = @{ url = "https://web-scraping.dev/product/1" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/analysis/website -ContentType "application/json" -Body $body
```

Successful responses contain `source`, `collection`, `metrics`, `insights`, `reviews`, and `analysis`, plus the saved run `id`. The request returns only after the full response validates and is saved.

### Website history

```powershell
Invoke-RestMethod http://127.0.0.1:8000/analysis/history
Invoke-RestMethod http://127.0.0.1:8000/analysis/history/<run-id>
```

The first route returns indexed website-level summaries. The second returns the exact stored report without rerunning collection or analysis.

### Errors

All API failures use one shape:

```json
{
  "error": {
    "code": "blocked_source",
    "message": "The website blocked automated access.",
    "stage": "scraping",
    "retryable": false,
    "details": {"url": "https://example.com/product"}
  }
}
```

Analysis error codes are `invalid_url`, `unsupported_source`, `blocked_source`, `no_reviews_found`, `insufficient_reviews`, `scrape_failed`, `llm_failed`, and `request_timeout`. Missing stored reports use the history-specific `analysis_not_found` code. Raw exceptions, provider bodies, and credentials are not returned.

## Configuration

The full environment-variable list is in [.env.example](.env.example). Common settings are:

- `REVIEWINSIGHT_LLM_PROVIDER`
- `REVIEWINSIGHT_LLM_MODEL`
- `GOOGLE_API_KEY` or `GROQ_API_KEY`
- `REVIEWINSIGHT_DB_PATH`
- `REVIEWINSIGHT_MAX_PAGES`
- `REVIEWINSIGHT_MAX_REVIEWS`
- `REVIEWINSIGHT_OVERALL_DEADLINE_SECONDS`

The default database is `data/reviewinsight.db`. Fresh databases create only `website_analysis_runs`. If an older local database contains `analysis_runs`, those rows are left untouched but are not read or written.

## Test

```powershell
python -m unittest discover -s tests -v
python -m compileall backend dashboard scripts tests
```

Tests use deterministic HTML, fake HTTP sessions, fake LangChain-compatible structured models, and temporary SQLite databases. They do not call live sites or real model providers.

## Known scraping limitations

- Static HTML only: no Playwright, JavaScript execution, scrolling, clicking, authenticated sessions, or browser fallback.
- Pages that load reviews only through client-side APIs are unsupported unless the initial HTML also exposes supported JSON-LD.
- Anti-bot, login, consent, and rate-limit pages return explicit errors; the app does not try to bypass them.
- The generic static extractor intentionally ignores arbitrary paragraphs and comments, so some accessible pages will return `unsupported_source` rather than guessed reviews.
- Pagination is followed only from review-specific, same-origin next links and stops at three pages.
- Markup and access policies are controlled by external sites and may change without notice.
- A successful scrape does not imply permission for bulk collection. Users remain responsible for site terms and applicable law.
