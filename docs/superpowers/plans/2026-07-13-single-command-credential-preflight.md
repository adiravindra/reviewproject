# Single-Command Startup and Credential Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Start ReviewInsight with one command, validate the selected AI provider credential before collection, safely expose validation failures, remove obsolete artifacts, and fully document every retained Python file.

**Architecture:** A dedicated credential module performs a non-generative provider model-list request and raises application-owned errors. Service orchestration calls that preflight before the collector. A root Python supervisor owns the Uvicorn and Streamlit child processes, while FastAPI and the dashboard keep their existing HTTP boundary.

**Tech Stack:** Python 3.12+, FastAPI, Requests, LangChain, Streamlit, `unittest`, `subprocess`, PowerShell verification commands.

## Global Constraints

- The supported providers remain exactly `google` and `groq`.
- Gemini validation uses `GET https://generativelanguage.googleapis.com/v1beta/models` with `x-goog-api-key`.
- Groq validation uses `GET https://api.groq.com/openai/v1/models` with `Authorization: Bearer`.
- Credential validation must finish successfully before `collect_reviews` is called.
- Missing or unvalidated credentials must prevent both review collection and AI model invocation.
- Public errors must never include API-key values, authorization headers, raw provider bodies, sensitive URLs, exception details, or stack traces.
- Preserve `.env`, `.venv`, `.vscode`, and `.codex_runtime`.
- Tests must not call live websites or live AI providers.
- Every retained Python module, class, and function must have a descriptive docstring; configuration and non-obvious processing decisions must have explanatory comments without narrating trivial lines.
- The supported one-command startup is `.\.venv\Scripts\python.exe run_app.py`.

---

## File map

- `backend/app/errors.py`: shared application analysis error type.
- `backend/app/credentials.py`: selected-provider key lookup, non-generative validation request, and safe failure mapping.
- `backend/app/analyzer.py`: model construction safeguard and one structured model invocation.
- `backend/app/service.py`: credential preflight → collection → analysis → deterministic metrics orchestration.
- `backend/app/main.py`: FastAPI routes and HTTP mapping for all safe public codes.
- `backend/app/models.py`: request, response, insight, metric, and public error schemas.
- `backend/app/collector.py`: bounded public-page retrieval and conservative review extraction.
- `dashboard/api_client.py`: safe backend HTTP client boundary.
- `dashboard/streamlit_app.py`: form, user-safe errors, and report presentation.
- `run_app.py`: lifecycle supervisor for Uvicorn and Streamlit.
- `tests/test_credentials.py`: provider request contract, call order, and sanitization tests.
- `tests/test_run_app.py`: supervisor commands, startup failures, interrupts, peer exits, and cleanup tests.
- `tests/test_documentation.py`: repository-wide module/class/function docstring contract.
- Existing `tests/test_*_mvp.py`: retained behavior and boundary regression coverage.
- `.gitignore`: generated database and temporary QA output exclusions.
- `README.md`, `docs/architecture.md`, `docs/project_status.md`: current operational and architectural documentation.

---

### Task 1: Add provider credential preflight before collection

**Files:**
- Create: `backend/app/errors.py`
- Create: `backend/app/credentials.py`
- Create: `tests/test_credentials.py`
- Modify: `backend/app/analyzer.py`
- Modify: `backend/app/service.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/models.py`
- Modify: `tests/test_analyzer_mvp.py`
- Modify: `tests/test_service_mvp.py`
- Modify: `tests/test_api_mvp.py`
- Modify: `tests/test_dashboard_mvp.py`

**Interfaces:**
- Produces: `AnalysisError(code: str, public_message: str)` in `backend.app.errors`.
- Produces: `validate_provider_credentials(provider: Provider, *, session=requests) -> None`.
- Changes: `run_analysis(url, provider, *, credential_validator=validate_provider_credentials, collector=collect_reviews, analyzer=analyze_reviews) -> AnalysisResponse`.
- Public codes added: `invalid_api_key`, `provider_unavailable`.

- [ ] **Step 1: Write failing unit tests for provider request construction and safe mapping**

Create `tests/test_credentials.py` with response/session fakes that record the URL, headers, and timeout. Cover these exact assertions:

