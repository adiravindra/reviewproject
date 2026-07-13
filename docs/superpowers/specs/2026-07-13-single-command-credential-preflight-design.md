# Single-Command Startup and Credential Preflight Design

**Date:** July 13, 2026  
**Status:** Approved for implementation

## Objective

Make ReviewInsight start through one documented command, reject unusable AI-provider credentials before collecting reviews or invoking a model, remove obsolete repository artifacts, and make every retained Python module understandable without relying on historical implementation context.

## Required behavior

The complete application starts from the repository root with:

```powershell
.\.venv\Scripts\python.exe run_app.py
```

The supervisor starts FastAPI on `127.0.0.1:8000` and Streamlit on `127.0.0.1:8501`. It detects immediate startup failures, remains alive while both children are healthy, handles `Ctrl+C`, and terminates both children if either process exits. Child processes are launched as argument lists without a shell so user-controlled environment values cannot become executable command text.

Before any page collection or AI analysis, the backend validates the selected provider credential:

- Gemini uses `GET https://generativelanguage.googleapis.com/v1beta/models` with the key in the `x-goog-api-key` header.
- Groq uses `GET https://api.groq.com/openai/v1/models` with the key in an `Authorization: Bearer` header.

Both endpoints list accessible models and do not generate model output. The selected provider's credential must be nonblank and the preflight request must return success. Missing, invalid, unauthorized, permission-denied, timed-out, unreachable, rate-limited, or otherwise unvalidated credentials stop the workflow before the collector is called.

The dashboard displays only application-owned messages. API keys, authorization headers, endpoint query strings, provider response bodies, exception details, and stack traces never cross the backend boundary.

Model construction retains its existing environment-variable check as defense in depth. The preflight is the authoritative workflow gate; model construction protects direct or future callers that bypass orchestration.

## Architecture and data flow

```text
Streamlit form submission
  -> POST /api/analyze
      -> validate_provider_credentials(provider)
          -> read only the selected provider's environment variable
          -> call the provider's non-generative model-list endpoint
          -> map response or network failure to a safe AnalysisError
      -> collect_reviews(url)
      -> analyze_reviews(reviews, provider)
          -> build_model(provider), including defensive key-presence check
          -> one structured LangChain invocation
      -> deterministic metrics
      -> validated response
```

Credential preflight belongs in backend orchestration rather than the dashboard. This preserves one security boundary for browser and API clients and makes call ordering directly testable.

## Error contract

Credential failures use these public codes and messages:

- `missing_api_key`: name the required environment variable and selected provider without including a value.
- `invalid_api_key`: explain that the selected provider rejected the credential and that the key or its permissions must be checked.
- `provider_unavailable`: explain that the credential could not be validated and analysis did not start; suggest retrying when the provider is reachable.

HTTP mapping is `400` for a missing key, `401` for rejected or unauthorized credentials, and `503` when validation cannot be completed. Other analysis failures retain their existing safe mapping.

The dashboard already renders structured backend messages. Tests will explicitly verify that sensitive fake key text, raw response text, headers, and lower-level exception details are absent from API and dashboard-visible messages.

## Supervisor design

The root `run_app.py` owns process lifecycle only. It builds commands from `sys.executable`, starts Uvicorn and Streamlit, polls both children, and shuts down the surviving child when its peer exits. Graceful termination is attempted first; a bounded wait is followed by forced termination only when necessary. The script returns a nonzero exit status for startup or unexpected child failures and zero for a user-requested interrupt after cleanup.

The supervisor does not install dependencies, open a browser, modify credentials, or hide child output. Keeping those responsibilities out makes failures visible and keeps startup deterministic.

## Repository cleanup

Retain only the active backend, dashboard, tests and fixture, root launcher, environment template, dependency list, README, current architecture/status documentation, and this approved design/implementation record.

Remove:

- Historical specifications, plans, and design images for superseded database/history and earlier MVP workflows.
- Stale bytecode-only package directories and every `__pycache__` directory.
- Obsolete local databases, temporary QA logs, and the untracked `tmp` tree.
- Empty directories left behind by removed implementations.

Preserve `.env`, `.venv`, `.vscode`, and `.codex_runtime`. Extend `.gitignore` for project-wide runtime databases and temporary workspace output so cleanup artifacts do not reappear as repository noise.

## Python documentation standard

Every retained Python file receives a module docstring. Public and internal classes and functions receive descriptive docstrings that explain responsibilities, inputs, outputs, failure behavior, and boundary decisions where relevant. Configuration constants and major processing stages receive comments explaining why their values or ordering matter. Tests document the behavior each helper or fake represents. Simple assignments, imports, and self-evident statements are not narrated line by line.

## Testing and verification

Implementation follows test-first development. Regression coverage must demonstrate:

1. Missing selected-provider credentials fail before collection.
2. Gemini and Groq use the documented model-list endpoints and authentication headers.
3. Invalid, unauthorized, permission-denied, timeout, connection, rate-limit, and unexpected validation responses stop before collection.
4. API and dashboard-visible errors contain only safe application messages.
5. Model construction still rejects missing credentials when called directly.
6. The supervisor starts both expected commands, detects immediate startup failures, stops both children on `Ctrl+C`, and stops the surviving child if its peer exits.

Final verification includes the complete unit-test suite, Python compilation, a repository-content audit, and a local startup/shutdown smoke test. The smoke test starts both services through `run_app.py`, checks their health endpoints without an in-app browser, stops the supervisor, and verifies that neither child remains listening.

## Authoritative provider references

- [Gemini API authentication](https://ai.google.dev/api)
- [Gemini models API](https://ai.google.dev/api/models)
- [Groq API reference](https://console.groq.com/docs/api-reference)
- [Groq error codes](https://console.groq.com/docs/errors)
