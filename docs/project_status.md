# Project Status

**Date:** July 13, 2026
**Status:** ReviewInsight MVP implemented with supervised startup and credential preflight

## Current feature inventory

- One root startup command, `.\.venv\Scripts\python.exe run_app.py`, loads the repository-root `.env`, launches FastAPI on `127.0.0.1:8000` and Streamlit on `127.0.0.1:8501`, then opens the ready dashboard in the operating system's default browser.
- Existing shell and system environment values take precedence over matching `.env` values; both child services inherit the same resulting configuration.
- The supervisor uses the current interpreter and argument-list child commands, waits on Streamlit's local health endpoint before one browser-open attempt, returns nonzero on startup or unexpected child failure, stops a surviving peer, and cleans up both children on `Ctrl+C`.
- Gemini and Groq credentials are checked through non-generative model-list endpoints before destination resolution, review collection, model construction, or AI analysis.
- Missing, rejected, unavailable, rate-limited, and transport-failed credential checks map to stable safe codes without exposing keys, headers, provider bodies, or internal exceptions.
- The static collector enforces public destinations and redirect revalidation, streams at most 1 MiB of HTML, prefers JSON-LD, recognizes conservative review cards, deduplicates exact text, requires two reviews, and caps output at 40.
- One structured LangChain agent invocation returns bounded insights and an exact review-level sentiment mapping from Gemini or Groq.
- Counts, rating aggregates, sentiment distribution, and rating distribution are calculated deterministically in Python.
- FastAPI exposes only `GET /health` and `POST /api/analyze`, with validated response schemas and explicit public status mappings.
- The Streamlit dashboard provides provider selection, readiness checks, safe error rendering, four headline metrics, two charts, summary, themes, strengths, weaknesses, actions, and review evidence.
- Every retained Python module, class, function, and test helper has descriptive docstring coverage.
- The repository retains only active runtime, test fixture, operational documentation, and current design/plan artifacts; generated runtime output is ignored.

## Current test inventory

The discovered suite contains 60 deterministic tests and makes no live website or AI-provider calls.

- `tests/test_credentials.py`: provider endpoint, header, timeout, missing-key, rejected-key, availability, and sanitization contracts.
- `tests/test_run_app.py`: project-root dotenv precedence, readiness probing, one-time browser opening, child command construction, interrupt cleanup, peer exit, startup failure, and forced-shutdown escalation.
- `tests/test_documentation.py`: startup-documentation, retained-source discovery, and module/class/function docstring enforcement.
- `tests/test_collector_mvp.py`: public-address safety, redirects, streamed limits, extraction, deduplication, minimum review count, and cap.
- `tests/test_analyzer_mvp.py`: direct key safeguards, one structured invocation, exact sentiment IDs, and sanitized provider errors.
- `tests/test_service_mvp.py`: preflight-before-collection ordering, one-pass orchestration, and deterministic metrics.
- `tests/test_api_mvp.py`: route surface, validation, safe envelopes, credential statuses, and generic unexpected failures.
- `tests/test_dashboard_mvp.py`: health and analysis timeouts, safe client errors, backend unavailability, metrics, charts, and visual tokens.

Current verification commands are:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q backend dashboard tests run_app.py
```

## Current limits

- Collection covers one static HTML page and does not execute JavaScript or paginate.
- The demonstration site is external and may change independently.
- Provider credentials, permissions, quotas, availability, model access, and free-tier eligibility are controlled by Google or Groq.
- Credential preflight confirms provider acceptance through the model-list endpoint; it does not guarantee that a later generative request will succeed.
- Automated tests use fixtures and fakes; live provider and external-page behavior require separate operational checks.
