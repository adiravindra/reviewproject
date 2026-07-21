# Analysis UI and Demo Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the bundled Groq demo complete without HTTP 502 and deliver a more readable, consistently styled analysis report.

**Architecture:** Preserve the existing supervisor, FastAPI, Streamlit, Groq, and SQLite boundaries. Expand only the structured theme-sentiment contract, retain the three-state review sentiment used by deterministic metrics, and refine the report with reusable semantic markup and section-heading primitives.

**Tech Stack:** Python 3.12, Pydantic 2, LangChain, LangChain-Groq, FastAPI, Streamlit, Vega-Lite, unittest, Chrome.

## Global Constraints

- Theme sentiment supports exactly `positive`, `neutral`, `negative`, and `mixed`.
- Review sentiment supports exactly `positive`, `neutral`, and `negative`.
- Provider responses, credentials, exception internals, and tracebacks never cross the public API boundary.
- All source- and model-supplied text inserted into HTML is escaped.
- Keep `run_app.py` as the single complete-application launcher.
- Final validation must use Chrome at desktop and mobile viewport sizes.

---

### Task 1: Mixed Theme Contract and 502 Regression

**Files:**
- Modify: `tests/test_api_mvp.py`
- Modify: `tests/test_analyzer_mvp.py`
- Modify: `backend/app/models.py`
- Modify: `backend/app/analyzer.py`

**Interfaces:**
- Consumes: `Theme`, `ReviewSentiment`, `AgentInsights`, and `analyze_reviews()`.
- Produces: `ThemeSentiment = Literal["positive", "neutral", "negative", "mixed"]`; `Theme.sentiment: ThemeSentiment`; an analyzer contract that accepts mixed themes without changing review-level metrics.

- [ ] **Step 1: Write failing schema and analyzer tests**

Add a contract test that validates `Theme(..., sentiment="mixed")` and proves `ReviewSentiment(..., sentiment="mixed")` still raises `ValidationError`. Update the analyzer fixture to return one mixed theme and assert `analyze_reviews()` returns it unchanged.

```python
def test_theme_accepts_mixed_without_expanding_review_sentiment(self):
    theme = Theme(
        name="Temperature consistency",
        description="Customers report both precise and inconsistent results.",
        mentions=4,
        sentiment="mixed",
    )
    self.assertEqual(theme.sentiment, "mixed")
    with self.assertRaises(ValidationError):
        ReviewSentiment(review_id="r1", sentiment="mixed")
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_api_mvp.ApiContractTests.test_theme_accepts_mixed_without_expanding_review_sentiment tests.test_analyzer_mvp.AnalyzerTests.test_one_agent_invocation_returns_validated_evidence_only_insights -v
```

Expected: the contract test fails because `Theme.sentiment` rejects `mixed`.

- [ ] **Step 3: Implement the minimal contract fix**

Define the distinct theme alias and update only `Theme.sentiment`:

```python
Sentiment = Literal["positive", "neutral", "negative"]
ThemeSentiment = Literal["positive", "neutral", "negative", "mixed"]
OverallSentiment = Literal["positive", "neutral", "negative", "mixed"]

class Theme(BaseModel):
    sentiment: ThemeSentiment
```

Update the system prompt to state that a theme may be mixed when it contains meaningful positive and negative evidence, while review sentiments remain three-state.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: both tests pass.

- [ ] **Step 5: Commit the contract fix**

```powershell
git add backend/app/models.py backend/app/analyzer.py tests/test_api_mvp.py tests/test_analyzer_mvp.py
git commit -m "fix: accept mixed analysis themes"
```

---

### Task 2: Safe Actionable Analysis Errors

**Files:**
- Modify: `tests/test_api_mvp.py`
- Modify: `tests/test_dashboard_mvp.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `AnalysisError.code`, `ANALYSIS_ERRORS`, and dashboard `ApiClientError` rendering.
- Produces: distinct safe messages for transient provider invocation failure and invalid structured output.

- [ ] **Step 1: Write failing error-message tests**

Add assertions that `analysis_failed` returns an actionable retry message and `model_output_invalid` returns a different message, both without raw provider markers.

```python
self.assertEqual(
    analysis_failed.json()["detail"]["message"],
    "Groq could not complete the analysis. Your reviews are still available; try again.",
)
self.assertEqual(
    invalid_output.json()["detail"]["message"],
    "Groq returned an invalid analysis result. Your reviews are still available; try again.",
)
```

Add a dashboard client test proving each structured backend message reaches `ApiClientError.message` unchanged while extra response fields are discarded.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_api_mvp.ApiTests.test_analysis_and_history_errors_map_to_exact_safe_statuses tests.test_dashboard_mvp.DashboardClientTests.test_structured_api_error_is_preserved -v
```

Expected: the API assertion fails on the old generic wording.

- [ ] **Step 3: Implement the minimal safe-message change**

Update only the public mappings:

```python
"analysis_failed": (
    502,
    "Groq could not complete the analysis. Your reviews are still available; try again.",
),
"model_output_invalid": (
    502,
    "Groq returned an invalid analysis result. Your reviews are still available; try again.",
),
```

