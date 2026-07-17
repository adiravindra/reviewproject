# Reliable Launch and Analysis UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent the dashboard from opening before FastAPI is ready and deliver a responsive, professionally organized analysis report.

**Architecture:** Preserve the two-process FastAPI/Streamlit topology and make `run_app.py` own a combined, bounded readiness gate. Refactor the Streamlit presentation through small escaped-markup helpers and semantic CSS while keeping collection, analysis, and history HTTP contracts unchanged.

**Tech Stack:** Python 3.12, FastAPI, Streamlit, requests, unittest, Google Chrome

## Global Constraints

- `run_app.py` remains the only supported complete-application launcher.
- The browser opens only after both `GET /health` on port 8000 and Streamlit `/_stcore/health` on port 8501 succeed.
- Startup readiness is bounded to 30 seconds.
- Existing FastAPI request and response contracts do not change.
- Positive, neutral, negative, and mixed states use text, icons, and distinct accessible colors.
- Untrusted source, review, and model text is escaped before styled HTML rendering.
- Live extraction never falls back to demo data implicitly.
- Verification uses installed Google Chrome, not the in-app browser.

---

### Task 1: Combined supervisor readiness

**Files:**
- Modify: `run_app.py`
- Modify: `tests/test_run_app.py`

**Interfaces:**
- Consumes: FastAPI `GET /health` returning `{"status":"ok"}` and Streamlit `GET /_stcore/health` returning HTTP 200.
- Produces: `backend_is_ready(*, urlopen=...) -> bool`, `dashboard_is_ready(*, urlopen=...) -> bool`, and `run(..., backend_ready=..., dashboard_ready=..., monotonic=...) -> int`.

- [ ] **Step 1: Write failing readiness tests**

Add tests that inject independent backend and dashboard readiness sequences:

```python
def test_browser_waits_until_backend_and_dashboard_are_ready(self):
    backend_ready = SequenceResult([False, True])
    dashboard_ready = SequenceResult([True, True])
    opened = []
    sleep_calls = 0

    def sleep(_):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 3:
            raise KeyboardInterrupt

    result = run(
        popen=FakePopen([FakeProcess(), FakeProcess()]),
        sleep=sleep,
        load_environment=lambda: None,
        backend_ready=backend_ready,
        dashboard_ready=dashboard_ready,
        open_browser=lambda url: opened.append(url) or True,
    )

    self.assertEqual(result, 0)
    self.assertEqual(opened, [DASHBOARD_URL])
```

Add a probe-contract test for `BACKEND_HEALTH_URL` and a startup-timeout test
using an injected monotonic sequence. The timeout test must assert a nonzero
result, both children terminated, the browser was not opened, and the exact
message `The application did not become ready within 30 seconds.`

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_run_app -v
```

Expected: failures because `backend_is_ready`, `BACKEND_HEALTH_URL`,
`STARTUP_TIMEOUT_SECONDS`, and the new injected arguments do not exist.

- [ ] **Step 3: Implement combined bounded readiness**

Add:

```python
BACKEND_URL = "http://127.0.0.1:8000"
BACKEND_HEALTH_URL = f"{BACKEND_URL}/health"
STARTUP_TIMEOUT_SECONDS = 30.0

def backend_is_ready(*, urlopen=urllib.request.urlopen) -> bool:
    try:
        with urlopen(
            BACKEND_HEALTH_URL,
            timeout=READINESS_REQUEST_TIMEOUT_SECONDS,
        ) as response:
            return response.status == 200 and json.load(response) == {"status": "ok"}
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return False
```

Capture `startup_started = monotonic()` after both children launch. Inside the
supervision loop, open the browser only when
`backend_ready() and dashboard_ready()` is true. Before sleeping, return `1`
with the exact safe timeout message when
`monotonic() - startup_started >= STARTUP_TIMEOUT_SECONDS`.

- [ ] **Step 4: Run supervisor tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_run_app -v
```

Expected: all supervisor tests pass.

- [ ] **Step 5: Commit the supervisor fix**

```powershell
git add run_app.py tests/test_run_app.py
git commit -m "fix: wait for complete application readiness"
```

### Task 2: Semantic dashboard presentation primitives

**Files:**
- Modify: `dashboard/streamlit_app.py`
- Modify: `tests/test_dashboard_mvp.py`

**Interfaces:**
- Consumes: existing `SentimentVisual`, collection dictionaries, and analysis-response dictionaries.
- Produces: `safe_panel_markup(...) -> str`, `safe_metric_card_markup(...) -> str`, `format_history_timestamp(value: Any) -> str`, and the expanded `DASHBOARD_CSS` token system.

- [ ] **Step 1: Write failing formatting tests**

Add tests proving that:

```python
markup = safe_metric_card_markup(
    label="<Reviews>",
    value="5",
    detail="Analyzed",
    semantic="positive",
)
self.assertNotIn("<Reviews>", markup)
self.assertIn("&lt;Reviews&gt;", markup)
self.assertIn("ri-metric-card", markup)
self.assertIn("ri-positive", markup)
```

