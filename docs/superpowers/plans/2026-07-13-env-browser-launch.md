# Environment Loading and Browser Launch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `run_app.py` load the repository-root `.env` without overriding existing variables and open the ready Streamlit dashboard once in the operating system's default browser.

**Architecture:** The root supervisor owns configuration loading, readiness probing, browser launch, and both child processes. Small injectable boundaries around dotenv loading, HTTP readiness, browser opening, and user-safe reporting keep the behavior deterministic under unit tests while production defaults use `python-dotenv`, `urllib.request`, and `webbrowser`.

**Tech Stack:** Python 3.12+, `python-dotenv`, standard-library `urllib.request`, standard-library `webbrowser`, `unittest`.

## Global Constraints

- Existing process environment values take precedence over `.env` values.
- Resolve `.env` relative to `PROJECT_ROOT`, not the caller's working directory.
- Keep subprocess commands as argument lists with no shell.
- Open `http://127.0.0.1:8501` only after `http://127.0.0.1:8501/_stcore/health` succeeds and at most once per supervisor run.
- A missing `.env` is valid; an exception while loading it stops startup before either child begins.
- Browser launch failure reports the manual URL but does not stop either service.
- Do not print, log, commit, or return credential values.
- Do not use Codex's built-in browser; interactive browser verification, if needed, uses the user's Google Chrome session.

---

## File Structure

- `run_app.py`: Own project environment loading, Streamlit health probing, default-browser launch, and existing peer supervision.
- `tests/test_run_app.py`: Define regression contracts for `.env` precedence/path, readiness ordering, one-time browser opening, safe failures, and existing cleanup semantics.
- `requirements.txt`: Add the bounded `python-dotenv` runtime dependency.
- `README.md`: Replace shell-only configuration guidance with `.env` plus precedence behavior and automatic dashboard opening.
- `docs/architecture.md`: Record environment propagation and readiness-gated browser ownership at the supervisor boundary.
- `docs/project_status.md`: Update the implemented startup capability and verification inventory.

### Task 1: Project-root dotenv loading

**Files:**
- Modify: `requirements.txt`
- Modify: `run_app.py`
- Test: `tests/test_run_app.py`

**Interfaces:**
- Produces: `load_project_environment(*, loader=load_dotenv) -> None`
- Changes: `run(*, load_environment=load_project_environment, ...) -> int`
- Consumes: `PROJECT_ROOT: pathlib.Path`

- [ ] **Step 1: Add failing environment-loading tests**

Update the test imports and add a recording loader:

```python
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from run_app import (
    PROJECT_ROOT,
    build_commands,
    load_project_environment,
    run,
    stop_process,
)


class RecordingEnvironmentLoader:
    def __init__(self, *, error=None):
        """Configure optional failure and initialize recorded calls."""

        self.error = error
        self.calls = []

    def __call__(self, *args, **kwargs):
        """Record a dotenv call or raise the configured safe-test error."""

        self.calls.append((args, kwargs))
        if self.error is not None:
            raise self.error
```

Add these test methods to `RunAppTests`:

```python
def test_project_environment_loads_root_dotenv_without_override(self):
    """Anchor dotenv loading to the project root and preserve parent values."""

    loader = RecordingEnvironmentLoader()

    load_project_environment(loader=loader)

    self.assertEqual(
        loader.calls,
        [((PROJECT_ROOT / ".env",), {"override": False})],
    )

def test_existing_environment_value_takes_precedence_over_dotenv(self):
    """Keep a process value when the project dotenv defines the same name."""

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / ".env").write_text(
            "GROQ_API_KEY=dotenv-value\n",
            encoding="utf-8",
        )
        with (
            patch("run_app.PROJECT_ROOT", root),
            patch.dict(os.environ, {"GROQ_API_KEY": "process-value"}, clear=True),
        ):
            load_project_environment()
            self.assertEqual(os.environ["GROQ_API_KEY"], "process-value")

def test_environment_load_failure_stops_before_child_start(self):
    """Return safely before starting children when dotenv loading raises."""

    loader = RecordingEnvironmentLoader(error=OSError("secret file details"))
    fake_popen = FakePopen([])
    messages = []

    self.assertEqual(
        run(
            popen=fake_popen,
            load_environment=lambda: load_project_environment(loader=loader),
            report=messages.append,
        ),
        1,
    )

    self.assertEqual(fake_popen.calls, [])
    self.assertEqual(
        messages,
        [f"Could not load configuration from {PROJECT_ROOT / '.env'}."],
    )
    self.assertNotIn("secret file details", messages[0])
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_run_app.RunAppTests.test_project_environment_loads_root_dotenv_without_override tests.test_run_app.RunAppTests.test_existing_environment_value_takes_precedence_over_dotenv tests.test_run_app.RunAppTests.test_environment_load_failure_stops_before_child_start -v
```