```python
def test_gemini_uses_non_generative_model_list_endpoint(self):
    session = FakeSession(FakeResponse(200))
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "google-secret"}, clear=True):
        validate_provider_credentials("google", session=session)
    self.assertEqual(session.url, "https://generativelanguage.googleapis.com/v1beta/models")
    self.assertEqual(session.headers, {"x-goog-api-key": "google-secret"})
    self.assertEqual(session.timeout, (3, 5))

def test_groq_uses_non_generative_model_list_endpoint(self):
    session = FakeSession(FakeResponse(200))
    with patch.dict(os.environ, {"GROQ_API_KEY": "groq-secret"}, clear=True):
        validate_provider_credentials("groq", session=session)
    self.assertEqual(session.url, "https://api.groq.com/openai/v1/models")
    self.assertEqual(session.headers, {"Authorization": "Bearer groq-secret"})

def test_missing_selected_key_stops_before_http(self):
    session = FakeSession(FakeResponse(200))
    with patch.dict(os.environ, {}, clear=True):
        with self.assertRaises(AnalysisError) as raised:
            validate_provider_credentials("google", session=session)
    self.assertEqual(raised.exception.code, "missing_api_key")
    self.assertIsNone(session.url)

def test_provider_rejection_is_safe(self):
    for status in (400, 401, 403):
        with self.subTest(status=status):
            session = FakeSession(FakeResponse(status, text="raw provider secret response"))
            with patch.dict(os.environ, {"GROQ_API_KEY": "groq-secret"}, clear=True):
                with self.assertRaises(AnalysisError) as raised:
                    validate_provider_credentials("groq", session=session)
            self.assertEqual(raised.exception.code, "invalid_api_key")
            self.assertNotIn("groq-secret", str(raised.exception))
            self.assertNotIn("raw provider", str(raised.exception))

def test_temporary_or_unknown_failure_is_safe(self):
    cases = [
        FakeResponse(429, text="quota internals"),
        FakeResponse(500, text="provider stack"),
        requests.Timeout("timeout details"),
        requests.ConnectionError("socket details"),
        requests.RequestException("transport details"),
    ]
    # Each case must raise provider_unavailable and omit every supplied detail and key.
```

- [ ] **Step 2: Run credential tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_credentials -v
```

Expected: import failure because `backend.app.credentials` and `backend.app.errors` do not exist.

- [ ] **Step 3: Implement the shared error and credential validator**

Implement `backend/app/errors.py`:

```python
"""Define safe application errors shared by credential and analysis boundaries."""


class AnalysisError(Exception):
    """Carry a stable public code and message without leaking internal exceptions."""

    def __init__(self, code: str, public_message: str):
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message
```

Implement `backend/app/credentials.py` with immutable provider configuration and these rules:

```python
"""Validate provider credentials without generating AI output."""

import os
from dataclasses import dataclass

import requests

from backend.app.errors import AnalysisError
from backend.app.models import Provider

VALIDATION_TIMEOUT = (3, 5)


@dataclass(frozen=True)
class CredentialConfig:
    """Describe one provider's secret location and authentication request."""

    display_name: str
    environment_variable: str
    endpoint: str
    header_name: str
    header_prefix: str = ""


PROVIDER_CREDENTIALS = {
    "google": CredentialConfig(
        "Gemini",
        "GOOGLE_API_KEY",
        "https://generativelanguage.googleapis.com/v1beta/models",
        "x-goog-api-key",
    ),
    "groq": CredentialConfig(
        "Groq",
        "GROQ_API_KEY",
        "https://api.groq.com/openai/v1/models",
        "Authorization",
        "Bearer ",
    ),
}


