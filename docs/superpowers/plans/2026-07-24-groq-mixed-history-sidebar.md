# Groq Mixed Sentiment and History Sidebar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent valid mixed-sentiment Google Maps reviews from causing a Groq 502 and make saved analysis history visible on initial dashboard load.

**Architecture:** Extend the shared sentiment contract so provider output, deterministic metrics, and dashboard evidence rendering agree on four sentiment values. Keep history persistence unchanged, but configure Streamlit to expand the existing sidebar and hydrate its entries once per session.

**Tech Stack:** Python 3.12, Pydantic 2, LangChain/Groq, FastAPI, Streamlit, unittest

## Global Constraints

- Preserve the existing positive-percentage calculation.
- Preserve safe API errors and never expose provider responses or credentials.
- Do not modify the user's existing Amazon adapter, fixture, or adapter-test changes.
- Use the existing local SQLite history store and existing sidebar controls.

---

### Task 1: Mixed sentiment contract and metrics

**Files:**
- Modify: `tests/test_service_mvp.py`
- Modify: `tests/test_analyzer_mvp.py`
- Modify: `backend/app/models.py`
- Modify: `backend/app/service.py`
- Modify: `backend/app/analyzer.py`

**Interfaces:**
- Consumes: `ReviewSentiment.sentiment` and `calculate_metrics(reviews, sentiments)`.
- Produces: a four-value `Sentiment` literal and `metrics.sentiment_counts` containing `mixed`.

- [ ] **Step 1: Write failing mixed-sentiment tests**

Add a service test that creates one `mixed` `ReviewSentiment`, expects
`{"positive": 1, "neutral": 0, "negative": 1, "mixed": 1}`, and keeps the
positive percentage at `33.3`. Add an analyzer contract test proving a valid
structured response containing `mixed` is accepted.

- [ ] **Step 2: Run the focused tests and verify failure**

Run:
`.\.venv\Scripts\python.exe -m unittest tests.test_service_mvp tests.test_analyzer_mvp`

Expected: failure because `mixed` is rejected by the current Pydantic literal.

- [ ] **Step 3: Implement the four-value contract**

Change `Sentiment` in `backend/app/models.py` to include `"mixed"`, initialize
the metrics counts with all four values in `backend/app/service.py`, and update
the analyzer prompt so meaningful positive and negative evidence may be
classified as mixed.

- [ ] **Step 4: Re-run the focused tests**

Run:
`.\.venv\Scripts\python.exe -m unittest tests.test_service_mvp tests.test_analyzer_mvp`

Expected: all focused tests pass.

### Task 2: Visible and hydrated History sidebar

**Files:**
- Modify: `tests/test_dashboard_mvp.py`
- Modify: `dashboard/streamlit_app.py`

**Interfaces:**
- Consumes: `_configure_page()`, `_render_history(base_url)`, and
  `st.session_state["history_items"]`.
- Produces: an initially expanded sidebar and one initial history request per
  Streamlit session.

- [ ] **Step 1: Write failing dashboard tests**

Assert that `_configure_page()` passes `initial_sidebar_state="expanded"`.
Assert that `_render_history()` calls `_load_history(base_url)` when
`history_items` has not been initialized, but does not re-fetch when the key is
already present.

- [ ] **Step 2: Run the focused dashboard tests and verify failure**

Run:
`.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_mvp`

Expected: failures for automatic sidebar state and initial history hydration.

- [ ] **Step 3: Implement sidebar visibility and hydration**

Set `initial_sidebar_state="expanded"` in `_configure_page()`. At the start of
`_render_history()`, call `_load_history(base_url)` only when `history_items` is
absent, preserving the refresh and load-report buttons.

- [ ] **Step 4: Re-run dashboard tests**

Run:
`.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_mvp`

Expected: all dashboard tests pass.

### Task 3: Full verification in tests and Chrome

**Files:**
- Modify only if verification reveals a regression.

**Interfaces:**
- Consumes: the FastAPI and Streamlit processes launched by `run_app.py`.
- Produces: a successful Google Maps analysis saved to SQLite and visible in
  the expanded History sidebar.

- [ ] **Step 1: Run the full automated suite**

Run:
`.\.venv\Scripts\python.exe -m unittest`

Expected: all tests pass.

- [ ] **Step 2: Start the application**

Run `.\.venv\Scripts\python.exe run_app.py` and wait for FastAPI port 8000 and
Streamlit port 8501.

- [ ] **Step 3: Verify with Google Chrome**

Open `http://127.0.0.1:8501`, confirm History is visible, import the cached
Google Maps source, click **Analyze with Groq**, and confirm the report renders
without a 502 and appears under saved analyses.

- [ ] **Step 4: Re-run the full suite after any verification adjustment**

Run:
`.\.venv\Scripts\python.exe -m unittest`

Expected: all tests pass with no unrelated working-tree changes.