Expected: import failure because `load_project_environment` does not exist.

- [ ] **Step 3: Add the dependency and minimal environment implementation**

Add to `requirements.txt`:

```text
python-dotenv>=1.0,<2
```

Add the production import and function to `run_app.py`:

```python
from dotenv import load_dotenv


def load_project_environment(*, loader=load_dotenv) -> None:
    """Load project settings without replacing the parent environment."""

    loader(PROJECT_ROOT / ".env", override=False)
```

Extend `run` with injected loading and reporting boundaries, and perform loading before child construction or startup:

```python
def run(
    *,
    popen=subprocess.Popen,
    sleep=time.sleep,
    python_executable=sys.executable,
    load_environment=load_project_environment,
    report=print,
) -> int:
    """Supervise both peers after safely loading project configuration."""

    backend = None
    dashboard = None
    try:
        load_environment()
    except Exception:
        report(f"Could not load configuration from {PROJECT_ROOT / '.env'}.")
        return 1

    backend_command, dashboard_command = build_commands(python_executable)
    try:
        backend = popen(backend_command, cwd=PROJECT_ROOT)
        dashboard = popen(dashboard_command, cwd=PROJECT_ROOT)
        while True:
            for process in (backend, dashboard):
                returncode = process.poll()
                if returncode is not None:
                    return returncode or 1
            sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        return 0
    except OSError:
        return 1
    finally:
        for process in (backend, dashboard):
            if process is not None:
                stop_process(process)
```

The broad exception boundary is intentionally limited to third-party configuration loading, converts failures to a safe status, and runs before any child exists.

- [ ] **Step 4: Install the declared dependency**

Run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Expected: exit code `0`, with `python-dotenv` installed or already satisfied.

- [ ] **Step 5: Run launcher tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_run_app -v
```

Expected: all launcher tests pass. Existing `run(...)` calls use the real loader against a missing-or-present `.env`; because loading an existing valid `.env` is allowed and secrets are never asserted, tests remain safe.

- [ ] **Step 6: Commit the environment-loading task**

```powershell
git add requirements.txt run_app.py tests/test_run_app.py
git commit -m "fix: load project environment before startup"
```

### Task 2: Readiness-gated one-time browser launch

**Files:**
- Modify: `run_app.py`
- Test: `tests/test_run_app.py`

**Interfaces:**
- Produces: `dashboard_is_ready(*, urlopen=urllib.request.urlopen) -> bool`
- Changes: `run(*, dashboard_ready=dashboard_is_ready, open_browser=webbrowser.open, ...) -> int`
- Consumes: `DASHBOARD_URL: str`, `DASHBOARD_HEALTH_URL: str`, `READINESS_REQUEST_TIMEOUT_SECONDS: float`

- [ ] **Step 1: Add a fake health response and failing probe tests**

Add to `tests/test_run_app.py`:

```python
from urllib.error import URLError

from run_app import (
    DASHBOARD_HEALTH_URL,
    READINESS_REQUEST_TIMEOUT_SECONDS,
    dashboard_is_ready,
)


class FakeHealthResponse:
    def __init__(self, status):
        """Store the HTTP status returned by the fake context manager."""

        self.status = status

    def __enter__(self):
        """Return this fake as the opened response context."""

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Leave the fake response context without suppressing errors."""

        return False
```

Add these test methods:

```python
def test_dashboard_readiness_uses_local_health_endpoint_and_timeout(self):
    """Probe Streamlit's fixed local health URL with a bounded timeout."""

    calls = []

    def urlopen(url, *, timeout):
        """Record the readiness request and return a healthy response."""

        calls.append((url, timeout))
        return FakeHealthResponse(200)

    self.assertTrue(dashboard_is_ready(urlopen=urlopen))
    self.assertEqual(
        calls,
        [(DASHBOARD_HEALTH_URL, READINESS_REQUEST_TIMEOUT_SECONDS)],
    )

def test_dashboard_readiness_treats_transient_failures_as_not_ready(self):
    """Convert local connection failures into a retryable not-ready result."""

    cases = [URLError("not listening"), OSError("socket unavailable")]
    for error in cases:
        with self.subTest(error=error):
            def urlopen(url, *, timeout, error=error):
                """Raise one configured transient readiness error."""

                raise error

            self.assertFalse(dashboard_is_ready(urlopen=urlopen))
