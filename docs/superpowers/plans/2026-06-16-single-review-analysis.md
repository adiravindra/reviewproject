# Single Review Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a rule-based `/api/analyze/single` backend endpoint and Streamlit card display for analyzing one customer review.

**Architecture:** Add Pydantic request/response schemas, a focused single-review analysis service, and a thin FastAPI route. Update the dashboard API client and home page to use the new endpoint for typed reviews while preserving the existing saved analysis flows.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, Streamlit, unittest.

---

### Task 1: Backend Contract And Route

**Files:**
- Modify: `backend/app/schemas/reviews.py`
- Modify: `backend/app/routers/reviews.py`
- Modify: `backend/app/services/analysis.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write failing route tests**

Add tests that post to `/api/analyze/single`, assert the requested response keys, check urgency scoring and topics for urgent crash/login/payment wording, and assert empty text returns 422.

- [ ] **Step 2: Run tests to verify failure**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_api.ReviewInsightApiTests.test_api_analyze_single_returns_structured_review_result tests.test_api.ReviewInsightApiTests.test_api_analyze_single_rejects_empty_text`

Expected: failure because `/api/analyze/single` does not exist yet.

- [ ] **Step 3: Add schemas and service**

Add `SingleReviewStructuredAnalysis` with fields `text`, `sentiment`, `topics`, `urgency_score`, `urgency_label`, and `summary`. Add `analyze_single_review_text(text: str)` in `analysis.py` using keyword maps and the existing sentiment and summary helpers.

- [ ] **Step 4: Add thin route**

Add `@router.post("/api/analyze/single", response_model=SingleReviewStructuredAnalysis)` to `reviews.py`. Clean text with `_prepare_or_422([review.text])[0]`, then return `analyze_single_review_text(review_text)`.

- [ ] **Step 5: Run backend tests**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_api`

Expected: all API tests pass.

- [ ] **Step 6: Commit backend route**

Run: `git add backend/app/schemas/reviews.py backend/app/services/analysis.py backend/app/routers/reviews.py tests/test_api.py` then `git commit -m "feat: add single review analysis endpoint"`.

### Task 2: Dashboard Client Contract

**Files:**
- Modify: `dashboard/api_client.py`
- Test: `tests/test_dashboard_api_client.py`

- [ ] **Step 1: Write failing client test**

Add a test for `analyze_single_review_card` showing that it trims text and posts `{"text": "..."}` to `/api/analyze/single`.

- [ ] **Step 2: Run test to verify failure**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_api_client.DashboardApiClientTests.test_analyze_single_review_card_posts_to_api_analyze_single`

Expected: failure because the client function does not exist.

- [ ] **Step 3: Add client helper**

Add `analyze_single_review_card(review_text, api_base_url=DEFAULT_API_BASE_URL, post=requests.post)` that reuses `_clean_review_text`, posts to `/api/analyze/single`, and returns `_parse_response(response)`.

- [ ] **Step 4: Run client tests**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_api_client`

Expected: all dashboard API client tests pass.

- [ ] **Step 5: Commit client helper**

Run: `git add dashboard/api_client.py tests/test_dashboard_api_client.py` then `git commit -m "feat: add dashboard single analysis client"`.

### Task 3: Streamlit Result Card

**Files:**
- Modify: `dashboard/ui.py`
- Modify: `dashboard/streamlit_app.py`
- Test: `tests/test_dashboard_ui.py`

- [ ] **Step 1: Write failing UI helper test**

Add a test for `single_analysis_card_fields(result)` showing title-cased sentiment and urgency, comma-separated topics, formatted urgency score, and fallback topics text.

- [ ] **Step 2: Run test to verify failure**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_ui.DashboardUiTests.test_single_analysis_card_fields_formats_result`

Expected: failure because the UI helper does not exist.

- [ ] **Step 3: Add UI helper and renderer**

Add `single_analysis_card_fields(result)` and `render_single_analysis_card(result)` in `dashboard/ui.py`. The renderer should use existing `ri-panel` styling and Streamlit columns/metrics to show sentiment, topics, urgency label, urgency score, summary, and original text.

- [ ] **Step 4: Wire home page**

Update `dashboard/streamlit_app.py` so the typed review tab calls `analyze_single_review_card`, stores the result in `st.session_state["single_review_analysis"]`, and renders `render_single_analysis_card`.

- [ ] **Step 5: Run UI tests**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_dashboard_ui`

Expected: all dashboard UI tests pass.

- [ ] **Step 6: Commit frontend card**

Run: `git add dashboard/ui.py dashboard/streamlit_app.py tests/test_dashboard_ui.py` then `git commit -m "feat: show single review analysis card"`.

### Task 4: Full Verification

**Files:**
- Verify: all changed files

- [ ] **Step 1: Run full test suite**

Run: `.\.venv\Scripts\python.exe -m scripts.run_tests`

Expected: unit tests and py_compile checks pass.

- [ ] **Step 2: Review git status**

Run: `git status --short`

Expected: no uncommitted changes after final commit.