Also assert `safe_panel_markup` escapes its heading and every item, history
timestamps drop microseconds/timezone suffixes, and `DASHBOARD_CSS` includes
`.ri-report-hero`, `.ri-metric-grid`, `.ri-insight-grid`,
`.ri-theme-grid`, `.ri-chart-card`, plus mobile and tablet media queries.

- [ ] **Step 2: Run the focused formatting tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_mvp.DashboardFormattingTests -v
```

Expected: failures for missing helpers and CSS selectors.

- [ ] **Step 3: Implement escaped semantic helpers and tokens**

Implement helpers using `html.escape(str(value))` for every dynamic value.
`safe_panel_markup` must render a semantic class, icon, heading, and an escaped
unordered list. `safe_metric_card_markup` must render label, value, and detail
inside one `.ri-metric-card`. Add reusable surface, shadow, radius, spacing,
typography, semantic, responsive grid, and sidebar tokens to `DASHBOARD_CSS`.

- [ ] **Step 4: Run formatting tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_mvp.DashboardFormattingTests -v
```

Expected: all dashboard formatting tests pass.

- [ ] **Step 5: Commit presentation primitives**

```powershell
git add dashboard/streamlit_app.py tests/test_dashboard_mvp.py
git commit -m "feat: add semantic report presentation primitives"
```

### Task 3: Refactor the staged dashboard and report layout

**Files:**
- Modify: `dashboard/streamlit_app.py`
- Modify: `tests/test_dashboard_mvp.py`

**Interfaces:**
- Consumes: Task 2 helpers and all existing API client functions.
- Produces: redesigned `_render_source`, `_render_evidence`, `_render_themes`, `_render_report`, `_render_history`, and `main` without changing their HTTP behavior.

- [ ] **Step 1: Write failing source-structure tests**

Extend the dashboard source audit to require:

```python
self.assertIn('st.expander("Supporting review evidence"', source)
self.assertIn("Executive summary", source)
self.assertIn("Customer signals", source)
self.assertIn("Recommended actions", source)
self.assertIn("How it works", source)
self.assertNotIn('st.header("Extracted reviews (evidence)")', source)
```

Keep existing assertions that no provider selector, credential input, or
implicit demo fallback is present.

- [ ] **Step 2: Run dashboard tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_mvp -v
```

Expected: source-structure assertions fail against the old layout.

- [ ] **Step 3: Implement the staged workspace layout**

Refactor `main()` to render:

- an eyebrow/title/subtitle hero;
- a bordered extraction workspace;
- a three-step **How it works** strip;
- side-by-side primary extraction and demo actions on desktop;
- a grouped source summary and evidence section after successful extraction.

Do not change `_new_collection`, `analysis_call`, API payloads, or session-state
keys.

- [ ] **Step 4: Implement the report scan order**

Refactor `_render_report()` to render the report hero, a CSS metric grid,
executive summary, chart cards, a responsive theme grid, three semantic insight
panels, and:

```python
with st.expander("Supporting review evidence", expanded=False):
    _render_source(...)
    _render_evidence(..., compact=True)
```

The original pre-analysis evidence remains visible. Only the duplicate
post-analysis evidence is collapsed.

- [ ] **Step 5: Run all dashboard tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_mvp -v
```

Expected: all dashboard client and formatting tests pass.

- [ ] **Step 6: Commit the dashboard refactor**

```powershell
git add dashboard/streamlit_app.py tests/test_dashboard_mvp.py
git commit -m "feat: redesign review analysis workspace"
```

### Task 4: Documentation and complete verification

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/project_status.md`
- Test: all files under `tests/`

**Interfaces:**
- Consumes: completed launcher and dashboard.
- Produces: current startup, UX, and verification documentation.

- [ ] **Step 1: Update operational documentation**

Document that `run_app.py` waits for both health endpoints and fails after 30
seconds if the complete application is not ready. Update the dashboard-flow and
report-layout descriptions, while retaining the current credential, static
collection, and demo-data limitations.

- [ ] **Step 2: Run the complete automated suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q backend dashboard tests run_app.py
```

Expected: every unittest passes and compileall exits with status 0.

- [ ] **Step 3: Run the Google Chrome end-to-end workflow**

Start:

```powershell
.\.venv\Scripts\python.exe run_app.py
```

In installed Google Chrome, verify the nine scenarios in the design spec:
fresh readiness, live extraction, live Groq analysis, history restoration,
invalid URL, no-review handling, demo analysis, desktop/narrow layouts, and a
clean application console.

- [ ] **Step 4: Record exact verification results**

Update `docs/project_status.md` with the final unittest count, compileall
result, live URL review count and extractor, analysis result, history reload,
error-state results, responsive widths inspected, and Chrome console result.

- [ ] **Step 5: Commit documentation and verification record**

```powershell
git add README.md docs/architecture.md docs/project_status.md
git commit -m "docs: record reliable launch and Chrome verification"
```

