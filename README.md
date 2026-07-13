# ReviewInsight

ReviewInsight turns reviews from one public, static HTML page into a structured product readout. A supervised local application runs a FastAPI backend and Streamlit dashboard together. The backend validates the selected AI-provider credential, collects bounded review evidence, makes one structured Gemini or Groq call, and calculates reproducible metrics in Python.

## Architecture

```text
.\run_app.py supervisor
  +-- FastAPI http://127.0.0.1:8000
  |     POST /api/analyze
  |       -> validate selected provider credential
  |       -> collect reviews from one public page
  |       -> run one structured AI analysis
  |       -> calculate deterministic metrics
  |       -> return a validated report
  +-- Streamlit http://127.0.0.1:8501
        -> health check and JSON API calls to FastAPI
        -> metrics, charts, themes, actions, and review evidence
```

The dashboard and backend communicate only through HTTP JSON contracts. The root supervisor owns both child processes: it starts them with the current Python interpreter, keeps running while both are active, stops the survivor if either child exits, and cleans up both on `Ctrl+C`.

## Supported review sources and limits

- The input must be a public `http` or `https` URL without embedded credentials.
- Collection uses static HTTP only; client-rendered JavaScript is not executed.
- Schema.org/JSON-LD reviews are preferred. Recognized static review-card markup is used when structured reviews are absent.
- One page, at most three redirects, a 1 MiB HTML response, and at most 40 unique reviews are processed.
- Every redirect destination is revalidated as a globally routable address.
- At least two unique reviews are required.
- Pagination, authenticated pages, browser automation, anti-bot bypasses, persistent reports, user accounts, and background jobs are outside this MVP.

The sample page is `https://web-scraping.dev/product/1`. External markup can change; automated collection tests use `tests/fixtures/review_page.html`.

## Installation and configuration

Python 3.12 or newer is recommended. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Set the credential for each provider you intend to select:

```powershell
$env:GOOGLE_API_KEY = "your-gemini-key" # required when Gemini is selected
$env:GROQ_API_KEY = "your-groq-key"     # required when Groq is selected
```

Only the selected provider's credential is read and validated. The unselected provider's variable may be absent. `.env.example` lists every active setting, but the application reads process environment variables and does not load a `.env` file itself.

Default model and backend URL settings are:

```powershell
$env:REVIEWINSIGHT_GOOGLE_MODEL = "gemini-2.5-flash-lite"
$env:REVIEWINSIGHT_GROQ_MODEL = "llama-3.3-70b-versatile"
$env:REVIEWINSIGHT_API_URL = "http://127.0.0.1:8000"
```

The model and API URL variables are optional overrides. Provider access, quotas, and model availability remain controlled by the provider account. Never commit keys or include them in logs.

## Start the complete application

With the virtual environment installed and the selected provider credential set, run exactly:

```powershell
.\.venv\Scripts\python.exe run_app.py
```

Open `http://127.0.0.1:8501`. FastAPI listens on `127.0.0.1:8000`. Press `Ctrl+C` in the supervising terminal to stop both services.

## Credential preflight

Credential validation is the first analysis stage, before page collection and before any generative model invocation.

| Selection | Required variable | Non-generative request | Authentication |
|---|---|---|---|
| Gemini (`google`) | `GOOGLE_API_KEY` | `GET https://generativelanguage.googleapis.com/v1beta/models` | `x-goog-api-key` header |
| Groq (`groq`) | `GROQ_API_KEY` | `GET https://api.groq.com/openai/v1/models` | `Authorization: Bearer` header |

Both requests list accessible models; neither produces model output. The request uses a 3-second connection timeout and a 5-second read timeout. A `2xx` response passes preflight. A blank selected key fails before any provider request; `400`, `401`, or `403` means the credential was rejected; every other non-success status or transport failure means validation could not be completed.

Only stable application-owned codes and messages cross the API boundary. Credential values, authorization headers, provider response bodies, transport details, internal exceptions, and stack traces are never returned to the dashboard.

## Project structure