def validate_provider_credentials(provider: Provider, *, session=requests) -> None:
    """Require the selected key and verify it through a non-generative endpoint."""
    config = PROVIDER_CREDENTIALS[provider]
    api_key = os.getenv(config.environment_variable, "").strip()
    if not api_key:
        raise AnalysisError(
            "missing_api_key",
            f"Set {config.environment_variable} before using {config.display_name}.",
        )

    try:
        response = session.get(
            config.endpoint,
            headers={config.header_name: f"{config.header_prefix}{api_key}"},
            timeout=VALIDATION_TIMEOUT,
        )
    except requests.RequestException:
        raise AnalysisError(
            "provider_unavailable",
            f"{config.display_name} credentials could not be validated. Analysis did not start; try again when the provider is reachable.",
        ) from None

    if response.status_code in {400, 401, 403}:
        raise AnalysisError(
            "invalid_api_key",
            f"{config.display_name} rejected the configured credential. Check the key and its permissions.",
        )
    if response.status_code < 200 or response.status_code >= 300:
        raise AnalysisError(
            "provider_unavailable",
            f"{config.display_name} credentials could not be validated. Analysis did not start; try again when the provider is reachable.",
        )
```

Move `AnalysisError` out of `analyzer.py` and import it there instead. Keep `build_model`'s nonblank selected-key checks unchanged except for using the shared type.

- [ ] **Step 4: Run credential tests and verify GREEN**

Run the command from Step 2. Expected: all credential tests pass with no network access.

- [ ] **Step 5: Write the failing orchestration-order regression test**

Add to `tests/test_service_mvp.py`:

```python
def test_credentials_are_validated_before_collection(self):
    events = []

    def validate(provider):
        events.append(("validate", provider))
        raise AnalysisError("invalid_api_key", "The selected credential is invalid.")

    collector = Mock(side_effect=lambda url: events.append(("collect", url)))
    analyzer = Mock()
    with self.assertRaises(AnalysisError):
        run_analysis(
            "https://example.com/product",
            "google",
            credential_validator=validate,
            collector=collector,
            analyzer=analyzer,
        )
    self.assertEqual(events, [("validate", "google")])
    collector.assert_not_called()
    analyzer.assert_not_called()
```

Update the successful pipeline test to inject a `credential_validator` mock and assert it is called before the collector.

- [ ] **Step 6: Run the service test and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_service_mvp.ServiceTests.test_credentials_are_validated_before_collection -v
```

Expected: `run_analysis` rejects the new keyword argument or calls collection first.

- [ ] **Step 7: Gate orchestration on the credential preflight**

Modify `run_analysis` so its first stage is exactly:

```python
credential_validator(provider)
collection = collector(url)
insights = analyzer(collection.reviews, provider)
```

The validator is injectable only to keep tests deterministic; production defaults to `validate_provider_credentials`.

- [ ] **Step 8: Extend API and dashboard-visible error tests before changing mappings**

In `tests/test_api_mvp.py`, add `invalid_api_key` expecting `401` and `provider_unavailable` expecting `503`. Use messages containing fake secrets/raw details internally and assert those strings never occur in `response.text`.

In `tests/test_dashboard_mvp.py`, return each structured credential error from `FakeSession` and assert `ApiClientError.code` and the safe message are preserved while fake key/header/provider-body strings are absent.

In `backend/app/models.py`, extend `PublicError.code` with `invalid_api_key` and `provider_unavailable`.

- [ ] **Step 9: Run API/dashboard tests and verify RED, then implement HTTP mapping**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_api_mvp tests.test_dashboard_mvp -v
```

Expected before mapping: credential cases use `502` instead of `401`/`503`.

Implement the explicit mapping in `backend/app/main.py`:

```python
ANALYSIS_STATUS_CODES = {
    "missing_api_key": 400,
    "invalid_api_key": 401,
    "provider_unavailable": 503,
    "analysis_failed": 502,
}
```

Use only `exc.code` and `exc.public_message` in the HTTP detail.

- [ ] **Step 10: Run the complete behavior slice and commit**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_credentials tests.test_analyzer_mvp tests.test_service_mvp tests.test_api_mvp tests.test_dashboard_mvp -v
```

Expected: all tests pass.

Commit:

```powershell
git add backend/app/errors.py backend/app/credentials.py backend/app/analyzer.py backend/app/service.py backend/app/main.py backend/app/models.py tests/test_credentials.py tests/test_analyzer_mvp.py tests/test_service_mvp.py tests/test_api_mvp.py tests/test_dashboard_mvp.py
git commit -m "fix: validate provider credentials before collection"
```

---

### Task 2: Add the single-command process supervisor