```

- [ ] **Step 2: Run probe tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_run_app.RunAppTests.test_dashboard_readiness_uses_local_health_endpoint_and_timeout tests.test_run_app.RunAppTests.test_dashboard_readiness_treats_transient_failures_as_not_ready -v
```

Expected: import failure because readiness constants and `dashboard_is_ready` do not exist.

- [ ] **Step 3: Implement the minimal readiness probe**

Add to `run_app.py`:

```python
import urllib.request
import webbrowser
from urllib.error import URLError

DASHBOARD_URL = "http://127.0.0.1:8501"
DASHBOARD_HEALTH_URL = f"{DASHBOARD_URL}/_stcore/health"
READINESS_REQUEST_TIMEOUT_SECONDS = 0.25


def dashboard_is_ready(*, urlopen=urllib.request.urlopen) -> bool:
    """Return whether Streamlit's local health endpoint is ready."""

    try:
        with urlopen(
            DASHBOARD_HEALTH_URL,
            timeout=READINESS_REQUEST_TIMEOUT_SECONDS,
        ) as response:
            return response.status == 200
    except (OSError, URLError):
        return False
```

- [ ] **Step 4: Run probe tests and verify GREEN**

Run the focused command from Step 2.

Expected: both readiness tests pass.

- [ ] **Step 5: Add failing browser-ordering tests**

Add this deterministic sequence helper to `tests/test_run_app.py`:

```python
class SequenceResult:
    def __init__(self, values):
        """Create an iterator over deterministic readiness results."""

        self.values = iter(values)

    def __call__(self):
        """Return the next configured readiness value."""

        return next(self.values)
```

Add these test methods:

```python
def test_browser_opens_once_only_after_dashboard_is_ready(self):
    """Open the dashboard once after readiness and never before it."""

    fake_popen = FakePopen([FakeProcess(), FakeProcess()])
    readiness = SequenceResult([False, True])
    opened = []
    sleep_calls = 0

    def sleep(_):
        """Stop the simulated supervisor after three polling passes."""

        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 3:
            raise KeyboardInterrupt

    self.assertEqual(
        run(
            popen=fake_popen,
            sleep=sleep,
            load_environment=lambda: None,
            dashboard_ready=readiness,
            open_browser=lambda url: opened.append(url) or True,
        ),
        0,
    )

    self.assertEqual(opened, [DASHBOARD_URL])

def test_browser_failure_reports_manual_url_and_keeps_supervising(self):
    """Report a manual URL while preserving supervision on a false result."""

    fake_popen = FakePopen([FakeProcess(), FakeProcess()])
    messages = []
    sleep_calls = 0

    def sleep(_):
        """Stop the simulated supervisor after browser failure is observed."""

        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 2:
            raise KeyboardInterrupt

    self.assertEqual(
        run(
            popen=fake_popen,
            sleep=sleep,
            load_environment=lambda: None,
            dashboard_ready=lambda: True,
            open_browser=lambda _: False,
            report=messages.append,
        ),
        0,
    )

    self.assertEqual(
        messages,
        [f"Open {DASHBOARD_URL} manually; the default browser could not be started."],
    )
    self.assertTrue(all(process.terminated for process in fake_popen.processes))

def test_browser_exception_is_safe_and_not_retried(self):
    """Sanitize a browser exception and keep the launch attempt one-shot."""

    fake_popen = FakePopen([FakeProcess(), FakeProcess()])
    messages = []
    attempts = 0
    sleep_calls = 0

    def open_browser(_):
        """Raise a browser error containing details that must stay private."""

        nonlocal attempts
        attempts += 1
        raise OSError("browser internals")

    def sleep(_):
        """Stop after enough polls to expose any incorrect browser retry."""

        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 2:
            raise KeyboardInterrupt

    self.assertEqual(
        run(
            popen=fake_popen,
            sleep=sleep,
            load_environment=lambda: None,
            dashboard_ready=lambda: True,
            open_browser=open_browser,
            report=messages.append,
        ),
        0,
    )

    self.assertEqual(attempts, 1)
    self.assertNotIn("browser internals", messages[0])
```

- [ ] **Step 6: Run browser tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_run_app.RunAppTests.test_browser_opens_once_only_after_dashboard_is_ready tests.test_run_app.RunAppTests.test_browser_failure_reports_manual_url_and_keeps_supervising tests.test_run_app.RunAppTests.test_browser_exception_is_safe_and_not_retried -v
```

Expected: `run()` rejects the new `dashboard_ready` or `open_browser` keyword arguments.

- [ ] **Step 7: Implement one-time readiness-gated opening**

Extend the `run` signature:

```python
def run(
    *,
    popen=subprocess.Popen,
    sleep=time.sleep,
    python_executable=sys.executable,
    load_environment=load_project_environment,
    dashboard_ready=dashboard_is_ready,
    open_browser=webbrowser.open,
    report=print,
) -> int:
```

After starting both children, initialize `browser_attempted = False`. Inside the existing supervision loop, after polling both processes and before sleeping, add:

```python
if not browser_attempted and dashboard_ready():
    browser_attempted = True
    try:
        browser_opened = open_browser(DASHBOARD_URL)
    except Exception:
        browser_opened = False
    if not browser_opened:
        report(
            f"Open {DASHBOARD_URL} manually; "
            "the default browser could not be started."
        )
