# Project Status

**Date:** July 17, 2026
**Status:** Groq-only staged MVP implemented; final live-source and Chrome verification is recorded during the release smoke test.

## Current feature inventory

- `run_app.py` retains the local FastAPI + Streamlit supervisor. It loads the repository-root `.env` without overriding existing shell or system values, starts FastAPI on `127.0.0.1:8000` and Streamlit on `127.0.0.1:8501`, waits for Streamlit readiness, and opens the dashboard in the operating system's default browser.
- The UI accepts a public review-page URL, calls `POST /api/collect`, and displays normalized evidence before analysis. Collection is static HTTP only and prefers JSON-LD before conservative HTML review cards.
- `GET /api/demo` loads the ten-review bundled local dataset only after the user selects **Use bundled demo data**. Demo provenance is visible with `🧪 DEMO DATA`; failed live extraction never activates that dataset.
- `POST /api/analyze` accepts the already displayed source and review evidence, validates `GROQ_API_KEY`, uses the Llama Versatile Groq configuration, validates structured insights, and computes metrics in Python.
- The Streamlit report uses text, icons, and distinct semantic treatments for positive, negative, neutral, and mixed results. It surfaces strengths, complaints, themes, actions, charts, and review-level sentiment labels without relying on color alone.
- Successful reports are written atomically to local SQLite at `data/review_history.db`. `GET /api/history` returns newest-first summaries, and `GET /api/history/{run_id}` restores one saved report.
- The backend exposes safe actionable errors for invalid URLs, blocked sites, timeouts, malformed structured review data, missing reviews, missing or invalid Groq configuration, unavailable Groq validation, model-output parsing, and history failures.
- Credentials, headers, raw AI responses, upstream response bodies, internal exceptions, and tracebacks do not cross the FastAPI boundary.

## Runtime and configuration

The active non-secret settings are:

```dotenv
REVIEWINSIGHT_API_URL=http://127.0.0.1:8000
GROQ_API_KEY=
REVIEWINSIGHT_GROQ_MODEL=llama-3.3-70b-versatile
```

`GROQ_API_KEY` is required only when analysis begins. It is never entered through the UI. The model override is optional; the default remains `llama-3.3-70b-versatile`.

## Automated coverage

Focused tests cover:

- strict collection, analysis, source, demo, and history contracts;
- Groq key trimming, validation status mapping, structured-output validation, and response sanitization;
- static collection safety, redirects, limits, JSON-LD priority, HTML fallback, and specific failure codes;
- SQLite first-use schema creation, atomic save, newest-first summaries, round trips, and safe failures;
- staged API routes, safe error envelopes, dashboard HTTP boundaries, accessible presentation helpers, and history navigation;
- supervisor dotenv precedence, browser readiness/open behavior, child lifecycle, and cleanup; and
- current-facing documentation/source audits for retired configuration or model-choice language.

Run the full local checks with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q backend dashboard tests run_app.py
```

## Final verification checklist

The release smoke test runs the supervised app with the existing local environment and installed Google Chrome. It verifies a live extraction, evidence display before analysis, Groq analysis, semantic result labels, history persistence and reload, explicit demo behavior, and representative safe errors. It records only key presence, never its value.

## Known limitations

- Static HTML collection cannot support pages that require client-side rendering, login, pagination, or access-control circumvention.
- External page markup can change; only URLs verified with the completed collector are suitable for a live presentation.
- Groq access, quotas, model availability, and later generative request success remain external service concerns even after pre-analysis validation succeeds.
- SQLite history is intentionally local to this machine and has no multi-user synchronization or backup layer.
- Automated tests use fixtures and fakes; live sources and real model calls require the separate local smoke check.