**Files:**
- Create: `run_app.py`
- Create: `tests/test_run_app.py`

**Interfaces:**
- Produces: `build_commands(python_executable: str) -> tuple[list[str], list[str]]`.
- Produces: `stop_process(process, *, timeout: float = 5.0) -> None`.
- Produces: `run(*, popen=subprocess.Popen, sleep=time.sleep, python_executable=sys.executable) -> int`.
- Produces: `main() -> int` and `raise SystemExit(main())` script entry point.

- [ ] **Step 1: Write failing supervisor tests**

Create deterministic `FakeProcess` and `FakePopen` test doubles. Cover:

```python
def test_commands_use_current_python_without_a_shell(self):
    backend, dashboard = build_commands(r"C:\Python\python.exe")
    self.assertEqual(backend[:3], [r"C:\Python\python.exe", "-m", "uvicorn"])
    self.assertIn("backend.app.main:app", backend)
    self.assertEqual(dashboard[:4], [r"C:\Python\python.exe", "-m", "streamlit", "run"])
    self.assertIn("dashboard/streamlit_app.py", dashboard)

def test_ctrl_c_terminates_and_waits_for_both_children(self):
    # Inject sleep that raises KeyboardInterrupt after both starts.
    self.assertEqual(run(popen=fake_popen, sleep=interrupting_sleep), 0)
    self.assertTrue(all(process.terminated and process.waited for process in fake_popen.processes))

def test_peer_exit_stops_survivor_and_returns_failure(self):
    # Backend poll returns 2 while Streamlit remains active.
    self.assertEqual(run(popen=fake_popen, sleep=lambda _: None), 2)
    self.assertTrue(streamlit.terminated)

def test_second_start_failure_stops_first_child(self):
    # Popen raises OSError for Streamlit after starting Uvicorn.
    self.assertEqual(run(popen=fake_popen), 1)
    self.assertTrue(backend.terminated)

def test_stubborn_child_is_killed_after_graceful_timeout(self):
    stop_process(stubborn_process, timeout=0)
    self.assertTrue(stubborn_process.killed)
```

- [ ] **Step 2: Run supervisor tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_run_app -v
```

Expected: import failure because root `run_app.py` does not exist.

- [ ] **Step 3: Implement the minimal lifecycle supervisor**

Implement `run_app.py` with:

```python
PROJECT_ROOT = Path(__file__).resolve().parent
POLL_INTERVAL_SECONDS = 0.1
SHUTDOWN_TIMEOUT_SECONDS = 5.0