- `run_app.py` — starts, supervises, and stops the FastAPI and Streamlit child processes.
- `backend/app/errors.py` — shared safe application error type.
- `backend/app/credentials.py` — selected-provider credential lookup and non-generative validation.
- `backend/app/collector.py` — public-destination checks, bounded static retrieval, extraction, normalization, and limits.
- `backend/app/analyzer.py` — provider model construction and one structured LangChain agent invocation.
- `backend/app/service.py` — credential preflight, collection, analysis, and metric orchestration.
- `backend/app/models.py` — validated request, review, insight, metric, response, and public-error contracts.
- `backend/app/main.py` — FastAPI routes and safe HTTP error mapping.
- `dashboard/api_client.py` — health and analysis HTTP client boundary with safe error decoding.
- `dashboard/streamlit_app.py` — input form and staged report presentation.
- `tests/fixtures/review_page.html` — deterministic static collection fixture.
- `tests/test_credentials.py` — provider endpoint, authentication, timeout, and safe-status tests.
- `tests/test_run_app.py` — supervisor command, exit, interrupt, and cleanup tests.
- `tests/test_documentation.py` — retained Python docstring coverage.
- `tests/test_collector_mvp.py` — collection safety, extraction, deduplication, and limit tests.
- `tests/test_analyzer_mvp.py` — model construction, single invocation, schema, and sanitization tests.
- `tests/test_service_mvp.py` — stage ordering and deterministic metric tests.
- `tests/test_api_mvp.py` — route, response, status, and safe-envelope tests.
- `tests/test_dashboard_mvp.py` — client boundary and report-formatting tests.
- `tests/__init__.py` — test package marker and package documentation.
- `requirements.txt` — bounded runtime and test dependencies.
- `.env.example` — active environment-variable names and default values without secrets.
- `README.md` — installation, operation, contracts, testing, and troubleshooting.
- `docs/architecture.md` — detailed runtime ownership and data boundaries.
- `docs/project_status.md` — current implementation and verification inventory.
- `docs/superpowers/specs/2026-07-13-single-command-credential-preflight-design.md` — approved current design.
- `docs/superpowers/plans/2026-07-13-single-command-credential-preflight.md` — current implementation plan.

## API example and errors

After starting the application and setting the credential for the selected provider:

```powershell
$body = @{ url = "https://web-scraping.dev/product/1"; provider = "google" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/analyze -ContentType application/json -Body $body
```

Application failures use this envelope:

```json
{"detail":{"code":"no_reviews","message":"At least two public reviews are required."}}
```

| Code | HTTP status | Meaning |
|---|---:|---|
| `invalid_url` | 422 | The destination is malformed, unsupported, credential-bearing, or not public. |
| `no_reviews` | 422 | Fewer than two usable unique reviews were found. |
| `collection_failed` | 502 | The public page could not be collected safely. |
| `missing_api_key` | 400 | The selected provider variable is blank or absent. |
| `invalid_api_key` | 401 | The selected provider rejected the key or its permissions. |
| `provider_unavailable` | 503 | Credential validation could not complete because of provider or transport availability. |
| `analysis_failed` | 502 | A known model-analysis failure occurred. |

Malformed request schemas also receive FastAPI's standard `422` response. An unexpected internal failure is reduced to a generic `analysis_failed` message with HTTP `500`.

## Tests

Tests use fixtures and fakes; they do not call live review pages or AI providers.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q backend dashboard tests run_app.py
```

The first command runs credential, collector, analyzer, service, API, dashboard, supervisor, and Python-documentation coverage. The second compiles every retained Python source.

## Troubleshooting

### Missing or invalid credential

Set the variable for the provider selected in the dashboard. A missing key returns `missing_api_key`; a key rejected with provider status `400`, `401`, or `403` returns `invalid_api_key`. Check that the key has no surrounding whitespace and has permission to access the provider's models endpoint.

### Provider cannot be validated

`provider_unavailable` covers timeouts, connection failures, rate limits, server errors, and other non-success responses. No page collection or AI analysis has started. Check network access and provider status, then retry.

### Port 8000 or 8501 is occupied

Stop the process already listening on the occupied port, then rerun the startup command. The ports are fixed by `run_app.py`; `REVIEWINSIGHT_API_URL` changes only where the dashboard sends backend requests.

### A child process exits

The supervisor stops the remaining service and exits nonzero when Uvicorn or Streamlit fails or exits unexpectedly. Read the child output in the supervising terminal, correct the first reported dependency, configuration, or port error, and rerun the same startup command. If graceful shutdown exceeds five seconds, the supervisor forces that child to stop.

### The dashboard reports that FastAPI is unreachable

Confirm that `run_app.py` is still running and that `Invoke-RestMethod http://127.0.0.1:8000/health` returns `status: ok`. If the supervisor already exited, use its terminal output to diagnose the child that failed and restart the complete application.
