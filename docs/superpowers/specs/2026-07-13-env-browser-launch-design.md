# Environment Loading and Browser Launch Design

## Context

`run_app.py` starts the FastAPI backend and Streamlit dashboard, but it does not load the project-root `.env` file. Provider code reads credentials only from the inherited process environment, so a `GROQ_API_KEY` stored solely in `.env` is reported as missing. The launcher also forces Streamlit headless mode and never asks the operating system to open the dashboard URL.

## Goals

- Load settings from the repository-root `.env` before either child process starts.
- Preserve values already present in the parent process environment.
- Open the dashboard once in the operating system's configured default browser after Streamlit is ready.
- Preserve the supervisor's existing process ownership, shutdown, and shell-free launch behavior.
- Keep configuration and browser failures safe, explicit, and testable.

Changing provider validation, model selection, ports, or application UI is outside this change.

## Approach

Add `python-dotenv` as a bounded runtime dependency and call `load_dotenv(PROJECT_ROOT / ".env", override=False)` in the root supervisor before constructing or starting child processes. Loading in the supervisor gives FastAPI and Streamlit the same inherited environment without duplicating configuration logic in either application.

Keep Streamlit headless so browser ownership remains explicit in the supervisor. After both children start, the supervisor probes `http://127.0.0.1:8501/_stcore/health` on its existing polling loop. Once the probe succeeds, it calls Python's `webbrowser.open()` exactly once with `http://127.0.0.1:8501` and then continues normal peer supervision.

This is preferred over relying on Streamlit's implicit browser behavior because readiness, single-open semantics, and failure handling remain under the launcher's control. It is preferred over a custom `.env` parser because `python-dotenv` implements established quoting, whitespace, and escaping rules.

## Runtime Flow

1. Resolve the repository root from `run_app.py`.
2. Load `PROJECT_ROOT / ".env"` without overriding existing environment variables.
3. Construct and start the FastAPI and Streamlit child commands using the current Python interpreter and repository-root working directory.
4. Poll both child processes and the Streamlit health endpoint.
5. If either child exits, return a failure and clean up its peer as today.
6. When the Streamlit health endpoint first succeeds, request one operating-system default-browser open and never request another during that run.
7. Continue supervising both children until a peer exits or the user presses `Ctrl+C`.

## Configuration Semantics

The parent process environment has highest priority. `.env` supplies only variables that are absent from that environment; it never replaces an already-set value. A missing `.env` file is valid because users may configure all settings through their shell or system environment.

The `.env` path is anchored to `PROJECT_ROOT`, so launching `run_app.py` from another working directory behaves consistently. Credential values are never printed, returned to the dashboard, or included in test output.

If dotenv loading raises because the file cannot be parsed or read, startup returns a nonzero status with a safe message before any child process begins. The message identifies the configuration file but does not include its contents.

## Browser and Readiness Behavior

The dashboard URL is `http://127.0.0.1:8501`, and readiness is determined by Streamlit's local `/_stcore/health` endpoint. A short request timeout prevents any probe from blocking supervision. Failed probes are expected while Streamlit starts and are retried on the normal polling loop.

Browser launch is attempted only after readiness and at most once. If the operating system rejects the request or no browser is registered, the launcher reports that the user can open the dashboard URL manually and continues running both services. Automated verification does not require Codex's built-in browser; it uses injected test doubles and local HTTP health checks. If interactive verification is needed, it will use the user's Google Chrome session rather than the built-in browser.

## Testing

Launcher unit tests will establish these contracts before production changes:

- the supervisor requests the exact project-root `.env` path with `override=False`;
- values already present in the environment are not replaced;
- neither child starts when dotenv loading fails;
- the browser is not opened before dashboard readiness;
- the dashboard URL opens exactly once after readiness;
- transient readiness failures do not stop either child;
- browser-open failure leaves both services supervised;
- existing peer-exit, `Ctrl+C`, partial-startup, and forced-shutdown behavior remains intact.

The full test suite and Python compilation check will run after the focused launcher tests. README and project documentation will be updated to describe `.env` loading, precedence, and automatic opening.