def build_commands(python_executable: str) -> tuple[list[str], list[str]]:
    backend = [python_executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"]
    dashboard = [python_executable, "-m", "streamlit", "run", "dashboard/streamlit_app.py", "--server.address", "127.0.0.1", "--server.port", "8501", "--server.headless", "true"]
    return backend, dashboard
```

`run` must start children with `popen(command, cwd=PROJECT_ROOT)` and no `shell=True`, poll both, return a nonzero status when either exits, catch `KeyboardInterrupt` as a normal user shutdown, and execute `stop_process` for both children in `finally`. `stop_process` skips an already-exited child, otherwise calls `terminate()`, waits with the bounded timeout, then calls `kill()` and waits again after `subprocess.TimeoutExpired`.

- [ ] **Step 4: Run supervisor tests and verify GREEN**

Run the command from Step 2. Expected: all supervisor lifecycle tests pass.

- [ ] **Step 5: Commit the supervisor**

```powershell
git add run_app.py tests/test_run_app.py
git commit -m "feat: start the complete app with one command"
```

---

### Task 3: Document every retained Python file

**Files:**
- Modify: every retained `*.py` under `backend/`, `dashboard/`, and `tests/`
- Modify: `run_app.py`
- Create: `tests/test_documentation.py`

**Interfaces:**
- No runtime interface changes.
- Produces a structural test that excludes `.venv`, `.git`, `.codex_runtime`, and generated cache directories.

- [ ] **Step 1: Write the failing docstring-coverage test**

Create `tests/test_documentation.py` that parses each retained Python file with `ast.parse` and reports relative paths and qualified names for any module, class, function, async function, or test helper without a nonblank docstring. Ignore nested lambdas because they cannot carry docstrings. The assertion failure must list all omissions in one run.

- [ ] **Step 2: Run the documentation test and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_documentation -v
```

Expected: failures listing the currently undocumented modules, functions, classes, and helpers.

- [ ] **Step 3: Add descriptive documentation by responsibility**

Apply this exact standard to each file:

- `models.py`: explain that Pydantic is the shared HTTP/agent contract; document every schema and the `Literal` aliases.
- `collector.py`: document public-address validation, redirect revalidation, streamed size enforcement, JSON-LD preference, conservative HTML fallback, normalization/deduplication, and why arbitrary paragraphs are rejected.
- `errors.py`: explain the safe error boundary.
- `credentials.py`: explain non-generative preflight, provider constants, short timeout, status mapping, and deliberate non-use of response bodies.
- `analyzer.py`: explain the evidence-only prompt, lazy provider imports, model-construction safeguard, one-agent invocation, and exact review-ID validation.
- `service.py`: explain deterministic metrics and why preflight is first.
- `main.py`: explain the API boundary and stable status mappings.
- `api_client.py`: explain short health versus long analysis timeouts and safe JSON error parsing.
- `streamlit_app.py`: explain configuration/CSS tokens, pure formatting helpers, report stages, session-state replacement, and safe error rendering.
- `run_app.py`: explain current-interpreter reuse, argument-list commands, peer lifecycle, graceful/forced shutdown, and exit semantics.
- Test modules: add module docstrings, helper/fake docstrings describing the boundary they simulate, class docstrings grouping behavior, and test-method docstrings stating the regression contract.
- `tests/__init__.py`: replace the blank file with a package docstring.

Do not add comments such as `# increment count`, `# return result`, or `# import requests`. Comments must explain purpose, ordering, security constraints, or non-obvious trade-offs.

- [ ] **Step 4: Run documentation and behavior tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_documentation -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit Python documentation**

```powershell
git add backend dashboard run_app.py tests
git commit -m "docs: explain Python application boundaries"
```

---

### Task 4: Remove obsolete artifacts and prevent regeneration

**Files:**
- Modify: `.gitignore`
- Delete: `docs/superpowers/designs/website-analysis-history.png`
- Delete: `docs/superpowers/designs/website-review-intelligence-dashboard.png`
- Delete: `docs/superpowers/plans/2026-07-10-website-review-intelligence.md`
- Delete: `docs/superpowers/plans/2026-07-13-simple-review-insights-mvp.md`
- Delete: `docs/superpowers/specs/2026-07-10-website-review-intelligence-design.md`
- Delete: `docs/superpowers/specs/2026-07-13-simple-review-insights-mvp-design.md`
- Delete generated workspace paths: `tmp/`, `data/`, every `__pycache__/`, and stale bytecode-only directories under `backend/app`, `dashboard`, `scripts`, `reviews`, and `tests`

**Interfaces:**
- Repository retains active source, tests, fixture, README, current architecture/status docs, and the current approved spec/plan.

- [ ] **Step 1: Record the cleanup allowlist and verify targets**

Run `git ls-files`, `rg --files --hidden -g '!.git/**'`, and a recursive file listing. Confirm every tracked deletion is superseded by current documentation and every generated deletion resolves inside the repository root. Confirm `.env`, `.venv`, `.vscode`, and `.codex_runtime` are absent from the removal list.

- [ ] **Step 2: Update `.gitignore`**

Replace the narrow database entries with root-scoped runtime exclusions:

```gitignore
# ReviewInsight generated runtime output
/data/
/tmp/
```

Retain the existing generic Python `__pycache__/` and `*.py[codz]` rules.

- [ ] **Step 3: Remove tracked obsolete documentation with `apply_patch`**

Delete the six historical documents/images listed above. Do not delete the current design or implementation plan.

- [ ] **Step 4: Remove generated directories with verified PowerShell paths**

Resolve the repository root and each candidate. Refuse any target whose absolute path is outside the root. Use `Remove-Item -LiteralPath ... -Recurse -Force` only after this check. Preserve the four user/runtime directories named in Global Constraints.

- [ ] **Step 5: Audit the resulting repository and commit**

Run:

```powershell
git status --short
git diff --check
rg --files --hidden -g '!.git/**' -g '!.venv/**' -g '!.vscode/**' -g '!.codex_runtime/**'
```

Expected: no old database/history design artifacts, `.pyc`, `__pycache__`, database, or `tmp` output remains.

Commit:

```powershell
git add .gitignore docs/superpowers
git commit -m "chore: remove obsolete project artifacts"
```

---

### Task 5: Update operational documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/project_status.md`
- Modify: `.env.example`

**Interfaces:**
- Documents the single startup command and exact credential preflight behavior.

- [ ] **Step 1: Update README and current docs**

README sections must cover:

1. Purpose and concise architecture.
2. Supported static-review sources and limits.
3. Installation and required `GOOGLE_API_KEY` / `GROQ_API_KEY` variables.
4. One-command startup using `.\.venv\Scripts\python.exe run_app.py`.
5. Credential preflight order, non-generative endpoints, and safe failure behavior.
6. Project structure with one line per retained runtime/test/documentation path.
7. API example and public error codes/statuses.
8. Complete test commands.
9. Troubleshooting for missing/invalid credentials, provider availability, occupied ports, and child-process exits.

Architecture must show preflight before collection and describe supervisor ownership. Project status must replace historical verification prose with the final current feature/test inventory and date. `.env.example` must contain only active configuration names with blank secret values and current model defaults.

- [ ] **Step 2: Scan documentation for obsolete behavior**

Run:

```powershell
rg -n -i "two-terminal|no launcher|history|sqlite|database|scripts\\run_app|analysis/website|REVIEWINSIGHT_DB|local model|fallback analysis" README.md docs/architecture.md docs/project_status.md .env.example
```

Expected: no obsolete runtime claim remains. Legitimate statements that databases/history are non-goals may remain only in the limitations section.

- [ ] **Step 3: Commit operational documentation**

```powershell
git add README.md docs/architecture.md docs/project_status.md .env.example
git commit -m "docs: explain startup and credential validation"
```

---

### Task 6: Full verification and startup/shutdown smoke test

**Files:**
- Modify only if verification reveals a demonstrated defect; any fix requires a new failing regression test first.

**Interfaces:**
- Verifies the complete user-visible outcome without a browser.

- [ ] **Step 1: Run the complete automated suite**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: zero failures and zero errors.

- [ ] **Step 2: Compile every retained Python file**

```powershell
.\.venv\Scripts\python.exe -m compileall -q backend dashboard tests run_app.py
```

Expected: exit code `0`. Remove the generated `__pycache__` directories afterward using the verified cleanup procedure.

- [ ] **Step 3: Verify missing-key behavior through the real API boundary**

Start the application with provider variables removed from the child environment, call `POST /api/analyze` with a valid public-shaped URL and provider `google`, and assert the response is `400 missing_api_key`. Because the preflight is first, this check must not make a website request or model call.

- [ ] **Step 4: Verify supervisor startup and shutdown without an in-app browser**

Start `.\.venv\Scripts\python.exe run_app.py` as a hidden background process. Poll `http://127.0.0.1:8000/health` and `http://127.0.0.1:8501/_stcore/health` until both return success or a bounded deadline expires. Stop the supervisor, wait for cleanup, then verify ports `8000` and `8501` have no listeners owned by the launched process tree.

- [ ] **Step 5: Run final repository and diff audits**

```powershell
git status --short
git diff --check
rg --files --hidden -g '!.git/**' -g '!.venv/**' -g '!.vscode/**' -g '!.codex_runtime/**'
rg -n "GOOGLE_API_KEY=.+|GROQ_API_KEY=.+|Authorization: Bearer [^\"']|x-goog-api-key.*[A-Za-z0-9]{16}" -g '!*.md' -g '!.env' .
```

Expected: only intentional changes, no whitespace errors, only retained files, and no committed secret values.

- [ ] **Step 6: Re-read the approved specification and report evidence**

Check every requirement in `docs/superpowers/specs/2026-07-13-single-command-credential-preflight-design.md` against the final diff and fresh command output. Report exact test count, compile result, health-check result, shutdown result, cleanup summary, and any verification limitation.