Keep the generic unexpected-exception envelope unchanged.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: both tests pass.

- [ ] **Step 5: Commit the error handling**

```powershell
git add backend/app/main.py tests/test_api_mvp.py tests/test_dashboard_mvp.py
git commit -m "fix: clarify recoverable analysis errors"
```

---

### Task 3: Report Hierarchy and Consistent Semantic Styling

**Files:**
- Modify: `tests/test_dashboard_mvp.py`
- Modify: `dashboard/streamlit_app.py`

**Interfaces:**
- Consumes: `_VISUALS`, `sentiment_visual()`, report dictionaries, and existing Streamlit render helpers.
- Produces: `safe_section_heading_markup(eyebrow, heading, description)` and `safe_panel_markup(..., semantic="info")`; refined responsive CSS and ordered report markup.

- [ ] **Step 1: Write failing markup and CSS tests**

Add tests requiring:

```python
heading = safe_section_heading_markup(
    "Analysis",
    "Customer signals",
    "Compare sentiment and rating patterns across the review set.",
)
self.assertIn('class="ri-section-heading"', heading)
self.assertIn('class="ri-section-heading__eyebrow"', heading)
self.assertNotIn("<script>", safe_section_heading_markup("<script>", "Signals", "Safe"))
```

Require the same internal anatomy for all four theme states, an informational
blue class for recommended actions, explicit section gaps, and responsive
one-column insight panels on mobile.

- [ ] **Step 2: Run dashboard formatting tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_mvp.DashboardFormattingTests -v
```

Expected: new section-heading and informational-panel assertions fail.

- [ ] **Step 3: Implement semantic layout primitives**

Add escaped section-heading markup:

```python
def safe_section_heading_markup(eyebrow: Any, heading: Any, description: Any) -> str:
    return (
        '<header class="ri-section-heading">'
        f'<span class="ri-section-heading__eyebrow">{html.escape(str(eyebrow))}</span>'
        f'<h2>{html.escape(str(heading))}</h2>'
        f'<p>{html.escape(str(description))}</p>'
        '</header>'
    )
```

Add blue informational design tokens and update `safe_panel_markup()` so
recommended actions use an information icon and `ri-info`, while strengths and
concerns retain their semantic visual objects. Use the new heading helper for
Customer signals, Recurring themes, and Customer priorities.

- [ ] **Step 4: Refine the CSS and report composition**

Implement:

- consistent `--ri-section-gap` and `--ri-card-gap` tokens;
- smaller report title and stronger metadata contrast;
- section-heading eyebrow, title, description, and vertical rhythm;
- equal-height metric, theme, chart, and insight surfaces;
- unified badge/card anatomy for positive, neutral, negative, and mixed;
- blue informational recommendation panels;
- desktop 4/2/3/3 grids, tablet 2/1/2/1 grids, and mobile stacked theme and insight grids;
- tighter mobile padding without horizontal overflow.

- [ ] **Step 5: Run dashboard formatting and runtime tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_mvp -v
```

Expected: all dashboard tests pass with no Streamlit exceptions.

- [ ] **Step 6: Commit the UI redesign**

```powershell
git add dashboard/streamlit_app.py tests/test_dashboard_mvp.py
git commit -m "feat: improve analysis report hierarchy"
```

---

### Task 4: Documentation, Full Verification, and Chrome Flow

**Files:**
- Modify: `README.md`
- Modify: `docs/project_status.md`
- Modify: `docs/architecture.md` only if the public contract description still excludes mixed themes.

**Interfaces:**
- Consumes: supported startup command, API error vocabulary, final UI behavior.
- Produces: current operator guidance and verified completion record.

- [ ] **Step 1: Update current-facing documentation**

Document mixed theme semantics, preserved evidence on retryable analysis errors,
the refined report hierarchy, and the final verification record. Do not include
API keys, raw provider responses, or diagnostic tracebacks.

- [ ] **Step 2: Run the complete automated suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q backend dashboard tests run_app.py
```

Expected: all tests pass and compilation exits 0.

- [ ] **Step 3: Start the supervised application**

Run:

```powershell
.\.venv\Scripts\python.exe run_app.py
```

Confirm `GET /health` returns `{"status":"ok"}` before Streamlit reports its
local URL.

- [ ] **Step 4: Verify the complete demo in Chrome**

Test flow:

```text
http://127.0.0.1:8501
-> Use bundled demo data
-> visible DEMO DATA provenance and 10 reviews
-> Analyze with Groq
-> complete report with no HTTP 502
-> Refresh history
-> Load selected report
```

Collect page identity, meaningful DOM, framework-overlay absence, console logs,
desktop screenshot, mobile screenshot, and interaction state evidence.

- [ ] **Step 5: Commit documentation and verification record**

```powershell
git add README.md docs/project_status.md docs/architecture.md
git commit -m "docs: record verified demo workflow"
```

- [ ] **Step 6: Review the final diff**

Run:

```powershell
git status --short
git diff --check
git log -5 --oneline
```

Expected: clean worktree, no whitespace errors, and focused commits for the
contract, errors, UI, and documentation.