```

Setting `browser_attempted` before the external call guarantees at-most-once behavior for both false returns and exceptions.

Update the existing `test_ctrl_c_terminates_and_waits_for_both_children` call so a unit test never probes or opens an unrelated local browser:

```python
self.assertEqual(
    run(
        popen=fake_popen,
        sleep=interrupting_sleep,
        dashboard_ready=lambda: False,
    ),
    0,
)
```

- [ ] **Step 8: Run all launcher tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_run_app -v
```

Expected: all launcher tests pass with no unexpected warnings or tracebacks.

- [ ] **Step 9: Commit readiness and browser behavior**

```powershell
git add run_app.py tests/test_run_app.py
git commit -m "feat: open dashboard when ready"
```

### Task 3: Documentation and end-to-end verification

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/project_status.md`
- Test: all retained test modules and runtime startup

**Interfaces:**
- Consumes: the finalized `.env` precedence and readiness-gated browser behavior from Tasks 1 and 2.
- Produces: accurate installation, startup, architecture, and verification documentation.

- [ ] **Step 1: Add failing documentation assertions**

Add this method to `DocumentationCoverageTests` in `tests/test_documentation.py`:

```python
def test_readme_documents_dotenv_precedence_and_automatic_browser_open(self):
    """Require startup documentation to match environment and browser behavior."""

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    self.assertIn(".env", readme)
    self.assertIn("take precedence", readme)
    self.assertIn("automatically opens", readme)
    self.assertNotIn("does not load a `.env` file itself", readme)
```

- [ ] **Step 2: Run the documentation assertion and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_documentation.DocumentationCoverageTests.test_readme_documents_dotenv_precedence_and_automatic_browser_open -v
```

Expected: failure because README still says the application does not load `.env` and requires manual opening.

- [ ] **Step 3: Update user and architecture documentation**

Change README configuration examples to support either a repository-root `.env`:

```dotenv
GOOGLE_API_KEY=your-gemini-key
GROQ_API_KEY=your-groq-key
```

or existing PowerShell environment variables. State explicitly:

```text
Values already set in the shell or system environment take precedence over matching `.env` entries.
```

Change startup guidance to state:

```text
After Streamlit becomes ready, the launcher automatically opens http://127.0.0.1:8501 in the operating system's default browser. If no browser can be opened, use the printed URL manually.
```

Update `docs/architecture.md` to show supervisor-owned `.env` loading before child launch and readiness-gated default-browser opening. Update `docs/project_status.md` to list the implemented behavior and its launcher tests.

- [ ] **Step 4: Run the documentation assertion and verify GREEN**

Run the same command from Step 2.

Expected: the new documentation test passes.

- [ ] **Step 5: Run the full automated suite**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: all tests pass with no unexpected warnings or tracebacks.

- [ ] **Step 6: Compile all retained Python files**

```powershell
.\.venv\Scripts\python.exe -m compileall -q backend dashboard tests run_app.py
```

Expected: exit code `0`.

- [ ] **Step 7: Verify real child readiness without opening any browser**

Start the supervisor as a hidden background process with browser launch suppressed through a short verification harness that imports `run_app` and calls `run(open_browser=lambda _: True)`. Poll both local health endpoints until ready or a bounded deadline expires:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8501/_stcore/health
```

Then stop the supervisor, wait for cleanup, and confirm ports `8000` and `8501` have no remaining listeners. Never print or inspect any credential value.

- [ ] **Step 8: Audit the final diff and secret safety**

```powershell
git diff --check
git status --short
rg -n "GOOGLE_API_KEY=.+|GROQ_API_KEY=.+|Authorization: Bearer [^\"']|x-goog-api-key.*[A-Za-z0-9]{16}" -g '!*.md' -g '!.env' .
```

Expected: only intentional files are changed, whitespace checks pass, `.env` is untracked/ignored, and no credential values appear in tracked source.

- [ ] **Step 9: Commit documentation and verification contracts**

```powershell
git add README.md docs/architecture.md docs/project_status.md tests/test_documentation.py
git commit -m "docs: explain dotenv and automatic browser startup"
```
